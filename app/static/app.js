// === State ===
let currentReport = null;

// === Sample loading ===
async function loadSample(scenario) {
    try {
        const res = await fetch(`/api/v1/samples/${scenario}`);
        const data = await res.json();
        document.getElementById("logInput").value = data.logs;
        document.getElementById("fileName").textContent = `Loaded: ${scenario}`;
    } catch (err) {
        alert("Failed to load sample: " + err.message);
    }
}

// === File upload ===
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById("logInput").value = e.target.result;
        document.getElementById("fileName").textContent = file.name;
    };
    reader.readAsText(file);
}

// === Analyze ===
async function analyzeIncident() {
    const logText = document.getElementById("logInput").value.trim();
    if (!logText) {
        alert("Please paste logs or load a sample scenario.");
        return;
    }

    const btn = document.getElementById("analyzeBtn");
    btn.disabled = true;
    document.getElementById("results").style.display = "none";
    document.getElementById("loading").style.display = "block";

    try {
        const formData = new FormData();
        formData.append("raw_logs", logText);

        const res = await fetch("/api/v1/analyze", { method: "POST", body: formData });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Analysis failed");
        }

        currentReport = await res.json();
        renderReport(currentReport);
    } catch (err) {
        alert("Analysis error: " + err.message);
    } finally {
        btn.disabled = false;
        document.getElementById("loading").style.display = "none";
    }
}

// === Render full report ===
function renderReport(r) {
    renderHeader(r);
    renderMetrics(r.payment_metrics);
    renderServices(r.affected_services);
    renderChain(r.failure_chain);
    renderAI(r.ai_analysis);
    renderSummary(r.ai_analysis);
    renderTimeline(r.timeline);
    document.getElementById("results").style.display = "block";
}

// === Incident header ===
function renderHeader(r) {
    const el = document.getElementById("incidentHeader");
    const window = r.incident_window;
    const start = window.start ? new Date(window.start).toLocaleTimeString() : "?";
    const end = window.end ? new Date(window.end).toLocaleTimeString() : "?";
    el.innerHTML = `
        <div>
            <div class="incident-id">${r.incident_id}</div>
            <div class="incident-window">${start} &mdash; ${end}</div>
        </div>
        <div>
            <span class="severity-badge severity-${r.severity}">${r.severity}</span>
        </div>
    `;
}

// === Metrics ===
function renderMetrics(m) {
    const el = document.getElementById("metricsGrid");
    const techClass = m.technical_failure_rate > 10 ? "danger" : m.technical_failure_rate > 5 ? "warning" : "ok";
    const successClass = m.success_rate < 80 ? "danger" : m.success_rate < 95 ? "warning" : "ok";
    el.innerHTML = `
        <div class="metric-card">
            <div class="label">Total Events</div>
            <div class="value">${m.total_events.toLocaleString()}</div>
        </div>
        <div class="metric-card">
            <div class="label">Success Rate</div>
            <div class="value ${successClass}">${m.success_rate}%</div>
        </div>
        <div class="metric-card">
            <div class="label">Business Declines</div>
            <div class="value">${m.business_decline_rate}%</div>
        </div>
        <div class="metric-card">
            <div class="label">Technical Failures</div>
            <div class="value ${techClass}">${m.technical_failure_rate}%</div>
        </div>
    `;
}

