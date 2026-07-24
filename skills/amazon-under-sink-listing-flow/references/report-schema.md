# HTML Report Schema

`scripts/generate_report.py` reads a UTF-8 JSON object and creates a standalone escaped HTML file.

## Top-Level Fields

- `title`: required non-empty report title.
- `subtitle`: optional subtitle.
- `source`: optional source description; do not include secrets or private absolute paths.
- `generatedAt`: optional generation time.
- `summary`: optional metric-card array.
- `sections`: optional report-section array.
- `notes`: optional list of limitations or methodology notes.

Metric items use `label`, `value`, and optional `hint`.

## Section Types

Every section may include optional `basis`: either a short plain-language string or a string array. Use it to explain why the section summary was made, in simple Chinese for internal employees. Tie it to visible inputs such as review counts, repeated review phrases, ratings, keyword coverage, ASIN comparisons, product facts, or stated assumptions. Do not use professional jargon, and do not invent evidence.

- `text`: `title`, `type`, `content`. Newlines are preserved.
- `insights`: `title`, `type`, `items` string array.
- `table`: `title`, `type`, `columns`, `rows`. Only the first 200 rows are rendered.
- `bars`: `title`, `type`, `items` containing `label`, numeric `value`, and optional `hint`. Only the first 20 items are rendered.
- `metrics`: `title`, `type`, `items` metric array.
- `qa`: `title`, `type`, `items` QA object array. Each item uses `question`, `answer`, and optional `basis`, `keywords`, `scenario`, `priority`. Only the first 50 items are rendered.

Use the `qa` section for recommended listing Q&A. Treat it as helpful but not mandatory: include it by default when evidence exists, and omit it when the user asks for a concise report or no QA. Good QA candidates can come from competitor negative-review factors the user's product can truthfully solve, high-intent autocomplete/search questions that match the product, strong related keywords, and clear usage scenarios. Do not make unsupported product promises.

## Minimal Example

```json
{
  "title": "Under-Sink Organizer Competitor Report",
  "subtitle": "Amazon US",
  "source": "Three BrowserAct review samples",
  "generatedAt": "2026-07-22T12:00:00+08:00",
  "summary": [
    {"label": "ASINs", "value": "3"},
    {"label": "Reviews", "value": "34"}
  ],
  "sections": [
    {
      "title": "核心发现",
      "type": "insights",
      "items": ["安装便利性是主要正向驱动。"]
    },
    {
      "title": "Ready-to-Use Listing",
      "type": "text",
      "content": "Title\n...\n\nBullet Points\n..."
    }
  ],
  "notes": ["Review samples are not the complete review population."]
}
```

All fields are HTML-escaped by the renderer. Do not pre-insert HTML markup.
