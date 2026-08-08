# ADR 0001: Demo-first provider boundary

- **Status:** Accepted
- **Date:** 2026-08-08
- **Release:** v0.2.0 private preview

## Context

EcoLogic needs useful local behavior without requiring a credential, consuming paid quota, transmitting user observations to a third party, or making tests depend on network/model availability. It also needs a credible path for experimenting with structured model output without coupling Flask routes to one SDK.

## Decision

Define an `AnalysisProvider` boundary with `analyze`, `coach`, and `chat` operations.

- Use `DemoProvider` by default. It is deterministic, local, and makes no outbound calls.
- Make `OpenAIResponsesProvider` an explicit `ECOLOGIC_PROVIDER=openai` experiment.
- Apply a local environmental text guard before the experimental provider, including when image evidence is attached.
- Require a written environmental description; demo mode does not inspect pixels.
- Request strict structured JSON with `store=False` and validate the returned result locally.
- Do not call OpenAI during application startup or health checks. Report that live verification did not occur.

## Consequences

### Positive

- A clone runs without secrets or provider cost.
- Tests and demos are reproducible and offline at the backend.
- Routes and services do not depend directly on provider-specific SDK objects.
- Experimental provider failures and invalid output cannot be mistaken for valid low-risk results.

### Negative

- Demo categories and scores are heuristics, not measured or expert findings.
- Demo mode cannot extract information from image pixels.
- The experimental adapter may still encounter live model, account, latency, schema, or policy behavior not covered by mocks.
- `store=False` does not define all provider logging or retention behavior.

## Alternatives considered

- **Require OpenAI for every run:** rejected because it introduces credential, privacy, cost, and availability requirements into the default path.
- **Return static fixtures only:** rejected because deterministic rules preserve meaningful variation across environmental observations.
- **Call the provider and accept free-form text:** rejected because it weakens validation and makes the browser depend on unpredictable shapes.

## Follow-up threshold

Before calling the experimental path production-ready, AIONEX must run controlled live acceptance tests with approved data, review provider terms and privacy controls, add shared quotas/cost limits, and define an operational fallback.
