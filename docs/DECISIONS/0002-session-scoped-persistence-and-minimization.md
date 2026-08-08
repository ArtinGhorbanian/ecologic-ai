# ADR 0002: Session-scoped persistence and privacy minimization

- **Status:** Accepted
- **Date:** 2026-08-08
- **Release:** v0.2.0 private preview

## Context

Users benefit from reopening recent assessments, and coach/chat operations need authoritative assessment context. The private preview does not have accounts, organizations, or a managed identity system. Persisting full submissions, images, or chat would create unnecessary exposure.

## Decision

Store recent validated assessments in a new SQLite database under the Flask instance directory.

- Generate a high-entropy ID in the signed browser session.
- Derive database scope with HMAC-SHA256 using the application secret; do not store the raw session ID.
- Apply the scope to every get, list, delete, clear, coach, and chat lookup.
- Store at most 500 normalized characters of the observation plus locale/provider metadata and validated result JSON.
- Do not persist image bytes or chat transcripts.
- Use UTC timestamps and a 30-day default expiry with opportunistic purge.
- Close every SQLite connection explicitly and enable `secure_delete` as defense in depth.

## Consequences

### Positive

- Recent history and contextual follow-up work without an account system.
- Client-supplied IDs cannot select records outside the current session.
- Stored data is smaller than the submitted request and excludes the highest-volume evidence field.
- The new instance database remains separate from the legacy root database file.

### Negative

- Clearing or losing the signed cookie can make still-retained records inaccessible to the browser.
- Browser-session isolation is not authenticated identity, tenant isolation, or access recovery.
- SQLite constrains horizontal scale and requires a different backup/migration plan for production.
- Row deletion and `secure_delete` do not guarantee erasure from WAL files, backups, snapshots, copied files, or provider logs.

## Alternatives considered

- **No persistence:** rejected because it removes history and authoritative context for coach/chat.
- **Store the full request and image:** rejected under data-minimization principles; the current user flows do not require durable pixels.
- **Add accounts and a managed database immediately:** deferred because it materially expands the private-preview identity, operations, and compliance scope.

## Follow-up threshold

A multi-user deployment must introduce authenticated ownership, organization isolation, reviewed retention/deletion behavior, managed migrations, backup/restore procedures, and privacy controls appropriate to the client's data.
