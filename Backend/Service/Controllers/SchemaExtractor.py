import importlib
import importlib.metadata
import pkgutil
import inspect
import subprocess
import sys
import os
import json
import difflib
import pickle
import urllib.request
import re
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from rank_bm25 import BM25Okapi


# =====================================================
# CONFIG
# =====================================================

CACHE_DIR = "sdk_cache"
os.makedirs(CACHE_DIR, exist_ok=True)


# =====================================================
# TOKENIZER
# =====================================================

def tokenize(text: str):
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())

    final = []
    for token in tokens:
        final.extend(token.split("_"))

    return [t for t in final if t]


# =====================================================
# PACKAGE RESOLVER
# =====================================================

class PackageResolver:

    PYPI_JSON_URL = "https://pypi.org/pypi/{}/json"
    PYPI_SIMPLE_URL = "https://pypi.org/simple/"
    CACHE_FILE = "pypi_package_cache.json"

    def __init__(self, auto_correct_threshold=0.90):
        self.auto_correct_threshold = auto_correct_threshold
        self.package_list = self._load_or_fetch_package_list()

    def resolve(self, package_name: str):

        base = package_name.split("==")[0].lower()
        metadata = self._get_package_metadata(base)

        if metadata:

            if not self._is_python_compatible(metadata):
                return {"status": "incompatible_python", "package": base}

            return {"status": "valid", "package": base}

        suggestions = difflib.get_close_matches(
            base,
            self.package_list,
            n=3,
            cutoff=0.75
        )

        if suggestions:
            best = suggestions[0]

            similarity = difflib.SequenceMatcher(
                None,
                base,
                best
            ).ratio()

            if similarity >= self.auto_correct_threshold:
                return {"status": "auto_corrected", "package": best}

        return {"status": "invalid", "input": base}

    def _get_package_metadata(self, package_name):

        try:
            with urllib.request.urlopen(
                self.PYPI_JSON_URL.format(package_name)
            ) as response:
                return json.load(response)
        except:
            return None

    def _is_python_compatible(self, metadata):

        requires_python = metadata["info"].get("requires_python")

        if not requires_python:
            return True

        spec = SpecifierSet(requires_python)

        current = Version(
            f"{sys.version_info.major}.{sys.version_info.minor}"
        )

        return current in spec

    def _load_or_fetch_package_list(self):

        if os.path.exists(self.CACHE_FILE):
            with open(self.CACHE_FILE, "r") as f:
                return json.load(f)

        response = urllib.request.urlopen(self.PYPI_SIMPLE_URL)
        html = response.read().decode("utf-8")

        names = []

        for line in html.splitlines():
            if "<a href=" in line:
                name = line.split(">")[1].split("<")[0]
                names.append(name.lower())

        with open(self.CACHE_FILE, "w") as f:
            json.dump(names, f)

        return names


# =====================================================
# SDK SCHEMA EXTRACTOR
# =====================================================

class SDKSchemaExtractor:

    def __init__(self, package_name: str):
        self.package_name = package_name

    @staticmethod
    def _clean_doc(doc):
        return inspect.cleandoc(doc) if doc else ""

    def _install_package(self):

        subprocess.run(
            [sys.executable, "-m", "pip", "install", self.package_name],
            check=True
        )

    def _get_import_modules(self):

        try:
            dist = importlib.metadata.distribution(self.package_name)

        except:

            self._install_package()
            dist = importlib.metadata.distribution(self.package_name)

        top_level = dist.read_text("top_level.txt")

        if not top_level:
            return [self.package_name.replace("-", "_")]

        return [line.strip() for line in top_level.splitlines() if line.strip()]

    def extract(self):

        schema = {}

        modules = self._get_import_modules()

        for module_name in modules:

            try:
                root_module = importlib.import_module(module_name)
            except:
                continue

            self._extract_from_module(root_module, schema)

            if hasattr(root_module, "__path__"):

                for _, modname, _ in pkgutil.walk_packages(
                        root_module.__path__,
                        root_module.__name__ + "."
                ):

                    try:
                        module = importlib.import_module(modname)
                        self._extract_from_module(module, schema)
                    except:
                        continue

        return schema

    def _extract_from_module(self, module, schema):

        module_name = module.__name__

        for name in dir(module):

            if name.startswith("_"):
                continue

            try:
                obj = getattr(module, name)
            except:
                continue

            # -------------------------
            # CLASS
            # -------------------------

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

            # -------------------------
            # FUNCTION
            # -------------------------

            elif inspect.isfunction(obj):

                func_info = {
                    "module": module_name,
                    "description": self._clean_doc(obj.__doc__),
                    "signature": ""
                }

                try:
                    func_info["signature"] = str(inspect.signature(obj))
                except:
                    pass

                schema[f"{module_name}.{name}"] = {
                    "module": module_name,
                    "description": func_info["description"],
                    "methods": {
                        name: {
                            "signature": func_info["signature"],
                            "description": func_info["description"]
                        }
                    }
                }


