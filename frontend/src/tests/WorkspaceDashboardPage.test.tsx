import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import WorkspaceDashboardPage from '../pages/WorkspaceDashboardPage';
import type { DiscoveryDashboardResponse } from '../types/discovery';

const { fetchDiscoveryDashboardMock } = vi.hoisted(() => ({
  fetchDiscoveryDashboardMock: vi.fn(),
}));

vi.mock('../api/discovery', () => ({
  fetchDiscoveryDashboard: fetchDiscoveryDashboardMock,
}));

const dashboard: DiscoveryDashboardResponse = {
  total_scans: 7,
  scans_by_status: {
    PENDING: 1,
    RUNNING: 1,
    COMPLETE: 4,
    COMPLETED_WITH_WARNINGS: 1,
    FAILED: 0,
  },
  total_findings: 10,
  findings_by_category: { RETIREMENT_INDICATOR: 10 },
  findings_by_review_status: {
    PENDING_REVIEW: 3,
    CONFIRMED: 5,
    DISMISSED: 2,
  },
  pending_reviews: 3,
  recent_scans: [
    {
      scan_id: 'scan-one',
      status: 'COMPLETE',
      documents_processed: 2,
      created_at: '2026-08-01T12:30:00Z',
      completed_at: '2026-08-01T12:31:00Z',
    },
  ],
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <WorkspaceDashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.clearAllMocks();
});

describe('WorkspaceDashboardPage', () => {
  it('keeps every implemented workspace area available while activity loads', () => {
    fetchDiscoveryDashboardMock.mockReturnValue(new Promise(() => undefined));

    renderPage();

    expect(screen.getByRole('heading', { name: 'Workspace home' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Open Document Vault/ })).toHaveAttribute('href', '/documents');
    expect(screen.getByRole('link', { name: /View discovery activity/ })).toHaveAttribute('href', '/discovery');
    expect(screen.getByRole('link', { name: /Manage assets/ })).toHaveAttribute('href', '/assets');
    expect(screen.getByRole('link', { name: /Manage beneficiaries/ })).toHaveAttribute('href', '/beneficiaries');
    expect(screen.getByRole('status')).toHaveTextContent('Loading discovery activity');
  });

  it('summarizes safe discovery activity and links to the review queue', async () => {
    fetchDiscoveryDashboardMock.mockResolvedValue(dashboard);

    renderPage();

    const needsReview = await screen.findByRole('article', { name: 'Needs review' });
    expect(within(needsReview).getByText('3')).toBeInTheDocument();
    expect(within(screen.getByRole('article', { name: 'Discovery scans' })).getByText('7')).toBeInTheDocument();
    expect(within(screen.getByRole('article', { name: 'Recent scans' })).getByText('1')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open review queue' })).toHaveAttribute('href', '/discovery/review');
    expect(screen.getByText('Signals waiting for your review—not verified assets.')).toBeInTheDocument();
  });

  it('explains the review-first workflow in order', () => {
    fetchDiscoveryDashboardMock.mockReturnValue(new Promise(() => undefined));

    renderPage();

    const workflow = screen.getByRole('list');
    expect(within(workflow).getAllByRole('listitem').map((item) => item.querySelector('h3')?.textContent)).toEqual([
      'Document Vault',
      'Discovery',
      'Review queue',
      'Assets',
      'Beneficiaries',
    ]);
  });

  it('shows a nontechnical activity error and retries without hiding workspace links', async () => {
    const user = userEvent.setup();
    fetchDiscoveryDashboardMock
      .mockRejectedValueOnce(new ApiError('C:\\private\\token.txt failed', 500))
      .mockResolvedValueOnce(dashboard);

    renderPage();

    expect(await screen.findByRole('alert')).toHaveTextContent('Your saved information has not been changed.');
    expect(screen.queryByText(/token\.txt/i)).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Open Document Vault/ })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByRole('article', { name: 'Needs review' })).toBeInTheDocument();
    expect(fetchDiscoveryDashboardMock).toHaveBeenCalledTimes(2);
  });
});
