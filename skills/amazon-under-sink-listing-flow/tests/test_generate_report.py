import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "generate_report.py"


def load_renderer():
    if not SCRIPT.exists():
        raise AssertionError(f"Report renderer is missing: {SCRIPT}")
    spec = importlib.util.spec_from_file_location("generate_report", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReportRendererTests(unittest.TestCase):
    def test_requires_non_empty_title(self):
        renderer = load_renderer()

        with self.assertRaisesRegex(ValueError, "title"):
            renderer.render_html({"sections": []})

    def test_escapes_all_report_content(self):
        renderer = load_renderer()
        html = renderer.render_html({
            "title": "<script>alert(1)</script>",
            "source": "reviews & listing",
            "summary": [{"label": "<b>Total</b>", "value": "3"}],
            "sections": [{"title": "Notes", "type": "text", "content": "A < B & C"}],
            "notes": ["Do not render <img src=x onerror=alert(1)>"],
        })

        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertIn("A &lt; B &amp; C", html)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertNotIn("<img src=x", html)

    def test_limits_table_rows_and_bar_items(self):
        renderer = load_renderer()
        html = renderer.render_html({
            "title": "Limits",
            "sections": [
                {
                    "title": "Rows",
                    "type": "table",
                    "columns": ["Value"],
                    "rows": [[f"row-{index}"] for index in range(205)],
                },
                {
                    "title": "Bars",
                    "type": "bars",
                    "items": [{"label": f"bar-{index}", "value": index + 1} for index in range(25)],
                },
            ],
        })

        self.assertIn("row-199", html)
        self.assertNotIn("row-200", html)
        self.assertIn("bar-19", html)
        self.assertNotIn("bar-20", html)

    def test_renders_plain_language_basis_for_sections(self):
        renderer = load_renderer()
        html = renderer.render_html({
            "title": "Basis",
            "sections": [
                {
                    "title": "核心发现",
                    "type": "insights",
                    "items": ["安装反馈较多"],
                    "basis": ["依据 18 条评论样本。", "用户多次提到 easy to install <fast>。"],
                }
            ],
        })

        self.assertIn("判断依据", html)
        self.assertIn("依据 18 条评论样本。", html)
        self.assertIn("easy to install &lt;fast&gt;", html)

    def test_renders_recommended_qa_sections(self):
        renderer = load_renderer()
        html = renderer.render_html({
            "title": "QA",
            "sections": [
                {
                    "title": "推荐 QA",
                    "type": "qa",
                    "items": [
                        {
                            "question": "Will it fit under a sink with pipes?",
                            "answer": "Measure your cabinet and pipe space first.",
                            "basis": "Competitor reviews often mention pipe clearance.",
                            "keywords": ["under sink organizer", "pull out drawer"],
                            "scenario": "Kitchen and bathroom cabinets",
                            "priority": "Medium <check>",
                        }
                    ],
                }
            ],
        })

        self.assertIn("Will it fit under a sink with pipes?", html)
        self.assertIn("Measure your cabinet and pipe space first.", html)
        self.assertIn("under sink organizer, pull out drawer", html)
        self.assertIn("Medium &lt;check&gt;", html)

    def test_limits_qa_items(self):
        renderer = load_renderer()
        html = renderer.render_html({
            "title": "QA Limits",
            "sections": [
                {
                    "title": "QA",
                    "type": "qa",
                    "items": [{"question": f"q-{index}", "answer": "a"} for index in range(55)],
                }
            ],
        })

        self.assertIn("q-49", html)
        self.assertNotIn("q-50", html)

    def test_generates_standalone_utf8_file(self):
        renderer = load_renderer()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            input_path = temp / "report.json"
            output_path = temp / "report.html"
            input_path.write_text(json.dumps({
                "title": "下水槽收纳架报告",
                "sections": [{"title": "Listing", "type": "text", "content": "Ready"}],
            }, ensure_ascii=False), encoding="utf-8")

            result = renderer.generate_report(input_path, output_path)

            html = output_path.read_text(encoding="utf-8")
            self.assertEqual(output_path.resolve(), result)
            self.assertIn("<!doctype html>", html.lower())
            self.assertIn("下水槽收纳架报告", html)
            self.assertNotIn("<script", html.lower())
            self.assertNotIn("https://", html.lower())


if __name__ == "__main__":
    unittest.main()
