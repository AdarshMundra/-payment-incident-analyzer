import json
import pytest
from app.analyzer import IncidentAnalyzer
from app.sample_data import generate_database_failure, generate_auth_failure, generate_normal_declines


@pytest.fixture
def analyzer():
    return IncidentAnalyzer()


# --- Failure classification ---------------------------------------------------

class TestClassifyFailure:
    def test_business_decline_insufficient_funds(self):
        assert IncidentAnalyzer.classify_failure("INSUFFICIENT_FUNDS", None) == "business_decline"

    def test_business_decline_invalid_pin(self):
        assert IncidentAnalyzer.classify_failure("INVALID_PIN", None) == "business_decline"

    def test_business_decline_card_expired(self):
        assert IncidentAnalyzer.classify_failure(None, "CARD_EXPIRED") == "business_decline"

    def test_business_decline_card_blocked(self):
        assert IncidentAnalyzer.classify_failure("CARD_BLOCKED", None) == "business_decline"

    def test_business_decline_limit_exceeded(self):
        assert IncidentAnalyzer.classify_failure("TRANSACTION_LIMIT_EXCEEDED", None) == "business_decline"

    def test_technical_failure_db_timeout(self):
        assert IncidentAnalyzer.classify_failure("DATABASE_TIMEOUT", None) == "technical_failure"

    def test_technical_failure_service_timeout(self):
        assert IncidentAnalyzer.classify_failure("SERVICE_TIMEOUT", None) == "technical_failure"

    def test_technical_failure_connection_error(self):
        assert IncidentAnalyzer.classify_failure(None, "CONNECTION_ERROR") == "technical_failure"

    def test_technical_failure_service_unavailable(self):
        assert IncidentAnalyzer.classify_failure("SERVICE_UNAVAILABLE", None) == "technical_failure"

    def test_success(self):
        assert IncidentAnalyzer.classify_failure("AUTH_APPROVED", "APPROVED") == "success"

    def test_none_inputs(self):
        assert IncidentAnalyzer.classify_failure(None, None) == "success"


# --- Log parsing --------------------------------------------------------------

class TestLogParsing:
    def test_parse_json_array(self, analyzer):
        logs = json.dumps([
            {"timestamp": "2026-10-24T10:30:00", "service": "payment-gateway", "event": "TRANSACTION_RECEIVED", "message": "test"},
            {"timestamp": "2026-10-24T10:30:01", "service": "authorization-service", "event": "AUTH_APPROVED", "message": "approved"},
        ])
        entries = analyzer.parse_logs(logs)
        assert len(entries) == 2
        assert entries[0].service == "payment-gateway"
        assert entries[1].service == "authorization-service"

    def test_parse_ndjson(self, analyzer):
        logs = (
            '{"timestamp": "2026-10-24T10:30:00", "service": "core-banking", "message": "ok"}\n'
            '{"timestamp": "2026-10-24T10:30:01", "service": "account-service", "message": "ok"}\n'
        )
        entries = analyzer.parse_logs(logs)
        assert len(entries) == 2

    def test_parse_kv_format(self, analyzer):
        logs = 'timestamp=2026-10-24T10:30:00 service=payment-gateway level=ERROR event=DATABASE_TIMEOUT message="db timed out"'
        entries = analyzer.parse_logs(logs)
        assert len(entries) == 1
        assert entries[0].event == "DATABASE_TIMEOUT"

    def test_parse_empty(self, analyzer):
        assert analyzer.parse_logs("") == []
        assert analyzer.parse_logs("   ") == []


# --- Metrics ------------------------------------------------------------------

