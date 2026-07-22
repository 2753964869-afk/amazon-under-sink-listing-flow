#!/usr/bin/env python3
"""Collect bounded Amazon US written reviews through the bundled public-source client."""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ASIN_PATTERN = re.compile(r"^[A-Z0-9]{10}$", re.IGNORECASE)


def load_fetch_reviews():
    path = Path(__file__).with_name("amazon_review_scraper.py")
    spec = importlib.util.spec_from_file_location("amazon_review_scraper", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.fetch_reviews


def validate_asins(asins):
    unique = []
    for asin in asins:
        value = str(asin).strip().upper()
        if not ASIN_PATTERN.fullmatch(value):
            raise ValueError(f"Invalid 10-character ASIN: {asin}")
        if value not in unique:
            unique.append(value)
    if not unique:
        raise ValueError("At least one ASIN is required")
    return unique


def normalize_text(value):
    return " ".join(html.unescape(str(value or "")).split())


def review_key(asin, review):
    return (asin, normalize_text(review.get("Author")).lower(), normalize_text(review.get("Title")).lower(), normalize_text(review.get("Text"))[:120].lower())


def clean_review(review):
    cleaned = dict(review)
    for field in ("Author", "Title", "Text"):
        cleaned[field] = normalize_text(cleaned.get(field))
    return cleaned


def adaptive_combinations(asins, mode):
    if mode == "basic":
        return [(asin, 0, 0) for asin in asins]
    if mode == "full":
        return [(asin, star, 0) for star in (5, 4, 3, 2, 1) for asin in asins]
    if mode == "max":
        return [(asin, star, sort) for star in (5, 4, 3, 2, 1) for sort in (0, 1, 2, 3) for asin in asins]
    combinations = [(asin, 0, 0) for asin in asins]
    combinations.extend((asin, 0, sort) for sort in (1, 2, 3) for asin in asins)
    combinations.extend((asin, star, sort) for star in (5, 4, 3, 2, 1) for sort in (0, 1, 2, 3) for asin in asins)
    return combinations


def collect_reviews(asins, total_limit=30, mode="adaptive", fetch_fn=None):
    if mode not in {"basic", "full", "max", "adaptive"}:
        raise ValueError("mode must be basic, full, max, or adaptive")
    if not isinstance(total_limit, int) or total_limit < 1:
        raise ValueError("total_limit must be a positive integer")
    asins = validate_asins(asins)
    fetch_fn = load_fetch_reviews() if fetch_fn is None else fetch_fn
    seen, reviews, attempts = set(), [], []
    for asin, star, sort in adaptive_combinations(asins, mode):
        if len(reviews) >= total_limit:
            break
        try:
            batch = fetch_fn(asin, filter_val=star, sort_val=sort)
        except Exception as exc:
            attempts.append({"asin": asin, "star": star, "sort": sort, "fetched": 0, "added": 0, "error": str(exc)})
            continue
        added = 0
        for review in batch:
            review = clean_review(review)
            key = review_key(asin, review)
            if key in seen:
                continue
            seen.add(key)
            reviews.append({"asin": asin, **review})
            added += 1
            if len(reviews) >= total_limit:
                break
        attempts.append({"asin": asin, "star": star, "sort": sort, "fetched": len(batch), "added": added})
    return {"requested_total": total_limit, "actual_total": len(reviews), "marketplace": "US", "counts_by_asin": {asin: sum(item["asin"] == asin for item in reviews) for asin in asins}, "collection_attempts": attempts, "reviews": reviews, "collected_at": datetime.now(timezone.utc).isoformat()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--marketplace", required=True, choices=("US",))
    parser.add_argument("--asins", nargs="+", required=True)
    parser.add_argument("--total-limit", type=int, default=30)
    parser.add_argument("--mode", choices=("basic", "full", "max", "adaptive"), default="adaptive")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    result = collect_reviews(args.asins, args.total_limit, args.mode)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("requested_total", "actual_total", "counts_by_asin")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
