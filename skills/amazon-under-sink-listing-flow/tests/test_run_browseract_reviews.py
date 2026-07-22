import importlib.util
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "run_browseract_reviews.py"


def load_client():
    if not SCRIPT.exists():
        raise AssertionError(f"Portable BrowserAct client is missing: {SCRIPT}")
    spec = importlib.util.spec_from_file_location("run_browseract_reviews", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BrowserActReviewTests(unittest.TestCase):
    def test_finishes_and_returns_review_output(self):
        client = load_client()
        responses = iter([
            {"id": "task-1"},
            {"status": "running"},
            {"status": "finished"},
            {"output": {"string": '[{"rating": 5}]'}},
        ])
        calls = []

        def request(method, url, api_key, payload=None, timeout=30):
            calls.append((method, url, payload))
            return next(responses)

        result = client.run_reviews_task(
            api_key="secret",
            asin="B0B3JJYJSS",
            request_fn=request,
            sleep_fn=lambda _: None,
            monotonic_fn=lambda: 0,
            poll_interval=0,
            total_timeout=30,
        )

        self.assertEqual('[{"rating": 5}]', result)
        self.assertEqual(["POST", "GET", "GET", "GET"], [call[0] for call in calls])

    def test_failed_task_stops_immediately(self):
        client = load_client()
        responses = iter([{"id": "task-1"}, {"status": "failed"}])
        calls = []

        def request(method, url, api_key, payload=None, timeout=30):
            calls.append(method)
            return next(responses)

        with self.assertRaisesRegex(RuntimeError, "failed"):
            client.run_reviews_task(
                api_key="secret",
                asin="B0B3JJYJSS",
                request_fn=request,
                sleep_fn=lambda _: None,
                monotonic_fn=lambda: 0,
                poll_interval=0,
                total_timeout=30,
            )

        self.assertEqual(["POST", "GET"], calls)

    def test_running_task_respects_total_timeout(self):
        client = load_client()
        responses = iter([{"id": "task-1"}, {"status": "running"}])
        times = iter([0, 2])

        with self.assertRaisesRegex(TimeoutError, "timed out"):
            client.run_reviews_task(
                api_key="secret",
                asin="B0B3JJYJSS",
                request_fn=lambda *args, **kwargs: next(responses),
                sleep_fn=lambda _: None,
                monotonic_fn=lambda: next(times),
                poll_interval=0,
                total_timeout=1,
            )

    def test_requires_api_key_and_valid_asin(self):
        client = load_client()

        with self.assertRaisesRegex(ValueError, "BROWSERACT_API_KEY"):
            client.require_api_key({})
        with self.assertRaisesRegex(ValueError, "10-character ASIN"):
            client.validate_asin("invalid")

    def test_writes_utf8_log_without_exposing_api_key(self):
        client = load_client()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "reviews.txt"
            responses = iter([
                {"id": "task-1"},
                {"status": "finished"},
                {"output": {"string": '[{"rating":5,"review_title":"好用"}]'}},
            ])

            client.run_and_write(
                api_key="top-secret",
                asin="B0B3JJYJSS",
                output_path=output,
                request_fn=lambda *args, **kwargs: next(responses),
                sleep_fn=lambda _: None,
                monotonic_fn=lambda: 0,
                poll_interval=0,
                total_timeout=30,
            )

            raw = output.read_bytes()
            text = raw.decode("utf-8")
            self.assertFalse(raw.startswith(b"\xff\xfe"))
            self.assertIn("好用", text)
            self.assertNotIn("top-secret", text)


if __name__ == "__main__":
    unittest.main()
