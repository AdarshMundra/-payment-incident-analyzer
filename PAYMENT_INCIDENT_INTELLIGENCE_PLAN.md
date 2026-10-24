# AI-Powered Payment Incident Intelligence Platform
## Coding Agent Implementation Plan

## 1. Project Goal

Build a prototype AI-assisted incident investigation platform for bank payment issuer environments.

The system will analyze simulated logs from distributed payment microservices and help an operations engineer answer:

1. What happened?
2. Which transactions are affected?
3. Which services are affected?
4. Where did the failure probably originate?
5. What evidence supports that conclusion?
6. What are assumptions versus confirmed observations?
7. How severe is the incident?
8. What should be investigated next?
9. Should the issue be escalated?

The original assignment requires a working prototype that accepts logs, identifies patterns/errors, suggests likely causes, classifies severity, recommends troubleshooting/escalation, and generates an incident summary. The implementation should extend those requirements into a payment-issuer microservices scenario.

IMPORTANT:
- Do NOT use Docker for development.
- Backend must use Python + FastAPI.
- Keep the system simple enough to finish and demonstrate reliably.
- Use simulated data only. No real bank/payment systems.
- Do not build unnecessary production infrastructure.

---

# 2. Product Positioning

Working name:

Payment Incident Intelligence Platform

Possible product tagline:

"AI-assisted investigation for distributed payment incidents."

Core idea:

Deterministic code finds and correlates facts.
AI interprets those facts and generates hypotheses/recommendations.

Do NOT make this a generic "upload logs and ask an LLM" application.

The main differentiator is cross-service payment transaction correlation.

---

# 3. Target Payment-Issuer Architecture

Simulate these logical services:

1. payment-gateway
2. transaction-switch
3. authorization-service
4. risk-service
5. account-service
6. core-banking
7. payment-database

Optional:
8. notification-service

The prototype does not need to implement these as separate running microservices.

They are simulated through structured logs and service metadata.

Example transaction journey:

Card/ATM/POS
    ->
Payment Gateway
    ->
Transaction Switch
    ->
Authorization Service
    -> Risk Service
    -> Account Service
    -> Core Banking
    -> Database

The analyzer should understand the dependency relationships.

---

# 4. Core User Story

An operations engineer notices that card authorization failures have increased.

They upload or paste logs from several payment services.

The system should produce:

- incident ID
- severity
- incident window
- total transactions
- successful transactions
- business declines
- technical failures
- affected transaction count
- affected services
- timeline
- service dependency/failure chain
- probable failure point
- evidence
- assumptions
- confidence
- recommended investigation steps
- escalation recommendation
- concise incident summary

---

# 5. Important Payment-Domain Distinction

The system MUST distinguish business declines from technical failures.

Business declines include:

- INSUFFICIENT_FUNDS
- INVALID_PIN
- CARD_EXPIRED
- CARD_BLOCKED
- TRANSACTION_LIMIT_EXCEEDED

Technical failures include:

- DATABASE_TIMEOUT
- SERVICE_TIMEOUT
- CONNECTION_ERROR
- SERVICE_UNAVAILABLE
- NETWORK_TIMEOUT
- DEPENDENCY_FAILURE

A high number of business declines should not automatically become a technical incident.

A sudden increase in technical failures should be treated as a stronger incident signal.

---

# 6. Recommended Tech Stack

## Backend

Python 3.11+

FastAPI

Pydantic v2

Uvicorn

## Data Processing

Python standard library
- re
- datetime
- collections

Pandas may be used where useful, but avoid unnecessary dependencies.

## AI

Use an LLM provider through a small abstraction layer.

Recommended interface:

AIProvider
    - analyze_incident(context)
    - summarize_incident(context)

Do not hard-code the entire application to one model provider.

The initial implementation can support one provider, with the interface designed for another provider later.

## Database

SQLite for the MVP.

Use SQLAlchemy if persistence is needed.

The system should remain usable without complex infrastructure.

## Frontend

For the first MVP, use a simple frontend that can communicate with FastAPI.

Preferred:
- HTML/CSS/JavaScript served by FastAPI

Alternative if implementation speed requires:
- Streamlit as a separate UI

Do not introduce React unless there is enough time after the MVP.

## Visualization

Use a lightweight JavaScript visualization or simple HTML/CSS for:

- service dependency graph
- incident timeline

Do not add a heavy visualization framework unless necessary.

## Testing

pytest

FastAPI TestClient

## Development

No Docker.

Run locally with:

uvicorn app.main:app --reload

---

# 7. Project Structure

Create approximately:

