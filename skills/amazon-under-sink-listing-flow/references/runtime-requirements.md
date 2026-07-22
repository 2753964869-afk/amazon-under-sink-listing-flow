# Runtime Requirements

## Core ASIN Mode

- Python 3.9 or newer.
- Network access to `https://api.browseract.com` for live review extraction.
- `BROWSERACT_API_KEY` set in the current process environment.
- Access to BrowserAct workflow template `77817507798321724`, or another template supplied through `--template-id`.

No Amazon account, Amazon login, Node.js runtime, Microsoft Excel installation, pip package, or separately installed workflow skill is required.

Run:

```powershell
python <skill>/scripts/preflight.py --mode asin --workdir ./work
```

## Anonymous Discovery Mode

Current competitor discovery additionally requires the `browser-act` CLI and a configured anonymous browser session. This mode reads rendered public Amazon search results. It must not request Amazon credentials.

Run:

```powershell
python <skill>/scripts/preflight.py --mode discovery --workdir ./work
```

If anonymous discovery is unavailable, continue with user-provided ASINs or the documented exact baseline.

## Offline Installation Check

Use this after installation without contacting BrowserAct:

```powershell
python <skill>/scripts/preflight.py --mode asin --offline --json --workdir ./work
python -m unittest discover -s <skill>/tests -v
```

## Secret Handling

- Read `BROWSERACT_API_KEY` from the environment only.
- Do not write it to skill files, manifests, logs, workbooks, reports, shell history examples, or final responses.
- Report only whether the key is configured.
