import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RequestQueue } from './RequestQueue.jsx';
import { mountQueue } from './queue-entry.jsx';

afterEach(() => { cleanup(); document.body.replaceChildren(); });

const labels = { TRAVEL_PLANNING: 'Travel planning', COMPLAINT: 'Complaint' };
const states = { CONFIRMED: 'Request confirmed', HUMAN_ASSISTANCE: 'Human assistance requested',
  READY_TO_RESPOND: 'Checked response ready', CLOSED: 'Closed', UNDER_REVIEW: 'Under review',
  AWAITING_APPROVAL: 'Under review' };
const item = (caseId, status, caseType = 'TRAVEL_PLANNING') => ({
  case: { caseId, status, caseType, createdAt: '2026-11-01T00:00:00Z' },
});
const cases = [item('alpha-1234', 'CONFIRMED'), item('beta-5678', 'HUMAN_ASSISTANCE', 'COMPLAINT'),
  item('gamma-9012', 'READY_TO_RESPOND'), item('delta-3456', 'CLOSED')];
const props = { cases, labels, states, role: 'TRAVELLER', loading: false, onSelect: vi.fn() };
const cards = () => screen.queryAllByRole('button', { pressed: false });

describe('Request queue', () => {
  it.each(['TRAVELLER', 'SUPPLIER', 'OPERATOR'])('renders supplied authorized cases for %s', role => {
    render(<RequestQueue {...props} role={role} />);
    expect(cards()).toHaveLength(4);
    expect(screen.getByText('4 of 4 requests')).toBeTruthy();
  });

  it('combines case-insensitive ID search and status filters, then clears them', async () => {
    const user = userEvent.setup();
    render(<RequestQueue {...props} />);
    await user.type(screen.getByRole('searchbox'), ' BETA ');
    expect(cards()).toHaveLength(1);
    await user.selectOptions(screen.getByLabelText('Request status'), 'Closed');
    expect(cards()).toHaveLength(0);
    expect(screen.getByText(/No matching requests/)).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Clear filters' }));
    expect(cards()).toHaveLength(4);
  });

  it('searches user-facing request types and statuses', async () => {
    const user = userEvent.setup();
    render(<RequestQueue {...props} />);
    await user.type(screen.getByRole('searchbox'), 'complaint');
    expect(cards()).toHaveLength(1);
    await user.clear(screen.getByRole('searchbox'));
    await user.type(screen.getByRole('searchbox'), 'checked response');
    expect(cards()).toHaveLength(1);
  });

  it('preserves filters and selection through new API data and busy updates', async () => {
    const user = userEvent.setup();
    const view = render(<RequestQueue {...props} selectedCaseId="alpha-1234" />);
    await user.type(screen.getByRole('searchbox'), 'alpha');
    await user.selectOptions(screen.getByLabelText('Request status'), 'Request confirmed');
    view.rerender(<RequestQueue {...props} cases={[...cases, item('alpha-new', 'CONFIRMED')]}
      selectedCaseId="alpha-1234" busy />);
    expect(screen.getByRole('searchbox').value).toBe('alpha');
    expect(screen.getByLabelText('Request status').value).toBe('Request confirmed');
    expect(screen.getByRole('button', { pressed: true }).textContent).toContain('alpha-12');
    expect(cards()).toHaveLength(1);
  });

  it('blocks queue actions and filter editing while a command is busy', async () => {
    const user = userEvent.setup(), onSelect = vi.fn();
    render(<RequestQueue {...props} busy onSelect={onSelect} />);
    await user.click(cards()[0]);
    await user.type(screen.getByRole('searchbox'), 'alpha');
    expect(onSelect).not.toHaveBeenCalled();
    expect(screen.getByRole('searchbox').value).toBe('');
    expect(cards().every(button => button.disabled)).toBe(true);
  });

  it('passes the exact selected ID to the existing business callback', async () => {
    const user = userEvent.setup(), onSelect = vi.fn();
    render(<RequestQueue {...props} onSelect={onSelect} />);
    await user.click(cards()[1]);
    expect(onSelect).toHaveBeenCalledExactlyOnceWith('beta-5678');
  });

  it('keeps operator counts global when the visible list is filtered', async () => {
    const user = userEvent.setup(), target = document.createElement('div');
    document.body.append(target);
    render(<RequestQueue {...props} role="OPERATOR" metricsTarget={target} />);
    await user.type(screen.getByRole('searchbox'), 'delta');
    expect(cards()).toHaveLength(1);
    expect([...target.querySelectorAll('strong')].map(node => node.textContent)).toEqual(['3', '1', '1']);
    expect(target.textContent).toContain('Counts cover all requests');
  });

  it('does not render operator statistics in requester roles', () => {
    const target = document.createElement('div');
    document.body.append(target);
    render(<RequestQueue {...props} metricsTarget={target} />);
    expect(target.children).toHaveLength(0);
  });

  it('retains the last data during loading and exposes refresh errors', () => {
    const view = render(<RequestQueue {...props} loading />);
    expect(screen.getByRole('status').textContent).toBe('Loading requests…');
    expect(cards()).toHaveLength(4);
    view.rerender(<RequestQueue {...props} error="Cloud unavailable." />);
    expect(screen.getByRole('alert').textContent).toContain('Showing the last loaded requests.');
    expect(cards()).toHaveLength(4);
  });

  it('distinguishes an empty queue from filtered-out results', () => {
    render(<RequestQueue {...props} cases={[]} />);
    expect(screen.getByText(/No requests yet/)).toBeTruthy();
  });

  it('groups both review states under the same user-facing filter', async () => {
    const user = userEvent.setup();
    render(<RequestQueue {...props} cases={[item('one', 'UNDER_REVIEW'), item('two', 'AWAITING_APPROVAL')]} />);
    await user.selectOptions(screen.getByLabelText('Request status'), 'Under review');
    expect(cards()).toHaveLength(2);
    expect(screen.getAllByRole('option', { name: 'Under review' })).toHaveLength(1);
  });

  it('escapes server-supplied text instead of interpreting HTML', () => {
    render(<RequestQueue {...props} cases={[item('unsafe', 'CONFIRMED', '<img src=x onerror=alert(1)>')]} />);
    expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeTruthy();
    expect(document.querySelector('img')).toBeNull();
  });

  it('synchronously applies bridge busy updates without resetting search', async () => {
    const user = userEvent.setup(), container = document.createElement('div');
    document.body.append(container);
    const queue = mountQueue(container, null, props);
    await user.type(screen.getByRole('searchbox'), 'beta');
    queue.update({ busy: true, selectedCaseId: 'beta-5678' });
    expect(screen.getByRole('button', { pressed: true }).disabled).toBe(true);
    queue.update({ busy: false });
    expect(screen.getByRole('searchbox').value).toBe('beta');
    expect(screen.getByRole('button', { pressed: true }).disabled).toBe(false);
  });
});
