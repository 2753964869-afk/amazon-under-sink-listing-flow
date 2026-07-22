import importlib.util
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "collect_amazon_reviews.py"


def load_collector():
    spec = importlib.util.spec_from_file_location("collect_amazon_reviews", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CollectAmazonReviewsTests(unittest.TestCase):
    def test_records_source_error_and_continues_other_asins(self):
        collector = load_collector()

        def fetch(asin, filter_val, sort_val):
            if asin == "B0B3JJYJSS":
                raise TimeoutError("source timed out")
            return [{"Author": "Buyer", "Title": "Useful", "Text": "Works", "OverallRating": 4}]

        result = collector.collect_reviews(["B0B3JJYJSS", "B0DNTQ2YNT"], total_limit=1, mode="basic", fetch_fn=fetch)

        self.assertEqual(1, result["actual_total"])
        self.assertEqual("source timed out", result["collection_attempts"][0]["error"])
        self.assertEqual("B0DNTQ2YNT", result["reviews"][0]["asin"])

    def test_decodes_html_entities_without_cross_asin_deduplication(self):
        collector = load_collector()

        def fetch(asin, filter_val, sort_val):
            return [{"Author": "A&amp;B", "Title": "Fits &#39;well&#39;", "Text": "Pipe &amp; shelf", "OverallRating": 5}]

        result = collector.collect_reviews(["B0B3JJYJSS", "B0DNTQ2YNT"], total_limit=2, mode="basic", fetch_fn=fetch)

        self.assertEqual(2, result["actual_total"])
        self.assertEqual(["B0B3JJYJSS", "B0DNTQ2YNT"], [item["asin"] for item in result["reviews"]])
        self.assertEqual("A&B", result["reviews"][0]["Author"])
        self.assertEqual("Fits 'well'", result["reviews"][0]["Title"])
        self.assertEqual("Pipe & shelf", result["reviews"][0]["Text"])

    def test_full_mode_requests_each_star_once_per_asin(self):
        collector = load_collector()
        calls = []

        def fetch(asin, filter_val, sort_val):
            calls.append((asin, filter_val, sort_val))
            return []

        result = collector.collect_reviews(["B0B3JJYJSS", "B0DNTQ2YNT"], total_limit=10, mode="full", fetch_fn=fetch)

        self.assertEqual(0, result["actual_total"])
        self.assertEqual(
            [
                ("B0B3JJYJSS", 5, 0), ("B0DNTQ2YNT", 5, 0),
                ("B0B3JJYJSS", 4, 0), ("B0DNTQ2YNT", 4, 0),
                ("B0B3JJYJSS", 3, 0), ("B0DNTQ2YNT", 3, 0),
                ("B0B3JJYJSS", 2, 0), ("B0DNTQ2YNT", 2, 0),
                ("B0B3JJYJSS", 1, 0), ("B0DNTQ2YNT", 1, 0),
            ],
            calls,
        )


if __name__ == "__main__":
    unittest.main()
