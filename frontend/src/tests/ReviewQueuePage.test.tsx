import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import ReviewQueuePage from '../pages/ReviewQueuePage';
import type {
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

afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe('ReviewQueuePage', () => {
  it('renders whole-number confidence and accessible status tabs without category filtering', async () => {
    fetchDiscoveryReviewQueueMock.mockResolvedValue(queuePayload('PENDING_REVIEW'));
    vi.stubGlobal('fetch', vi.fn());

    renderReviewQueue();

    expect(await screen.findByText('85%')).toBeInTheDocument();
    expect(screen.queryByText('8500%')).not.toBeInTheDocument();
    expect(screen.queryByRole('combobox', { name: /category/i })).not.toBeInTheDocument();

    const tabList = screen.getByRole('tablist', { name: 'Review status filters' });
    const pendingTab = within(tabList).getByRole('tab', { name: 'Pending Review' });
    const confirmedTab = within(tabList).getByRole('tab', { name: 'Confirmed' });
    const panel = screen.getByRole('tabpanel', { name: 'Pending Review' });

    expect(pendingTab).toHaveAttribute('aria-selected', 'true');
    expect(confirmedTab).toHaveAttribute('aria-selected', 'false');
    expect(pendingTab).toHaveAttribute('aria-controls', panel.id);
    expect(panel).toHaveAttribute('aria-labelledby', pendingTab.id);
    expect(fetchDiscoveryReviewQueueMock).toHaveBeenCalledWith(1, 10, 'PENDING_REVIEW');
    expect(globalThis.fetch).not.toHaveBeenCalled();
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

    expect(await screen.findByText('Retirement Indicator')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Confirm' })).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: 'Confirmed' }));

    expect(screen.getByRole('status')).toHaveTextContent('Loading discovery review queue');
    expect(screen.queryByText('Retirement Indicator')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Confirm' })).not.toBeInTheDocument();
    expect(fetchDiscoveryReviewQueueMock).toHaveBeenLastCalledWith(1, 10, 'CONFIRMED');

    await act(async () => {
      resolveConfirmed(queuePayload('CONFIRMED'));
    });

    expect(await screen.findByText('Insurance Indicator')).toBeInTheDocument();
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
    expect(await screen.findByText(category)).toBeInTheDocument();
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

    expect(await screen.findByText('Retirement Indicator')).toBeInTheDocument();
    await waitFor(() => expect(fetchDiscoveryReviewQueueMock).toHaveBeenCalledTimes(2));
  });
});
