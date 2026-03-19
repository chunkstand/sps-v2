const dashboard = document.getElementById("ops-dashboard");
const endpoint = dashboard?.dataset.metricsEndpoint || "/api/v1/ops/dashboard/metrics";

const statusEl = document.getElementById("ops-status");
const queueDepthEl = document.getElementById("metric-queue-depth");
const contradictionEl = document.getElementById("metric-contradiction-backlog");
const stalledEl = document.getElementById("metric-stalled-review-count");
const queueMeta = document.getElementById("metric-queue-depth-meta");
const contradictionMeta = document.getElementById("metric-contradiction-backlog-meta");
const stalledMeta = document.getElementById("metric-stalled-review-meta");
const refreshButton = document.getElementById("ops-refresh");

function apiHeaders() {
  const token = document.getElementById("ops-bearer-token").value.trim();
  const mtlsHeaderName = document.getElementById("ops-mtls-header-name").value.trim();
  const mtlsHeaderValue = document.getElementById("ops-mtls-header-value").value.trim();
  if (!token || !mtlsHeaderName || !mtlsHeaderValue) return null;
  return {
    Authorization: `Bearer ${token}`,
    [mtlsHeaderName]: mtlsHeaderValue,
  };
}

function setStatus(message, variant) {
  statusEl.textContent = message;
  statusEl.classList.remove("error", "success");
  if (variant) {
    statusEl.classList.add(variant);
  }
}

function formatTimestamp(timestamp) {
  if (!timestamp) return "Unknown";
  const parsed = new Date(timestamp);
  if (Number.isNaN(parsed.getTime())) return "Unknown";
  return parsed.toLocaleString();
}

function updateMetrics(payload) {
  queueDepthEl.textContent = payload.queue_depth ?? "—";
  contradictionEl.textContent = payload.contradiction_backlog ?? "—";
  stalledEl.textContent = payload.stalled_review_count ?? "—";

  const generatedAt = formatTimestamp(payload.generated_at);
  queueMeta.textContent = `Generated at ${generatedAt}`;
  contradictionMeta.textContent = `Generated at ${generatedAt}`;

  const stalledBefore = formatTimestamp(payload.stalled_review_before);
  const thresholdHours = payload.stalled_review_threshold_hours ?? "—";
  stalledMeta.textContent = `Stalled before ${stalledBefore} (>${thresholdHours}h)`;

  setStatus(`Last refresh: ${generatedAt}`, "success");
}

async function fetchMetrics() {
  const headers = apiHeaders();
  if (!headers) {
    setStatus("Provide a bearer token and mTLS signal to fetch protected metrics.");
    return;
  }
  setStatus("Fetching metrics snapshot using service-principal auth...");
  try {
    const resp = await fetch(endpoint, { headers });
    const text = await resp.text();
    if (!resp.ok) {
      throw { status: resp.status, body: text };
    }
    const payload = text ? JSON.parse(text) : {};
    updateMetrics(payload);
  } catch (err) {
    const status = err && err.status ? `HTTP ${err.status}` : "HTTP error";
    const body = err && err.body ? err.body : "";
    const message = `Metrics fetch failed.\n${status}\n${body}`.trim();
    setStatus(message, "error");
    console.error("ops.dashboard.metrics_fetch_failed", err);
  }
}

refreshButton?.addEventListener("click", fetchMetrics);

fetchMetrics();
setInterval(fetchMetrics, 30000);
