import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import { AuthProvider } from '../context/AuthContext';
import App from '../pages/App';
import FindingDetailPage from '../pages/FindingDetailPage';
import type {
  DiscoveryReviewStatus,
  EvidenceFindingDetailResponse,
  EvidenceFindingResponse,
} from '../types/discovery';

const { fetchDiscoveryFindingMock, updateDiscoveryFindingStatusMock } = vi.hoisted(() => ({
  fetchDiscoveryFindingMock: vi.fn(),
  updateDiscoveryFindingStatusMock: vi.fn(),
}));

vi.mock('../api/discovery', () => ({
  fetchDiscoveryDashboard: vi.fn(),
  fetchDiscoveryScans: vi.fn(),
  fetchDiscoveryScan: vi.fn(),
  fetchDiscoveryScanSummary: vi.fn(),
  fetchDiscoveryScanReport: vi.fn(),
  fetchDiscoveryScanDocuments: vi.fn(),
  fetchDiscoveryScanFindings: vi.fn(),
  fetchDiscoveryReviewQueue: vi.fn(),
  fetchDiscoveryFinding: fetchDiscoveryFindingMock,
  updateDiscoveryFindingStatus: updateDiscoveryFindingStatusMock,
}));

const pendingFinding: EvidenceFindingDetailResponse = {
  finding_id: 'finding/123',
  scan_id: 'scan/456',
  document_id: 'document-789',
  document_name: 'Benefits summary',
  document_type: 'EMPLOYER_BENEFIT_DOCUMENT',
  category: 'RETIREMENT_INDICATOR',
  confidence_score: 87,
  review_status: 'PENDING_REVIEW',
  created_at: '2026-08-01T10:03:00Z',
};

function detailWithStatus(status: DiscoveryReviewStatus): EvidenceFindingDetailResponse {
  return { ...pendingFinding, review_status: status };
}

