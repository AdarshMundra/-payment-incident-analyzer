from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import AIAnalysis
from app.sample_data import generate_database_failure, generate_normal_declines


@pytest.fixture
def client():
    return TestClient(app)


MOCK_AI = AIAnalysis(
    probable_root_cause="Test root cause",
    confidence="HIGH",
    evidence=["Evidence 1"],
    assumptions=["Assumption 1"],
    contributing_factors=["Factor 1"],
    recommended_actions=["Action 1"],
    escalation_required=True,
    escalation_team="Test Team",
    summary="Test incident summary.",
)


class TestHealthEndpoint:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"


class TestSamplesEndpoint:
    def test_get_sample(self, client):
        r = client.get("/api/v1/samples/database_failure")
        assert r.status_code == 200
        assert "logs" in r.json()

    def test_unknown_sample(self, client):
        r = client.get("/api/v1/samples/nonexistent")
        assert r.status_code == 404


class TestAnalyzeEndpoint:
    @patch("app.main.analyze_incident", new_callable=AsyncMock, return_value=MOCK_AI)
    def test_analyze_database_failure(self, mock_ai, client):
        logs = generate_database_failure()
        r = client.post("/api/v1/analyze", data={"raw_logs": logs})
        assert r.status_code == 200

        report = r.json()
        assert report["severity"] in ("CRITICAL", "HIGH")
        assert report["incident_id"].startswith("INC-")
        assert len(report["failure_chain"]) > 0
        assert report["failure_chain"][0]["service"] == "payment-database"
        assert report["payment_metrics"]["technical_failures"] > 0
        assert report["ai_analysis"]["probable_root_cause"] == "Test root cause"

    @patch("app.main.analyze_incident", new_callable=AsyncMock, return_value=MOCK_AI)
    def test_analyze_normal_declines(self, mock_ai, client):
        logs = generate_normal_declines()
        r = client.post("/api/v1/analyze", data={"raw_logs": logs})
        assert r.status_code == 200

        report = r.json()
        assert report["severity"] == "LOW"
        assert len(report["failure_chain"]) == 0
        assert report["payment_metrics"]["business_declines"] > 0
        assert report["payment_metrics"]["technical_failures"] == 0

    def test_analyze_empty_input(self, client):
        r = client.post("/api/v1/analyze", data={"raw_logs": ""})
        assert r.status_code == 400

    def test_analyze_unparseable_input(self, client):
        r = client.post("/api/v1/analyze", data={"raw_logs": "this is not a log"})
        assert r.status_code == 400
