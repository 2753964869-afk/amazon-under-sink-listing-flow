# Portable Amazon Under-Sink Listing Skill Design

## Goal

Package `amazon-under-sink-listing-flow` so another local agent can install it, configure BrowserAct, and run the standard workflow without an Amazon login or separately installed workflow skills.

## Confirmed Requirements

- Do not require an Amazon account or Amazon login.
- Do not use Rufus/Alexa in the standard workflow.
- Allow user-provided ASINs, the documented baseline ASINs, or anonymous Amazon search for competitor discovery.
- Require only Python 3.9+, network access, and `BROWSERACT_API_KEY` for the review workflow.
- Keep BrowserAct browser automation optional unless current competitor discovery is requested.
- Generate raw review logs, translated review manifests, XLSX workbooks, listing copy, and Chinese HTML reports from the one skill folder.
- Fail quickly and clearly when credentials, API access, data fields, or task status are invalid.
- Do not persist API keys, cookies, authorization headers, or Amazon credentials.

## Architecture

The skill becomes self-contained. `run_browseract_reviews.py` owns BrowserAct API submission and bounded polling. `export_reviews_excel.py` validates and normalizes review data before creating XLSX. `generate_report.py` renders escaped standalone HTML from a documented JSON schema. `preflight.py` checks local readiness without performing a paid or authenticated operation.

The standard data flow is:

1. Select ASINs from user input, the exact benchmark, or anonymous rendered Amazon search.
2. Fetch reviews through BrowserAct's workflow API using the environment-only API key.
3. Translate reviews in source order and write a manifest.
4. Export a traceable XLSX with private local paths removed.
5. Derive competitor insights and create conservative English Amazon US listing copy.
6. Render a local Chinese HTML report with escaped content.

## Error Handling

- Reject malformed ASINs before network access.
- Stop immediately for BrowserAct `failed` or `canceled` states.
- Stop after a configurable total timeout.
- Reject invalid JSON, non-review arrays, non-finite/out-of-range ratings, invalid verified-purchase values, and translation count mismatches.
- Never print the API key.
- Report unavailable optional browser automation separately from core review API readiness.

## Testing

- Unit-test review polling with injected HTTP, clock, and sleep functions.
- Reproduce and test the previously observed wrong-array, string-boolean, NaN-rating, and source-path leaks.
- Test HTML escaping and output structure.
- Test preflight behavior with isolated temporary skill and executable paths.
- Test the SKILL.md contract: no mandatory Rufus/Amazon login, self-contained scripts referenced, BrowserAct key documented.
- Run all tests with Python bytecode disabled and validate generated XLSX and HTML artifacts.

## Distribution

The release repository contains the skill under `skills/amazon-under-sink-listing-flow`, offline tests, and repository-level installation documentation added when the GitHub destination is known. Release archives exclude caches, work files, outputs, credentials, and raw customer review data.
