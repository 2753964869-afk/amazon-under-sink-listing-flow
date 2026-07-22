# Data Source Routing

Use only sources that are available and configured. Record the source, collection time, ASINs, actual row count, and known limitations. Never merge time-sensitive measurements without retaining their observation dates.

## Capability Order

| Capability | Default | Optional enhancement | No-source behavior |
|---|---|---|---|
| Written reviews | `free-public` bundled collector | BrowserAct | Continue with actual collected count; never pad reviews |
| Competitor ASINs | User ASINs or exact baseline | `sellersprite-competitors`, `sellersprite-products`, anonymous BrowserAct search | Ask for ASINs or use the exact baseline only with user consent |
| Keyword measurements | None | `sellersprite-keywords`, `sellersprite-aba` | Use qualitative priorities and do not invent volumes |
| Listing generation | User product facts | Evidence from configured sources | Generate conservative copy and list assumptions separately |

## Free Public Reviews

Run `scripts/collect_amazon_reviews.py` first for Amazon US written reviews. It requires no API key, Amazon login, browser extension, or external Python package. It depends on a non-official public endpoint that may change or return fewer written reviews than requested. Distinguish written reviews from star-only ratings and report `actual_total`.

## BrowserAct

Use BrowserAct only when the user has configured `BROWSERACT_API_KEY` and requests the enhancement or the public source cannot provide usable results. Do not expose the key. Do not require BrowserAct for installation, preflight, or baseline listing generation.

## SellerSprite

Use SellerSprite only after the user has installed the applicable `sellersprite-*` skills, connected WebBridge, and logged in to SellerSprite in that browser profile.

- Use `sellersprite-competitors` for keyword-, brand-, seller-, or ASIN-driven competitor candidates.
- Use `sellersprite-products` for top-product and market-ranking data.
- Use `sellersprite-keywords` for search, purchase, impression, and PPC keyword fields.
- Use `sellersprite-aba` for ABA search-frequency and ASIN reverse-lookup signals.

Treat masked free-tier values as unavailable. Do not infer exact values from caps or placeholders. SellerSprite provides market and keyword enrichment, not review-body text.

## Failure Rules

- A missing optional provider is not an error.
- A configured provider failure is recorded and skipped unless the user explicitly required that provider.
- If all live sources fail, generate listing copy only from user-confirmed product facts and clearly label evidence gaps.
