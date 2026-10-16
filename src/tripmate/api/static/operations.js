"use strict";
const el = id => document.getElementById(id);
let csrf = "", session = "", identity = null, intake = null, currentCase = null;
let busy = false;
let planningConnected = false;
let modelConfigured = false;
const pendingKeys = new Map();
async function api(action, body) {
  const path = "/api/operations/" + action;
  const headers = {"X-Ops-Session": session};
  let options = {headers};
  let fingerprint;
  if (body !== undefined) {
    // Retain the same key after a lost response; a deliberate new command gets a new key.
    if (action !== "session") {
      fingerprint = JSON.stringify([session, action, body]);
      if (!pendingKeys.has(fingerprint)) pendingKeys.set(fingerprint, crypto.randomUUID());
      body = {...body, requestKey: pendingKeys.get(fingerprint)};
    }
    options = {method: "POST", headers: {...headers, "Content-Type": "application/json", "X-TripMate-Token": csrf}, body: JSON.stringify(body)};
  }
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || data.error);
  if (fingerprint) pendingKeys.delete(fingerprint);
  return data;
}
async function task(work) {
  if (busy) return;
  busy = true;
  for (const b of document.querySelectorAll("button")) b.disabled = true;
  try { await work(); }
  catch (error) { el("ops-notice").textContent = error.message + " Reload the case status before retrying."; el("ops-notice").classList.add("error"); }
  finally {
    busy = false;
    for (const b of document.querySelectorAll("button")) b.disabled = false;
    controls();
  }
}
function message(text) { el("ops-notice").textContent = text; el("ops-notice").classList.remove("error"); }
const categoryNames = {TRAVEL_PLANNING: "Plan a trip", PLAN_REVISION: "Revise a plan", DISRUPTION: "Travel disruption", COMPLAINT: "Complaint", MEMBERSHIP: "Membership support", ROUTINE_ENQUIRY: "Service enquiry", SUPPLIER_COOPERATION: "Supplier cooperation", INVENTORY: "Supplier inventory", OFFER: "Supplier offer", PRICE_NEGOTIATION: "Supplier price discussion"};
function summaryText(kind, f) {
  const lines = [categoryNames[kind]];
  if (f.origin) lines.push("From: " + f.origin, "To: " + f.destination, "Travellers: " + f.partySize,
    "Dates: " + f.travelDates.startDate + " to " + f.travelDates.endDate, "Total budget: AUD " + f.budgetCeiling.amount,
    "Preference mode: " + f.rankingMode.toLowerCase());
  if (f.preferences?.length) lines.push("Preferences: " + f.preferences.join("; "));
  for (const constraint of f.constraints || []) lines.push(constraint.description + ": " + constraint.value);
  if (f.details) lines.push("Request: " + f.details);
  if (f.planId) lines.push("Affected plan: " + f.planId);
  if (f.baselineVersionId) lines.push("Baseline proposal: " + f.baselineVersionId);
  return lines.join("\n");
}
function fields() {
  const kind = el("category").value;
  let values;
  if (kind === "TRAVEL_PLANNING" || kind === "PLAN_REVISION") {
    values = {origin: el("origin").value, destination: el("destination").value,
      partySize: Number(el("party-size").value), budgetCeiling: {amount: Number(el("ops-budget").value).toFixed(2), currency: "AUD"},
      travelDates: {startDate: el("start-date").value, endDate: el("end-date").value}, rankingMode: el("ranking").value,
      preferences: el("preferences").value ? [el("preferences").value] : [], constraints: []};
    if (el("baggage").value !== "") values.constraints.push({kind: "BAGGAGE", value: Number(el("baggage").value), description: "Confirmed baggage allowance in kilograms"});
    if (el("transfers").value !== "") values.constraints.push({kind: "TRANSFER_LIMIT", value: Number(el("transfers").value), description: "Confirmed maximum transfers"});
    if (el("accessibility").checked) values.constraints.push({kind: "ACCESSIBILITY", value: true, description: "Accessible services required"});
    if (kind === "PLAN_REVISION") values.baselineVersionId = el("baseline").value;
  } else {
    values = {details: el("request-text").value};
    if (["DISRUPTION", "COMPLAINT"].includes(kind)) values.planId = el("affected-plan").value;
  }
  return [{caseType: kind, fields: values}];
}
function categoryFields() {
  const kind = el("category").value;
  el("travel-fields").hidden = !["TRAVEL_PLANNING", "PLAN_REVISION"].includes(kind);
  el("baseline-field").hidden = kind !== "PLAN_REVISION";
  el("trip-field").hidden = !["DISRUPTION", "COMPLAINT"].includes(kind);
}
function showIntake() {
  el("confirmation").hidden = false;
  el("confirmed").checked = false;
  el("summary").textContent = intake.intents.map(i => summaryText(i.caseType, i.fields)).join("\n\n");
  el("questions").textContent = intake.questions.join(" ") || "Review all details. Nothing has been routed yet.";
  message("Request captured · " + intake.state.replaceAll("_", " ") + ". Explicit confirmation is required.");
}
async function reloadCases() {
  const data = await api("cases");
  el("case-list").replaceChildren();
  if (!data.cases.length) { const li = document.createElement("li"); li.textContent = "No confirmed cases for this identity. Start with a request."; el("case-list").append(li); }
  for (const item of data.cases) {
    const li = document.createElement("li"), button = document.createElement("button"), state = document.createElement("span");
    button.className = "text-button"; button.textContent = categoryNames[item.case.caseType] + " · " + item.case.caseId.slice(0, 8);
    state.textContent = item.case.status.replaceAll("_", " ");
    button.addEventListener("click", () => task(() => loadCase(item.case.caseId)));
    li.append(button, state); el("case-list").append(li);
  }
}
async function loadCase(id) {
  currentCase = await api("case?caseId=" + encodeURIComponent(id));
  el("case-detail").hidden = false;
  el("case-status").textContent = currentCase.case.status.replaceAll("_", " ") + " · VERSION " + currentCase.revision;
  el("case-summary").textContent = summaryText(currentCase.case.caseType, currentCase.fields);
  const c = currentCase.case;
  el("case-reason").textContent = c.errors.map(e => e.message).concat(c.unresolvedQuestions, c.entitlementDecision ? [c.entitlementDecision.reason] : []).join(" ");
  el("response-text").textContent = currentCase.response || (c.status === "READY_TO_RESPOND" ? "Your checked response is ready. Select Receive checked response to view it." : "A checked response is not available yet.");
  el("operator-review").hidden = identity.role !== "OPERATOR";
  el("edited-response").value = "";
  el("exception-investigation").hidden = !currentCase.exception;
  el("exception-evidence").textContent = "";
  if (currentCase.exception) {
    el("exception-stage").textContent = currentCase.exception.exceptionStage.replaceAll("_", " ");
    const data = await api("exception?caseId=" + encodeURIComponent(id));
    el("exception-evidence").textContent = JSON.stringify(data.investigation, null, 2);
  }
  const proposalPending = Boolean(currentCase.exception?.exceptionApprovalId);
  el("operator-decision").querySelector('[value="APPROVE"]').textContent = proposalPending ? "Approve current Exception proposal" : "Approve current response";
  el("edited-response").disabled = proposalPending;
  el("recovery-selection").hidden = !currentCase.recoveryOptions;
  el("recovery-options").replaceChildren();
  if (currentCase.recoveryOptions) {
    const presented = currentCase.recoveryOptions;
    for (const [index, option] of presented.options.entries()) {
      const box = document.createElement("div"), description = document.createElement("p"), button = document.createElement("button");
      description.textContent = option.currency + " " + option.totalCost + " total · arrival change " + option.arrivalChangeMinutes + " minutes · " + option.terms;
      button.textContent = "Confirm option " + (index + 1);
      button.dataset.recoveryChoice = "true";
      button.addEventListener("click", () => task(() => caseCommand("exception-selection", {runId: presented.runId, optionId: option.offerId, confirmed: true})));
      box.append(description, button); el("recovery-options").append(box);
    }
    const decline = document.createElement("button");
    decline.textContent = "Decline all options and ask for a human"; decline.className = "secondary";
    decline.dataset.recoveryChoice = "true";
    decline.addEventListener("click", () => task(() => caseCommand("exception-selection", {runId: presented.runId, optionId: null, confirmed: true})));
    el("recovery-options").append(decline);
  }
  const {events} = await api("traces?caseId=" + encodeURIComponent(id));
  el("case-history").replaceChildren();
  for (const event of events) {
    const li = document.createElement("li"); li.textContent = event.eventType.replaceAll("_", " ") + " · " + event.result + " · " + new Date(event.timestamp).toLocaleString();
    if (identity.role === "OPERATOR" && event.summary) li.textContent += " · " + event.summary;
    el("case-history").append(li);
  }
  controls();
}
function controls() {
  if (busy) return;
  el("confirm-request").disabled = !intake || !el("confirmed").checked || intake.questions.length > 0 || !identity.verified;
  el("read-plan").disabled = !planningConnected;
  el("adopt-plan").disabled = !planningConnected;
  el("interpret-request").disabled = !modelConfigured || identity?.verified !== true;
  el("intake-form").hidden = identity?.role === "OPERATOR";
  if (!currentCase) return;
  const state = currentCase.case.status, operator = identity.role === "OPERATOR", closed = ["CLOSED", "WITHDRAWN"].includes(state);
  el("dispatch-case").disabled = operator || !["CONFIRMED", "ASSIGNED"].includes(state);
  el("deliver-case").disabled = operator || state !== "READY_TO_RESPOND";
  el("human-case").disabled = operator || closed;
  el("withdraw-case").disabled = operator || closed;
  el("clarify-case").disabled = operator || ["CLOSED", "WITHDRAWN", "IN_PROGRESS", "HUMAN_ASSISTANCE"].includes(state);
  el("review-case").disabled = !operator || closed;
  el("close-case").disabled = !operator || closed;
  for (const button of document.querySelectorAll('[data-recovery-choice]')) button.disabled = !currentCase.canSelectRecovery;
}
async function caseCommand(action, extra={}) {
  if (!currentCase) throw new Error("Choose a case first.");
  const id = currentCase.case.caseId;
  await api(action, {caseId: id, revision: currentCase.revision, ...extra});
  await reloadCases(); await loadCase(id);
  message("Case updated. " + currentCase.case.status.replaceAll("_", " ") + ".");
}
el("identity-form").addEventListener("submit", event => { event.preventDefault(); task(async () => {
  const data = await api("session", {identityId: el("identity").value}); session = data.session; identity = data.identity;
  currentCase = null; intake = null; el("confirmation").hidden = true; el("case-detail").hidden = true;
  for (const option of el("category").options) option.disabled = identity.role === "SUPPLIER" ? !["SUPPLIER_COOPERATION", "INVENTORY", "OFFER", "PRICE_NEGOTIATION"].includes(option.value) : ["SUPPLIER_COOPERATION", "INVENTORY", "OFFER", "PRICE_NEGOTIATION"].includes(option.value);
  el("category").value = identity.role === "SUPPLIER" ? "SUPPLIER_COOPERATION" : "TRAVEL_PLANNING";
  categoryFields();
  el("desk").hidden = false; el("member-panel").hidden = identity.role !== "TRAVELLER";
  el("plan-panel").hidden = identity.role !== "TRAVELLER";
  el("analysis-panel").hidden = identity.role !== "OPERATOR";
  el("route-map").hidden = true; el("advertisement").hidden = true; el("membership-result").textContent = "";
  await reloadCases(); message("Simulated " + identity.role.toLowerCase() + " identity selected. " + (identity.verified ? "Local evidence verified." : "Unverified identity: protected actions are blocked."));
}); });
el("category").addEventListener("change", categoryFields);
el("confirmed").addEventListener("change", controls);
el("intake-form").addEventListener("submit", event => { event.preventDefault(); task(async () => {
  if (!identity) throw new Error("Select a simulated identity first.");
  if (intake && !intake.caseIds.length && ["AWAITING_CONFIRMATION", "AWAITING_VERIFICATION"].includes(intake.state) && !el("interpret-request").checked)
    intake = await api("update-intake", {intakeId: intake.id, revision: intake.revision, intents: fields()});
  else {
    const body = {text: el("request-text").value};
    if (!el("interpret-request").checked) body.intents = fields();
    intake = await api("intake", body);
  }
  showIntake();
}); });
el("confirm-request").addEventListener("click", () => task(async () => {
  if (!el("confirmed").checked) throw new Error("Confirm the displayed summary first.");
  const result = await api("confirm", {intakeId: intake.id, revision: intake.revision, intents: intake.intents, confirmed: true});
  intake.caseIds = result.caseIds; el("confirmation").hidden = true;
  await reloadCases(); await loadCase(result.caseIds[0]); message("Confirmed. Your case is ready to continue.");
}));
el("intake-human").addEventListener("click", () => task(async () => { intake = await api("update-intake", {intakeId: intake.id, revision: intake.revision, human: true}); showIntake(); }));
el("reload-cases").addEventListener("click", () => task(reloadCases));
el("dispatch-case").addEventListener("click", () => task(() => caseCommand("dispatch")));
el("deliver-case").addEventListener("click", () => task(() => caseCommand("deliver")));
el("human-case").addEventListener("click", () => task(() => caseCommand("case-action", {action: "HUMAN"})));
el("withdraw-case").addEventListener("click", () => task(() => caseCommand("case-action", {action: "WITHDRAW"})));
el("clarify-case").addEventListener("click", () => task(async () => {
  if (!window.confirm("Confirm all current form details as the revised case summary? Prior response approval will be invalidated.")) return;
  await caseCommand("clarify", {intents: fields(), confirmed: true});
}));
el("review-case").addEventListener("click", () => task(() => {
  const extra = {decision: el("operator-decision").value, reason: el("review-reason").value};
  if (el("edited-response").value) extra.editedText = el("edited-response").value;
  return caseCommand("review", extra);
}));
el("close-case").addEventListener("click", () => task(() => caseCommand("case-action", {action: "CLOSE_CASE", reason: el("review-reason").value})));
async function membership(action) {
  const result = await api("premium", {action});
  el("membership-result").textContent = result.decision.outcome + " · " + result.decision.reason;
  el("advertisement").hidden = result.advertising === "AD_FREE";
  if (action === "ROUTE_MAP") {
    el("route-map").hidden = result.decision.outcome !== "ALLOWED";
    if (result.routePoints) {
      el("map-notice").textContent = result.mapNotice; el("route-buttons").replaceChildren();
      for (const point of result.routePoints) { const button = document.createElement("button"); button.className = "text-button"; button.textContent = point.label;
        button.addEventListener("click", () => { el("route-selection").textContent = point.label + " · B03 simulated itinerary point."; }); el("route-buttons").append(button); }
    }
  }
}
el("check-membership").addEventListener("click", () => task(() => membership("MEMBERSHIP")));
el("check-map").addEventListener("click", () => task(() => membership("ROUTE_MAP")));
el("read-plan").addEventListener("click", () => task(async () => { const data = await api("plan?versionId=" + encodeURIComponent(el("proposal-id").value)); el("plan-result").textContent = JSON.stringify(data, null, 2); }));
el("adopt-plan").addEventListener("click", () => task(async () => {
  const data = await api("adopt", {versionId: el("proposal-id").value, expectedBaseline: el("expected-baseline").value || null, accepted: el("accept-plan").checked});
  el("plan-result").textContent = JSON.stringify(data, null, 2); el("accept-plan").checked = false;
}));
el("analysis-data").value = JSON.stringify({periodStart: "2026-10-01", periodEnd: "2026-10-13", impressions: 100, clicks: 10, costAUD: "20.00",
  qualificationRule: "Consenting domestic-trip enquiry", leads: [{id: "lead-1", campaignId: "simulated-campaign-1", channel: "SIMULATED_CAMPAIGN", createdAt: "2026-10-10", consent: true, qualified: true, converted: true}],
  activeAtStart: ["customer-1", "customer-2"], activeAtEnd: ["customer-1", "new-customer"]}, null, 2);
el("analyse").addEventListener("click", () => task(async () => {
  const data = await api("analysis", {data: JSON.parse(el("analysis-data").value)});
  el("analysis-result").textContent = JSON.stringify(data, (key, value) => value === null ? "Not applicable" : value, 2);
}));
async function start() {
  const status = await (await fetch("/api/status")).json(); csrf = status.csrfToken;
  const data = await api("status");
  planningConnected = data.planning === "INJECTED";
  modelConfigured = data.modelExtraction === "CONFIGURED";
  el("interpret-request").disabled = data.modelExtraction !== "CONFIGURED";
  el("interpret-notice").textContent = data.modelExtraction === "CONFIGURED" ? "Suggested details are unconfirmed. Review every field and answer missing questions before continuing." : "Automatic interpretation is unavailable. You can confirm the form details directly.";
  for (const profile of data.identities) { const option = document.createElement("option"); option.value = profile.id; option.textContent = profile.id + (profile.verified ? "" : " · unverified"); el("identity").append(option); }
  message("Operations desk · simulated business data. Select a role to begin."); categoryFields(); controls();
}
start().catch(error => { message(error.message); el("ops-notice").classList.add("error"); });
