import importlib
import pkgutil
import inspect
import subprocess
import sys
import os
import json
import difflib
import urllib.request
import urllib.error
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import SentenceTransformer
import numpy as np


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
                return {
                    "status": "incompatible_python",
                    "package": base_name,
                    "requires_python": metadata["info"].get("requires_python")
                }
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
# HYBRID SEARCH ENGINE (TF-IDF + SEMANTIC)
# =====================================================

class HybridSearchEngine:
    def __init__(self, schema):
        self.schema = schema
        self.documents = []
        self.class_keys = []

        self._build_documents()

        # TF-IDF
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.tfidf_matrix = self.vectorizer.fit_transform(self.documents)

        # Semantic Model (Local, No API)
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.semantic_embeddings = self.model.encode(self.documents, show_progress_bar=True)

    def _build_documents(self):
        for class_path, class_data in self.schema.items():
            text = f"Class {class_path}\n{class_data.get('description', '')}\n"
            for m, d in class_data.get("methods", {}).items():
                text += f"Method {m} {d.get('signature')} {d.get('description')}\n"
            self.documents.append(text)
            self.class_keys.append(class_path)

    def search(self, query, top_k=5):
        # Step 1: TF-IDF shortlist
        query_vec = self.vectorizer.transform([query])
        scores = (self.tfidf_matrix @ query_vec.T).toarray().flatten()
        top_indices = scores.argsort()[::-1][:20]

        # Step 2: Semantic rerank
        query_embedding = self.model.encode([query])[0]

        candidate_embeddings = self.semantic_embeddings[top_indices]
        similarities = np.dot(candidate_embeddings, query_embedding)

        reranked = np.argsort(similarities)[::-1][:top_k]

        final_results = []
        for idx in reranked:
            real_index = top_indices[idx]
            class_path = self.class_keys[real_index]
            final_results.append({
                "class_path": class_path,
                "description": self.schema[class_path]["description"],
                "methods": self.schema[class_path]["methods"]
            })

        return final_results



class SDKGroundingEngine:
    def __init__(self):
        self.resolver = PackageResolver()
        self.schema_cache = {}
        self.search_cache = {}

    def load_package(self, package_name):
        resolution = self.resolver.resolve(package_name)
        if resolution["status"] != "valid":
            return resolution

        pkg = resolution["package"]

        if pkg not in self.schema_cache:
            extractor = SDKSchemaExtractor(pkg)
            schema = extractor.extract()
            self.schema_cache[pkg] = schema
            print(f"📦 Extracted {len(schema)} classes.")

        if pkg not in self.search_cache:
            self.search_cache[pkg] = HybridSearchEngine(self.schema_cache[pkg])

        return {"status": "success", "package": pkg}

    def search(self, package_name, query):
        return self.search_cache[package_name].search(query)