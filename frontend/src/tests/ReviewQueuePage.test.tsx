import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import ProtectedRoute from '../components/ProtectedRoute';
import { AuthProvider } from '../context/AuthContext';
import ReviewQueuePage from '../pages/ReviewQueuePage';
import type {
  DiscoveryFindingCategory,
  DiscoveryReviewStatus,
  EvidenceFindingResponse,
  PaginatedEvidenceFindingResponse,
} from '../types/discovery';

const { fetchDiscoveryReviewQueueMock, updateDiscoveryFindingStatusMock } = vi.hoisted(() => ({
  fetchDiscoveryReviewQueueMock: vi.fn(),
  updateDiscoveryFindingStatusMock: vi.fn(),
}));

vi.mock('../api/discovery', () => ({
  fetchDiscoveryReviewQueue: fetchDiscoveryReviewQueueMock,
  updateDiscoveryFindingStatus: updateDiscoveryFindingStatusMock,
}));

const findingsByStatus: Record<DiscoveryReviewStatus, EvidenceFindingResponse> = {
  PENDING_REVIEW: {
    finding_id: 'finding-pending',
    category: 'RETIREMENT_INDICATOR',
    confidence_score: 85,
    review_status: 'PENDING_REVIEW',
    created_at: '2026-08-01T10:00:00Z',
  },
  CONFIRMED: {
    finding_id: 'finding-confirmed',
    category: 'INSURANCE_INDICATOR',
    confidence_score: 91,
    review_status: 'CONFIRMED',
    created_at: '2026-08-01T11:00:00Z',
  },
  DISMISSED: {
    finding_id: 'finding-dismissed',
    category: 'BANKING_INDICATOR',
    confidence_score: 72,
    review_status: 'DISMISSED',
    created_at: '2026-08-01T12:00:00Z',
  },
};

