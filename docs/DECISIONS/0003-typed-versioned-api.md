# ADR 0003: Typed versioned API

- **Status:** Accepted
- **Date:** 2026-08-08
- **Release:** v0.2.0 private preview

## Context

The browser needs stable behavior across deterministic and experimental providers. Raw provider responses, permissive request bodies, and ad hoc error strings make failure handling unsafe and allow contradictory results to reach users.

## Decision

Use canonical `/api/v1` routes with strict request/result validation and a stable `api_version` field.

- Reject non-JSON bodies, non-object JSON, unknown fields, oversized content, invalid images, and out-of-range values.
- Require CSRF for every POST and DELETE operation.
- Keep provider-specific objects behind the service/provider boundary.
- Return a validated analysis shape with explicit consultation/forensic risk invariants and exactly six roadmap steps.
- Return expected failures as typed non-2xx JSON with a public code, safe message, opaque request ID, and bounded details where useful.
- Keep health truthful and side-effect free.
- Retain limited legacy aliases during transition, while documenting `/api/v1` as canonical.

## Consequences

### Positive

- The browser can render one provider-neutral contract.
- Provider failures cannot silently become successful zero-risk assessments.
- Error status and code are machine-readable without exposing private exception detail.
- Versioning creates an explicit place for future incompatible changes.

### Negative

- Manual validators and schemas must be kept in sync.
- Strict rejection can require coordinated client updates when fields change.
- Compatibility aliases add temporary surface area and should not become a second contract.

## Alternatives considered

- **Expose provider JSON directly:** rejected because provider output is untrusted and provider-specific.
- **Return HTTP 200 for all outcomes:** rejected because failures would be difficult to distinguish from successful assessments.
- **Adopt a larger schema framework immediately:** deferred; the current manual contracts are small, typed, tested, and avoid adding another runtime dependency.

## Follow-up threshold

Before a public API commitment, publish a formal schema, define deprecation windows, remove or explicitly support compatibility aliases, add authenticated authorization semantics, and test backward compatibility across released clients.
