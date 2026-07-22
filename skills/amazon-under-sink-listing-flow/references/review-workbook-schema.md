# Review Workbook Manifest

Use this schema to join Amazon Reviews API raw outputs with Chinese translations before running `scripts/export_reviews_excel.py`.

## Manifest

```json
{
  "products": [
    {
      "asin": "B0B3JJYJSS",
      "brand": "DEKAVA",
      "reviews_file": "reviews/DEKAVA_B0B3JJYJSS.txt",
      "translations": [
        {
          "title_zh": "安装简单，收纳方便",
          "description_zh": "完整、忠实的简体中文翻译。"
        }
      ]
    }
  ]
}
```

## Rules

- `products` must be a non-empty array.
- `asin`, `reviews_file`, and `translations` are required for every product.
- Relative `reviews_file` paths resolve from the manifest directory.
- `translations` must contain exactly one entry per API review, in the same order as the raw JSON array.
- Every translation entry must include `title_zh` and `description_zh`.
- Preserve the complete meaning and qualifications of the source review. Do not summarize, embellish, or remove complaints from positive reviews.
- Leave a translation empty only when the corresponding source field is empty.
- Ratings must be finite whole numbers from `1` through `5`.
- Verified-purchase values may be JSON booleans, `0`/`1`, or unambiguous true/false strings. Unknown values are rejected.
- `source_file` stores only the source filename, not an absolute local path.

## Sentiment

Sentiment is derived from the numeric Amazon rating, not inferred from wording:

| Rating | English | Chinese |
|---|---|---|
| 4-5 | Positive | 好评 |
| 3 | Neutral | 中评 |
| 1-2 | Negative | 差评 |

## Workbook Sheets

- `Summary`: ASIN, brand, total reviews, positive count, neutral count, negative count, average rating.
- `All Reviews`: all normalized review rows.
- `<ASIN>`: rows for one ASIN, sorted by rating descending and source order.

The review sheets contain original title/body, Chinese title/body, sentiment, rating, reviewer metadata, source URLs, and source traceability fields.
