from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    """Normalized log event from any payment service."""
    timestamp: datetime
    service: str
    level: str = "INFO"
    transaction_id: Optional[str] = None
    trace_id: Optional[str] = None
    request_id: Optional[str] = None
    event: Optional[str] = None
    status: Optional[str] = None
    response_code: Optional[str] = None
    latency_ms: Optional[float] = None
    message: str = ""


class PaymentMetrics(BaseModel):
    """Deterministic payment health metrics."""
    total_events: int = 0
    unique_transactions: int = 0
    successful: int = 0
    business_declines: int = 0
    technical_failures: int = 0
    success_rate: float = 0.0
    business_decline_rate: float = 0.0
    technical_failure_rate: float = 0.0


class ServiceStatus(BaseModel):
    """Health status of a single service."""
    service: str
    total_events: int = 0
    error_count: int = 0
    timeout_count: int = 0
    status: str = "healthy"  # healthy / degraded / down


class FailureChainLink(BaseModel):
    """One node in a failure propagation chain."""
    service: str
    error: str
    timestamp: Optional[datetime] = None
    evidence: str = ""


class TimelineEvent(BaseModel):
    """A summarized event for the incident timeline."""
    timestamp: datetime
    service: str
    event: str
    level: str
    message: str


class AIAnalysis(BaseModel):
    """Structured output from the AI analyst."""
    probable_root_cause: str = "Unknown"
    confidence: str = "LOW"  # LOW / MEDIUM / HIGH
    evidence: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    contributing_factors: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    escalation_required: bool = False
    escalation_team: Optional[str] = None
    summary: str = ""


class IncidentReport(BaseModel):
    """Complete incident analysis report."""
    incident_id: str
    severity: str  # CRITICAL / HIGH / MEDIUM / LOW
    severity_reasoning: str
    incident_window: dict = Field(default_factory=dict)  # {start, end}
    payment_metrics: PaymentMetrics
    affected_services: list[ServiceStatus] = Field(default_factory=list)
    failure_chain: list[FailureChainLink] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    ai_analysis: Optional[AIAnalysis] = None
