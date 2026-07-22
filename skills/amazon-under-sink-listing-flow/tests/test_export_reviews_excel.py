import importlib.util
import json
import math
import tempfile
import unittest
import zipfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "export_reviews_excel.py"


def load_exporter():
    if not SCRIPT.exists():
        raise AssertionError(f"Exporter script is missing: {SCRIPT}")
    spec = importlib.util.spec_from_file_location("export_reviews_excel", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReviewExportTests(unittest.TestCase):
    def test_parses_json_array_after_browseract_status_logs(self):
        exporter = load_exporter()
        text = "Start Task\n[12:00:00] Task Status: finished\n" + json.dumps([
            {"rating": 5, "review_title": "Works", "review_description": "Useful"}
        ])

        reviews = exporter.parse_review_log(text)

        self.assertEqual(1, len(reviews))
        self.assertEqual("Works", reviews[0]["review_title"])

    def test_ignores_unrelated_object_array_before_reviews(self):
        exporter = load_exporter()
        text = (
            json.dumps({"events": [{"status": "finished"}]})
            + "\n"
            + json.dumps([
                {"rating": 5, "review_title": "Works", "review_description": "Useful"}
            ])
        )

        reviews = exporter.parse_review_log(text)

        self.assertEqual("Works", reviews[0]["review_title"])

    def test_normalizes_title_aliases_and_preserves_original_fields(self):
        exporter = load_exporter()
        raw = {
            "commentator": "Reviewer",
            "rating": 4,
            "reviewTitle": "Easy setup",
            "review_description": "No tools needed.",
            "published_at": "July 1, 2026",
            "is_verified": True,
        }
        translated = {"title_zh": "安装简单", "description_zh": "无需工具。"}

        row = exporter.normalize_review(
            raw=raw,
            asin="B000000001",
            brand="Example",
            source_file="example.txt",
            source_index=1,
            translation=translated,
        )

        self.assertEqual("Easy setup", row["review_title_original"])
        self.assertEqual("安装简单", row["review_title_zh"])
        self.assertEqual("No tools needed.", row["review_description_original"])
        self.assertEqual("无需工具。", row["review_description_zh"])
        self.assertEqual("好评", row["sentiment_zh"])
        self.assertTrue(row["is_verified"])

    def test_classifies_rating_boundaries(self):
        exporter = load_exporter()

        self.assertEqual(("Positive", "好评"), exporter.classify_sentiment(5))
        self.assertEqual(("Positive", "好评"), exporter.classify_sentiment(4))
        self.assertEqual(("Neutral", "中评"), exporter.classify_sentiment(3))
        self.assertEqual(("Negative", "差评"), exporter.classify_sentiment(2))
        self.assertEqual(("Negative", "差评"), exporter.classify_sentiment(1))

    def test_rejects_non_finite_and_non_integral_ratings(self):
        exporter = load_exporter()

        with self.assertRaisesRegex(ValueError, "finite whole number"):
            exporter.classify_sentiment(math.nan)
        with self.assertRaisesRegex(ValueError, "finite whole number"):
            exporter.classify_sentiment(3.5)

    def test_parses_verified_purchase_strings(self):
        exporter = load_exporter()
        translated = {"title_zh": "", "description_zh": ""}

        false_row = exporter.normalize_review(
            raw={"rating": 5, "is_verified": "false"},
            asin="B000000001",
            brand="Example",
            source_file="example.txt",
            source_index=1,
            translation=translated,
        )
        true_row = exporter.normalize_review(
            raw={"rating": 5, "is_verified": "true"},
            asin="B000000001",
            brand="Example",
            source_file="example.txt",
            source_index=2,
            translation=translated,
        )

        self.assertFalse(false_row["is_verified"])
        self.assertTrue(true_row["is_verified"])

    def test_rejects_unknown_verified_purchase_value(self):
        exporter = load_exporter()

        with self.assertRaisesRegex(ValueError, "verified-purchase"):
            exporter.normalize_review(
                raw={"rating": 5, "is_verified": "sometimes"},
                asin="B000000001",
                brand="Example",
                source_file="example.txt",
                source_index=1,
                translation={"title_zh": "", "description_zh": ""},
            )

    def test_rejects_missing_translation(self):
        exporter = load_exporter()
        raw = {"rating": 3, "review_title": "Mixed", "review_description": "It is okay."}

        with self.assertRaisesRegex(ValueError, "Chinese translation"):
            exporter.normalize_review(
                raw=raw,
                asin="B000000001",
                brand="Example",
                source_file="example.txt",
                source_index=1,
                translation={"title_zh": "一般"},
            )

    def test_builds_summary_all_reviews_and_asin_sheets(self):
        exporter = load_exporter()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            raw_path = temp / "reviews.txt"
            raw_path.write_text(
                "Task Status: finished\n" + json.dumps([
                    {
                        "commentator": "A",
                        "rating": 5,
                        "review_title": "Great",
                        "review_description": "Very useful.",
                    },
                    {
                        "commentator": "B",
                        "rating": 2,
                        "reviewTitle": "Weak",
                        "review_description": "Moves around.",
                    },
                ]),
                encoding="utf-8",
            )
            manifest_path = temp / "manifest.json"
            manifest_path.write_text(json.dumps({
                "products": [{
                    "asin": "B000000001",
                    "brand": "Example",
                    "reviews_file": str(raw_path),
                    "translations": [
                        {"title_zh": "很好", "description_zh": "非常实用。"},
                        {"title_zh": "不稳", "description_zh": "会移动。"},
                    ],
                }]
            }), encoding="utf-8")
            output_path = temp / "reviews.xlsx"

            exporter.export_manifest(manifest_path, output_path)

            self.assertTrue(output_path.exists())
            with zipfile.ZipFile(output_path) as workbook:
                names = set(workbook.namelist())
                self.assertIn("xl/worksheets/sheet1.xml", names)
                self.assertIn("xl/worksheets/sheet2.xml", names)
                self.assertIn("xl/worksheets/sheet3.xml", names)
                workbook_xml = workbook.read("xl/workbook.xml").decode("utf-8")
                all_reviews_xml = workbook.read("xl/worksheets/sheet2.xml").decode("utf-8")
                self.assertIn('name="Summary"', workbook_xml)
                self.assertIn('name="All Reviews"', workbook_xml)
                self.assertIn('name="B000000001"', workbook_xml)
                self.assertIn("很好", all_reviews_xml)
                self.assertIn("差评", all_reviews_xml)

    def test_manifest_uses_source_filename_not_absolute_path(self):
        exporter = load_exporter()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            raw_path = temp / "reviews.txt"
            raw_path.write_text(json.dumps([
                {"rating": 5, "review_title": "Great", "review_description": "Useful"}
            ]), encoding="utf-8")
            manifest_path = temp / "manifest.json"
            manifest_path.write_text(json.dumps({
                "products": [{
                    "asin": "B000000001",
                    "brand": "Example",
                    "reviews_file": str(raw_path),
                    "translations": [{"title_zh": "很好", "description_zh": "实用"}],
                }]
            }), encoding="utf-8")

            rows = exporter.load_manifest(manifest_path)

            self.assertEqual("reviews.txt", rows[0]["source_file"])


if __name__ == "__main__":
    unittest.main()
