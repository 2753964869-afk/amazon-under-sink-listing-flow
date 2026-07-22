#!/usr/bin/env python3
"""Run BrowserAct's Amazon Reviews workflow with bounded polling and UTF-8 logs."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_BASE_URL = "https://api.browseract.com/v2/workflow"
DEFAULT_TEMPLATE_ID = "77817507798321724"
ASIN_PATTERN = re.compile(r"^[A-Z0-9]{10}$")


def validate_asin(value: str) -> str:
    asin = str(value or "").strip().upper()
    if not ASIN_PATTERN.fullmatch(asin):
        raise ValueError(f"Expected a 10-character ASIN, got {value!r}")
    return asin


def require_api_key(environ=None) -> str:
    environ = os.environ if environ is None else environ
    api_key = str(environ.get("BROWSERACT_API_KEY", "")).strip()
    if not api_key:
        raise ValueError("BROWSERACT_API_KEY is not configured")
    return api_key


def request_json(method, url, api_key, payload=None, timeout=30):
    data = None
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8-sig")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code in (401, 403):
            raise RuntimeError("BrowserAct authorization failed; verify BROWSERACT_API_KEY") from exc
        raise RuntimeError(f"BrowserAct HTTP {exc.code}: {detail[:300]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach BrowserAct: {exc.reason}") from exc
    try:
        value = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("BrowserAct returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError("BrowserAct returned an unexpected response type")
    return value


def run_reviews_task(
    *,
    api_key: str,
    asin: str,
    template_id: str = DEFAULT_TEMPLATE_ID,
    poll_interval: float = 10,
    total_timeout: float = 600,
    request_timeout: float = 30,
    request_fn=request_json,
    sleep_fn=time.sleep,
    monotonic_fn=time.monotonic,
    status_callback=None,
) -> str:
    asin = validate_asin(asin)
    if total_timeout <= 0:
        raise ValueError("total_timeout must be greater than zero")
    start_response = request_fn(
        "POST",
        f"{API_BASE_URL}/run-task-by-template",
        api_key,
        {
            "workflow_template_id": str(template_id),
            "input_parameters": [{"name": "ASIN", "value": asin}],
        },
        request_timeout,
    )
    task_id = str(start_response.get("id", "")).strip()
    if not task_id:
        raise RuntimeError("BrowserAct did not return a workflow task ID")

    started_at = monotonic_fn()
    while True:
        if monotonic_fn() - started_at > total_timeout:
            raise TimeoutError(f"BrowserAct review task timed out after {total_timeout:g} seconds")
        status_response = request_fn(
            "GET",
            f"{API_BASE_URL}/get-task-status?task_id={task_id}",
            api_key,
            None,
            request_timeout,
        )
        status = str(status_response.get("status", "unknown")).strip().lower()
        if status_callback:
            status_callback(f"Task Status: {status}")
        if status == "finished":
            break
        if status in {"failed", "canceled"}:
            raise RuntimeError(f"BrowserAct review task {status}")
        sleep_fn(poll_interval)

    task = request_fn(
        "GET",
        f"{API_BASE_URL}/get-task?task_id={task_id}",
        api_key,
        None,
        request_timeout,
    )
    output = task.get("output")
    if isinstance(output, dict) and output.get("string"):
        return str(output["string"])
    return json.dumps(task, ensure_ascii=False)


def run_and_write(*, output_path, status_callback=None, **kwargs) -> Path:
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    asin = validate_asin(kwargs.get("asin"))
    with output_path.open("w", encoding="utf-8", newline="\n") as stream:
        def emit(message):
            line = str(message)
            stream.write(line + "\n")
            stream.flush()
            print(line, flush=True)
            if status_callback:
                status_callback(line)

        emit("Start Task")
        emit(f"ASIN: {asin}")
        result = run_reviews_task(status_callback=emit, **kwargs)
        stream.write(result)
        if not result.endswith("\n"):
            stream.write("\n")
    return output_path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asin", help="Amazon ASIN")
    parser.add_argument("--output", required=True, help="UTF-8 review log output path")
    parser.add_argument("--template-id", default=DEFAULT_TEMPLATE_ID)
    parser.add_argument("--poll-interval", type=float, default=10)
    parser.add_argument("--timeout", type=float, default=600)
    return parser.parse_args(argv)


def main(argv=None, environ=None) -> int:
    args = parse_args(argv)
    try:
        api_key = require_api_key(environ)
        output = run_and_write(
            api_key=api_key,
            asin=args.asin,
            output_path=args.output,
            template_id=args.template_id,
            poll_interval=args.poll_interval,
            total_timeout=args.timeout,
        )
    except (ValueError, RuntimeError, TimeoutError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
