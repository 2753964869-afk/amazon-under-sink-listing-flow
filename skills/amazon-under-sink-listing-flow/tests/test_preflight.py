import importlib.util
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "preflight.py"


def load_preflight():
    if not SCRIPT.exists():
        raise AssertionError(f"Preflight script is missing: {SCRIPT}")
    spec = importlib.util.spec_from_file_location("preflight", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PreflightTests(unittest.TestCase):
    def test_asin_mode_needs_key_but_not_browser_cli(self):
        preflight = load_preflight()
        with tempfile.TemporaryDirectory() as temp_dir:
            result = preflight.run_checks(
                mode="asin",
                environ={"BROWSERACT_API_KEY": "secret"},
                python_version=(3, 12, 0),
                which_fn=lambda _: None,
                workdir=Path(temp_dir),
            )

        self.assertTrue(result["ok"])
        self.assertNotIn("secret", str(result))
        self.assertEqual("optional", self.check(result, "browser-act CLI")["status"])

    def test_missing_browseract_key_keeps_free_asin_collection_available(self):
        preflight = load_preflight()
        with tempfile.TemporaryDirectory() as temp_dir:
            result = preflight.run_checks(
                mode="asin",
                environ={},
                python_version=(3, 12, 0),
                which_fn=lambda _: "browser-act",
                workdir=Path(temp_dir),
            )

        self.assertTrue(result["ok"])
        self.assertEqual("optional", self.check(result, "BROWSERACT_API_KEY")["status"])

    def test_discovery_mode_requires_browser_cli(self):
        preflight = load_preflight()
        with tempfile.TemporaryDirectory() as temp_dir:
            result = preflight.run_checks(
                mode="discovery",
                environ={"BROWSERACT_API_KEY": "secret"},
                python_version=(3, 12, 0),
                which_fn=lambda _: None,
                workdir=Path(temp_dir),
            )

        self.assertFalse(result["ok"])
        self.assertEqual("fail", self.check(result, "browser-act CLI")["status"])

    def test_offline_mode_skips_key_and_browser_requirements(self):
        preflight = load_preflight()
        with tempfile.TemporaryDirectory() as temp_dir:
            result = preflight.run_checks(
                mode="discovery",
                offline=True,
                environ={},
                python_version=(3, 12, 0),
                which_fn=lambda _: None,
                workdir=Path(temp_dir),
            )

        self.assertTrue(result["ok"])
        self.assertEqual("optional", self.check(result, "BROWSERACT_API_KEY")["status"])

    def test_rejects_old_python(self):
        preflight = load_preflight()
        with tempfile.TemporaryDirectory() as temp_dir:
            result = preflight.run_checks(
                mode="asin",
                offline=True,
                environ={},
                python_version=(3, 8, 10),
                which_fn=lambda _: None,
                workdir=Path(temp_dir),
            )

        self.assertFalse(result["ok"])
        self.assertEqual("fail", self.check(result, "Python")["status"])

    @staticmethod
    def check(result, name):
        return next(item for item in result["checks"] if item["name"] == name)


if __name__ == "__main__":
    unittest.main()
