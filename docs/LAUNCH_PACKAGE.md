# Ethical launch package — hold for clearance

**Do not publish this material yet.** It is prepared for use only after the
rights checklist, credential rotation, production access/cost controls, privacy
notice, and public-release security review are complete.

## Tagline

Turn environmental observations into traceable decision-support steps—without
disguising assumptions as certainty.

## GitHub announcement

EcoLogic by AIONEX is an environmental decision-support private preview that
organizes a written observation into a bounded score, contributing factors, and
a practical review roadmap. The default demo runs locally without model calls;
the architecture also demonstrates an opt-in, validated provider boundary.
Explore the code, security model, and engineering decisions in the repository.

## LinkedIn draft

We built EcoLogic, an AIONEX environmental decision-support project focused on
a deceptively hard product problem: how do you turn an informal site
observation into a structured next step without presenting automation as a
measurement or expert verdict?

The private preview uses a deterministic local demo by default, separates
provider failures from real results, scopes saved history to an anonymous
session, and labels scores and recommendations with their limits. The rebuild
also includes a versioned API, strict validation, responsive accessible UI,
security/privacy documentation, and regression coverage for the highest-risk
flows.

It is not a site inspection, certification, savings forecast, or autonomous
control system. It is a concrete example of building AI-adjacent decision
support with safer defaults and honest boundaries.

## X/Twitter draft thread

1. EcoLogic is an AIONEX private preview for turning environmental observations
   into structured decision-support steps.
2. Safe default: deterministic local demo, no external model request, no image
   persistence, and no outage disguised as a result.
3. The architecture adds a versioned Flask API, typed errors, strict schemas,
   session-scoped history, CSRF, and an accessible responsive UI.
4. Scores are not probabilities or forecasts. Outputs require measured evidence
   and qualified human review.
5. The repository documents the tradeoffs, threat model, data flow, tests, and
   limits so reviewers can evaluate the engineering rather than a marketing
   claim.

## Product Hunt-style copy

**Tagline:** Environmental observations, organized into honest next steps.

**Short description:** EcoLogic is a decision-support workspace that structures
an environmental observation into a bounded score, contributing factors, and a
review roadmap. It defaults to a deterministic local demo and makes uncertainty,
evidence gaps, and human-review requirements visible.

## Reddit-style introduction

I have been working on EcoLogic, a small environmental decision-support web app
and an exercise in honest automation boundaries. You describe an observation
(for example a leak or energy-use anomaly), and it returns a structured score
and action roadmap. The interesting part is less the score than the safeguards:
the default is local/deterministic, provider failures are typed errors, history
is session-scoped, images are not stored, and the UI avoids calling the result a
forecast or expert finding. I would value technical feedback on the API,
threat model, validation invariants, and accessibility—not promotional votes.

## Hacker News-style copy

**Title:** Show HN: EcoLogic – demo-first environmental decision support with
typed AI failure boundaries

**Introduction:** EcoLogic is a Flask/vanilla-JS private preview that turns a
site observation into a structured score and six-step roadmap. The default
provider is deterministic and local; the optional Responses API adapter sits
behind strict schemas, local invariants, timeouts, `store=false`, typed non-2xx
errors, and no fallback persistence. The repository includes the threat model,
privacy boundary, ADRs, and regression tests. It does not claim measured risk,
forecasting, certification, or production readiness.

## Customer-focused value propositions

1. Standardize how teams capture and review sustainability observations.
2. Make evidence gaps and human-verification steps explicit before action.
3. Demonstrate a safer provider boundary without requiring paid calls in demos.
4. Give reviewers a traceable API contract, data model, and security posture.
5. Provide an adaptable workflow foundation for measured-data integrations.

## Candidate customer groups

1. Facilities and building-operations teams.
2. Sustainability and environmental program managers.
3. Energy and water audit consultancies prototyping internal workflows.
4. Industrial maintenance teams evaluating observation intake tools.
5. Software teams building accountable AI-assisted decision support.

## Discovery keywords

environmental decision support, sustainability workflow, Flask API,
responsible AI, structured outputs, facilities operations, environmental
observations, accessible dashboard, privacy by design, demo-first architecture

## Launch checklist

- Complete written chain-of-title and competition/team/employer clearance.
- Revoke and rotate the exposed legacy credential; record completion privately.
- Approve the final proprietary license and all third-party notices.
- Add production authentication, shared quotas, monitoring, and spend limits.
- Publish a deployment-specific privacy notice and deletion/backup procedure.
- Run independent security, accessibility, and cross-browser assessments.
- Create hash-verified per-platform locks/SBOM and re-run dependency audit.
- Verify screenshots and demo video against the exact public release commit.
- Make the private repository public only after every hard gate is documented.
- Publish selectively; never automate unsolicited outreach or fabricate proof.

## Demo video structure

1. State the problem and non-claims in 15 seconds.
2. Show demo mode and the no-external-call status.
3. Submit one synthetic environmental observation.
4. Explain score context, evidence gaps, and the action roadmap.
5. Demonstrate history, coach, chat, and qualified deletion.
6. Show image acknowledgment while noting demo mode does not inspect pixels.
7. Walk through the API boundary, privacy model, tests, and known limitations.
8. End with the intended adaptation opportunities, not an unsupported outcome.

## Portfolio case-study structure

Use: context; user problem; baseline defects; constraints; architecture; failure
boundaries; data minimization; UI/accessibility decisions; test evidence;
rights/publication gate; limitations; and next measurable evaluation. Do not add
invented adoption, savings, accuracy, performance, or customer-impact metrics.
