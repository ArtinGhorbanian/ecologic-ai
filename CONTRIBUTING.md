# Contributing

EcoLogic is currently a private preview with unresolved chain-of-title status.
General contributions are closed. A repository owner may authorize a specific
change only after written incoming-rights terms are agreed; this file is not a
CLA, copyright assignment, DCO, or public/open-source license.

## Local setup

1. Use Python 3.12 and create an isolated virtual environment.
2. Upgrade pip to a non-vulnerable current release.
3. Install `requirements-dev.lock` for the exact validated toolchain, or
   `requirements-dev.txt` when deliberately refreshing dependencies.
4. Copy `.env.example` to `.env` and keep `ECOLOGIC_PROVIDER=demo`.

Do not use `pip install .`; this repository is run from a source checkout.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install pip==26.1.2
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pytest -q
```

## Required checks

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m bandit -q -r app.py wsgi.py ecologic
node --check static/script.js
```

Run the affected browser flow at 375, 768, 1024, and 1440 CSS pixels for UI
changes. Use synthetic observations and the demo provider. A live-provider test
requires explicit authorization, a safe account, a low-cost request, and no
private data.

## Change rules

- Keep API errors typed and non-2xx; never turn an outage into an assessment.
- Preserve session scoping, CSRF, validation bounds, and no-image persistence.
- Treat every model field as untrusted and render it as text.
- Do not describe scores as probability, confidence, forecast, certification,
  or measured impact.
- Update privacy/security/rights notices for boundary changes.
- Do not add third-party code, data, copy, fonts, or artwork without provenance
  and compatible terms.
- Never commit `.env`, databases, logs, screenshots with private content, or
  secrets.

Use Conventional Commit-style subjects when practical. Keep pull requests
small enough to review and include exact validation evidence.
