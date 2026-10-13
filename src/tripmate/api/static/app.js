"use strict";
let token = "";
const $ = id => document.getElementById(id);
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
    label.textContent = item.kind === "LLM_SMOKE" ? "Model connection check" : "Planning · simulated data";
    date.textContent = new Date(item.createdAt).toLocaleString() + " · " + (item.details.modelExecution || "NONE");
    outcome.textContent = item.outcome;
    outcome.className = "outcome" + (item.outcome === "SUCCESS" ? "" : " blocked");
    label.append(date); li.append(label, outcome); $("history").append(li);
  }
}
async function run(path, body, kind) {
  for (const b of document.querySelectorAll("button")) b.disabled = true;
  show("Running check…", "RUNNING", "Please wait. The result is not yet available.", {});
  try {
    const data = await api(path, body);
    if (kind === "planning") {
      const ok = data.result.status === "SUCCESS";
      show(ok ? "Planning check complete." : "Plan not released.", data.result.status + " · FIXTURE",
           ok ? "Simulated proposal saved. It has not been accepted or booked." : "The workflow returned a refusal or blocked result. Inspect the reasons below.", data);
    } else show(data.outcome === "SUCCESS" ? "Model connection verified." : "Model check blocked.", data.outcome, data.details.message, data);
    await history();
  } catch (error) { show("Check could not complete.", "ERROR", error.message, {error: error.message}); }
  finally { for (const b of document.querySelectorAll("button")) b.disabled = false; }
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
  if (!window.confirm("Reset B03 synthetic fixtures and the separate local Planning demonstration database?")) return;
  for (const b of document.querySelectorAll("button")) b.disabled = true;
  try {
    const result = await api("/api/fixtures/reset", {});
    show("Synthetic fixtures reset.", "FIXTURE", "Baseline restored. No actual booking or approval was made.", result);
    await fixtures();
  } catch (error) { show("Fixture reset failed", "ERROR", error.message, {error: error.message}); }
  finally { for (const b of document.querySelectorAll("button")) b.disabled = false; }
});
$("planning-form").addEventListener("submit", event => {
  event.preventDefault();
  const budget = Number($("budget").value).toFixed(2);
  run("/api/planning-demo", {mode: $("travel-mode").value, budget}, "planning");
});
$("model-check").addEventListener("click", () => run("/api/model-smoke", {}, "model"));
$("refresh").addEventListener("click", () => history().catch(e => show("Refresh failed", "ERROR", e.message, {})));
async function start() {
  try {
    const data = await api("/api/status"); token = data.csrfToken;
    $("backend").textContent = "Connected"; $("database").textContent = data.database === "CONNECTED" ? "Connected" : "Unavailable";
    $("mode").textContent = data.executionMode; $("model").textContent = data.modelConfigured ? "Configured" : "Key needed";
    $("fixture-time").textContent = "Fixture clock: " + data.fixtureTime;
    $("notice").textContent = "Shared workspace · " + data.executionMode + " business data. Operations has a local simulation desk; four-agent integration and production authentication remain pending.";
    if (data.integration.planning === "NOT_INSTALLED") {
      $("planning-form").querySelector('button[type="submit"]').disabled = true;
      $("planning-form").querySelector('button[type="submit"]').textContent = "Planning module is on a separate branch";
    }
    await history();
    if (data.executionMode === "FIXTURE") await fixtures();
    else { $("fixture-summary").textContent = "Fixture catalog disabled outside FIXTURE mode."; $("fixture-reset").disabled = true; }
  } catch (error) { $("notice").textContent = "Application unavailable: " + error.message; $("notice").classList.add("error"); $("backend").textContent = "Unavailable"; }
}
start();