payment-incident-intelligence/
|
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── routes/
│   │   │   ├── health.py
│   │   │   ├── incidents.py
│   │   │   └── logs.py
│   │   └── schemas/
│   │       ├── incident.py
│   │       ├── log.py
│   │       └── analysis.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── logging.py
│   │
│   ├── models/
│   │   └── incident.py
│   │
│   ├── services/
│   │   ├── log_parser.py
│   │   ├── normalizer.py
│   │   ├── correlation.py
│   │   ├── incident_detector.py
│   │   ├── severity.py
│   │   ├── payment_metrics.py
│   │   ├── dependency_graph.py
│   │   ├── ai_analyzer.py
│   │   └── report_generator.py
│   │
│   ├── ai/
│   │   ├── provider.py
│   │   ├── prompts.py
│   │   └── schemas.py
│   │
│   ├── db/
│   │   ├── database.py
│   │   └── repositories.py
│   │
│   └── static/
│       ├── index.html
│       ├── app.js
│       └── styles.css
│
├── data/
│   └── sample_incidents/
│       ├── database_failure/
│       ├── authorization_failure/
│       ├── risk_timeout/
│       ├── normal_business_declines/
│       └── network_failure/
│
├── tests/
│   ├── test_log_parser.py
│   ├── test_normalizer.py
│   ├── test_correlation.py
│   ├── test_severity.py
│   ├── test_payment_metrics.py
│   ├── test_incident_detection.py
│   └── test_api.py
│
├── prompts/
│   └── incident_analysis.md
│
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── PLAN.md

The exact structure can be adjusted if the coding agent has a cleaner implementation,
but the responsibilities should remain separated.

---

# 8. Phase 1 — Project Setup

Tasks:

- Create Python virtual environment instructions.
- Create requirements.txt.
- Create FastAPI application.
- Add /health endpoint.
- Add basic configuration using environment variables.
- Add CORS configuration if required.
- Add structured application logging.
- Create basic project README.
- Ensure application starts locally without Docker.

Expected command:

uvicorn app.main:app --reload

Expected:

GET /health

returns:

{
  "status": "ok"
}

---

# 9. Phase 2 — Define Common Log Schema

Create a normalized event model.

Minimum fields:

- timestamp
- service
- level
- transaction_id
- trace_id
- request_id
- event
- status
- response_code
- latency_ms
- message

Fields may be optional because different logs may not contain everything.

Example:

{
  "timestamp": "2026-10-24T10:32:01",
  "service": "authorization-service",
  "level": "ERROR",
  "transaction_id": "TXN-1001",
  "trace_id": "TRACE-ABC123",
  "request_id": "REQ-123",
  "event": "ACCOUNT_SERVICE_TIMEOUT",
  "status": "FAILED",
  "response_code": "TIMEOUT",
  "latency_ms": 3000,
  "message": "Account service request timed out"
}

Use Pydantic validation.

---

# 10. Phase 3 — Log Ingestion

Support:

1. Upload one or multiple log files.
2. Paste raw logs.
3. JSON logs.
4. Simple plain-text logs.

API:

POST /api/v1/logs/analyze

Input:
- uploaded files OR raw log text

Output:
- normalized event count
- parsing warnings
- service list
- time range

Do not send raw logs directly to the LLM.

---

# 11. Phase 4 — Log Normalization

Build a normalizer that converts different input formats into the common event schema.

Support:

- JSON structured logs
- key=value logs
- simple timestamp/level/message logs

If fields cannot be extracted:

- preserve the raw message
- leave unavailable structured fields as null
- record a parsing warning

Never silently invent transaction IDs or trace IDs.

---

# 12. Phase 5 — Payment Metrics

Calculate deterministic metrics.

Required:

- total transaction events
- unique transactions
- successful transactions
- business declines
- technical failures
- overall decline rate
- technical failure rate
- timeout count
- service error counts

Example:

{
  "total_transactions": 12450,
  "successful": 10120,
  "business_declines": 1860,
  "technical_failures": 470,
  "technical_failure_rate": 3.77
}

The exact calculation rules should be documented.

---

# 13. Phase 6 — Transaction Correlation

Correlation priority:

1. transaction_id
2. trace_id
3. request_id
4. timestamp + known service dependency

Build a transaction journey.

Example:

TXN-1001

payment-gateway
    ->
transaction-switch
    ->
authorization-service
    ->
account-service
    ->
database

For each transaction, preserve chronological order.

Do not claim correlation when evidence is insufficient.

---

# 14. Phase 7 — Service Dependency Graph

Create a configurable dependency map.

Initial configuration:

payment-gateway
    -> transaction-switch

transaction-switch
    -> authorization-service

authorization-service
    -> risk-service

authorization-service
    -> account-service

account-service
    -> core-banking

