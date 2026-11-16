# ObservIQ — AI Submission

*Observability AI Assistant — powered by Anthropic Claude*

---

## What are you building?

**ObservIQ — an Observability AI Assistant.** A plugin-based app (Streamlit UI + a
provider-agnostic core) that lets you ask questions about your monitoring platforms
in plain English and get back operational answers. It ships with three agents —
**Dynatrace**, **SolarWinds Orion**, and **ScienceLogic SL1** — and is architected so
new platforms (e.g. Datadog) can be added as a self-contained provider package
without touching the core.

---

## The problem and how AI helps solve it

**The problem.** Every monitoring platform speaks its own query language — Dynatrace
uses Environment API v2 paths, SolarWinds uses SWQL, ScienceLogic uses its SL1 REST
API. To get answers, an engineer must know each dialect, build the query, run it, and
manually interpret raw telemetry JSON. That's slow, needs per-platform expertise, and
doesn't scale across a multi-vendor estate.

**How AI solves it.** ObservIQ puts Claude at the center of a three-step flow that
removes the need to know any query language:

1. **Generate** — Claude turns the natural-language question + a platform-specific
   prompt into that platform's *native* query string.
2. **Execute** — the app runs that query against the real platform API.
3. **Summarize** — Claude reads the question, query, and raw telemetry and returns a
   concise operational answer with recommended actions.

The user just asks *"What problems are open right now?"* and gets a human-readable
answer — with a debug view showing the generated query and raw response. AI is what
bridges plain English to each vendor's dialect **and** turns raw telemetry back into
an operational conclusion.

---

## What outcome do you expect?

ObservIQ lets anyone get operational answers from Dynatrace, SolarWinds, and
ScienceLogic by asking in plain English — cutting time-to-answer from minutes to
seconds and removing the need to know each platform's query language. The result is
**faster incident resolution** across a **unified, easily extensible** interface that
scales to any monitoring vendor.

---

## Engineering hours AI replaced

**~30+ engineering hours/week saved (≈1 FTE freed).**

Context: 5 engineers currently support Dynatrace across 2 accounts.

| Assumption | Value |
|---|---|
| Engineers on Dynatrace | 5 |
| Accounts covered | 2 |
| Query/monitoring tasks per engineer per day | ~8–10 |
| Time per task today (recall syntax → build → run → interpret JSON) | ~8–12 min |
| Time per task with ObservIQ (ask → get summarized answer) | ~1–2 min |
| **Time saved per task** | **~7–10 min** |

Per week: 5 engineers × ~9 tasks/day × 5 days × ~8 min ≈ **~30 hours/week (~1 FTE)** —
plus eliminated ramp-up time, since new team members no longer need to learn the
platform's query language.

---

## Build cost avoided by using AI

**~$50K in development cost avoided (~12 engineer-weeks).**

| Component | Traditional build | With AI |
|---|---|---|
| Hand-coding each platform's query language (Dynatrace v2, SWQL, SL1 REST) | ~3–4 wks × 3 | Claude generates queries — no engine to build |
| Telemetry parser/summarizer per platform | ~2–3 wks | Claude summarizes raw JSON — no parser to build |
| Core app + UI + plugin architecture | ~2–3 wks | Accelerated with AI-assisted coding |
| **Estimated effort** | **~14–18 engineer-weeks** | **~3–4 engineer-weeks** |

Cost avoided ≈ 12 engineer-weeks × ~$100/hr × 40 hrs ≈ **~$48K**. The biggest avoided
cost is structural: there is **no custom NLP-to-query engine or per-platform output
parser** to design, build, test, and maintain — Claude does that at runtime. Each new
platform costs ~4 files + 2 lines instead of weeks.

---

## Weeks earlier than no-AI baseline

**~8–10 weeks earlier to delivery.**

| | No-AI baseline | With AI | Earlier by |
|---|---|---|---|
| Calendar time to working 3-platform tool | ~11–13 weeks | ~3–4 weeks | **~8–10 weeks** |

Acceleration comes from skipping the longest-pole work entirely: no per-platform query
engine, no telemetry parser, and AI-assisted build of the core/UI/architecture.

---

## Where is it in the lifecycle?

**Working prototype / MVP — functional, not yet production-hardened.**

**Built and working:**
- End-to-end three-step agent flow (generate → execute → summarize) powered by Claude
- Three live agents (Dynatrace, SolarWinds, ScienceLogic) hitting real platform APIs
- Streamlit UI: per-agent chat, credential status badges, sample questions, debug view
- Proven plugin architecture (new platform = 4 files + 2 lines, zero core changes)
- Contract tests guardrail (every provider must satisfy the `Provider` protocol)

**Not done yet (keeps it pre-production):**
- Roadmap open: vendor **MCP servers** + **custom function tools** → full Claude tool use
- No auth/multi-user, audit logging, rate-limiting, or usage/cost tracking
- Credentials are local `.env` only — not a managed secrets store

---

## Anything else worth capturing

- **Extensibility is the headline** — adding any platform (Datadog, New Relic,
  Prometheus…) costs ~4 files + 2 lines; core and UI never change. Near-zero marginal
  cost of coverage.
- **Vendor-agnostic by design** — `core/` and `app.py` have zero per-platform
  knowledge; a broken provider can't affect another.
- **Built-in trust/verifiability** — every answer exposes the exact generated query
  and raw API response, so engineers can audit what the AI did.
- **Model-flexible** — defaults to Claude Sonnet 4.6, configurable to Opus 4.8 via one
  env var; tune cost vs. capability per deployment.
- **Clear growth path** — roadmap (MCP + custom tools → full tool use) turns today's
  "answer my question" into proactive, multi-step cross-platform investigation.
- **Low operational footprint today** — runs locally with just an Anthropic key +
  platform creds; no infra to stand up for a pilot.

---

*Note: hours, cost, and timeline figures are estimates based on stated assumptions
(team size, tasks/day, time/task, ~$100/hr blended rate). Swap in actual rates and
query volumes to firm them up.*

*Powered by Anthropic Claude.*
