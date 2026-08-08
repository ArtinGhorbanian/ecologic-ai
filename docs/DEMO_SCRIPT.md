# Private-preview demo script

> AIONEX EcoLogic v0.2.0. Target length: 6–8 minutes. Run in default demo mode; do not configure or call OpenAI for this demonstration.

## Pre-demo setup

Use a fresh clone and virtual environment. This repository is not an installable package, so never use `pip install .`.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python app.py
```

Open `http://127.0.0.1:5000`. Confirm the header shows demo mode and a ready service. Do not use the voice button during a no-outbound demonstration because browser voice recognition may contact the browser vendor.

Recommended reset: use a fresh browser profile/session so saved assessments from an earlier run do not distract from the flow.

## 0:00–0:45 — Set truthful context

**Show:** landing screen, provider badge, evidence form, review notice.

**Say:**

> “EcoLogic is an AIONEX private preview for organizing environmental observations into a structured decision-support assessment and action roadmap. This demo uses deterministic local rules. The backend makes no outbound provider calls, and the output is not an inspection, prediction, financial estimate, or certification.”

Point out the instruction not to include personal or confidential information.

## 0:45–2:00 — Consultation flow

Select the **Waste reduction** example or enter:

```text
How can a small office reduce avoidable waste each month?
```

Select **Assess observation**.

**Show:**

- consultation/evidence label;
- zero aggregate and component risk;
- factors and confidence note;
- six-step improvement roadmap;
- financial and ISO fields that state when they were not assessed;
- the decision-support disclaimer.

**Say:**

> “Advice is represented as a zero-risk consultation, not as an incident finding. The contract requires aggregate and component risks to agree, and it requires exactly six roadmap steps. Demo mode does not invent a verified saving or ISO conclusion.”

Check two roadmap steps and show the progress indicator. Explain that checklist state is only in browser memory and is not proof of completed work.

## 2:00–3:20 — Observation requiring verification

Enter:

```text
There is a recurring water leak and visible staining beneath a pipe connection.
```

Select **Assess observation**.

**Show:** nonzero forensic-style risk, component breakdown, causes, immediate hazard-oriented first step, and the expandable current-score context.

**Say:**

> “Damage language produces a deterministic nonzero review so the interface does not present an observed leak as an optimization success. The score is a bounded demo heuristic. It must be verified on site by a qualified person.”

Point out that the score context is only a position on the 0–100 scale and explicitly provides no forecast, target, trend, probability, or severity threshold.

## 3:20–4:10 — Evidence boundary

Point to **Add image** and the demo disclosure.

**Say:**

> “The server accepts only signature-checked PNG, JPEG, or WebP files up to two megabytes, and it still requires a written environmental description. Demo mode does not inspect pixels. Images are not stored in assessment history.”

For a short demo, do not upload an image. If demonstrating one, use a synthetic, non-confidential file and describe its relevant details in text.

## 4:10–5:00 — Explanation and follow-up

Select **Explain this assessment**.

**Show:** plain-language explanation, eco tip, and confidence note.

Open follow-up chat and ask:

```text
What should be verified before anyone changes the pipe connection?
```

**Say:**

> “Coach and chat reload the authoritative assessment by server-side session scope. The client sends an ID, not a replacement assessment. Demo replies are deterministic, bounded, and still require professional verification. Chat is held in browser memory rather than saved to the database.”

## 5:00–5:50 — Session history and privacy

Open **Saved assessments**. Select the earlier waste consultation, then open the delete action for one record and confirm it.

**Say:**

> “History is anonymous and browser-session scoped, not account based. The database stores an HMAC-derived session scope, at most 500 normalized characters of input, and the validated result for up to 30 days by default. It does not store image bytes or chat transcripts. Row deletion is not a promise of forensic erasure from backups, WAL files, snapshots, or provider systems.”

## 5:50–6:30 — Safe refusal and typed error

Enter:

```text
What is a chair?
```

Select **Assess observation**.

**Show:** unsupported-topic error and unchanged saved history.

**Say:**

> “The scope guard tokenizes environmental terms rather than using unsafe substring matching, so ‘air’ inside ‘chair’ does not pass. Rejected requests are not persisted and would not cross the experimental provider boundary.”

## 6:30–7:15 — Architecture and limits

Optionally open `/api/v1/health` in a separate tab.

**Say:**

> “Health reports configuration readiness and explicitly says that a live provider was not verified. The optional OpenAI Responses adapter uses strict structured JSON and `store=False`, but it remains experimental and has not been live-tested in this release.”

Close with the production boundary:

> “This private preview uses SQLite, anonymous sessions, and an in-memory per-process limiter. A public or paid-provider deployment needs authentication, managed persistence, shared quotas and cost controls, observability, and a controlled live-provider acceptance process.”

## Questions to answer conservatively

| Question | Accurate answer for v0.2.0 |
| --- | --- |
| Does it use AI by default? | No. Default demo mode is deterministic local logic with no backend outbound call. |
| Does it analyze image pixels? | Not in demo mode. The image is validated as evidence, but text must describe the relevant observation. |
| Are savings or ISO claims verified? | No. Those require measured client data and qualified review. |
| Is OpenAI production ready? | No. The adapter is implemented and mock-tested but not live-verified. |
| Is history tied to a user account? | No. It is scoped to a signed anonymous browser session. |
| Is deletion guaranteed erasure? | No. It deletes the application row; backups, WAL files, snapshots, or provider logs can outlive it. |
| Can it run across many workers safely? | Not as-is. The limiter is per process and SQLite/session assumptions need a production architecture review. |
| Has it delivered customer outcomes? | No customer outcomes or quantitative impact are claimed for this private preview. |
