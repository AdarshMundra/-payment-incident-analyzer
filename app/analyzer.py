from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from typing import Optional

from app.models import (
    FailureChainLink,
    LogEntry,
    PaymentMetrics,
    ServiceStatus,
    TimelineEvent,
)

# --- Service dependency graph ---------------------------------------------------
# Maps each service to the services it directly calls (downstream).
SERVICE_DEPENDENCIES: dict[str, list[str]] = {
    "payment-gateway": ["transaction-switch"],
    "transaction-switch": ["authorization-service"],
    "authorization-service": ["risk-service", "account-service"],
    "account-service": ["core-banking"],
    "core-banking": ["payment-database"],
}

ALL_SERVICES = [
    "payment-gateway",
    "transaction-switch",
    "authorization-service",
    "risk-service",
    "account-service",
    "core-banking",
    "payment-database",
]

# --- Failure classification sets ------------------------------------------------
BUSINESS_DECLINE_CODES = {
    "INSUFFICIENT_FUNDS",
    "INVALID_PIN",
    "CARD_EXPIRED",
    "CARD_BLOCKED",
    "TRANSACTION_LIMIT_EXCEEDED",
}

TECHNICAL_FAILURE_CODES = {
    "DATABASE_TIMEOUT",
    "SERVICE_TIMEOUT",
    "CONNECTION_ERROR",
    "SERVICE_UNAVAILABLE",
    "NETWORK_TIMEOUT",
    "DEPENDENCY_FAILURE",
    "CONNECTION_POOL_EXHAUSTED",
}


