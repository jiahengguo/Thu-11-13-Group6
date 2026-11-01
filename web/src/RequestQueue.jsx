import React, { useState } from 'react';
import { createPortal } from 'react-dom';

export function QueueMetrics({ cases }) {
  const counts = [
    ['Open requests', cases.filter(({ case: item }) => !['CLOSED', 'WITHDRAWN'].includes(item.status)).length],
    ['Human assistance', cases.filter(({ case: item }) => item.status === 'HUMAN_ASSISTANCE').length],
    ['Ready to respond', cases.filter(({ case: item }) => item.status === 'READY_TO_RESPOND').length],
  ];
  return <>
    {counts.map(([label, count]) => <div className="card" key={label}>
      <span>{label}</span><strong>{count}</strong>
    </div>)}
    <p className="queue-count-note muted">Counts cover all requests, including those hidden by filters.</p>
  </>;
}

export function RequestQueue({ cases = [], labels = {}, states = {}, role, metricsTarget,
  busy = false, loading = true, error = '', selectedCaseId = null, onSelect }) {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('');
  const displayStatus = item => states[item.status] || item.status;
  const search = query.trim().toLowerCase();
  const visible = cases.filter(({ case: item }) =>
    (!status || displayStatus(item) === status) &&
    `${item.caseId} ${labels[item.caseType] || item.caseType} ${displayStatus(item)}`.toLowerCase().includes(search));
  // The two backend review states share one user-facing filter label.
  const statuses = [...new Set([...Object.values(states), ...cases.map(({ case: item }) => displayStatus(item))])];
  return <>
    {role === 'OPERATOR' && metricsTarget && createPortal(<QueueMetrics cases={cases} />, metricsTarget)}
    <fieldset className="queue-controls" disabled={busy}>
      <legend className="visually-hidden">Filter requests</legend>
      <label htmlFor="case-search">Search requests by ID or type
        <input id="case-search" type="search" placeholder="Case ID, e.g. 80e6ba76"
          value={query} onChange={event => setQuery(event.target.value)} />
      </label>
      <label htmlFor="case-status">Request status
        <select id="case-status" value={status} onChange={event => setStatus(event.target.value)}>
          <option value="">All statuses</option>
          {statuses.map(value => <option key={value} value={value}>{value}</option>)}
        </select>
      </label>
      {(query || status) && <button type="button" className="secondary"
        onClick={() => { setQuery(''); setStatus(''); }}>Clear filters</button>}
    </fieldset>
    {loading && <p role="status" className="muted">Loading requests…</p>}
    {error && <p role="alert" className="notice">{error} {cases.length ? 'Showing the last loaded requests.' : ''}</p>}
    {!loading && <p className="queue-result-count muted" role="status">{visible.length} of {cases.length} requests</p>}
    {!loading && !visible.length && <p className="empty">{cases.length || query || status
      ? 'No matching requests. Clear the filters to see all requests.'
      : 'No requests yet. Start a new request to see its progress here.'}</p>}
    <div className="case-list" aria-label="Requests" aria-busy={loading || busy}>
      {visible.map(({ case: item }) => <button type="button" className="case-item" key={item.caseId}
        disabled={busy} aria-pressed={selectedCaseId === item.caseId}
        onClick={() => onSelect(item.caseId)}>
        <strong>{labels[item.caseType] || item.caseType}</strong>
        <span className="tag">{displayStatus(item)}</span>
        <small>{new Date(item.createdAt).toLocaleDateString()} · {item.caseId.slice(0, 8)}</small>
      </button>)}
    </div>
  </>;
}
