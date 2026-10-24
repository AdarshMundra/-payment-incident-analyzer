"""AI analysis client using OpenAI API with structured output."""
from __future__ import annotations

import json
import os
from typing import Any

from app.models import AIAnalysis

SYSTEM_PROMPT = """You are a senior payment systems incident analyst. You will receive structured incident data from a payment-issuer platform consisting of multiple microservices (payment-gateway, transaction-switch, authorization-service, risk-service, account-service, core-banking, payment-database).

Your job is to analyze the incident and provide a structured investigation report.

RULES — you must follow these strictly:
1. Never claim an assumption is a confirmed fact.
2. Only use the supplied incident evidence — do not invent data.
3. Do not invent metrics, transaction IDs, services, or infrastructure state.
4. Use "probable" or "possible" when evidence is incomplete.
5. If evidence is insufficient to determine a cause, say so explicitly.
6. Clearly separate what is confirmed evidence from what is an assumption or inference.
7. Recommendations must be practical, prioritized, and actionable.
8. Never recommend directly changing production state automatically.
9. Consider the distinction between business declines (e.g. insufficient funds, expired card) and technical failures (e.g. timeouts, connection errors). Business declines are normal operations, not incidents.
10. Focus on the failure chain — identify the probable origin of cascading failures.

Respond with a JSON object matching this exact schema:
{
  "probable_root_cause": "string — the most likely origin of the incident",
  "confidence": "HIGH | MEDIUM | LOW",
  "evidence": ["list of confirmed observations from the data"],
  "assumptions": ["list of inferences or assumptions you are making"],
  "contributing_factors": ["list of factors that may have contributed"],
  "recommended_actions": ["prioritized list of investigation/remediation steps"],
  "escalation_required": true/false,
  "escalation_team": "string or null — which team should be escalated to",
  "summary": "string — 2-3 sentence incident summary suitable for sharing with an operations team"
}"""


async def analyze_incident(context: dict[str, Any]) -> AIAnalysis:
    """Send structured incident context to an LLM and return AI analysis.

    Falls back to a deterministic summary if the API call fails.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return _build_fallback(context)

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(context, default=str)},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=1500,
        )

        raw = response.choices[0].message.content
        data = json.loads(raw)  # type: ignore[arg-type]
        return AIAnalysis(**data)

    except Exception:
        return _build_fallback(context)


def _build_fallback(context: dict[str, Any]) -> AIAnalysis:
    """Build a deterministic fallback analysis when AI is unavailable."""
    chain = context.get("failure_chain", [])
    metrics = context.get("payment_metrics", {})
    severity = context.get("severity", "UNKNOWN")
    affected = context.get("affected_services", [])

    # Determine root cause from failure chain
    if chain:
        origin = chain[0]
        root_cause = f"Probable origin: {origin.get('service', 'unknown')} — {origin.get('error', 'unknown error')}"
    else:
        root_cause = "No clear failure chain detected. Errors may be isolated."

    # Build evidence from chain
    evidence = [link.get("evidence", "") for link in chain if link.get("evidence")]

    # Build assumptions
    assumptions = []
    if chain:
        assumptions.append(
            f"Assumes the failure in {chain[0].get('service', 'unknown')} "
            f"caused downstream failures in dependent services."
        )

    # Affected services summary
    down_services = [s["service"] for s in affected if s.get("status") == "down"]
    degraded_services = [s["service"] for s in affected if s.get("status") == "degraded"]

    contributing = []
    if down_services:
        contributing.append(f"Services currently down: {', '.join(down_services)}")
    if degraded_services:
        contributing.append(f"Services degraded: {', '.join(degraded_services)}")

    actions = []
    if chain:
        actions.append(f"Investigate {chain[0].get('service', 'unknown')} logs and health metrics immediately.")
    actions.append("Check service dashboards and recent deployments.")
    if metrics.get("technical_failure_rate", 0) > 10:
        actions.append("Consider enabling circuit breakers on affected services.")
    actions.append("Monitor transaction success rates for recovery.")

    escalation = severity in ("CRITICAL", "HIGH")
    escalation_team = None
    if escalation and chain:
        svc = chain[0].get("service", "")
        if "database" in svc:
            escalation_team = "Database / Infrastructure"
        elif "core-banking" in svc:
            escalation_team = "Core Banking Engineering"
        else:
            escalation_team = "Payment Platform Engineering"

    tech_rate = metrics.get("technical_failure_rate", 0)
    summary = (
        f"{severity} severity incident detected. "
        f"Technical failure rate: {tech_rate}%. "
    )
    if chain:
        summary += (
            f"Probable origin: {chain[0].get('service', 'unknown')} "
            f"({chain[0].get('error', 'unknown')}). "
        )
    summary += f"{len(down_services)} service(s) down, {len(degraded_services)} degraded."

    return AIAnalysis(
        probable_root_cause=root_cause,
        confidence="MEDIUM" if chain else "LOW",
        evidence=evidence,
        assumptions=assumptions,
        contributing_factors=contributing,
        recommended_actions=actions,
        escalation_required=escalation,
        escalation_team=escalation_team,
        summary=summary,
    )
