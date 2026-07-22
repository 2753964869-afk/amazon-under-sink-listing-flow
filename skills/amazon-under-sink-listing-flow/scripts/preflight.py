#!/usr/bin/env python3
"""Check local readiness without contacting Amazon or BrowserAct."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


MIN_PYTHON = (3, 9)


def check(name, status, message):
    return {"name": name, "status": status, "message": message}


def run_checks(
    *,
    mode="asin",
    offline=False,
    environ=None,
    python_version=None,
    which_fn=shutil.which,
    workdir=None,
):
    if mode not in {"asin", "discovery"}:
        raise ValueError("mode must be 'asin' or 'discovery'")
    environ = os.environ if environ is None else environ
    python_version = sys.version_info[:3] if python_version is None else tuple(python_version)
    workdir = Path.cwd() if workdir is None else Path(workdir)
    checks = []

    python_ok = python_version[:2] >= MIN_PYTHON
    checks.append(check(
        "Python",
        "pass" if python_ok else "fail",
        f"Python {python_version[0]}.{python_version[1]}.{python_version[2]} detected; 3.9+ required",
    ))

    has_key = bool(str(environ.get("BROWSERACT_API_KEY", "")).strip())
    if offline:
        checks.append(check("BROWSERACT_API_KEY", "optional", "Skipped for offline validation"))
    else:
        checks.append(check(
            "BROWSERACT_API_KEY",
            "pass" if has_key else "optional",
            "Configured for BrowserAct enhancement" if has_key else "Optional; free Amazon US written-review collector is available",
        ))

    browser_path = which_fn("browser-act")
    if offline or mode == "asin":
        message = "Available for anonymous competitor discovery" if browser_path else "Not required for ASIN mode"
        checks.append(check("browser-act CLI", "optional", message))
    else:
        checks.append(check(
            "browser-act CLI",
            "pass" if browser_path else "fail",
            str(browser_path) if browser_path else "Install browser-act for anonymous competitor discovery",
        ))

    try:
        workdir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=workdir, prefix="preflight-", delete=True):
            pass
    except OSError as exc:
        checks.append(check("Work directory", "fail", f"Not writable: {exc}"))
    else:
        checks.append(check("Work directory", "pass", str(workdir.resolve())))

    return {
        "ok": not any(item["status"] == "fail" for item in checks),
        "mode": mode,
        "offline": bool(offline),
        "checks": checks,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("asin", "discovery"), default="asin")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--workdir", default="work")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    result = run_checks(mode=args.mode, offline=args.offline, workdir=args.workdir)
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for item in result["checks"]:
            print(f"[{item['status'].upper()}] {item['name']}: {item['message']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
