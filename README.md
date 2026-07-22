# Amazon Under-Sink Listing Flow

A self-contained agent skill for Amazon US under-sink pull-out organizer competitor reviews, Chinese Excel workbooks, listing copy, and standalone Chinese HTML reports.

The standard workflow does not require an Amazon account or Amazon login. Live review extraction requires a BrowserAct API key. Anonymous current-competitor discovery additionally requires the `browser-act` CLI.

## Agent Installation Prompt

Give the local agent the GitHub repository URL and this instruction:

```text
Install the skill at skills/amazon-under-sink-listing-flow using your skill installer. Do not require an Amazon login. Run its offline preflight and unit tests after installation. Install the browser-act CLI only if I need anonymous current-competitor discovery. Stop when BROWSERACT_API_KEY configuration or another user authorization is required.
```

Codex agents should use the built-in `skill-installer` flow for a GitHub repository path. The skill becomes available on the next agent turn after installation.

## Runtime Configuration

For ASIN-based review analysis, configure only:

```text
BROWSERACT_API_KEY
```

The key must be provided through the current process environment and must not be committed or written to reports.

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

- Bounded BrowserAct review workflow client using only the Python standard library.
- Strict review JSON normalization and portable XLSX generation.
- Escaped standalone HTML report generation without Node.js.
- Offline and live runtime preflight.
- Cross-platform unit tests.

Third-party account credentials, API keys, review outputs, and generated reports are not part of the repository.
