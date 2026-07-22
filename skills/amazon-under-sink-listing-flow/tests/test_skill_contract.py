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
            "run_browseract_reviews.py",
            "export_reviews_excel.py",
            "generate_report.py",
        ):
            self.assertIn(script_name, text)
            self.assertTrue((SKILL_DIR / "scripts" / script_name).exists())
        self.assertNotIn("run-browseract-reviews.ps1", text)
        self.assertNotIn("data-analysis-preview", text)
        self.assertNotIn("amazon-listing-optimization", text)

    def test_runtime_references_and_agent_prompt_match_contract(self):
        runtime = SKILL_DIR / "references" / "runtime-requirements.md"
        report_schema = SKILL_DIR / "references" / "report-schema.md"
        prompt = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")

        self.assertTrue(runtime.exists())
        self.assertTrue(report_schema.exists())
        self.assertIn("without an Amazon login", prompt)
        self.assertNotIn("Rufus", prompt)


if __name__ == "__main__":
    unittest.main()