core-banking
    -> payment-database

Use this graph to support correlation and failure-chain analysis.

Keep the dependency configuration outside the business logic so it can be changed later.

---

# 15. Phase 8 — Incident Detection

Detect potential incidents using deterministic rules.

Initial rules:

- technical failure rate exceeds threshold
- timeout spike
- service unavailable spike
- database failure spike
- authorization failure spike
- multiple dependent services failing
- sudden decline-rate increase

Do not over-engineer anomaly detection.

For the prototype, threshold-based detection is sufficient.

The thresholds should be configurable.

---

# 16. Phase 9 — Failure Chain Detection

This is a core feature.

Given:

Database:
connection pool exhausted

Account Service:
database timeout

Authorization:
account service timeout

Transaction Switch:
authorization declined

The system should construct:

Database
    ->
Account Service
    ->
Authorization Service
    ->
Transaction Switch
    ->
Transaction failure

Determine the earliest observed correlated failure.

Call this:

"Probable Failure Origin"

Do not call it "confirmed root cause."

---

# 17. Phase 10 — Severity Engine

Implement deterministic severity first.

Factors:

- technical failure rate
- affected transaction count
- affected service criticality
- number of dependent services
- duration
- authorization impact

Suggested baseline:

CRITICAL:
- authorization broadly unavailable
- very high technical failure rate
- multiple critical payment services unavailable

HIGH:
- significant authorization/transaction failures
- multiple services affected
- substantial technical failure rate

MEDIUM:
- limited service degradation
- moderate technical failures

LOW:
- isolated errors
- low technical impact

The exact thresholds should be configurable and documented.

AI should explain severity rather than being the sole authority for it.

---

# 18. Phase 11 — AI Analyst

The AI should receive a structured incident context, not an uncontrolled raw log dump.

Example context:

{
  "incident_window": {},
  "payment_metrics": {},
  "affected_services": [],
  "top_errors": [],
  "timeline": [],
  "failure_chain": [],
  "dependency_graph": {},
  "sample_events": []
}

AI responsibilities:

- identify probable failure point
- explain evidence
- identify possible contributing factors
- distinguish evidence from assumptions
- recommend investigation steps
- recommend escalation
- generate incident summary

AI should return strict structured JSON.

Required output:

{
  "probable_root_cause": "...",
  "confidence": "HIGH",
  "evidence": [],
  "assumptions": [],
  "contributing_factors": [],
  "recommended_actions": [],
  "escalation_required": true,
  "escalation_team": "...",
  "summary": "..."
}

If the model cannot determine a likely cause, it should explicitly say so.

---

# 19. Phase 12 — AI Safety / Reliability Rules

The prompt must instruct the model:

1. Never claim an assumption is a confirmed fact.
2. Only use supplied incident evidence.
3. Do not invent metrics.
4. Do not invent transaction IDs.
5. Do not invent services.
6. Do not invent infrastructure state.
7. Prefer "probable" / "possible" when evidence is incomplete.
8. If evidence is insufficient, state that.
9. Recommendations should be practical and prioritized.
10. Never recommend directly changing production state automatically.

---

# 20. Phase 13 — Incident API

Implement:

POST /api/v1/incidents/analyze

Input:
- logs/files

Output:
- incident analysis

GET /api/v1/incidents/{incident_id}

Returns:
- incident overview
- metrics
- timeline
- affected services
- failure chain
- AI analysis

GET /api/v1/incidents

Returns previous analyzed incidents if persistence is enabled.

GET /api/v1/incidents/{incident_id}/summary

Returns concise incident summary.

---

# 21. Phase 14 — Dashboard

Build a simple browser UI.

Required sections:

## Incident Header

- Incident ID
- Severity
- Incident window
- Status

## Payment Health

- total transactions
- success rate
- business decline rate
- technical failure rate

## Affected Services

Example:

Database              CRITICAL
Account Service       HIGH
Authorization         HIGH
Transaction Switch    MEDIUM

## Failure Chain

Database
  ↓
Account Service
  ↓
Authorization
  ↓
Transaction Switch

## Timeline

Show chronological events.

## AI Investigation

Show:

- probable cause
- confidence
- evidence
- assumptions
- contributing factors
- recommended actions
- escalation

## Incident Summary

Provide copy/download functionality if practical.

---

# 22. Phase 15 — Sample Data

Create realistic simulated payment incidents.

## Scenario A — Database Connection Exhaustion

Expected chain:

Database
->
Account Service
->
Authorization
->
Transaction failures

Expected classification:
HIGH or CRITICAL depending on simulated impact.

---

## Scenario B — Authorization Service Failure

Expected:

