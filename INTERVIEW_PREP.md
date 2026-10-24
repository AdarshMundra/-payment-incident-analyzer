# Interview Preparation — Payment Incident Intelligence

---

## Architecture Diagram (Text)

```
┌─────────────────────────────────────────────────────────────┐
│                     BROWSER DASHBOARD                       │
│  [ Load Sample / Upload File / Paste Logs ] → [ Analyze ]  │
│                                                             │
│  Incident Header │ Metrics │ Services │ Failure Chain       │
│  AI Investigation │ Evidence vs Assumptions │ Summary       │
└────────────────────────┬────────────────────────────────────┘
                         │  POST /api/v1/analyze
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           1. LOG PARSER  (analyzer.py)              │   │
│  │   JSON array / NDJSON / key=value  →  LogEntry[]    │   │
│  └───────────────────────┬─────────────────────────────┘   │
│                          │                                  │
│  ┌───────────────────────▼─────────────────────────────┐   │
│  │         2. DETERMINISTIC ANALYSIS ENGINE            │   │
│  │                                                     │   │
│  │  ┌─────────────────┐   ┌─────────────────────────┐ │   │
│  │  │ Failure          │   │ Payment Metrics         │ │   │
│  │  │ Classifier       │   │ · total / success rate  │ │   │
│  │  │                  │   │ · business declines     │ │   │
│  │  │ INSUFFICIENT     │   │ · technical failures    │ │   │
│  │  │ _FUNDS → business│   │ · tech failure rate     │ │   │
│  │  │                  │   └─────────────────────────┘ │   │
│  │  │ DATABASE_TIMEOUT │                               │   │
│  │  │ → technical      │   ┌─────────────────────────┐ │   │
│  │  └─────────────────┘   │ Failure Chain Detector  │ │   │
│  │                         │                         │ │   │
│  │  ┌─────────────────┐   │ Dependency Graph:        │ │   │
│  │  │ Severity Engine  │   │ payment-gateway          │ │   │
│  │  │                  │   │   → transaction-switch   │ │   │
│  │  │ CRITICAL >20%    │   │     → authorization      │ │   │
│  │  │ HIGH     >10%    │   │       → account-service  │ │   │
│  │  │ MEDIUM   > 5%    │   │         → core-banking   │ │   │
│  │  │ LOW      rest    │   │           → database     │ │   │
│  │  └─────────────────┘   └─────────────────────────┘ │   │
│  └───────────────────────┬─────────────────────────────┘   │
│                          │  Structured Incident Context     │
│  ┌───────────────────────▼─────────────────────────────┐   │
│  │              3. AI ANALYST  (ai_client.py)          │   │
│  │                                                     │   │
│  │  Input: { metrics, failure_chain, timeline,         │   │
│  │           affected_services, top_errors }           │   │
│  │                        │                            │   │
│  │                        ▼                            │   │
│  │              OpenAI gpt-4o-mini                     │   │
│  │          (structured JSON output mode)              │   │
│  │                        │                            │   │
│  │  Output: { probable_root_cause, confidence,         │   │
│  │            evidence[], assumptions[],               │   │
│  │            recommended_actions[],                   │   │
│  │            escalation_required }                    │   │
│  │                                                     │   │
│  │  Fallback: deterministic summary if API fails       │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 10-Minute Presentation Script

### Min 0–2 — The Problem
> "Banks run card transactions through 7 microservices in under 200ms. When failures spike, an ops engineer needs to know fast: is this a real outage or just normal business declines? And if it's real — which service caused it? This tool answers those questions."

### Min 2–5 — Live Demo: Database Failure
- Load "Database Failure" → Analyze
- Point out: CRITICAL severity, tech failure rate, failure chain starting at `payment-database`
- Show AI evidence vs assumptions panel
  > "Notice the system explicitly labels what's observed vs what's inferred — the evaluators specifically look for this."
- Show recommended actions and escalation banner

### Min 5–7 — The Payment Domain Knowledge Proof
- Load "Normal Declines" → Analyze
- Show: LOW severity, zero failure chain, no escalation
  > "Insufficient funds and expired cards are not system failures. A generic log analyzer would flag these as errors. This one knows the difference — that's the payment domain knowledge."

### Min 7–9 — Architecture Walkthrough
- Walk through the diagram
- Key talking point:
  > "Deterministic code runs first — AI never sees raw logs. It receives a structured context with pre-computed facts. This prevents hallucination and makes the output auditable and reproducible."
- Mention: evidence vs assumptions separation, fallback if API key is unavailable

### Min 9–10 — Q&A buffer

---

## Likely Q&A Questions

| Question | Your Answer |
|---|---|
| How do you know the AI isn't making things up? | It only receives structured facts computed by code. The prompt has 10 explicit rules against inventing data. Evidence and assumptions are labeled separately in the output. |
| What if the API key is unavailable? | The deterministic fallback kicks in automatically — the system still produces a full report from the analysis engine alone. |
| How would you scale this for production? | Add a message queue (Kafka), persistent storage (PostgreSQL), real-time log streaming, OpenTelemetry integration, and historical incident search. |
| Why not just send raw logs to the LLM? | Unpredictable output, token limits, no reproducibility, and the model can't correlate transactions across services as reliably as deterministic code. |
| How accurate is the failure chain? | It's a heuristic based on the dependency graph and earliest error timestamps. We deliberately call it "probable origin", never "confirmed root cause". |
| What AI model did you use? | OpenAI gpt-4o-mini with structured JSON output mode. The abstraction makes it easy to swap in another model later. |
| How did you test it? | 32 unit and API tests. Key tests: business declines are never classified as technical failures, the database failure chain always traces back to payment-database as origin, and normal declines always produce LOW severity. |

---

## Image Generation Prompt

Use this prompt in **ChatGPT (DALL-E)**, **Midjourney**, or **Adobe Firefly**:

```
A clean, professional software architecture diagram for an AI-powered payment incident 
intelligence platform. Dark navy blue background (#0f1724). Three clearly labeled 
horizontal layers connected by downward arrows:

Top layer — "Browser Dashboard": a dark UI panel showing metric cards (Total Events, 
Success Rate, Business Declines, Technical Failure Rate), a failure chain flowchart 
with colored boxes, and an AI Investigation panel with green evidence bullets and 
amber assumption bullets.

Middle layer — "FastAPI Backend": three connected boxes labeled (1) Log Parser — 
accepts JSON/text logs, normalizes to LogEntry schema; (2) Deterministic Analysis 
Engine — contains sub-boxes for Failure Classifier, Payment Metrics, Failure Chain 
Detector with a small service dependency graph showing payment-gateway → 
transaction-switch → authorization-service → account-service → core-banking → 
payment-database, and Severity Engine with CRITICAL/HIGH/MEDIUM/LOW tiers; (3) AI 
Analyst — shows structured context going in, OpenAI gpt-4o-mini in the center, 
structured JSON output coming out with a "Fallback" note.

Bottom layer — "Payment Microservices (Simulated)": seven small service boxes in a 
chain: payment-gateway, transaction-switch, authorization-service, risk-service, 
account-service, core-banking, payment-database. The payment-database box is 
highlighted in red to indicate it is the failure origin.

Arrows: white POST /api/v1/analyze arrow from dashboard to backend. Red cascading 
failure arrow going upward from payment-database through the service chain. Blue 
"Structured Context" arrow from Analysis Engine to AI Analyst.

Style: modern fintech dashboard aesthetic, flat design, white and cyan text labels, 
color-coded severity badges (red=CRITICAL, orange=HIGH, yellow=MEDIUM, green=LOW), 
subtle grid lines, clean sans-serif font. No decorative elements. Suitable for a 
technical presentation slide.
```

---

## Key Phrases to Use in the Interview

- *"Deterministic code finds facts. AI interprets facts."*
- *"We never send raw logs to the model — we send a structured context."*
- *"Business declines are normal payment operations, not incidents."*
- *"We call it probable origin, not confirmed root cause."*
- *"Evidence and assumptions are first-class concepts in the output."*
- *"The system works even if the AI API is unavailable — there's always a fallback."*
