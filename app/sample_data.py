"""Sample incident scenarios for demo and testing.

Each generator returns a JSON string (array of log objects) representing
a realistic payment incident across multiple services.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

BASE_TIME = datetime(2026, 10, 24, 10, 30, 0)


def _ts(offset_seconds: int) -> str:
    return (BASE_TIME + timedelta(seconds=offset_seconds)).strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------------------
# Scenario A: Database Connection Pool Exhaustion
# Chain: payment-database -> core-banking -> account-service -> authorization-service -> transaction-switch
# Expected: CRITICAL severity
# ---------------------------------------------------------------------------
def generate_database_failure() -> str:
    logs = []

    # Normal transactions first (0-60s)
    for i in range(1, 11):
        txn = f"TXN-{1000+i}"
        trace = f"TRACE-A{i:03d}"
        logs.extend([
            {"timestamp": _ts(i*5), "service": "payment-gateway", "level": "INFO", "transaction_id": txn, "trace_id": trace, "event": "TRANSACTION_RECEIVED", "status": "SUCCESS", "response_code": "APPROVED", "latency_ms": 45, "message": f"Card transaction received"},
            {"timestamp": _ts(i*5+1), "service": "transaction-switch", "level": "INFO", "transaction_id": txn, "trace_id": trace, "event": "ROUTE_TO_AUTH", "status": "SUCCESS", "latency_ms": 12, "message": "Routed to authorization"},
            {"timestamp": _ts(i*5+2), "service": "authorization-service", "level": "INFO", "transaction_id": txn, "trace_id": trace, "event": "AUTH_APPROVED", "status": "SUCCESS", "response_code": "APPROVED", "latency_ms": 85, "message": "Transaction authorized"},
        ])

    # Database starts failing (120s)
    logs.append({"timestamp": _ts(120), "service": "payment-database", "level": "WARN", "event": "CONNECTION_POOL_HIGH", "status": "WARNING", "message": "Connection pool usage at 85%"})
    logs.append({"timestamp": _ts(150), "service": "payment-database", "level": "ERROR", "event": "CONNECTION_POOL_EXHAUSTED", "status": "FAILED", "message": "Connection pool exhausted - no available connections"})
    logs.append({"timestamp": _ts(155), "service": "payment-database", "level": "ERROR", "event": "CONNECTION_POOL_EXHAUSTED", "status": "FAILED", "message": "Connection pool exhausted - rejecting new connections"})

    # Core banking hits database timeout (160s+)
    for i in range(3):
        logs.append({"timestamp": _ts(160+i*10), "service": "core-banking", "level": "ERROR", "event": "DATABASE_TIMEOUT", "status": "FAILED", "response_code": "DATABASE_TIMEOUT", "latency_ms": 3000, "message": "Database query timed out"})

    # Account service hits core banking timeout (180s+)
    for i in range(5):
        txn = f"TXN-{1020+i}"
        trace = f"TRACE-A{20+i:03d}"
        logs.extend([
            {"timestamp": _ts(180+i*8), "service": "account-service", "level": "ERROR", "transaction_id": txn, "trace_id": trace, "event": "SERVICE_TIMEOUT", "status": "FAILED", "response_code": "SERVICE_TIMEOUT", "latency_ms": 5000, "message": "Core banking service timed out"},
        ])

    # Authorization sees account service failures (200s+)
    for i in range(8):
        txn = f"TXN-{1030+i}"
        trace = f"TRACE-A{30+i:03d}"
        logs.extend([
            {"timestamp": _ts(200+i*8), "service": "payment-gateway", "level": "INFO", "transaction_id": txn, "trace_id": trace, "event": "TRANSACTION_RECEIVED", "status": "SUCCESS", "latency_ms": 40, "message": "Card transaction received"},
            {"timestamp": _ts(200+i*8+1), "service": "transaction-switch", "level": "INFO", "transaction_id": txn, "trace_id": trace, "event": "ROUTE_TO_AUTH", "status": "SUCCESS", "latency_ms": 10, "message": "Routed to authorization"},
            {"timestamp": _ts(200+i*8+2), "service": "authorization-service", "level": "ERROR", "transaction_id": txn, "trace_id": trace, "event": "DEPENDENCY_FAILURE", "status": "FAILED", "response_code": "DEPENDENCY_FAILURE", "latency_ms": 5100, "message": "Account service unavailable - cannot authorize"},
            {"timestamp": _ts(200+i*8+3), "service": "transaction-switch", "level": "ERROR", "transaction_id": txn, "trace_id": trace, "event": "AUTH_FAILED", "status": "FAILED", "response_code": "SERVICE_UNAVAILABLE", "latency_ms": 5200, "message": "Authorization failed - upstream dependency"},
        ])

    # Some business declines mixed in (normal — should not inflate technical failures)
    for i in range(3):
        txn = f"TXN-{1050+i}"
        trace = f"TRACE-A{50+i:03d}"
        logs.extend([
            {"timestamp": _ts(220+i*15), "service": "authorization-service", "level": "INFO", "transaction_id": txn, "trace_id": trace, "event": "INSUFFICIENT_FUNDS", "status": "DECLINED", "response_code": "INSUFFICIENT_FUNDS", "latency_ms": 60, "message": "Declined: insufficient funds"},
        ])

    return json.dumps(logs, indent=2)


# ---------------------------------------------------------------------------
# Scenario B: Authorization Service Failure
# Chain: authorization-service -> transaction-switch -> payment-gateway
# Expected: HIGH severity
# ---------------------------------------------------------------------------
def generate_auth_failure() -> str:
    logs = []

    # Normal traffic (0-60s)
    for i in range(1, 8):
        txn = f"TXN-{2000+i}"
        trace = f"TRACE-B{i:03d}"
        logs.extend([
            {"timestamp": _ts(i*7), "service": "payment-gateway", "level": "INFO", "transaction_id": txn, "trace_id": trace, "event": "TRANSACTION_RECEIVED", "status": "SUCCESS", "latency_ms": 50, "message": "Card transaction received"},
            {"timestamp": _ts(i*7+1), "service": "transaction-switch", "level": "INFO", "transaction_id": txn, "trace_id": trace, "event": "ROUTE_TO_AUTH", "status": "SUCCESS", "latency_ms": 15, "message": "Routed to authorization"},
            {"timestamp": _ts(i*7+2), "service": "authorization-service", "level": "INFO", "transaction_id": txn, "trace_id": trace, "event": "AUTH_APPROVED", "status": "SUCCESS", "response_code": "APPROVED", "latency_ms": 90, "message": "Transaction authorized"},
        ])

    # Auth service starts returning 503 (90s+)
    for i in range(6):
        txn = f"TXN-{2020+i}"
        trace = f"TRACE-B{20+i:03d}"
        logs.extend([
            {"timestamp": _ts(90+i*10), "service": "payment-gateway", "level": "INFO", "transaction_id": txn, "trace_id": trace, "event": "TRANSACTION_RECEIVED", "status": "SUCCESS", "latency_ms": 42, "message": "Card transaction received"},
            {"timestamp": _ts(90+i*10+1), "service": "transaction-switch", "level": "INFO", "transaction_id": txn, "trace_id": trace, "event": "ROUTE_TO_AUTH", "status": "SUCCESS", "latency_ms": 11, "message": "Routed to authorization"},
            {"timestamp": _ts(90+i*10+2), "service": "authorization-service", "level": "ERROR", "transaction_id": txn, "trace_id": trace, "event": "SERVICE_UNAVAILABLE", "status": "FAILED", "response_code": "SERVICE_UNAVAILABLE", "latency_ms": 50, "message": "Service unavailable - internal error"},
            {"timestamp": _ts(90+i*10+3), "service": "transaction-switch", "level": "ERROR", "transaction_id": txn, "trace_id": trace, "event": "AUTH_FAILED", "status": "FAILED", "response_code": "SERVICE_UNAVAILABLE", "latency_ms": 65, "message": "Authorization service unavailable"},
        ])

    # Database and account service are fine
    for i in range(3):
        logs.append({"timestamp": _ts(100+i*30), "service": "payment-database", "level": "INFO", "event": "HEALTH_CHECK", "status": "SUCCESS", "message": "Database health check passed"})
        logs.append({"timestamp": _ts(100+i*30), "service": "account-service", "level": "INFO", "event": "HEALTH_CHECK", "status": "SUCCESS", "message": "Account service healthy"})

    return json.dumps(logs, indent=2)


# ---------------------------------------------------------------------------
# Scenario C: Normal Business Declines (NOT an incident)
# All services healthy, just normal decline reasons.
# Expected: LOW severity
# ---------------------------------------------------------------------------
def generate_normal_declines() -> str:
    logs = []
    decline_reasons = [
        ("INSUFFICIENT_FUNDS", "Declined: insufficient funds"),
        ("INVALID_PIN", "Declined: invalid PIN entered"),
        ("CARD_EXPIRED", "Declined: card has expired"),
        ("CARD_BLOCKED", "Declined: card is blocked"),
        ("TRANSACTION_LIMIT_EXCEEDED", "Declined: daily transaction limit exceeded"),
    ]

    for i in range(1, 31):
        txn = f"TXN-{3000+i}"
        trace = f"TRACE-C{i:03d}"

        # Most transactions succeed
        if i % 4 != 0:  # ~75% success
            logs.extend([
                {"timestamp": _ts(i*10), "service": "payment-gateway", "level": "INFO", "transaction_id": txn, "trace_id": trace, "event": "TRANSACTION_RECEIVED", "status": "SUCCESS", "latency_ms": 48, "message": "Card transaction received"},
                {"timestamp": _ts(i*10+1), "service": "transaction-switch", "level": "INFO", "transaction_id": txn, "trace_id": trace, "event": "ROUTE_TO_AUTH", "status": "SUCCESS", "latency_ms": 14, "message": "Routed to authorization"},
                {"timestamp": _ts(i*10+2), "service": "authorization-service", "level": "INFO", "transaction_id": txn, "trace_id": trace, "event": "AUTH_APPROVED", "status": "SUCCESS", "response_code": "APPROVED", "latency_ms": 80, "message": "Transaction authorized"},
            ])
        else:
            # Business decline
            reason_code, reason_msg = decline_reasons[i % len(decline_reasons)]
            logs.extend([
                {"timestamp": _ts(i*10), "service": "payment-gateway", "level": "INFO", "transaction_id": txn, "trace_id": trace, "event": "TRANSACTION_RECEIVED", "status": "SUCCESS", "latency_ms": 48, "message": "Card transaction received"},
                {"timestamp": _ts(i*10+1), "service": "transaction-switch", "level": "INFO", "transaction_id": txn, "trace_id": trace, "event": "ROUTE_TO_AUTH", "status": "SUCCESS", "latency_ms": 14, "message": "Routed to authorization"},
                {"timestamp": _ts(i*10+2), "service": "authorization-service", "level": "INFO", "transaction_id": txn, "trace_id": trace, "event": reason_code, "status": "DECLINED", "response_code": reason_code, "latency_ms": 75, "message": reason_msg},
            ])

    # All services report healthy
    for svc in ["payment-database", "core-banking", "account-service", "risk-service"]:
        logs.append({"timestamp": _ts(150), "service": svc, "level": "INFO", "event": "HEALTH_CHECK", "status": "SUCCESS", "message": f"{svc} health check passed"})

    return json.dumps(logs, indent=2)


SCENARIOS = {
    "database_failure": generate_database_failure,
    "auth_failure": generate_auth_failure,
    "normal_declines": generate_normal_declines,
}
