# Architecture decision records

This directory records consequential engineering decisions for AIONEX EcoLogic. The records describe the v0.2.0 private-preview architecture and its tradeoffs; they are not claims of production readiness.

| ADR | Status | Decision |
| --- | --- | --- |
| [0001](0001-demo-first-provider-boundary.md) | Accepted | Make deterministic, no-outbound demo behavior the default behind a provider protocol. |
| [0002](0002-session-scoped-persistence-and-minimization.md) | Accepted | Keep minimized assessment history under an opaque browser-session scope with bounded retention. |
| [0003](0003-typed-versioned-api.md) | Accepted | Use a strict versioned JSON contract and typed failures between the browser and Flask service. |

## Record format

Each record states its context, decision, consequences, and alternatives. A decision can later be superseded by a new ADR; historical records should remain available so tradeoffs are reviewable.

Dates use UTC repository dates. “Accepted” means implemented for the private preview, not universally correct for every future deployment.
