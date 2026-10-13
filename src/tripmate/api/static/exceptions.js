/* Customer Exception's isolated simulation. All server strings rendered as text. */
(() => {
  'use strict';
  const el = id => document.getElementById(id);
  let token = '', enabled = false, busy = false;
  const labels = {SUCCESS: 'Proposal passed simulated checks', HUMAN_ASSISTANCE: 'Human assistance required', APPROVAL_PENDING: 'Awaiting human approval', FAILURE: 'Processing incomplete'};
  const buttons = ['exception-disruption', 'exception-complaint'];
  function lock() { for (const id of buttons) el(id).disabled = !enabled || busy; }
  async function call(path, body) {
    const response = await fetch(path, body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json', 'X-TripMate-Token': token}, body: JSON.stringify(body)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || data.error);
    return data;
  }
  function list(id, entries) {
    el(id).replaceChildren();
    for (const text of entries) { const li = document.createElement('li'); li.textContent = text; el(id).append(li); }
  }
  function display(run) {
    const r = run.result, p = run.proposal;
    el('exception-output').hidden = false;
    el('exception-outcome').textContent = labels[r.status] || r.status;
    el('exception-badge').textContent = r.status + ' · FIXTURE';
    el('exception-next').textContent = r.status === 'SUCCESS' ? 'The result is saved for Operations to review and coordinate follow-up. The case remains open; no booking or payment has changed.' :
      r.status === 'APPROVAL_PENDING' ? 'The approval request is saved and awaits a human decision. No commitment is authorised.' : 'Issues and available evidence are recorded for Operations to coordinate human assistance. The case remains open.';
    const findings = [];
    if (r.status === 'HUMAN_ASSISTANCE') {
      const reasons = {MISSING_REQUIRED_FIELDS:'Required information is incomplete. Additional evidence or clarification is needed.', LOW_CONFIDENCE:'Evidence does not support a reliable conclusion.',
        HUMAN_ASSISTANCE_REQUIRED:'Conflicting evidence, safety or legal concerns, or another issue requires human judgement.', NO_FEASIBLE_ITINERARY:'No alternative meets the confirmed budget and timing requirements.',
        REVIEW_FAILED:'Review did not pass. Clarification or revision is required.', TOOL_UNAVAILABLE:'A required dependency is unavailable.', INVALID_CONTRACT:'Input data or record references are invalid.',
        STALE_EVIDENCE:'Evidence is expired, has an invalid source timestamp, or has unverified freshness.', UNSUPPORTED_CONSTRAINT:'A constraint cannot be validated by this prototype and requires human assessment.'};
      for (const issue of r.errors) findings.push(reasons[issue.code] || issue.message);
      findings.push('Available evidence and specific failure reasons are retained in the full record for Operations to coordinate human handling.');
    }
    if (p && r.status !== 'HUMAN_ASSISTANCE') {
      if (p.options) {
        findings.push('The affected flight and subsequent accommodation and activity have been checked. The original itinerary is preserved.');
        for (const option of p.options) findings.push(`Eligible option ${option.offerId}: total AUD ${option.totalCost}; arrival is ${option.arrivalChangeMinutes} minutes later than the original flight.`);
        for (const option of p.rejectedOptions) findings.push(`Excluded option ${option.offerId}: failed cost, timing, availability or completeness checks. See the full record for specific reasons.`);
        findings.push('Operations should explain the eligible options and cost and timing changes to the traveller for consideration.');
      }
      if (p.delayMinutes !== undefined) {
        findings.push(`Scheduled and actual arrival records establish a ${p.delayMinutes}-minute delay.`);
        findings.push(`Applicable simulated policy: ${p.policyIds.join(', ')}.`);
        findings.push(r.requiresApproval ? 'Restricted requests require human judgement. Refund eligibility and amount remain undetermined.' : 'Explain the documented delay and offer an apology. No refund or compensation entitlement is inferred.');
      }
    }
    list('exception-findings', findings);
    const groups = [
      ['Case confirmation and ownership', ['EXC_INTAKE','EXC_CONFIRMATION_GAPS','EXC_MANUAL_REQUEST','EXC_CONTEXT_OWNER','EXC_SIMULATION','EXC_INTAKE_TIME']],
      ['Evidence provenance, freshness and consistency', ['EXC_INTAKE_SOURCE_IDS','EXC_EVIDENCE_IDS','EXC_SOURCE_IDENTITY','EXC_SOURCE_FRESHNESS','EXC_EVIDENCE_CONSISTENCY']],
      ['Confidence and human oversight', ['EXC_CONFIDENCE','EXC_LEGAL_SAFETY']],
      ['Affected itinerary and service records', ['EXC_ITEM_IDENTIFIERS','EXC_AFFECTED_ITEM','EXC_ITEM_EVIDENCE','EXC_ACTIVE_TRIP','EXC_CANCELLATION','EXC_SERVICE_RECORDS','EXC_SCHEDULE_MATCH','EXC_OBSERVED_SERVICE']],
      ['Budget, timing and itinerary completeness', ['EXC_RECOVERY_SCOPE','EXC_CONSTRAINT_SCOPE','EXC_CONSTRAINT_WINDOW','EXC_FEASIBLE_OPTION']],
      ['Policy evidence and approval requirements', ['EXC_POLICY','EXC_POLICY_EVIDENCE','EXC_REFUND_REQUEST']],
      ['Proposal version and simulated review', ['EXC_REVIEW_BINDING','EXC_REVIEW']]
    ];
    const summaries = [];
    for (const [name, rules] of groups) {
      const checks = r.validationResults.filter(c => rules.includes(c.ruleId));
      if (checks.length) summaries.push(`${checks.every(c => c.outcome === 'PASS') ? '✓ Executed checks passed' : '✕ Action required'} · ${name}`);
    }
    if (r.status === 'HUMAN_ASSISTANCE') summaries.push('Processing stops at the identified issue. Unexecuted checks are not treated as passed.');
    if (r.status === 'APPROVAL_PENDING') summaries.push('Approval pending: the request is saved; no human decision has been recorded.');
    list('exception-checks', summaries);
    el('exception-json').textContent = JSON.stringify(run, null, 2);
  }
  async function history() {
    const data = await call('/api/exception-runs');
    el('exception-history').replaceChildren();
    for (const run of data.runs) {
      const li = document.createElement('li'), button = document.createElement('button');
      button.className = 'text-button';
      button.textContent = `${new Date(run.recordedAt).toLocaleString('en-AU')} · ${run.inputCase.caseType === 'DISRUPTION' ? 'Flight cancellation' : 'Delay complaint'} · ${labels[run.result.status] || run.result.status}`;
      button.addEventListener('click', () => { display(run); el('exception-message').textContent = 'Viewing a saved investigation.'; });
      li.append(button); el('exception-history').append(li);
    }
    if (!data.runs.length) list('exception-history', ['No investigations saved yet.']);
  }
  async function run(kind) {
    if (!enabled || busy) return;
    busy = true; lock(); el('exception-output').hidden = true;
    el('exception-message').textContent = 'Checking simulated evidence, preparing recommendations and saving the investigation…';
    try {
      const saved = await call('/api/exception-demo', {kind, scenario: el('exception-scenario').value});
      display(saved); el('exception-message').textContent = 'Investigation saved. Sources, proposals, review and handoff results are available below.';
      await history();
    } catch (error) { el('exception-message').textContent = 'Processing incomplete: ' + error.message; }
    finally { busy = false; lock(); }
  }
  el('exception-disruption').addEventListener('click', () => run('DISRUPTION'));
  el('exception-complaint').addEventListener('click', () => run('COMPLAINT'));
  el('exception-refresh').addEventListener('click', () => history().catch(e => { el('exception-message').textContent = 'Could not load history: ' + e.message; }));
  call('/api/status').then(async status => {
    token = status.csrfToken; enabled = status.executionMode === 'FIXTURE'; lock();
    el('exception-message').textContent = enabled ? 'Choose a scenario, then select either investigation button above.' : 'Simulation is disabled in the current mode.';
    if (enabled) await history();
  }).catch(error => { el('exception-message').textContent = 'Could not connect to the workbench: ' + error.message; });
})();
