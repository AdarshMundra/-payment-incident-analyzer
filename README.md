# Payment Incident Intelligence

AI-assisted investigation platform for distributed payment incidents. Analyzes logs from payment microservices, identifies failure patterns, traces root causes through service dependencies, and generates structured incident reports.

> **Note:** AI output is an investigation aid and does not represent a confirmed production root cause.

## Approach

The system uses a **deterministic-first** architecture: code finds and correlates facts, AI interprets those facts and generates hypotheses. Raw logs are never sent directly to the LLM — instead, a structured incident context (metrics, failure chain, timeline) is assembled by code and then passed to the model. This makes the analysis auditable, reproducible, and less prone to hallucination.

The payment-issuer domain framing distinguishes this from a generic log analyzer. The system understands the difference between a business decline (insufficient funds — normal operation) and a technical failure (database timeout — real incident), and it understands how failures cascade through dependent services.

## AI Tools & Models Used

- **Model**: OpenAI `gpt-4o-mini` via the OpenAI Python SDK
- **Technique**: Structured JSON output (`response_format: json_object`) so the model always returns a schema-conforming response
- **Prompt design**: System prompt includes 10 explicit safety rules (never claim assumptions as facts, never invent data, prefer "probable" over "confirmed", etc.)
- **Fallback**: If no API key is set or the call fails, the system falls back to a deterministic summary built from the analysis results — the prototype always works

## Assumptions

- Log timestamps are in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS`)
- Service names in logs match the known dependency graph (payment-gateway, transaction-switch, authorization-service, risk-service, account-service, core-banking, payment-database)
- A "technical failure" is signaled by specific response codes (DATABASE_TIMEOUT, SERVICE_TIMEOUT, CONNECTION_ERROR, SERVICE_UNAVAILABLE, NETWORK_TIMEOUT, DEPENDENCY_FAILURE)
- The first service in the failure chain to exhibit errors is the "probable origin" — this is a heuristic, not a confirmed root cause
- Severity thresholds (CRITICAL >20% tech failure rate, HIGH >10%, MEDIUM >5%) are configurable defaults, not calibrated to real production baselines

## Setup

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure AI (optional — the system works without it using deterministic fallback)
copy .env.example .env
# Edit .env and add your OpenAI API key
```

## Run

```bash
uvicorn app.main:app --reload
```

Open http://localhost:8000 in your browser.

## How It Works

1. **Parse** — Logs are normalized into a common schema (supports JSON, newline-delimited JSON, key=value formats)
2. **Analyze** — Deterministic engine computes payment metrics, classifies failures (business vs technical), correlates transactions across services, and detects failure chains using a service dependency graph
3. **Classify** — Severity is determined by technical failure rate, number of affected services, and failure chain depth
4. **Investigate** — AI receives structured incident context (not raw logs) and produces a report distinguishing evidence from assumptions

## Key Design Decisions

- **Business declines vs technical failures**: Insufficient funds, expired cards, etc. are normal business operations — not incidents. Only technical failures (timeouts, connection errors, service unavailability) signal a real incident.
- **Failure chain detection**: The system traces cascading failures through the service dependency graph to find the probable origin, rather than just reporting the most common error.
- **Evidence vs assumptions**: Every AI finding is explicitly labeled as confirmed evidence or an inference/assumption.
- **Deterministic first**: All metrics, correlations, and severity classifications are computed by code. The AI interprets and explains — it is not the sole authority.

## API

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/api/v1/analyze` | POST | Analyze logs (form field `raw_logs` or file upload) |
| `/api/v1/samples/{scenario}` | GET | Get sample logs (`database_failure`, `auth_failure`, `normal_declines`) |

## Sample Scenarios

- **Database Failure** — Connection pool exhaustion cascades through core-banking, account-service, authorization. CRITICAL severity.
- **Auth Service Failure** — Authorization service returns 503. HIGH severity.
- **Normal Business Declines** — Insufficient funds, expired cards. LOW severity, no escalation. Proves the system understands payment semantics.

## Testing

```bash
pytest -v
```

## Limitations

- Uses simulated data only — no real payment systems
- AI analysis quality depends on the LLM provider; deterministic fallback is available
- No persistent storage — each analysis is independent
- Threshold-based incident detection, not statistical anomaly detection
- Single-user prototype, no authentication
