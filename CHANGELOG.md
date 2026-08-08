# Changelog

All notable verified changes are recorded here. Dates use ISO 8601.

## [0.2.0] - 2026-08-08

Private preview; not cleared for public proprietary release.

### Added

- Versioned `/api/v1` contract, typed errors, provider adapter, and app factory.
- Deterministic no-network demo mode and opt-in Responses API integration.
- Session-scoped SQLite history with bounded retention and minimized input.
- CSRF, security headers, request limits, production config gates, and tests.
- Responsive accessible assessment, roadmap, history, coach, and chat interface.
- Privacy, security, rights, third-party, architecture, and reviewer documentation.
- Exact runtime/development version locks and least-privilege CI.

### Fixed

- Removed the embedded provider credential from source; rotation is still
  required because the original value was exposed.
- Image data now reaches the API and is validated without local persistence.
- Provider failures no longer appear as safe, high-confidence assessments.
- History restore, coach/chat contracts, database connection handling, and
  cross-session authorization were corrected.
- Server-derived UI content is rendered without HTML injection sinks.
- Arbitrary confidence, savings, forecast, certification, and permanent-delete
  claims were removed or qualified.

### Removed

- Unversioned CDNs, the unverified legacy raster, decorative third-party pattern,
  debug mode, and unsupported startup/security claims.

## Pre-0.2 workspace baseline

The original folder had no Git repository or release history. A redacted local
manifest is intentionally ignored and is not part of this publication.