Transaction Switch
->
Authorization unavailable
->
High transaction failures

---

## Scenario C — Risk Service Timeout

Expected:

Authorization
->
Risk Service timeout
->
Authorization latency increase
->
Transaction failures

---

## Scenario D — Normal Business Declines

Include:

- insufficient funds
- invalid PIN
- card expired
- transaction limit

Expected:
No technical incident.

This test is mandatory because it proves the analyzer understands payment semantics.

---

## Scenario E — Network/Core Banking Dependency Failure

Expected:

Authorization
->
Account/Core Banking
->
Network timeout
->
Transaction failures

---

# 23. Phase 16 — Testing

Write unit tests for:

- log parsing
- normalization
- payment metric calculations
- business vs technical decline classification
- transaction correlation
- timeline generation
- severity calculation
- failure-chain generation

Write API tests using FastAPI TestClient.

At least one end-to-end test should:

1. load sample incident
2. parse logs
3. calculate metrics
4. correlate transactions
5. detect incident
6. produce incident context

AI tests should mock the AI provider.

Do not make normal unit tests dependent on an external LLM API.

---

# 24. Phase 17 — README Documentation

README must explain:

- problem
- payment issuer context
- architecture
- setup
- environment variables
- running locally
- API endpoints
- log schema
- correlation approach
- severity rules
- AI role
- evidence vs assumptions
- sample incidents
- testing
- limitations
- future improvements

Include a clear statement:

"AI output is an investigation aid and does not represent a confirmed production root cause."

---

# 25. Phase 18 — Demo Flow

The demo should take approximately 5-7 minutes.

Demo Scenario:

"Bank has reported a sudden increase in card transaction failures."

Step 1:
Upload logs from:

- transaction-switch
- authorization-service
- account-service
- database

Step 2:
Show transaction metrics.

Step 3:
Show increased technical failure rate.

Step 4:
Show affected services.

Step 5:
Show transaction journey.

Step 6:
Show timeline.

Step 7:
Show failure chain.

Step 8:
Show probable failure origin.

Step 9:
Show evidence vs assumptions.

Step 10:
Show recommended investigation steps.

The demo should make it obvious that the system found the likely upstream problem rather than simply repeating the most common error.

---

# 26. Future Scope

Do NOT implement these in the MVP unless there is extra time.

Potential future additions:

- OpenTelemetry integration
- Kafka
- real-time log streaming
- Prometheus metrics
- Elasticsearch/OpenSearch
- distributed tracing
- historical incident search
- RAG over runbooks
- similar incident detection
- ServiceNow integration
- Jira integration
- Slack/Teams alerts
- automated remediation with human approval

---

# 27. Explicit Non-Goals

Do NOT build:

- Docker
- Kubernetes
- real bank integrations
- real payment gateway integrations
- real card networks
- automatic production remediation
- authentication/authorization for the prototype
- complex user management
- unnecessary microservices
- a full observability platform

The objective is a convincing working prototype, not a production banking platform.

---

# 28. Definition of Done

The project is complete when:

[ ] FastAPI starts locally without Docker.

[ ] Logs can be uploaded.

[ ] Multiple service logs can be analyzed together.

[ ] Logs are normalized into a common schema.

[ ] Payment transactions can be correlated.

[ ] Business declines and technical failures are distinguished.

[ ] Payment metrics are calculated.

[ ] Incident severity is determined.

[ ] A service dependency graph is available.

[ ] An incident timeline is generated.

[ ] A probable failure chain is generated.

[ ] Evidence and assumptions are separated.

[ ] AI produces structured analysis.

[ ] Recommendations are prioritized.

[ ] Escalation is suggested when appropriate.

[ ] At least five simulated incidents work.

[ ] Unit tests pass.

[ ] API tests pass.

[ ] README contains setup and architecture documentation.

[ ] Demo can be completed without external production systems.

---

# 29. Coding Agent Instructions

Implement incrementally.

Priority order:

1. Backend skeleton
2. Log schema/parser
3. Payment metrics
4. Correlation engine
5. Dependency graph
6. Incident detection
7. Severity engine
8. AI abstraction/provider
9. AI analysis
10. API endpoints
11. Dashboard
12. Sample incidents
13. Tests
14. README

Do not implement future infrastructure before the MVP works.

After each phase:
- run tests
- fix failures
- keep the application runnable

Keep business logic independent from FastAPI routes.

Keep AI provider code isolated from deterministic incident logic.

Use type hints throughout.

Use Pydantic models for API contracts.

Prefer simple, readable code over unnecessary abstractions.

Do not add dependencies unless there is a clear reason.

Do not use Docker.

The final application must run locally with a Python virtual environment and Uvicorn.
