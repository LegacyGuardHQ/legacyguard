import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import { AuthProvider } from '../context/AuthContext';
import App from '../pages/App';
import DiscoveryOverviewPage from '../pages/DiscoveryOverviewPage';
import type { DiscoveryDashboardResponse } from '../types/discovery';

const { fetchDiscoveryDashboardMock } = vi.hoisted(() => ({
  fetchDiscoveryDashboardMock: vi.fn(),
}));

vi.mock('../api/discovery', () => ({
  fetchDiscoveryDashboard: fetchDiscoveryDashboardMock,
}));

const populatedDashboard: DiscoveryDashboardResponse = {
  total_scans: 7,
  scans_by_status: {
    PENDING: 1,
    RUNNING: 2,
    COMPLETE: 2,
    COMPLETED_WITH_WARNINGS: 1,
    FAILED: 1,
  },
  total_findings: 10,
  findings_by_category: {
    RETIREMENT_INDICATOR: 4,
    EMPLOYER_BENEFIT_INDICATOR: 2,
    INSURANCE_INDICATOR: 4,
  },
  findings_by_review_status: {
    PENDING_REVIEW: 3,
    CONFIRMED: 5,
    DISMISSED: 2,
  },
  pending_reviews: 3,
  recent_scans: [
    {
      scan_id: 'scan-one',
      status: 'COMPLETED_WITH_WARNINGS',
      documents_processed: 2,
      created_at: '2026-08-01T12:30:00Z',
      completed_at: '2026-08-01T12:31:00Z',
    },
    {
      scan_id: 'scan-two',
      status: 'RUNNING',
      documents_processed: 1,
      created_at: '2026-08-02T09:00:00Z',
      completed_at: null,
    },
  ],
};

const emptyDashboard: DiscoveryDashboardResponse = {
  total_scans: 0,
  scans_by_status: {
    PENDING: 0,
    RUNNING: 0,
    COMPLETE: 0,
    COMPLETED_WITH_WARNINGS: 0,
    FAILED: 0,
  },
  total_findings: 0,
  findings_by_category: {},
  findings_by_review_status: {
    PENDING_REVIEW: 0,
    CONFIRMED: 0,
    DISMISSED: 0,
  },
  pending_reviews: 0,
  recent_scans: [],
};

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

function renderDashboard() {
  const queryClient = createQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/discovery']}>
        <DiscoveryOverviewPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function expectSummaryValue(sectionName: string, label: string, value: number) {
  const section = screen.getByRole('region', { name: sectionName });
  const term = within(section).getByText(label);
  const row = term.closest('.summary-row');

  expect(row).not.toBeNull();
  expect(within(row as HTMLElement).getByText(String(value))).toBeInTheDocument();
}

afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe('DiscoveryOverviewPage', () => {
  it('shows a reassuring loading state while dashboard data is pending', () => {
    fetchDiscoveryDashboardMock.mockReturnValue(new Promise(() => undefined));
    vi.stubGlobal('fetch', vi.fn());

    renderDashboard();

    expect(screen.getByText('Securely loading your discovery activity.')).toBeInTheDocument();
    expect(fetchDiscoveryDashboardMock).toHaveBeenCalledOnce();
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it('renders all dashboard aggregates exactly without making a real network request', async () => {
    fetchDiscoveryDashboardMock.mockResolvedValue(populatedDashboard);
    vi.stubGlobal('fetch', vi.fn());

    renderDashboard();

    expect(await screen.findByRole('article', { name: 'Total scans' })).toBeInTheDocument();

    expect(within(screen.getByRole('article', { name: 'Total scans' })).getByText('7')).toBeInTheDocument();
    expect(within(screen.getByRole('article', { name: 'Total findings' })).getByText('10')).toBeInTheDocument();
    expect(within(screen.getByRole('article', { name: 'Needs review' })).getByText('3')).toBeInTheDocument();

    expectSummaryValue('Scan status', 'Queued', 1);
    expectSummaryValue('Scan status', 'Processing', 2);
    expectSummaryValue('Scan status', 'Complete', 2);
    expectSummaryValue('Scan status', 'Complete with warnings', 1);
    expectSummaryValue('Scan status', 'Failed', 1);

    expectSummaryValue('Review status', 'Needs review', 3);
    expectSummaryValue('Review status', 'Confirmed', 5);
    expectSummaryValue('Review status', 'Dismissed', 2);

    expectSummaryValue('Findings by category', 'Employer Benefit Indicator', 2);
    expectSummaryValue('Findings by category', 'Insurance Indicator', 4);
    expectSummaryValue('Findings by category', 'Retirement Indicator', 4);

    expect(fetchDiscoveryDashboardMock).toHaveBeenCalledOnce();
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it('shows a safe empty state when no discovery activity exists', async () => {
    fetchDiscoveryDashboardMock.mockResolvedValue(emptyDashboard);

    renderDashboard();

    expect(await screen.findByRole('heading', { name: 'No discovery activity yet' })).toBeInTheDocument();
    expect(screen.getByText(/Activity will appear here after supported documents are uploaded/)).toBeInTheDocument();
    expect(screen.queryByRole('article', { name: 'Total scans' })).not.toBeInTheDocument();
  });

  it('shows a nontechnical error with recovery guidance and can retry', async () => {
    const user = userEvent.setup();
    fetchDiscoveryDashboardMock
      .mockRejectedValueOnce(new ApiError('C:\\private\\token.txt failed', 500))
      .mockResolvedValueOnce(populatedDashboard);

    renderDashboard();

    expect(await screen.findByRole('heading', { name: 'We couldn’t load your discovery activity.' })).toBeInTheDocument();
    expect(screen.getByText(/Your saved information has not been changed/)).toBeInTheDocument();
    expect(screen.queryByText(/token\.txt/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByRole('article', { name: 'Total scans' })).toBeInTheDocument();
    expect(fetchDiscoveryDashboardMock).toHaveBeenCalledTimes(2);
  });

  it('links recent scans to their existing detail routes', async () => {
    fetchDiscoveryDashboardMock.mockResolvedValue(populatedDashboard);

    renderDashboard();

    const recentScans = await screen.findByRole('region', { name: 'Recent scans' });
    const links = within(recentScans).getAllByRole('link');

    expect(links.some((link) => link.getAttribute('href') === '/discovery/scans/scan-one')).toBe(true);
    expect(links.some((link) => link.getAttribute('href') === '/discovery/scans/scan-two')).toBe(true);
  });

  it('links pending review guidance to the existing review route', async () => {
    fetchDiscoveryDashboardMock.mockResolvedValue(populatedDashboard);

    renderDashboard();

    expect(await screen.findByRole('link', { name: 'Open review queue' })).toHaveAttribute(
      'href',
      '/discovery/review',
    );
  });

  it('remains behind the existing authentication boundary', async () => {
    const queryClient = createQueryClient();
    vi.stubGlobal('fetch', vi.fn());

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/discovery']}>
          <AuthProvider>
            <App />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
    expect(fetchDiscoveryDashboardMock).not.toHaveBeenCalled();
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });
});
