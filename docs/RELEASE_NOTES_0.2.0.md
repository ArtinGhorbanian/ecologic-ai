# EcoLogic 0.2.0 — Private Preview

- Release date: 2026-08-08
- Audience: authorized private collaborators
- Stability: experimental decision support; not production-ready

## What is included

- A versioned Flask API and accessible responsive web interface for turning an
  environmental observation into a bounded score, contributing factors, and a
  six-step action roadmap.
- A deterministic local demo provider that makes no external model request.
- An opt-in OpenAI Responses adapter with image input, strict structured output,
  `store=false`, timeout/retry bounds, and local result validation. It is
  configuration-compatible but has not been live-verified in this release.
- Session-scoped history, coach, follow-up chat, and qualified deletion.
- CSRF, production fail-closed configuration, minimized persistence, security
  headers, tests, lint, typing, static analysis, dependency audit, and CI.

## Install and run

Clone the source, use Python 3.12, install `requirements.lock`, copy
`.env.example` to `.env`, keep `ECOLOGIC_PROVIDER=demo`, then run `python app.py`.
Do not use `pip install .`; this is a source-checkout application.

## Security notes

The original workspace contained an embedded provider credential. It is absent
from publishable source, but the credential must be revoked/rotated before any
live-provider use. The original user database and legacy raster are excluded.
No live OpenAI call was made during release verification.

## Known limitations

- Not cleared for public/proprietary publication; see `docs/RIGHTS_STATUS.md`.
- Anonymous browser sessions are not account authentication.
- The in-memory limiter is not sufficient cost protection for a public or
  multi-worker live deployment.
- Scores are automated decision-support values, not probabilities, forecasts,
  measurements, certifications, or professional findings.
- English static UI; submitted locale/direction and dynamic localized provider
  content have limited support and no native-speaker evaluation in this release.
- Exact dependency versions are locked but artifacts are not hash-locked.

## Upgrade notes

This is the first Git-backed private-preview baseline. Do not migrate the
original `database.db`; start with the new instance database. Existing local
`.env` files must use `ECOLOGIC_PROVIDER`, not the legacy variable name.
