# Privacy and data handling

Status: private preview, reviewed 2026-08-08. This document describes the
current source configuration; a deployer is responsible for publishing a
deployment-specific notice and honoring applicable law.

## Safe default: deterministic demo mode

`ECOLOGIC_PROVIDER=demo` is the default. It makes no model-provider request.
Observation text is processed by deterministic local rules. In demo mode an
uploaded image is validated and acknowledged, but its pixels are not analyzed.

## Local records

For successful assessments, the service stores a session-scoped record in
SQLite containing:

- the first 500 normalized characters of the submitted observation;
- the validated result, locale, provider metadata, and timestamps; and
- a keyed, pseudonymous session scope used to separate browser sessions.

Images, chat messages, and coach responses are not stored in SQLite. A selected
image and the most recent retry payload remain in the current page's browser
memory until the image is removed or the page is reloaded. The default history
retention setting is 30 days. Old rows are purged during later service
activity; an inactive database is not a real-time deletion scheduler. A signed,
HTTP-only browser cookie identifies the anonymous session. Anyone with access
to the same browser profile/session may see its saved excerpts and results.

Deleting history removes the row from the active database and SQLite secure
deletion is enabled. It cannot guarantee removal from filesystem snapshots,
host backups, provider logs, browser-vendor records, or copies made outside the
application. Secret rotation or session expiry may orphan rows until retention
cleanup runs.

## Optional OpenAI mode

OpenAI mode is opt-in and experimental. For an assessment it sends the
observation text, locale instructions, and optional image data to the OpenAI
API. Coach and chat calls send the validated assessment plus the submitted
follow-up context. A stable HMAC-derived pseudonymous session value is sent as
the API `safety_identifier`; the raw session cookie is not sent.

The adapter uses the Responses API with `store=false`, but that setting does
not eliminate all provider-side processing or retention. OpenAI states that API
data is not used to train models unless the customer opts in, while default
abuse-monitoring logs may contain prompts, responses, and metadata for up to 30
days, with stated legal/safety exceptions. Provider-side prompt caching and
image safety scanning may also apply. Review the current official
[OpenAI API data controls](https://developers.openai.com/api/docs/guides/your-data)
before enabling live mode.

Do not submit personal, confidential, regulated, or client data unless the
deployment has an appropriate legal basis, contract, access control, retention
policy, and provider configuration.

## Voice input

Voice recognition is initiated only by the user. It is implemented by the
browser and may send audio to the browser vendor. EcoLogic receives the
returned transcript in the text box and submits that text only when the user
chooses **Assess observation**. Audio processing and retention are controlled
by the browser/vendor, not this repository. Typing remains in the browser until
submission.

## Operator responsibilities

Before serving users, an operator must define access control, lawful purpose,
regional hosting, retention and backup deletion, incident response, user
notice/consent, data-subject request handling, provider agreements, and shared
cost/abuse controls. The private preview does not supply account authentication
or a production privacy-management system.