function mutationResponse(status: DiscoveryReviewStatus): EvidenceFindingResponse {
  return {
    finding_id: pendingFinding.finding_id,
    category: pendingFinding.category,
    confidence_score: pendingFinding.confidence_score,
    review_status: status,
    created_at: pendingFinding.created_at,
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

function renderFindingDetail(findingId = pendingFinding.finding_id) {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/discovery/findings/${encodeURIComponent(findingId)}`]}>
        <Routes>
          <Route path="/discovery/findings/:findingId" element={<FindingDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
  sessionStorage.clear();
});

describe('FindingDetailPage', () => {
  it('shows an accessible loading state without making an unmocked request', () => {
    fetchDiscoveryFindingMock.mockReturnValue(new Promise(() => undefined));
    vi.stubGlobal('fetch', vi.fn());

    renderFindingDetail();

    expect(screen.getByRole('heading', { name: 'Securely loading this finding.' })).toBeInTheDocument();
    expect(fetchDiscoveryFindingMock).toHaveBeenCalledWith('finding/123');
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it('renders privacy-safe metadata, whole-number confidence, timestamps, and navigation', async () => {
    const responseWithIgnoredPrivateFields = {
      ...pendingFinding,
      evidence_excerpt: 'private evidence value',
      matched_terms: ['private matched term'],
      storage_reference: 'private/storage/path',
    } as unknown as EvidenceFindingDetailResponse;
    fetchDiscoveryFindingMock.mockResolvedValue(responseWithIgnoredPrivateFields);
    vi.stubGlobal('fetch', vi.fn());

    renderFindingDetail();

    expect(await screen.findByRole('heading', { name: 'Retirement Indicator' })).toBeInTheDocument();
    expect(screen.getByText('87%')).toBeInTheDocument();
    expect(screen.queryByText('8700%')).not.toBeInTheDocument();
    expect(screen.getByText('Benefits summary')).toBeInTheDocument();
    expect(screen.getByText('Employer Benefit Document')).toBeInTheDocument();
    expect(screen.getByText('document-789')).toBeInTheDocument();
    expect(screen.getByText(
      new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(
        new Date(pendingFinding.created_at)
      )
    )).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'View scan scan/456' })).toHaveAttribute(
      'href',
      '/discovery/scans/scan%2F456'
    );
    expect(screen.getByRole('link', { name: /Back to Review Queue/ })).toHaveAttribute(
      'href',
      '/discovery/review'
    );
    expect(screen.queryByText('private evidence value')).not.toBeInTheDocument();
    expect(screen.queryByText('private matched term')).not.toBeInTheDocument();
    expect(screen.queryByText('private/storage/path')).not.toBeInTheDocument();
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it.each([
    { status: 'PENDING_REVIEW' as const, actions: ['Confirm', 'Dismiss'] },
    { status: 'CONFIRMED' as const, actions: ['Reopen', 'Dismiss'] },
    { status: 'DISMISSED' as const, actions: ['Reopen', 'Confirm'] },
  ])('shows the correct actions for $status', async ({ status, actions }) => {
    fetchDiscoveryFindingMock.mockResolvedValue(detailWithStatus(status));

    renderFindingDetail();

    const actionGroup = await screen.findByRole('group', { name: 'Finding review actions' });
    expect(within(actionGroup).getAllByRole('button').map((button) => button.textContent)).toEqual(actions);
  });

  it('updates the visible status and actions after confirmation', async () => {
    const user = userEvent.setup();
    fetchDiscoveryFindingMock
      .mockResolvedValueOnce(pendingFinding)
      .mockResolvedValue(detailWithStatus('CONFIRMED'));
    updateDiscoveryFindingStatusMock.mockResolvedValue(mutationResponse('CONFIRMED'));

    renderFindingDetail();

    await user.click(await screen.findByRole('button', { name: 'Confirm' }));

    expect(updateDiscoveryFindingStatusMock).toHaveBeenCalledWith('finding/123', 'CONFIRMED');
    expect(await screen.findByText('Finding status updated.')).toBeInTheDocument();
    expect(screen.getByText('Confirmed', { selector: '.finding-review-status' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reopen' })).toBeInTheDocument();
    await waitFor(() => expect(fetchDiscoveryFindingMock).toHaveBeenCalledTimes(2));
  });

  it('shows sanitized feedback when a status update fails', async () => {
    const user = userEvent.setup();
    fetchDiscoveryFindingMock.mockResolvedValue(pendingFinding);
    updateDiscoveryFindingStatusMock.mockRejectedValue(
      new ApiError('C:\\private\\finding-mutation-secret.txt', 500)
    );

    renderFindingDetail();

    await user.click(await screen.findByRole('button', { name: 'Dismiss' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to update this finding. Please try again.'
    );
    expect(screen.queryByText(/finding-mutation-secret/i)).not.toBeInTheDocument();
  });

  it('sanitizes loading errors and supports retry', async () => {
    const user = userEvent.setup();
    fetchDiscoveryFindingMock
      .mockRejectedValueOnce(new ApiError('C:\\private\\finding-query-secret.txt', 500))
      .mockResolvedValueOnce(pendingFinding);

    renderFindingDetail();

    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load this finding');
    expect(screen.queryByText(/finding-query-secret/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByRole('heading', { name: 'Retirement Indicator' })).toBeInTheDocument();
    expect(fetchDiscoveryFindingMock).toHaveBeenCalledTimes(2);
  });

  it('shows a safe unavailable state for a missing or inaccessible finding', async () => {
    fetchDiscoveryFindingMock.mockRejectedValue(new ApiError('Evidence finding not found', 404));

    renderFindingDetail();

    expect(await screen.findByRole('heading', { name: 'Finding unavailable' })).toBeInTheDocument();
    expect(screen.getByText('This finding is unavailable or you do not have access to it.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
  });

  it('stays behind the existing authentication boundary', async () => {
    const queryClient = createQueryClient();
    vi.stubGlobal('fetch', vi.fn());

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/discovery/findings/finding-123']}>
          <AuthProvider>
            <App />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
    expect(fetchDiscoveryFindingMock).not.toHaveBeenCalled();
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });
});
