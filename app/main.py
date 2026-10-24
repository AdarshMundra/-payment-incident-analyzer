from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.ai_client import analyze_incident
from app.analyzer import IncidentAnalyzer
from app.models import IncidentReport
from app.sample_data import SCENARIOS

load_dotenv()

app = FastAPI(
    title="Payment Incident Intelligence",
    description="AI-assisted investigation for distributed payment incidents",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

analyzer = IncidentAnalyzer()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "payment-incident-analyzer"}


@app.post("/api/v1/analyze")
async def analyze(
    raw_logs: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Analyze payment logs and return a full incident report."""
    # Get log text from either form field or file upload
    log_text = ""
    if raw_logs:
        log_text = raw_logs
    elif file:
        content = await file.read()
        log_text = content.decode("utf-8", errors="replace")

    if not log_text.strip():
        raise HTTPException(status_code=400, detail="No log data provided. Paste logs or upload a file.")

    # Deterministic analysis
    events = analyzer.parse_logs(log_text)
    if not events:
        raise HTTPException(status_code=400, detail="Could not parse any log entries from the input.")

    metrics = analyzer.compute_metrics(events)
    affected = analyzer.get_affected_services(events)
    chain = analyzer.build_failure_chain(events)
    severity, reasoning = analyzer.determine_severity(metrics, chain, affected)
    timeline = analyzer.build_timeline(events)
    context = analyzer.build_incident_context(events)

    # AI analysis
    ai_analysis = await analyze_incident(context)

    # Build incident window
    timestamps = [e.timestamp for e in events if e.timestamp != datetime.min]
    window = {}
    if timestamps:
        window = {
            "start": min(timestamps).isoformat(),
            "end": max(timestamps).isoformat(),
        }

    incident_id = f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    report = IncidentReport(
        incident_id=incident_id,
        severity=severity,
        severity_reasoning=reasoning,
        incident_window=window,
        payment_metrics=metrics,
        affected_services=affected,
        failure_chain=chain,
        timeline=timeline,
        ai_analysis=ai_analysis,
    )

    return report.model_dump(mode="json")


@app.get("/api/v1/samples/{scenario}")
async def get_sample(scenario: str):
    """Return raw log text for a built-in sample scenario."""
    generator = SCENARIOS.get(scenario)
    if not generator:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown scenario '{scenario}'. Available: {list(SCENARIOS.keys())}",
        )
    return JSONResponse(content={"scenario": scenario, "logs": generator()})


# Serve static files (dashboard) — mount last so API routes take priority
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
