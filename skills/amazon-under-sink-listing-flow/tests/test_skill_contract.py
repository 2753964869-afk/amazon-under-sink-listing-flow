import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def test_standard_workflow_requires_no_amazon_login_or_rufus(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("Do not require an Amazon login.", text)
        self.assertNotIn("amazon-alexa-qa", text)
        self.assertNotIn("Rufus", text)
        self.assertNotIn("Alexa", text)

    def test_skill_is_self_contained_and_references_portable_scripts(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("No other skill is required", text)
        for script_name in (
            "preflight.py",
            "collect_amazon_reviews.py",
            "run_browseract_reviews.py",
            "export_reviews_excel.py",
            "generate_report.py",
        ):
            self.assertIn(script_name, text)
            self.assertTrue((SKILL_DIR / "scripts" / script_name).exists())
        self.assertNotIn("run-browseract-reviews.ps1", text)
        self.assertNotIn("data-analysis-preview", text)
        self.assertNotIn("amazon-listing-optimization", text)

    def test_free_review_collector_and_license_are_bundled(self):
        collector = SKILL_DIR / "scripts" / "collect_amazon_reviews.py"
        license_file = SKILL_DIR / "LICENSES" / "amazon-review-scraper-MIT.txt"

        self.assertTrue(collector.exists())
        self.assertTrue(license_file.exists())
        self.assertIn("MIT License", license_file.read_text(encoding="utf-8"))

    def test_runtime_references_and_agent_prompt_match_contract(self):
        runtime = SKILL_DIR / "references" / "runtime-requirements.md"
        report_schema = SKILL_DIR / "references" / "report-schema.md"
        prompt = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")

        self.assertTrue(runtime.exists())
        self.assertTrue(report_schema.exists())
        self.assertIn("without an Amazon login", prompt)
        self.assertNotIn("Rufus", prompt)

    def test_optional_provider_routing_is_documented_without_xiyou(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        routing_path = SKILL_DIR / "references" / "data-source-routing.md"

        self.assertTrue(routing_path.exists())
        routing = routing_path.read_text(encoding="utf-8")
        for source in ("free-public", "BrowserAct", "sellersprite-competitors", "sellersprite-keywords", "sellersprite-aba"):
            self.assertIn(source, routing)
        self.assertIn("data-source-routing.md", skill)
        self.assertNotIn("Xiyou", skill + routing)
        self.assertNotIn("西柚", skill + routing)


if __name__ == "__main__":
    unittest.main()
