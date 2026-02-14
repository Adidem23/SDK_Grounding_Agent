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
from importlib.metadata import distribution, PackageNotFoundError
from packaging.specifiers import SpecifierSet
from packaging.version import Version


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

            return {
                "status": "valid",
                "package": base_name
            }

        suggestions = self._suggest_package(base_name)

        if suggestions:
            best_match = suggestions[0]
            similarity = difflib.SequenceMatcher(None, base_name, best_match).ratio()

            if similarity >= self.auto_correct_threshold:
                return {
                    "status": "auto_corrected",
                    "package": best_match,
                    "original_input": base_name,
                    "similarity": similarity
                }

            return {
                "status": "invalid",
                "input": base_name,
                "suggestions": suggestions
            }

        return {
            "status": "invalid",
            "input": base_name,
            "suggestions": []
        }

    def _get_package_metadata(self, package_name: str):
        try:
            with urllib.request.urlopen(self.PYPI_JSON_URL.format(package_name)) as response:
                return json.load(response)
        except urllib.error.HTTPError:
            return None

    def _is_python_compatible(self, metadata) -> bool:
        requires_python = metadata["info"].get("requires_python")

        if not requires_python:
            return True

        spec = SpecifierSet(requires_python)
        current_version = Version(
            f"{sys.version_info.major}.{sys.version_info.minor}"
        )

        return current_version in spec

    def _suggest_package(self, input_name: str, n: int = 3):
        return difflib.get_close_matches(
            input_name,
            self.package_list,
            n=n,
            cutoff=0.75
        )

    def _load_or_fetch_package_list(self):
        if os.path.exists(self.CACHE_FILE):
            with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)

        response = urllib.request.urlopen(self.PYPI_SIMPLE_URL)
        html = response.read().decode("utf-8")

        package_names = []
        for line in html.splitlines():
            if "<a href=" in line:
                name = line.split(">")[1].split("<")[0]
                package_names.append(name.lower())

        with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(package_names, f)

        return package_names


# =====================================================
# SDK SCHEMA EXTRACTOR
# =====================================================

class SDKSchemaExtractor:
    def __init__(self, package_name: str):
        self.package_name = package_name
        self.base_package = package_name.split("==")[0]

    @staticmethod
    def _clean_doc(doc):
        return inspect.cleandoc(doc) if doc else None

    def _install_package(self):
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", self.package_name],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError:
            raise RuntimeError(f"Failed to install package '{self.package_name}'")

    def _resolve_import_names(self):
        """
        Robust import detection by scanning installed distribution files.
        Works for hyphenated and namespace packages.
        """
        try:
            dist = distribution(self.base_package)
            candidates = set()

            for file in dist.files:
                parts = str(file).split("/")
                if parts:
                    top = parts[0]
                    if (
                        "." not in top and
                        not top.endswith(".dist-info") and
                        not top.endswith(".data")
                    ):
                        candidates.add(top)

            return list(candidates)

        except PackageNotFoundError:
            return []

    def _import_package(self):
        try:
            return importlib.import_module(self.base_package)
        except ImportError:
            self._install_package()

        import_names = self._resolve_import_names()

        for name in import_names:
            try:
                return importlib.import_module(name)
            except ImportError:
                continue

        raise ImportError(
            f"Could not import package '{self.package_name}'. "
            f"Tried candidates: {import_names}"
        )

    def _extract_from_module(self, module, schema):
        module_name = module.__name__

        public_members = (
            module.__all__ if hasattr(module, "__all__")
            else [n for n in dir(module) if not n.startswith("_")]
        )

        for name in public_members:
            try:
                obj = getattr(module, name)
            except Exception:
                continue

            if inspect.isclass(obj):
                class_info = {
                    "type": "class",
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

            elif inspect.isfunction(obj):
                try:
                    schema[f"{module_name}.{name}"] = {
                        "type": "function",
                        "module": module_name,
                        "signature": str(inspect.signature(obj)),
                        "description": self._clean_doc(obj.__doc__)
                    }
                except:
                    continue

    def extract(self):
        schema = {}

        root_module = self._import_package()
        self._extract_from_module(root_module, schema)

        if hasattr(root_module, "__path__"):
            for _, modname, _ in pkgutil.walk_packages(
                root_module.__path__, root_module.__name__ + "."
            ):
                try:
                    module = importlib.import_module(modname)
                    self._extract_from_module(module, schema)
                except:
                    continue

        return schema


# =====================================================
# UNIFIED GROUNDING ENGINE
# =====================================================

class SDKGroundingEngine:
    def __init__(self):
        self.resolver = PackageResolver()

    def process(self, package_input: str):
        resolution = self.resolver.resolve(package_input)

        if resolution["status"] in ["invalid", "incompatible_python"]:
            return {
                "status": "error",
                "details": resolution
            }

        package_name = resolution["package"]

        try:
            extractor = SDKSchemaExtractor(package_name)
            schema = extractor.extract()
        except Exception as e:
            return {
                "status": "installation_failed",
                "package": package_name,
                "error": str(e)
            }

        return {
            "status": "success",
            "package": package_name,
            "schema": schema
        }