function queuePayload(status: DiscoveryReviewStatus): PaginatedEvidenceFindingResponse {
  return {
    items: [findingsByStatus[status]],
    total_count: 1,
    page: 1,
    page_size: 10,
    total_pages: 1,
  };
}

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderReviewQueue() {
  const queryClient = createQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/discovery/review']}>
        <ReviewQueuePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function selectCategory(user: ReturnType<typeof userEvent.setup>, category: DiscoveryFindingCategory) {
  const select = screen.getByRole('combobox', { name: 'Category' });
  await waitFor(() => expect(select).toBeEnabled());
  await user.selectOptions(select, category);
}

afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe('ReviewQueuePage', () => {
  it('renders whole-number confidence with accessible status and category filters', async () => {
    fetchDiscoveryReviewQueueMock.mockResolvedValue(queuePayload('PENDING_REVIEW'));
    vi.stubGlobal('fetch', vi.fn());

    renderReviewQueue();

    expect(await screen.findByText('85%')).toBeInTheDocument();
    expect(screen.queryByText('8500%')).not.toBeInTheDocument();
    expect(screen.getByText('Findings that still need your review before they are treated as confirmed or dismissed.')).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Category' })).toHaveValue('');
    expect(screen.getAllByRole('option')).toHaveLength(10);

    const tabList = screen.getByRole('tablist', { name: 'Review status filters' });
    const pendingTab = within(tabList).getByRole('tab', { name: 'Pending Review' });
    const confirmedTab = within(tabList).getByRole('tab', { name: 'Confirmed' });
    const panel = screen.getByRole('tabpanel', { name: 'Pending Review' });

    expect(pendingTab).toHaveAttribute('aria-selected', 'true');
    expect(confirmedTab).toHaveAttribute('aria-selected', 'false');
    expect(pendingTab).toHaveAttribute('aria-controls', panel.id);
    expect(panel).toHaveAttribute('aria-labelledby', pendingTab.id);
    expect(fetchDiscoveryReviewQueueMock).toHaveBeenCalledWith(1, 10, 'PENDING_REVIEW', null);
    expect(screen.getByRole('link', { name: /View finding details/ })).toHaveAttribute(
      'href',
      '/discovery/findings/finding-pending'
    );
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it('loads a selected category without showing stale findings', async () => {
    const user = userEvent.setup();
    let resolveInsurance!: (payload: PaginatedEvidenceFindingResponse) => void;
    const insuranceRequest = new Promise<PaginatedEvidenceFindingResponse>((resolve) => {
      resolveInsurance = resolve;
    });
    fetchDiscoveryReviewQueueMock.mockImplementation(
      (
        _page: number,
        _pageSize: number,
        status: DiscoveryReviewStatus,
        category: DiscoveryFindingCategory | null
      ) => category === 'INSURANCE_INDICATOR' ? insuranceRequest : Promise.resolve(queuePayload(status))
    );

    renderReviewQueue();

    expect(await screen.findByText('Retirement Indicator', { selector: '.category-badge' })).toBeInTheDocument();
    await selectCategory(user, 'INSURANCE_INDICATOR');

    expect(screen.getByText(/Loading discovery review queue/i).closest('.loading-card')).toBeInTheDocument();
    expect(screen.queryByText('Retirement Indicator', { selector: '.category-badge' })).not.toBeInTheDocument();
    expect(fetchDiscoveryReviewQueueMock).toHaveBeenLastCalledWith(
      1,
      10,
      'PENDING_REVIEW',
      'INSURANCE_INDICATOR'
    );

    await act(async () => {
      resolveInsurance({
        ...queuePayload('PENDING_REVIEW'),
        items: [{ ...findingsByStatus.PENDING_REVIEW, category: 'INSURANCE_INDICATOR' }],
      });
    });

    expect(await screen.findByText('Insurance Indicator', { selector: '.category-badge' })).toBeInTheDocument();
  });

  it('allows clearing the category filter from the page', async () => {
    const user = userEvent.setup();
    fetchDiscoveryReviewQueueMock.mockImplementation(
      (
        _page: number,
        _pageSize: number,
        status: DiscoveryReviewStatus,
        category: DiscoveryFindingCategory | null
      ) => Promise.resolve({
        items: category ? [{ ...findingsByStatus[status], category }] : [findingsByStatus[status]],
        total_count: 1,
        page: 1,
        page_size: 10,
        total_pages: 1,
      })
    );

    renderReviewQueue();

    await screen.findByText('Retirement Indicator', { selector: '.category-badge' });
    await selectCategory(user, 'INSURANCE_INDICATOR');

    expect(await screen.findByText('Insurance Indicator', { selector: '.category-badge' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Clear category filter' }));

    expect(screen.getByRole('combobox', { name: 'Category' })).toHaveValue('');
    expect(await screen.findByText('Retirement Indicator', { selector: '.category-badge' })).toBeInTheDocument();
    expect(fetchDiscoveryReviewQueueMock).toHaveBeenLastCalledWith(1, 10, 'PENDING_REVIEW', null);
  });

  it('summarizes the current review view and active category filter', async () => {
    const user = userEvent.setup();
    fetchDiscoveryReviewQueueMock.mockImplementation(
      (
        _page: number,
        _pageSize: number,
        status: DiscoveryReviewStatus,
        category: DiscoveryFindingCategory | null
      ) => Promise.resolve({
        items: category ? [{ ...findingsByStatus[status], category }] : [findingsByStatus[status]],
        total_count: 1,
        page: 1,
        page_size: 10,
        total_pages: 1,
      })
    );

    renderReviewQueue();

    expect(await screen.findByText('Showing pending review findings (1 total)')).toBeInTheDocument();

    await selectCategory(user, 'INSURANCE_INDICATOR');

    expect(await screen.findByText('Showing pending review findings filtered by Insurance Indicator (1 total)')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Clear category filter' })).toBeInTheDocument();
  });

  it('resets pagination for category and status changes while preserving filtered navigation', async () => {
    const user = userEvent.setup();
    fetchDiscoveryReviewQueueMock.mockImplementation(
      (
        page: number,
        pageSize: number,
        status: DiscoveryReviewStatus,
        category: DiscoveryFindingCategory | null
      ): Promise<PaginatedEvidenceFindingResponse> => Promise.resolve({
        items: [{
          ...findingsByStatus[status],
          finding_id: `${status}-${category ?? 'all'}-${page}`,
          category: category ?? findingsByStatus[status].category,
        }],
        total_count: 2,
        page,
        page_size: pageSize,
        total_pages: 2,
      })
    );

    renderReviewQueue();

    await screen.findByText('Retirement Indicator', { selector: '.category-badge' });
    await user.click(screen.getByRole('button', { name: 'Next' }));
    expect(await screen.findByText('Page 2 of 2 (2 items)')).toBeInTheDocument();
    expect(fetchDiscoveryReviewQueueMock).toHaveBeenLastCalledWith(
      2,
      10,
      'PENDING_REVIEW',
      null
    );

    await selectCategory(user, 'INSURANCE_INDICATOR');
    await waitFor(() => expect(fetchDiscoveryReviewQueueMock).toHaveBeenLastCalledWith(
      1,
      10,
      'PENDING_REVIEW',
      'INSURANCE_INDICATOR'
    ));
    expect(await screen.findByText('Page 1 of 2 (2 items)')).toBeInTheDocument();
    expect(await screen.findByText('Insurance Indicator', { selector: '.category-badge' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Next' }));
    expect(await screen.findByText('Page 2 of 2 (2 items)')).toBeInTheDocument();
    expect(fetchDiscoveryReviewQueueMock).toHaveBeenLastCalledWith(
      2,
      10,
      'PENDING_REVIEW',
      'INSURANCE_INDICATOR'
    );

    await user.click(screen.getByRole('button', { name: 'Previous' }));
    expect(await screen.findByText('Page 1 of 2 (2 items)')).toBeInTheDocument();
    expect(fetchDiscoveryReviewQueueMock).toHaveBeenLastCalledWith(
      1,
      10,
      'PENDING_REVIEW',
      'INSURANCE_INDICATOR'
    );

    await user.click(screen.getByRole('button', { name: 'Next' }));
    expect(await screen.findByText('Page 2 of 2 (2 items)')).toBeInTheDocument();
    expect(fetchDiscoveryReviewQueueMock).toHaveBeenLastCalledWith(
      2,
      10,
      'PENDING_REVIEW',
      'INSURANCE_INDICATOR'
    );

    await user.click(screen.getByRole('tab', { name: 'Confirmed' }));
    await waitFor(() => expect(fetchDiscoveryReviewQueueMock).toHaveBeenLastCalledWith(
      1,
      10,
      'CONFIRMED',
      'INSURANCE_INDICATOR'
    ));
    expect(await screen.findByText('Page 1 of 2 (2 items)')).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: 'Reopen' })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Category' })).toHaveValue('INSURANCE_INDICATOR');
  });

  it('shows a filter-specific empty state', async () => {
    const user = userEvent.setup();
    fetchDiscoveryReviewQueueMock.mockImplementation(
      (
        _page: number,
        _pageSize: number,
        status: DiscoveryReviewStatus,
        category: DiscoveryFindingCategory | null
      ) => Promise.resolve(category ? {
        items: [],
        total_count: 0,
        page: 1,
        page_size: 10,
        total_pages: 0,
      } : queuePayload(status))
    );

    renderReviewQueue();

    await screen.findByText('Retirement Indicator', { selector: '.category-badge' });
    await selectCategory(user, 'BANKING_INDICATOR');

    const emptyCard = screen.getByText('No pending review findings match Banking Indicator.').closest('.empty-card');
    expect(await screen.findByText('No pending review findings match Banking Indicator.')).toBeInTheDocument();
    expect(within(emptyCard as HTMLElement).getByRole('button', { name: 'Clear category filter' })).toBeInTheDocument();
  });

  it('offers a quick escape hatch when a tab has no findings', async () => {
    const user = userEvent.setup();
    fetchDiscoveryReviewQueueMock.mockImplementation(
      (_page: number, _pageSize: number, status: DiscoveryReviewStatus) => Promise.resolve(
        status === 'CONFIRMED'
          ? {
              items: [],
              total_count: 0,
              page: 1,
              page_size: 10,
              total_pages: 0,
            }
          : queuePayload(status)
      )
    );

    renderReviewQueue();

    await screen.findByText('Retirement Indicator', { selector: '.category-badge' });
    await user.click(screen.getByRole('tab', { name: 'Confirmed' }));

    expect(await screen.findByText('No findings found')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'View pending review' })).toBeInTheDocument();
  });

  it('shows the clearer review status label and empty-state copy', async () => {
    fetchDiscoveryReviewQueueMock.mockResolvedValue(queuePayload('PENDING_REVIEW'));

    renderReviewQueue();

    expect(await screen.findByText((_, element) => {
      return element?.textContent === 'Current review status: Pending Review';
    })).toBeInTheDocument();
    expect(screen.getByText('Review automated rule-engine discovery findings. Inspect signal strength and update the review status for each finding.')).toBeInTheDocument();
  });

  it('does not show pending findings or actions while a different status tab loads', async () => {
    const user = userEvent.setup();
    let resolveConfirmed!: (payload: PaginatedEvidenceFindingResponse) => void;
    const confirmedRequest = new Promise<PaginatedEvidenceFindingResponse>((resolve) => {
      resolveConfirmed = resolve;
    });

    fetchDiscoveryReviewQueueMock.mockImplementation(
      (_page: number, _pageSize: number, status: DiscoveryReviewStatus) =>
        status === 'CONFIRMED' ? confirmedRequest : Promise.resolve(queuePayload(status))
    );

    renderReviewQueue();

    expect(await screen.findByText('Retirement Indicator', { selector: '.category-badge' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Confirm' })).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: 'Confirmed' }));

    expect(screen.getByText(/Loading discovery review queue/i).closest('.loading-card')).toBeInTheDocument();
    expect(screen.queryByText('Retirement Indicator', { selector: '.category-badge' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Confirm' })).not.toBeInTheDocument();
    expect(fetchDiscoveryReviewQueueMock).toHaveBeenLastCalledWith(1, 10, 'CONFIRMED', null);

    await act(async () => {
      resolveConfirmed(queuePayload('CONFIRMED'));
    });

    expect(await screen.findByText('Insurance Indicator', { selector: '.category-badge' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reopen' })).toBeInTheDocument();
    expect(screen.getByRole('tabpanel', { name: 'Confirmed' })).toBeInTheDocument();
  });

  it.each([
    { tab: 'PENDING_REVIEW' as const, action: 'Confirm', nextStatus: 'CONFIRMED' as const },
    { tab: 'PENDING_REVIEW' as const, action: 'Dismiss', nextStatus: 'DISMISSED' as const },
    { tab: 'CONFIRMED' as const, action: 'Reopen', nextStatus: 'PENDING_REVIEW' as const },
  ])('shows sanitized feedback when $action fails', async ({ tab, action, nextStatus }) => {
    const user = userEvent.setup();
    fetchDiscoveryReviewQueueMock.mockImplementation(
      (_page: number, _pageSize: number, status: DiscoveryReviewStatus) => Promise.resolve(queuePayload(status))
    );
    updateDiscoveryFindingStatusMock.mockRejectedValue(
      new ApiError('C:\\private\\mutation-secret.txt', 500)
    );

    renderReviewQueue();

    if (tab !== 'PENDING_REVIEW') {
      await user.click(await screen.findByRole('tab', { name: 'Confirmed' }));
    }

    const category = tab === 'PENDING_REVIEW' ? 'Retirement Indicator' : 'Insurance Indicator';
    expect(await screen.findByText(category, { selector: '.category-badge' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: action }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to update this finding. Please try again.'
    );
    expect(screen.queryByText(/mutation-secret/i)).not.toBeInTheDocument();
    expect(updateDiscoveryFindingStatusMock).toHaveBeenCalledWith(
      findingsByStatus[tab].finding_id,
      nextStatus
    );
  });

  it('sanitizes review queue loading errors and supports retry', async () => {
    const user = userEvent.setup();
    fetchDiscoveryReviewQueueMock
      .mockRejectedValueOnce(new ApiError('C:\\private\\queue-secret.txt', 500))
      .mockResolvedValueOnce(queuePayload('PENDING_REVIEW'));

    renderReviewQueue();

    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load the review queue');
    expect(screen.queryByText(/queue-secret/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Retry' }));

    expect(await screen.findByText('Retirement Indicator', { selector: '.category-badge' })).toBeInTheDocument();
    await waitFor(() => expect(fetchDiscoveryReviewQueueMock).toHaveBeenCalledTimes(2));
  });

  it('retains the selected category when retrying a failed filtered request', async () => {
    const user = userEvent.setup();
    fetchDiscoveryReviewQueueMock
      .mockResolvedValueOnce(queuePayload('PENDING_REVIEW'))
      .mockRejectedValueOnce(new ApiError('C:\\private\\filtered-secret.txt', 500))
      .mockResolvedValueOnce({
        ...queuePayload('PENDING_REVIEW'),
        items: [{ ...findingsByStatus.PENDING_REVIEW, category: 'PROPERTY_INDICATOR' }],
      });

    renderReviewQueue();

    await screen.findByText('Retirement Indicator', { selector: '.category-badge' });
    await selectCategory(user, 'PROPERTY_INDICATOR');
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load the review queue');
    expect(screen.queryByText(/filtered-secret/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Retry' }));

    expect(await screen.findByText('Property Indicator', { selector: '.category-badge' })).toBeInTheDocument();
    expect(fetchDiscoveryReviewQueueMock).toHaveBeenLastCalledWith(
      1,
      10,
      'PENDING_REVIEW',
      'PROPERTY_INDICATOR'
    );
  });

  it('remains protected by the existing authentication boundary', async () => {
    const queryClient = createQueryClient();
    vi.stubGlobal('fetch', vi.fn());

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/discovery/review']}>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<h1>Sign in required</h1>} />
              <Route element={<ProtectedRoute />}>
                <Route path="/discovery/review" element={<ReviewQueuePage />} />
              </Route>
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByRole('heading', { name: 'Sign in required' })).toBeInTheDocument();
    expect(fetchDiscoveryReviewQueueMock).not.toHaveBeenCalled();
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });
});