class IncidentAnalyzer:
    """Deterministic analysis engine for payment incident logs."""

    # ------------------------------------------------------------------
    # Log parsing
    # ------------------------------------------------------------------
    def parse_logs(self, raw_text: str) -> list[LogEntry]:
        """Parse raw log text into normalized LogEntry objects.

        Supports:
        - JSON array of objects
        - Newline-delimited JSON (one object per line)
        - Simple key=value log lines
        """
        raw_text = raw_text.strip()
        if not raw_text:
            return []

        # Try JSON array first
        if raw_text.startswith("["):
            try:
                items = json.loads(raw_text)
                return [self._dict_to_entry(item) for item in items]
            except json.JSONDecodeError:
                pass

        # Try newline-delimited JSON / key=value
        entries: list[LogEntry] = []
        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue
            # JSON object
            if line.startswith("{"):
                try:
                    entries.append(self._dict_to_entry(json.loads(line)))
                    continue
                except json.JSONDecodeError:
                    pass
            # key=value format
            entry = self._parse_kv_line(line)
            if entry:
                entries.append(entry)
        return entries

    def _dict_to_entry(self, d: dict) -> LogEntry:
        ts = d.get("timestamp")
        if isinstance(ts, str):
            ts = self._parse_timestamp(ts)
        return LogEntry(
            timestamp=ts or datetime.min,
            service=d.get("service", "unknown"),
            level=d.get("level", "INFO"),
            transaction_id=d.get("transaction_id"),
            trace_id=d.get("trace_id"),
            request_id=d.get("request_id"),
            event=d.get("event"),
            status=d.get("status"),
            response_code=d.get("response_code"),
            latency_ms=d.get("latency_ms"),
            message=d.get("message", ""),
        )

    @staticmethod
    def _parse_timestamp(ts_str: str) -> Optional[datetime]:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _parse_kv_line(line: str) -> Optional[LogEntry]:
        """Parse a key=value formatted log line."""
        pairs: dict[str, str] = {}
        for match in re.finditer(r'(\w+)=("(?:[^"\\]|\\.)*"|\S+)', line):
            key = match.group(1)
            val = match.group(2).strip('"')
            pairs[key] = val
        if "timestamp" not in pairs or "service" not in pairs:
            return None
        ts = IncidentAnalyzer._parse_timestamp(pairs["timestamp"])
        latency = None
        if "latency_ms" in pairs:
            try:
                latency = float(pairs["latency_ms"])
            except ValueError:
                pass
        return LogEntry(
            timestamp=ts or datetime.min,
            service=pairs.get("service", "unknown"),
            level=pairs.get("level", "INFO"),
            transaction_id=pairs.get("transaction_id"),
            trace_id=pairs.get("trace_id"),
            request_id=pairs.get("request_id"),
            event=pairs.get("event"),
            status=pairs.get("status"),
            response_code=pairs.get("response_code"),
            latency_ms=latency,
            message=pairs.get("message", ""),
        )

    # ------------------------------------------------------------------
    # Failure classification
    # ------------------------------------------------------------------
    @staticmethod
    def classify_failure(event: Optional[str], response_code: Optional[str]) -> str:
        """Classify an event as 'success', 'business_decline', or 'technical_failure'."""
        codes_to_check = {c for c in (event, response_code) if c}
        for code in codes_to_check:
            code_upper = code.upper()
            if code_upper in BUSINESS_DECLINE_CODES:
                return "business_decline"
            if code_upper in TECHNICAL_FAILURE_CODES:
                return "technical_failure"
        # Check status field patterns
        return "success"

    # ------------------------------------------------------------------
    # Payment metrics
    # ------------------------------------------------------------------
    def compute_metrics(self, events: list[LogEntry]) -> PaymentMetrics:
        txn_ids: set[str] = set()
        successful = 0
        business = 0
        technical = 0

        for e in events:
            if e.transaction_id:
                txn_ids.add(e.transaction_id)
            classification = self.classify_failure(e.event, e.response_code)
            if classification == "business_decline":
                business += 1
            elif classification == "technical_failure":
                technical += 1
            else:
                if e.status and e.status.upper() in ("FAILED", "ERROR", "TIMEOUT"):
                    technical += 1
                else:
                    successful += 1

        total = successful + business + technical
        return PaymentMetrics(
            total_events=len(events),
            unique_transactions=len(txn_ids),
            successful=successful,
            business_declines=business,
            technical_failures=technical,
            success_rate=round(successful / total * 100, 2) if total else 0.0,
            business_decline_rate=round(business / total * 100, 2) if total else 0.0,
            technical_failure_rate=round(technical / total * 100, 2) if total else 0.0,
        )

    # ------------------------------------------------------------------
    # Affected services
    # ------------------------------------------------------------------
    def get_affected_services(self, events: list[LogEntry]) -> list[ServiceStatus]:
        svc_data: dict[str, dict] = defaultdict(lambda: {"total": 0, "errors": 0, "timeouts": 0})

        for e in events:
            svc_data[e.service]["total"] += 1
            classification = self.classify_failure(e.event, e.response_code)
            if classification == "technical_failure":
                svc_data[e.service]["errors"] += 1
                if e.event and "TIMEOUT" in e.event.upper():
                    svc_data[e.service]["timeouts"] += 1
            elif e.status and e.status.upper() in ("FAILED", "ERROR", "TIMEOUT"):
                svc_data[e.service]["errors"] += 1

        result: list[ServiceStatus] = []
        for svc, data in sorted(svc_data.items()):
            error_rate = data["errors"] / data["total"] if data["total"] else 0
            if error_rate > 0.5:
                status = "down"
            elif error_rate > 0.1:
                status = "degraded"
            else:
                status = "healthy"
            result.append(ServiceStatus(
                service=svc,
                total_events=data["total"],
                error_count=data["errors"],
                timeout_count=data["timeouts"],
                status=status,
            ))
        return result

    # ------------------------------------------------------------------
    # Failure chain detection
    # ------------------------------------------------------------------
    def build_failure_chain(self, events: list[LogEntry]) -> list[FailureChainLink]:
        """Walk the dependency graph to find the probable failure propagation chain.

        Finds services with technical failures, then traces upstream from the
        deepest dependency to determine the probable origin.
        """
        # Collect earliest technical failure per service
        svc_failures: dict[str, tuple[datetime, str]] = {}
        for e in events:
            classification = self.classify_failure(e.event, e.response_code)
            is_technical = classification == "technical_failure" or (
                e.status and e.status.upper() in ("FAILED", "ERROR", "TIMEOUT")
                and classification != "business_decline"
            )
            if is_technical and e.service not in svc_failures:
                error_desc = e.event or e.response_code or e.message or "ERROR"
                svc_failures[e.service] = (e.timestamp, error_desc)

        if not svc_failures:
            return []

        # Build reverse dependency map (downstream -> upstream callers)
        reverse_deps: dict[str, list[str]] = defaultdict(list)
        for upstream, downstreams in SERVICE_DEPENDENCIES.items():
            for ds in downstreams:
                reverse_deps[ds].append(upstream)

        # Find the deepest failing service in the dependency graph
        # (the one with no failing downstream dependencies)
        def depth(svc: str, visited: set[str] | None = None) -> int:
            if visited is None:
                visited = set()
            if svc in visited:
                return 0
            visited.add(svc)
            downstream = SERVICE_DEPENDENCIES.get(svc, [])
            failing_downstream = [d for d in downstream if d in svc_failures]
            if not failing_downstream:
                return 0
            return 1 + max(depth(d, visited) for d in failing_downstream)

        # Sort by depth descending — deepest dependency failure first
        origin = min(svc_failures.keys(), key=lambda s: depth(s))

        # Build chain from origin upward
        chain: list[FailureChainLink] = []
        visited: set[str] = set()
        queue = [origin]
        while queue:
            svc = queue.pop(0)
            if svc in visited or svc not in svc_failures:
                continue
            visited.add(svc)
            ts, error = svc_failures[svc]
            chain.append(FailureChainLink(
                service=svc,
                error=error,
                timestamp=ts,
                evidence=f"{svc} reported {error} at {ts.isoformat()}" if ts != datetime.min else f"{svc} reported {error}",
            ))
            # Add upstream callers that are also failing
            for caller in reverse_deps.get(svc, []):
                if caller in svc_failures and caller not in visited:
                    queue.append(caller)

        return chain

    # ------------------------------------------------------------------
    # Severity
    # ------------------------------------------------------------------
    def determine_severity(
        self,
        metrics: PaymentMetrics,
        chain: list[FailureChainLink],
        affected: list[ServiceStatus],
    ) -> tuple[str, str]:
        """Return (severity_level, reasoning)."""
        down_count = sum(1 for s in affected if s.status == "down")
        degraded_count = sum(1 for s in affected if s.status == "degraded")
        rate = metrics.technical_failure_rate

        if rate > 20 or down_count >= 3:
            return "CRITICAL", (
                f"Technical failure rate is {rate}% with {down_count} service(s) down. "
                "Broad payment processing impact likely."
            )
        if rate > 10 or (down_count >= 1 and degraded_count >= 1):
            return "HIGH", (
                f"Technical failure rate is {rate}% with {down_count} service(s) down "
                f"and {degraded_count} degraded. Significant transaction impact."
            )
        if rate > 5 or degraded_count >= 1:
            return "MEDIUM", (
                f"Technical failure rate is {rate}% with {degraded_count} service(s) degraded. "
                "Limited service degradation."
            )
        return "LOW", (
            f"Technical failure rate is {rate}%. "
            "Isolated errors with low business impact."
        )

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------
    @staticmethod
    def build_timeline(events: list[LogEntry], max_entries: int = 50) -> list[TimelineEvent]:
        """Build a chronological timeline of notable events."""
        notable = [
            e for e in events
            if e.level in ("ERROR", "WARN", "WARNING", "CRITICAL")
            or (e.status and e.status.upper() in ("FAILED", "ERROR", "TIMEOUT"))
        ]
        notable.sort(key=lambda e: e.timestamp)
        return [
            TimelineEvent(
                timestamp=e.timestamp,
                service=e.service,
                event=e.event or e.response_code or "UNKNOWN",
                level=e.level,
                message=e.message,
            )
            for e in notable[:max_entries]
        ]

    # ------------------------------------------------------------------
    # Incident context (for AI)
    # ------------------------------------------------------------------
    def build_incident_context(self, events: list[LogEntry]) -> dict:
        """Assemble the full structured context that gets sent to the AI."""
        metrics = self.compute_metrics(events)
        affected = self.get_affected_services(events)
        chain = self.build_failure_chain(events)
        severity, reasoning = self.determine_severity(metrics, chain, affected)
        timeline = self.build_timeline(events)

        timestamps = [e.timestamp for e in events if e.timestamp != datetime.min]
        window = {}
        if timestamps:
            window = {
                "start": min(timestamps).isoformat(),
                "end": max(timestamps).isoformat(),
            }

        return {
            "incident_window": window,
            "severity": severity,
            "severity_reasoning": reasoning,
            "payment_metrics": metrics.model_dump(),
            "affected_services": [s.model_dump() for s in affected],
            "failure_chain": [link.model_dump() for link in chain],
            "timeline": [t.model_dump() for t in timeline[:20]],
            "top_errors": self._top_errors(events),
            "service_dependency_graph": SERVICE_DEPENDENCIES,
        }

    @staticmethod
    def _top_errors(events: list[LogEntry], limit: int = 10) -> list[dict]:
        counts: dict[str, int] = defaultdict(int)
        for e in events:
            key = e.event or e.response_code
            if key:
                counts[key] += 1
        return [
            {"error": k, "count": v}
            for k, v in sorted(counts.items(), key=lambda x: -x[1])[:limit]
        ]
