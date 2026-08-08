# Case study: strengthening EcoLogic into a bounded private preview

> This is an engineering case study for AIONEX EcoLogic v0.2.0. It describes implemented capabilities and design choices. It does not claim customer adoption, measured impact, savings, certification, or production readiness.

## Project context

EcoLogic began as a compact Flask environmental-assessment prototype. Its core idea was useful: turn a written observation into a categorized assessment, contributing factors, and an action roadmap. The private-preview work preserved that product identity while giving the application explicit trust boundaries, deterministic local behavior, session isolation, and a clearer evidence-to-action interface.

## User and business problem

Environmental observations often arrive as unstructured notes: a recurring leak, an energy spike, or a question about avoidable waste. Before a team can act, it needs a consistent way to frame what was observed, what remains uncertain, and what to verify next.

EcoLogic addresses that framing step. It organizes an observation into a bounded decision-support artifact. It does not perform a site inspection, measure equipment, calculate verified savings, or certify compliance.

## Product approach

The v0.2.0 workflow asks the user to:

1. provide a required environmental description and optional image evidence;
2. review provider mode and evidence limitations;
3. receive a consultation or forensic-style structured assessment;
4. inspect risk components, assumptions, confidence, and a six-step roadmap;
5. request a plain-language explanation or bounded follow-up;
6. reopen or delete assessments saved to the current browser session.

The default experience is deterministic demo mode. That makes the repository useful immediately after local setup without transmitting observations to a model provider or consuming paid quota.

## Technical approach

The implementation keeps Flask and introduces a factory-led layered design:

- strict schemas at the HTTP and provider boundaries;
- an application service that coordinates use cases;
- a provider protocol with deterministic and experimental implementations;
- a session-scoped SQLite repository under the instance directory;
- typed versioned JSON responses and centralized error handling;
- self-hosted, accessible browser assets with no external CDN dependency.

The experimental OpenAI adapter uses the Responses API with strict structured JSON and `store=False`. A local environmental scope guard runs before the adapter, and returned output is locally validated before it can be persisted or displayed. The adapter is mock-tested, not live-verified.

## Architecture decisions

Three decisions shaped the private preview:

1. **Demo first.** The safest and most reproducible provider is the default; live model use is an explicit experiment.
2. **Session-scoped minimization.** The server derives an opaque scope from a signed browser session, stores only a shortened description and validated result, and applies a bounded retention window.
3. **Typed versioned API.** The browser consumes one explicit contract instead of depending on provider-specific shapes or raw exceptions.

The detailed records are in [docs/DECISIONS](DECISIONS/README.md).

## Main engineering challenges

### Separating advice from incident-style risk

A zero risk score can mean an optimization consultation, while nonzero risk represents an observed issue that warrants verification. The result validator now couples analysis mode, aggregate risk, and component risk so contradictory provider output is rejected.

### Treating provider output as untrusted

Structured output narrows format variance but does not make content automatically valid. Local validation limits fields, causes, roadmap length, roles, and mode/risk relationships. Provider exceptions become typed, non-sensitive failures.

### Preventing scope bypass through evidence

Demo mode cannot inspect image pixels. Image-only requests could therefore evade a text scope check or send unrelated data to an opt-in provider. The server now requires a written environmental description even with an image, rechecks scope at the provider boundary, and never stores image bytes.

### Preserving useful history without accounts

The private preview needs continuity but does not yet have user identities. A random signed session ID is transformed into an HMAC database scope, keeping raw cookie identity out of stored rows and preventing client-selected history scope. This is adequate for a local/private preview, not enterprise tenancy.

## Security and privacy considerations

- Production startup rejects unknown environment aliases, short/ephemeral secrets, insecure cookies, and missing trusted hosts.
- POST and DELETE routes require session-bound CSRF tokens.
- Security headers restrict scripts, styles, framing, forms, browser capabilities, and caching.
- Text and image size are bounded; image content is signature checked.
- Stored text is normalized and capped at 500 characters; image and chat content are not persisted.
- Errors include opaque request IDs but omit provider/SDK internals.
- Health describes configuration readiness and explicitly says live provider verification did not occur.

SQLite secure deletion and row removal are defense-in-depth, not promises of complete erasure. Provider data handling must be reviewed separately before enabling the experimental adapter.

## User-experience considerations

The interface makes uncertainty visible rather than hiding it:

- the active provider mode appears in the header;
- demo mode warns that image pixels are not inspected;
- evidence labels distinguish text from attached context;
- the current-score context says that no forecast, target, trend, probability, or severity threshold was generated;
- financial and ISO fields can state that they were not assessed;
- coach and chat copy repeats verification limits;
- errors preserve a safe retry path.

Native controls, live regions, focus management, keyboard dialogs, responsive layout, and text-node rendering support a safer browser experience without claiming formal accessibility certification.

## Capabilities delivered

- A clone-and-virtual-environment Flask application with deterministic no-outbound default behavior.
- Strict environmental text and optional validated image input.
- Structured consultation/forensic results with internally consistent risk fields.
- Six-step roadmaps, local completion tracking, coach explanations, and bounded follow-up chat.
- Anonymous session-scoped history with deletion and retention controls.
- An experimental, locally guarded OpenAI Responses adapter.
- Automated API, service, database, security, lint, type, dependency, and static-analysis gates.

These are capabilities, not evidence of customer outcomes.

## Lessons learned

- A safe offline path is valuable for both reproducibility and cost control.
- JSON schema is only one validation layer; domain invariants still belong in application code.
- Privacy boundaries must account for every modality, not only text.
- Anonymous sessions can provide lightweight isolation, but should not be stretched into an enterprise identity model.
- Truthful status and limitations are product features, especially when an integration has not been live-tested.
- Local rate limiting is useful for accidental bursts but should never be represented as shared production abuse protection.

## Future opportunities

Possible next phases include authenticated organizations, role-based history, shared quotas, managed persistence and migrations, evidence provenance, measurement imports, configurable domain taxonomies, controlled live-provider acceptance tests, and export workflows with explicit review/approval.

None of those capabilities is included in v0.2.0.

## How AIONEX could adapt the architecture for a client

A client adaptation could retain the core contracts and provider boundary while replacing anonymous sessions with the client's identity provider, SQLite with an approved managed database, and generic categories with a reviewed facility or sector taxonomy. Integrations could then route approved roadmap items into an existing maintenance or case-management system.

Such work would require discovery, data mapping, security/privacy review, domain-expert validation, success criteria, and a separate production acceptance process. It should not inherit demo scores as operational truth.