# =====================================================
# BM25 SEARCH ENGINE
# =====================================================

class BM25SearchEngine:

    def __init__(self, schema):

        self.schema = schema
        self.documents = []
        self.metadata = []

        self._build_documents()

        print("🔧 Building BM25 index...")
        self.bm25 = BM25Okapi(self.documents)
        print("✅ BM25 index ready.")

    def _build_documents(self):

        for class_path, class_data in self.schema.items():

            class_desc = class_data.get("description") or ""

            for method_name, method_data in class_data.get("methods", {}).items():

                signature = method_data.get("signature") or ""
                description = method_data.get("description") or ""

                boosted_method = " ".join([method_name] * 3)

                text = f"""
                class {class_path}
                class_description {class_desc}
                method {boosted_method}
                signature {signature}
                description {description}
                """

                tokens = tokenize(text)

                self.documents.append(tokens)

                self.metadata.append({
                    "class_path": class_path,
                    "method_name": method_name
                })

    def search(self, query, top_k=5):

        query_tokens = tokenize(query)

        scores = self.bm25.get_scores(query_tokens)

        ranked = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:top_k]

        results = []

        for idx in ranked:

            if scores[idx] <= 0:
                continue

            meta = self.metadata[idx]

            class_path = meta["class_path"]
            method_name = meta["method_name"]

            method_data = self.schema[class_path]["methods"].get(method_name, {})

            results.append({
                "class_path": class_path,
                "method_name": method_name,
                "signature": method_data.get("signature"),
                "description": method_data.get("description"),
                "score": float(scores[idx])
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

    def _get_cache_paths(self, pkg):

        pkg_dir = os.path.join(CACHE_DIR, pkg)
        os.makedirs(pkg_dir, exist_ok=True)

        return {
            "schema": os.path.join(pkg_dir, "schema.json"),
            "index": os.path.join(pkg_dir, "bm25_index.pkl")
        }

    def load_package(self, package_name):

        resolution = self.resolver.resolve(package_name)

        if resolution["status"] != "valid":
            return resolution

        pkg = resolution["package"]

        paths = self._get_cache_paths(pkg)

        # ------------------------
        # LOAD SCHEMA
        # ------------------------

        if os.path.exists(paths["schema"]):

            with open(paths["schema"], "r") as f:
                schema = json.load(f)

            print("📂 Loaded schema from cache.")

        else:

            extractor = SDKSchemaExtractor(pkg)

            schema = extractor.extract()

            with open(paths["schema"], "w") as f:
                json.dump(schema, f)

            print(f"📦 Extracted {len(schema)} classes/functions.")

        self.schema_cache[pkg] = schema

        # ------------------------
        # LOAD SEARCH INDEX
        # ------------------------

        if os.path.exists(paths["index"]):

            with open(paths["index"], "rb") as f:
                search_engine = pickle.load(f)

            print("📂 Loaded BM25 index from cache.")

        else:

            search_engine = BM25SearchEngine(schema)

            with open(paths["index"], "wb") as f:
                pickle.dump(search_engine, f)

            print("💾 BM25 index cached.")

        self.search_cache[pkg] = search_engine

        return {"status": "success", "package": pkg}

    def search(self, package_name, query):

        return self.search_cache[package_name].search(query)