class TestMetrics:
    def test_metrics_computation(self, analyzer):
        logs = json.dumps([
            {"timestamp": "2026-10-24T10:30:00", "service": "auth", "transaction_id": "T1", "event": "AUTH_APPROVED", "status": "SUCCESS", "message": "ok"},
            {"timestamp": "2026-10-24T10:30:01", "service": "auth", "transaction_id": "T2", "event": "INSUFFICIENT_FUNDS", "status": "DECLINED", "message": "declined"},
            {"timestamp": "2026-10-24T10:30:02", "service": "auth", "transaction_id": "T3", "event": "DATABASE_TIMEOUT", "status": "FAILED", "message": "timeout"},
        ])
        events = analyzer.parse_logs(logs)
        metrics = analyzer.compute_metrics(events)

        assert metrics.unique_transactions == 3
        assert metrics.successful == 1
        assert metrics.business_declines == 1
        assert metrics.technical_failures == 1
        assert metrics.technical_failure_rate == pytest.approx(33.33, rel=0.01)

    def test_all_success(self, analyzer):
        logs = json.dumps([
            {"timestamp": "2026-10-24T10:30:00", "service": "gw", "transaction_id": "T1", "event": "APPROVED", "status": "SUCCESS", "message": "ok"},
            {"timestamp": "2026-10-24T10:30:01", "service": "gw", "transaction_id": "T2", "event": "APPROVED", "status": "SUCCESS", "message": "ok"},
        ])
        events = analyzer.parse_logs(logs)
        metrics = analyzer.compute_metrics(events)
        assert metrics.technical_failure_rate == 0.0
        assert metrics.business_decline_rate == 0.0
        assert metrics.success_rate == 100.0


# --- Failure chain ------------------------------------------------------------

class TestFailureChain:
    def test_database_failure_chain(self, analyzer):
        """The database failure scenario should trace back to payment-database as origin."""
        events = analyzer.parse_logs(generate_database_failure())
        chain = analyzer.build_failure_chain(events)

        assert len(chain) > 0
        # The origin (first link) should be the deepest failing service
        services_in_chain = [link.service for link in chain]
        assert "payment-database" in services_in_chain
        assert chain[0].service == "payment-database"

    def test_auth_failure_chain(self, analyzer):
        """Auth failure should trace to authorization-service."""
        events = analyzer.parse_logs(generate_auth_failure())
        chain = analyzer.build_failure_chain(events)

        assert len(chain) > 0
        services_in_chain = [link.service for link in chain]
        assert "authorization-service" in services_in_chain

    def test_normal_declines_no_chain(self, analyzer):
        """Normal business declines should NOT produce a failure chain."""
        events = analyzer.parse_logs(generate_normal_declines())
        chain = analyzer.build_failure_chain(events)
        assert len(chain) == 0


# --- Severity -----------------------------------------------------------------

class TestSeverity:
    def test_database_failure_is_critical(self, analyzer):
        events = analyzer.parse_logs(generate_database_failure())
        metrics = analyzer.compute_metrics(events)
        chain = analyzer.build_failure_chain(events)
        affected = analyzer.get_affected_services(events)

        severity, _ = analyzer.determine_severity(metrics, chain, affected)
        assert severity in ("CRITICAL", "HIGH")

    def test_auth_failure_is_high(self, analyzer):
        events = analyzer.parse_logs(generate_auth_failure())
        metrics = analyzer.compute_metrics(events)
        chain = analyzer.build_failure_chain(events)
        affected = analyzer.get_affected_services(events)

        severity, _ = analyzer.determine_severity(metrics, chain, affected)
        assert severity in ("HIGH", "CRITICAL")

    def test_normal_declines_is_low(self, analyzer):
        events = analyzer.parse_logs(generate_normal_declines())
        metrics = analyzer.compute_metrics(events)
        chain = analyzer.build_failure_chain(events)
        affected = analyzer.get_affected_services(events)

        severity, _ = analyzer.determine_severity(metrics, chain, affected)
        assert severity == "LOW"


# --- Incident context ---------------------------------------------------------

class TestIncidentContext:
    def test_context_has_required_keys(self, analyzer):
        events = analyzer.parse_logs(generate_database_failure())
        ctx = analyzer.build_incident_context(events)

        required_keys = [
            "incident_window", "severity", "severity_reasoning",
            "payment_metrics", "affected_services", "failure_chain",
            "timeline", "top_errors", "service_dependency_graph",
        ]
        for key in required_keys:
            assert key in ctx, f"Missing key: {key}"

    def test_context_metrics_are_populated(self, analyzer):
        events = analyzer.parse_logs(generate_database_failure())
        ctx = analyzer.build_incident_context(events)

        assert ctx["payment_metrics"]["total_events"] > 0
        assert ctx["payment_metrics"]["technical_failures"] > 0