// === Services ===
function renderServices(services) {
    const el = document.getElementById("servicesContent");
    if (!services.length) {
        el.innerHTML = "<p style='color:var(--text-muted)'>No affected services.</p>";
        return;
    }
    const rows = services.map(s => `
        <tr>
            <td>${s.service}</td>
            <td>${s.error_count}</td>
            <td><span class="status-badge status-${s.status}">${s.status}</span></td>
        </tr>
    `).join("");
    el.innerHTML = `
        <table class="services-table">
            <thead><tr><th>Service</th><th>Errors</th><th>Status</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}

// === Failure chain ===
function renderChain(chain) {
    const el = document.getElementById("chainContent");
    if (!chain.length) {
        el.innerHTML = "<p style='color:var(--text-muted)'>No failure chain detected — services appear healthy.</p>";
        return;
    }
    const nodes = chain.map((link, i) => {
        const isOrigin = i === 0;
        const arrow = i < chain.length - 1 ? '<div class="chain-arrow">&#x2193;</div>' : "";
        return `
            <div class="chain-node ${isOrigin ? 'origin' : ''}">
                <div class="chain-service">${link.service}${isOrigin ? " (origin)" : ""}</div>
                <div class="chain-error">${link.error}</div>
            </div>
            ${arrow}
        `;
    }).join("");
    el.innerHTML = `<div class="failure-chain">${nodes}</div>`;
}

// === AI Analysis ===
function renderAI(ai) {
    const el = document.getElementById("aiSection");
    if (!ai) {
        el.innerHTML = "<h3>AI Investigation</h3><p>No AI analysis available.</p>";
        return;
    }

    const evidenceItems = (ai.evidence || []).map(e => `<li>${esc(e)}</li>`).join("");
    const assumptionItems = (ai.assumptions || []).map(a => `<li>${esc(a)}</li>`).join("");
    const actionItems = (ai.recommended_actions || []).map((a, i) => `<li>${i + 1}. ${esc(a)}</li>`).join("");
    const factorItems = (ai.contributing_factors || []).map(f => `<li>${esc(f)}</li>`).join("");

    const escalationHtml = ai.escalation_required
        ? `<div class="escalation-banner escalation-yes">Escalation recommended: ${esc(ai.escalation_team || "Engineering")}</div>`
        : `<div class="escalation-banner escalation-no">No escalation required at this time.</div>`;

    el.innerHTML = `
        <h3>AI Investigation</h3>
        <div class="ai-root-cause">${esc(ai.probable_root_cause)}</div>
        <span class="confidence-badge confidence-${ai.confidence}">Confidence: ${ai.confidence}</span>

        ${evidenceItems ? `<div class="sub-heading">Evidence</div><ul class="evidence-list">${evidenceItems}</ul>` : ""}
        ${assumptionItems ? `<div class="sub-heading">Assumptions</div><ul class="assumption-list">${assumptionItems}</ul>` : ""}
        ${factorItems ? `<div class="sub-heading">Contributing Factors</div><ul class="factor-list">${factorItems}</ul>` : ""}
        ${actionItems ? `<div class="sub-heading">Recommended Actions</div><ul class="action-list">${actionItems}</ul>` : ""}
        ${escalationHtml}
    `;
}

// === Summary ===
function renderSummary(ai) {
    const el = document.getElementById("summarySection");
    const summary = ai ? ai.summary : "No summary available.";
    el.innerHTML = `
        <h3>
            Incident Summary
            <button class="btn btn-copy" onclick="copySummary()">Copy</button>
        </h3>
        <div class="summary-text" id="summaryText">${esc(summary)}</div>
    `;
}

function copySummary() {
    const text = document.getElementById("summaryText").textContent;
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.querySelector(".btn-copy");
        btn.textContent = "Copied!";
        setTimeout(() => btn.textContent = "Copy", 1500);
    });
}

// === Timeline ===
function renderTimeline(timeline) {
    const el = document.getElementById("timelineSection");
    if (!timeline || !timeline.length) {
        el.innerHTML = "<h3>Timeline</h3><p style='color:var(--text-muted)'>No notable events.</p>";
        return;
    }
    const items = timeline.slice(0, 30).map(t => {
        const time = new Date(t.timestamp).toLocaleTimeString();
        return `
            <li class="timeline-item level-${t.level}">
                <span class="timeline-time">${time}</span>
                <span class="timeline-service">${t.service}</span>
                <span class="timeline-msg">${esc(t.message)}</span>
            </li>
        `;
    }).join("");
    el.innerHTML = `
        <h3>Timeline</h3>
        <ul class="timeline-list">${items}</ul>
    `;
}

// === Util ===
function esc(str) {
    if (!str) return "";
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
}
