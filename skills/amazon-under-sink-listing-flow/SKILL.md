---
name: amazon-under-sink-listing-flow
description: "Use when researching Amazon US under-sink pull-out organizers, analyzing competitor ASIN reviews, exporting original reviews with Chinese translations to Excel, creating listing copy, rerunning the DEKAVA/Ukeetap/REALINN benchmark, or generating a Chinese HTML listing report."
---

# Amazon Under-Sink Listing Flow

## Operating Contract

Run the complete workflow without an Amazon account. Do not require an Amazon login.

No other skill is required for ASIN-based review analysis, Excel export, listing generation, or HTML reporting. Python 3.9+ and the bundled scripts are sufficient. `BROWSERACT_API_KEY` is required only for live review extraction. The `browser-act` CLI is required only when the user asks the agent to discover current competitors from rendered Amazon search results.

Read `references/runtime-requirements.md` when installing, diagnosing, or validating the runtime.

## Workflow

### 1. Run Preflight

For user-provided ASINs or the exact benchmark:

```powershell
python <skill>/scripts/preflight.py --mode asin --workdir ./work
```

For anonymous current-competitor discovery:

```powershell
python <skill>/scripts/preflight.py --mode discovery --workdir ./work
```

Use `--offline` during installation tests. Never print or persist the value of `BROWSERACT_API_KEY`.

### 2. Select Competitor ASINs

Choose the first applicable source:

1. Use ASINs supplied by the user.
2. Reuse the exact baseline only when the user asks to rerun the prior benchmark.
3. Otherwise use an anonymous rendered Amazon search page and extract non-empty `[data-asin]` values.

Anonymous discovery URL:

```text
https://www.amazon.com/s?k=under+sink+organizer+pull+out+drawer
```

Match brand, title, color, pack size, product form, rating, and review count. Exclude makeup drawers, desktop drawers, and generic stackable bins that are not true cabinet pull-out organizers. If anonymous search is unavailable, ask the user for ASINs or offer the exact baseline; do not introduce an account-login requirement.

Baseline competitors:

| Brand | ASIN | Product signal |
|---|---|---|
| DEKAVA | `B0B3JJYJSS` | 2-pack black 2-tier sliding basket organizer |
| Ukeetap | `B0DNTQ2YNT` | black 12.8 inch 2-pack pull-out storage organizer |
| REALINN | `B0CFQFMC4F` | white 2-pack L-shaped metal pull-out organizer |

Treat prices, ratings, review counts, rankings, and variants as time-sensitive. Record when each value was observed.

### 3. Extract Reviews

Set `BROWSERACT_API_KEY` only in the current environment, then run the portable standard-library client for each ASIN:

```powershell
python <skill>/scripts/run_browseract_reviews.py B0B3JJYJSS --output ./work/reviews/DEKAVA_B0B3JJYJSS.txt
```

The default BrowserAct workflow template is `77817507798321724`. Use `--template-id` when the user's BrowserAct account provides a different shared template. Stop and report a clear error if authorization fails, the template is unavailable, the task fails/cancels, or the total timeout is reached.

Keep raw UTF-8 review logs under `work/reviews/`. Track the actual sample count for each ASIN. Do not save API keys, cookies, authorization headers, or account credentials in any artifact.

### 4. Build The Review Manifest

Read `references/review-workbook-schema.md`.

For every source review, in source order:

- Preserve the original title and body exactly.
- Add complete Simplified Chinese translations for title and body.
- Do not summarize, embellish, or remove qualifications or complaints.
- Preserve available reviewer, date, country, variant, verified-purchase, profile, and review URL fields.
- Leave a translation empty only when the corresponding source field is empty.

Sentiment is rating-derived, not language-model inferred:

- `4-5`: `Positive / 好评`
- `3`: `Neutral / 中评`
- `1-2`: `Negative / 差评`

### 5. Export Excel

```powershell
python <skill>/scripts/export_reviews_excel.py --manifest ./work/review-workbook-manifest.json --output ./outputs/under_sink_reviews_zh.xlsx
```

The workbook must contain `Summary`, `All Reviews`, and one sheet per ASIN. Keep source filenames and row numbers for traceability, but do not expose absolute local paths.

### 6. Summarize Competitor Feedback

Create a comparison table covering:

- Customers like
- Customers complain
- Installation experience
- Material and quality risk
- Size and fit risk
- Product opportunity
- Listing and image opportunity

Separate direct review evidence from inference. Include review counts behind each conclusion. Watch for recurring niche signals such as easy assembly, access to items in the back, units moving during drawer use, warped bases, light-duty construction, unstable upper baskets, pipe clearance, and measure-before-purchase guidance.

### 7. Generate Amazon US Listing Copy

Produce English ready-to-use copy:

- Title under 200 characters
- Five bullets under 500 characters each
- Description under 2000 characters
- Backend search terms
- Keyword priority and coverage table
- Image and A+ recommendations tied to review evidence

Use only product facts supplied or confirmed by the user. Do not convert competitor features or review complaints into claims about the user's product. If specifications are missing, include a separate assumption block and keep the listing copy conservative; never claim load capacity, material grade, rust resistance, BPA status, dimensions, pack quantity, warranty, or included accessories without evidence.

Do not invent keyword search volumes. When no measured keyword dataset is available, label priorities as qualitative and calculate coverage only against the explicit keyword set used in the report.

### 8. Build The HTML Report

Read `references/report-schema.md`, create the structured JSON report, then run:

```powershell
python <skill>/scripts/generate_report.py --input ./work/under_sink_report.json --output ./outputs/under_sink_listing_report.html
```

The report should contain Chinese analysis and English listing copy. Include data source, ASINs, sample counts, generation time, evidence limitations, competitor comparison, listing copy, keyword coverage, and image recommendations.

## Output Checklist

Before final response, verify:

- ASIN source and observation date are documented.
- Review sample counts are included.
- Raw logs remain under `work/reviews/`.
- Manifest translations match review counts and source order.
- Excel is a non-empty valid XLSX ZIP with all required sheets.
- HTML is non-empty, standalone, and contains the listing copy.
- Listing claims are supported or clearly separated as assumptions.
- No API key, cookie, authorization header, absolute local source path, or Amazon credential appears in outputs.
- Final response links the HTML and Excel deliverables and summarizes two to five evidence-backed conclusions.
