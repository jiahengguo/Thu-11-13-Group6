"use strict";
let token = "";
let fixtureEnabled = false, pricingAvailable = false;
const $ = id => document.getElementById(id);
function setBusy(busy) {
  for (const button of document.querySelectorAll('button')) button.disabled = busy;
  if (!busy) {
    $('planning-form').querySelector('button[type="submit"]').disabled = !fixtureEnabled || !pricingAvailable;
    $('supplier-run').disabled = !fixtureEnabled || !pricingAvailable;
    $('fixture-reset').disabled = !fixtureEnabled;
  }
}
async function api(path, body) {
  const options = body === undefined ? {} : {method: "POST", headers: {"Content-Type": "application/json", "X-TripMate-Token": token}, body: JSON.stringify(body)};
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || data.error || "Request failed");
  return data;
}
function show(title, badge, message, data) {
  $("result-title").textContent = title;
  $("result-badge").textContent = badge;
  $("result-message").textContent = message;
  $("result-json").textContent = JSON.stringify(data, null, 2);
}
async function history() {
  const {checks} = await api("/api/checks");
  $("history").replaceChildren();
  if (!checks.length) {
    const li = document.createElement("li"); li.textContent = "No checks recorded yet."; $("history").append(li);
  }
  for (const item of checks) {
    const li = document.createElement("li"), label = document.createElement("div"), date = document.createElement("small"), outcome = document.createElement("div");
    label.textContent = item.kind === "LLM_SMOKE" ? "Model connection check" : item.kind === 'SUPPLIER_FIXTURE' ? 'Supplier assessment · simulated data' : "Planning · simulated data";
    date.textContent = new Date(item.createdAt).toLocaleString() + " · " + (item.details.modelExecution || "NONE");
    outcome.textContent = item.outcome;
    outcome.className = "outcome" + (item.outcome === "SUCCESS" ? "" : " blocked");
    label.append(date); li.append(label, outcome); $("history").append(li);
  }
}
async function run(path, body, kind) {
  setBusy(true);
  show("Running check…", "RUNNING", "Please wait. The result is not yet available.", {});
  try {
    const data = await api(path, body);
    if (kind === 'supplier') {
      show('Supplier assessment complete.', data.result.status + ' · FIXTURE', data.notice, data);
    } else if (kind === "planning") {
      const ok = data.result.status === "SUCCESS";
      show(ok ? "Planning check complete." : "Plan not released.", data.result.status + " · FIXTURE",
           ok ? "Simulated proposal saved. It has not been accepted or booked." : "The workflow returned a refusal or blocked result. Inspect the reasons below.", data);
    } else show(data.outcome === "SUCCESS" ? "Model connection verified." : "Model check blocked.", data.outcome, data.details.message, data);
    await history();
  } catch (error) { show("Check could not complete.", "ERROR", error.message, {error: error.message}); }
  finally { setBusy(false); }
}
async function fixtures() {
  const data = await api("/api/fixtures");
  $("fixture-summary").textContent = `${data.totalEntities} synthetic records · ${data.scenarios.length} expected-outcome scenarios · Foreign keys: ${data.referentialIntegrity} · ${data.fixtureVersion}`;
  $("fixture-scenarios").replaceChildren();
  for (const scenario of data.scenarios) {
    const li = document.createElement("li"), info = document.createElement("div"), label = document.createElement("strong"), detail = document.createElement("small"), outcome = document.createElement("div");
    label.textContent = scenario.scenarioId;
    detail.textContent = scenario.description;
    outcome.textContent = scenario.expectedOutcome + " · EXPECTED ONLY";
    outcome.className = "outcome";
    info.append(label, detail); li.append(info, outcome); $("fixture-scenarios").append(li);
  }
}
$("fixture-reset").addEventListener("click", async () => {
  if (!window.confirm("Reset B03 fixtures and the separate Planning and Supplier demonstration databases?")) return;
  setBusy(true);
  try {
    const result = await api("/api/fixtures/reset", {});
    show("Synthetic fixtures reset.", "FIXTURE", "Baseline restored. No actual booking or approval was made.", result);
    await fixtures();
  } catch (error) { show("Fixture reset failed", "ERROR", error.message, {error: error.message}); }
  finally { setBusy(false); }
});
$("planning-form").addEventListener("submit", event => {
  event.preventDefault();
  const budget = Number($("budget").value).toFixed(2);
  run("/api/planning-demo", {mode: $("travel-mode").value, budget}, "planning");
});
$("model-check").addEventListener("click", () => run("/api/model-smoke", {}, "model"));
$('supplier-form').addEventListener('submit', event => {
  event.preventDefault();
  run('/api/supplier-demo', {scenario: $('supplier-scenario').value}, 'supplier');
});
$("refresh").addEventListener("click", () => history().catch(e => show("Refresh failed", "ERROR", e.message, {})));
async function start() {
  try {
    const data = await api("/api/status"); token = data.csrfToken;
    fixtureEnabled = data.executionMode === 'FIXTURE';
    pricingAvailable = data.supplierAssessment === 'FIXTURE_AVAILABLE';
    $("backend").textContent = "Connected"; $("database").textContent = data.database === "CONNECTED" ? "Connected" : "Unavailable";
    $("mode").textContent = data.executionMode; $("model").textContent = data.modelConfigured ? "Configured" : "Key needed";
    $("fixture-time").textContent = "Fixture clock: " + data.fixtureTime;
    $("notice").textContent = "B02 foundation · " + data.executionMode + " business data. Four-agent integration, real permissions and approval services are pending.";
    if (data.integration.planning === "NOT_INSTALLED") {
      $("planning-form").querySelector('button[type="submit"]').disabled = true;
      $("planning-form").querySelector('button[type="submit"]').textContent = "Planning module is on a separate branch";
    }
    if (!pricingAvailable) $('supplier-run').textContent = 'Merge B04 pricing to enable assessment';
    setBusy(false);
    await history();
    if (data.executionMode === "FIXTURE") await fixtures();
    else { $("fixture-summary").textContent = "Fixture catalog disabled outside FIXTURE mode."; $("fixture-reset").disabled = true; }
  } catch (error) { $("notice").textContent = "Application unavailable: " + error.message; $("notice").classList.add("error"); $("backend").textContent = "Unavailable"; }
}
start();
