# Security policy

## Supported version

Security fixes are currently applied only to the latest `0.2.x` private-preview
revision on the default branch. The project is not production-certified.

## Reporting a vulnerability

Use GitHub private vulnerability reporting when it is available to repository
collaborators. Otherwise contact the repository owner through a private channel
already established for the project. Do not open a public issue containing a
credential, exploit, private record, or personal data.

Include the affected commit, route or file, reproduction steps, impact, and a
redacted proof. Do not test against systems or data you do not own or have
permission to assess.

## Implemented controls

- deterministic, no-network demo provider by default;
- environment-only provider credentials and production fail-closed config;
- signed HTTP-only, SameSite session cookie and session-scoped records;
- CSRF enforcement on every mutation;
- strict JSON/content/image bounds and typed non-2xx errors;
- image MIME, base64, size, and magic-byte validation;
- self-only Content Security Policy and standard hardening headers;
- parameterized SQLite access, secure deletion, and bounded retention;
- no local persistence of images, coach replies, or chat transcripts;
- provider timeouts, bounded retries, strict structured output, and
  `store=false` for Responses API calls;
- deterministic tests for cross-session history/coach/chat isolation; and
- dependency pinning, lint, typing, Bandit, and pip-audit gates.

## Known limitations

- Anonymous browser sessions are not user accounts or strong authentication.
- The in-memory rate limiter is per process and per session; cookie rotation or
  multiple workers can bypass it. Live/paid deployments require authenticated
  users plus gateway or shared-store quotas, IP/account controls, monitoring,
  and spend limits.
- Development mode uses an ephemeral signing secret unless one is configured,
  so restarts invalidate sessions.
- Local SQLite is appropriate for a small private preview, not horizontally
  scaled production.
- SQLite records are not encrypted at rest. File-mode changes are not a complete
  Windows ACL boundary; the host, volume, backup, and OS account must enforce
  access control and encryption where required.
- Model outputs are schema/range checked but are not independently fact-checked,
  calibrated, certified, or grounded in site measurements.
- Deletion cannot erase external provider/browser logs or operator backups.
- This review is not a penetration test or compliance certification.

See [docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md) and
[PRIVACY.md](PRIVACY.md) for the full boundary and data-flow discussion.
