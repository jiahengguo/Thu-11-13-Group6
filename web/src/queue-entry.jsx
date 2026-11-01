import React from 'react';
import { createRoot } from 'react-dom/client';
import { flushSync } from 'react-dom';
import { RequestQueue } from './RequestQueue.jsx';

// The legacy portal passes authorized summaries and callbacks; React owns only
// these two mount points and never fetches identities or makes business decisions.
export function mountQueue(container, metricsTarget, initialState) {
  const root = createRoot(container);
  let state = { ...initialState, metricsTarget };
  const update = next => {
    state = { ...state, ...next };
    // Keep busy/selection changes synchronous with the portal's command guard.
    flushSync(() => root.render(<RequestQueue {...state} />));
  };
  update({});
  return { update };
}
