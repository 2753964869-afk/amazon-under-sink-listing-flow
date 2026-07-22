# Amazon Under-Sink Listing Flow

A self-contained agent skill for Amazon US under-sink pull-out organizer competitor reviews, Chinese Excel workbooks, listing copy, and standalone Chinese HTML reports.

The standard Amazon US written-review workflow does not require an Amazon account, API key, or browser software. The bundled free public-source collector is the default. BrowserAct and SellerSprite are optional configured enhancements.

## Agent Installation Prompt

Give the local agent the GitHub repository URL and this instruction:

```text
Install the skill at skills/amazon-under-sink-listing-flow using your skill installer. Do not require an Amazon login or API key for the default Amazon US written-review workflow. Run its offline preflight and unit tests after installation. Configure BrowserAct or SellerSprite only when I explicitly request those optional enhancements.
```

Codex agents should use the built-in `skill-installer` flow for a GitHub repository path. The skill becomes available on the next agent turn after installation.

## Runtime Configuration

No provider configuration is required for default Amazon US written-review analysis.

To enable optional BrowserAct enhancement, configure:

```text
BROWSERACT_API_KEY
```

The key must be provided through the current process environment and must not be committed or written to reports. SellerSprite enrichment requires its separately configured local skills, WebBridge session, and browser login.

Run offline verification:

```powershell
python skills/amazon-under-sink-listing-flow/scripts/preflight.py --mode asin --offline --json --workdir ./work
python -m unittest discover -s skills/amazon-under-sink-listing-flow/tests -v
```

Run live ASIN-mode preflight after configuring the key:

```powershell
python skills/amazon-under-sink-listing-flow/scripts/preflight.py --mode asin --workdir ./work
```

Use discovery mode only when the user wants current competitors found automatically:

```powershell
python skills/amazon-under-sink-listing-flow/scripts/preflight.py --mode discovery --workdir ./work
```

## Included Components

- Bounded, no-key Amazon US written-review collector using only the Python standard library.
- Optional BrowserAct review workflow client.
- Optional SellerSprite competitor and keyword routing.
- Strict review JSON normalization and portable XLSX generation.
- Escaped standalone HTML report generation without Node.js.
- Offline and live runtime preflight.
- Cross-platform unit tests.

Third-party account credentials, API keys, review outputs, and generated reports are not part of the repository.
