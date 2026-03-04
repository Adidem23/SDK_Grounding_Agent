import re
import requests
from bs4 import BeautifulSoup
from rapidfuzz import process


class PyPIPackageExtractor:
    SIMPLE_INDEX_URL = "https://pypi.org/simple/"

    def __init__(self, enable_fuzzy=True, fuzzy_threshold=90):
        self.enable_fuzzy = enable_fuzzy
        self.fuzzy_threshold = fuzzy_threshold
        self.package_set = set()
        self.package_list = []
        self._load_packages()

    # -------------------------------------------------
    # Load all package names from PyPI (once at startup)
    # -------------------------------------------------
    def _load_packages(self):
        print("Downloading PyPI package list...")
        response = requests.get(self.SIMPLE_INDEX_URL, timeout=60)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        packages = [a.text.strip() for a in soup.find_all("a")]

        normalized = [self._normalize(p) for p in packages]

        self.package_list = normalized
        self.package_set = set(normalized)

        print(f"Loaded {len(self.package_set)} packages.")

    # -------------------------------------------------
    # Normalize according to PyPI rules
    # -------------------------------------------------
    @staticmethod
    def _normalize(name: str) -> str:
        return re.sub(r"[-_.]+", "-", name).lower()

    # -------------------------------------------------
    # Extract possible tokens from user query
    # -------------------------------------------------
    @staticmethod
    def _extract_candidates(text: str):
        pattern = r"\b[a-zA-Z0-9][a-zA-Z0-9._-]*\b"
        return re.findall(pattern, text)

    # -------------------------------------------------
    # Main extraction logic
    # -------------------------------------------------
    def extract_packages(self, query: str):
        candidates = self._extract_candidates(query)
        results = []

        for token in candidates:
            normalized = self._normalize(token)

            # 1️⃣ Exact Match
            if normalized in self.package_set:
                results.append({
                    "input": token,
                    "matched_name": normalized,
                    "status": "VALID",
                    "confidence": 100
                })
                continue

            # 2️⃣ Fuzzy Match (Optional)
            if self.enable_fuzzy:
                match = process.extractOne(
                    normalized,
                    self.package_list,
                    score_cutoff=self.fuzzy_threshold
                )

                if match:
                    results.append({
                        "input": token,
                        "matched_name": match[0],
                        "status": "CORRECTED",
                        "confidence": match[1]
                    })

        return results


# -------------------------------------------------
# Example Usage
# -------------------------------------------------
if __name__ == "__main__":

    extractor = PyPIPackageExtractor(enable_fuzzy=True)

    test_queries = [
       """When building modern data-driven applications, developers often need to interact with external services, process structured information, and ensure smooth communication between systems. A common approach involves designing clean APIs, handling authentication securely, and managing network calls efficiently so that applications remain scalable and maintainable over time. In many real-world scenarios, engineers rely on lightweight tools to simplify HTTP communication—sometimes leveraging powerful libraries like **requests**—to reduce boilerplate code and improve readability, allowing them to focus more on business logic rather than low-level networking details such as session handling, headers, and retries"""

    ]

    for query in test_queries:
        print("\nQuery:", query)
        extracted = extractor.extract_packages(query)
        print("Detected Packages:", extracted)
