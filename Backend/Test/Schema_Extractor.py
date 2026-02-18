import importlib
import pkgutil
import inspect
import subprocess
import sys
import os
import json
import difflib
import pickle
import urllib.request
import urllib.error
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from sklearn.feature_extraction.text import TfidfVectorizer


# =====================================================
# CONFIG
# =====================================================

CACHE_DIR = "sdk_cache"
os.makedirs(CACHE_DIR, exist_ok=True)


# =====================================================
# PACKAGE RESOLVER
# =====================================================

class PackageResolver:
    PYPI_JSON_URL = "https://pypi.org/pypi/{}/json"
    PYPI_SIMPLE_URL = "https://pypi.org/simple/"
    CACHE_FILE = "pypi_package_cache.json"

    def __init__(self, auto_correct_threshold: float = 0.90):
        self.auto_correct_threshold = auto_correct_threshold
        self.package_list = self._load_or_fetch_package_list()

    def resolve(self, package_name: str) -> dict:
        base_name = package_name.split("==")[0].lower()
        metadata = self._get_package_metadata(base_name)

        if metadata:
            if not self._is_python_compatible(metadata):
                return {"status": "incompatible_python", "package": base_name}
            return {"status": "valid", "package": base_name}

        suggestions = difflib.get_close_matches(base_name, self.package_list, n=3, cutoff=0.75)

        if suggestions:
            best_match = suggestions[0]
            similarity = difflib.SequenceMatcher(None, base_name, best_match).ratio()
            if similarity >= self.auto_correct_threshold:
                return {"status": "auto_corrected", "package": best_match}

        return {"status": "invalid", "input": base_name}

    def _get_package_metadata(self, package_name: str):
        try:
            with urllib.request.urlopen(self.PYPI_JSON_URL.format(package_name)) as response:
                return json.load(response)
        except:
            return None

    def _is_python_compatible(self, metadata) -> bool:
        requires_python = metadata["info"].get("requires_python")
        if not requires_python:
            return True
        spec = SpecifierSet(requires_python)
        current_version = Version(f"{sys.version_info.major}.{sys.version_info.minor}")
        return current_version in spec

    def _load_or_fetch_package_list(self):
        if os.path.exists(self.CACHE_FILE):
            with open(self.CACHE_FILE, "r") as f:
                return json.load(f)

        response = urllib.request.urlopen(self.PYPI_SIMPLE_URL)
        html = response.read().decode("utf-8")

        package_names = []
        for line in html.splitlines():
            if "<a href=" in line:
                name = line.split(">")[1].split("<")[0]
                package_names.append(name.lower())

        with open(self.CACHE_FILE, "w") as f:
            json.dump(package_names, f)

        return package_names


# =====================================================
# SDK EXTRACTOR
# =====================================================

class SDKSchemaExtractor:
    def __init__(self, package_name: str):
        self.package_name = package_name

    @staticmethod
    def _clean_doc(doc):
        return inspect.cleandoc(doc) if doc else ""

    def _install_package(self):
        subprocess.run([sys.executable, "-m", "pip", "install", self.package_name], check=True)

    def _import_package(self):
        try:
            return importlib.import_module(self.package_name)
        except ImportError:
            self._install_package()
            return importlib.import_module(self.package_name)

    def extract(self):
        schema = {}
        root_module = self._import_package()

        def extract_from_module(module):
            module_name = module.__name__

            for name in dir(module):
                if name.startswith("_"):
                    continue

                try:
                    obj = getattr(module, name)
                except:
                    continue

                if inspect.isclass(obj):
                    class_info = {
                        "module": module_name,
                        "description": self._clean_doc(obj.__doc__),
                        "methods": {}
                    }

                    for method_name, method_obj in inspect.getmembers(obj):
                        if method_name.startswith("_"):
                            continue
                        if inspect.isfunction(method_obj) or inspect.ismethod(method_obj):
                            try:
                                class_info["methods"][method_name] = {
                                    "signature": str(inspect.signature(method_obj)),
                                    "description": self._clean_doc(method_obj.__doc__)
                                }
                            except:
                                continue

                    schema[f"{module_name}.{name}"] = class_info

        extract_from_module(root_module)

        if hasattr(root_module, "__path__"):
            for _, modname, _ in pkgutil.walk_packages(root_module.__path__, root_module.__name__ + "."):
                try:
                    module = importlib.import_module(modname)
                    extract_from_module(module)
                except:
                    continue

        return schema


# =====================================================
# LIGHTWEIGHT SEARCH ENGINE
# =====================================================

class LightweightSearchEngine:
    def __init__(self, schema):
        self.schema = schema
        self.documents = []
        self.class_keys = []

        self._build_documents()

        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=10000
        )

        print("🔧 Building TF-IDF index...")
        self.tfidf_matrix = self.vectorizer.fit_transform(self.documents)
        print("✅ Index ready.")

    def _build_documents(self):
        for class_path, class_data in self.schema.items():

            class_name = class_path.split(".")[-1]
            description = (class_data.get("description") or "")[:400]
            method_names = " ".join(class_data.get("methods", {}).keys())

            text = f"""
            Class {class_name}
            Description {description}
            Methods {method_names}
            """

            self.documents.append(text)
            self.class_keys.append(class_path)

    def search(self, query, top_k=3):

        query_vec = self.vectorizer.transform([query])
        scores = (self.tfidf_matrix @ query_vec.T).toarray().flatten()

        top_indices = scores.argsort()[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] <= 0:
                continue

            class_path = self.class_keys[idx]

            results.append({
                "class_path": class_path,
                "description": self.schema[class_path]["description"],
                "methods": self.schema[class_path]["methods"]
            })

        return results


# =====================================================
# GROUNDING ENGINE
# =====================================================

class SDKGroundingEngine:
    def __init__(self):
        self.resolver = PackageResolver()
        self.schema_cache = {}
        self.search_cache = {}

    def _get_package_cache_paths(self, pkg):
        pkg_dir = os.path.join(CACHE_DIR, pkg)
        os.makedirs(pkg_dir, exist_ok=True)
        return {
            "schema": os.path.join(pkg_dir, "schema.json"),
            "index": os.path.join(pkg_dir, "index.pkl")
        }

    def load_package(self, package_name):

        resolution = self.resolver.resolve(package_name)
        if resolution["status"] != "valid":
            return resolution

        pkg = resolution["package"]
        paths = self._get_package_cache_paths(pkg)

        # Load schema from disk if exists
        if os.path.exists(paths["schema"]):
            with open(paths["schema"], "r") as f:
                schema = json.load(f)
            print("📂 Loaded schema from cache.")
        else:
            extractor = SDKSchemaExtractor(pkg)
            schema = extractor.extract()
            with open(paths["schema"], "w") as f:
                json.dump(schema, f)
            print(f"📦 Extracted {len(schema)} classes and cached.")

        self.schema_cache[pkg] = schema

        # Load index if exists
        if os.path.exists(paths["index"]):
            with open(paths["index"], "rb") as f:
                search_engine = pickle.load(f)
            print("📂 Loaded search index from cache.")
        else:
            search_engine = LightweightSearchEngine(schema)
            with open(paths["index"], "wb") as f:
                pickle.dump(search_engine, f)
            print("💾 Search index cached.")

        self.search_cache[pkg] = search_engine

        return {"status": "success", "package": pkg}

    def search(self, package_name, query):
        return self.search_cache[package_name].search(query)