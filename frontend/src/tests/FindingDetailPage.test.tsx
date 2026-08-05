import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import { AuthProvider } from '../context/AuthContext';
import App from '../pages/App';
import FindingDetailPage from '../pages/FindingDetailPage';
import type {
  AssetResponse,
  DiscoveryReviewStatus,
  EvidenceFindingDetailResponse,
  EvidenceFindingResponse,
} from '../types/discovery';

const { createAssetFromDiscoveryFindingMock, fetchDiscoveryFindingMock, updateDiscoveryFindingStatusMock } = vi.hoisted(() => ({
  createAssetFromDiscoveryFindingMock: vi.fn(),
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
  createAssetFromDiscoveryFinding: createAssetFromDiscoveryFindingMock,
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

const createdAsset: AssetResponse = {
  id: 'asset/created-1',
  asset_category: 'Retirement',
  asset_name: 'Former employer plan',
  institution: null,
  description: null,
  estimated_value: null,
  ownership_type: null,
  status: 'Active',
  is_verified: false,
  verification_status: 'NEEDS_REVIEW',
  verified_at: null,
  archived_at: null,
  created_at: '2026-08-04T10:00:00Z',
  updated_at: '2026-08-04T10:00:00Z',
  details: null,
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

async function fillRequiredConversionFields(
  user: ReturnType<typeof userEvent.setup>,
  assetName = 'Former employer plan',
  assetCategory = 'Retirement'
) {
  await user.type(await screen.findByLabelText(/Asset name/), assetName);
  await user.type(screen.getByLabelText(/Asset category/), assetCategory);
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

  it.each(['PENDING_REVIEW', 'DISMISSED'] as const)(
    'hides manual asset conversion for %s findings',
    async (status) => {
      fetchDiscoveryFindingMock.mockResolvedValue(detailWithStatus(status));

      renderFindingDetail();

      expect(await screen.findByRole('heading', { name: 'Retirement Indicator' })).toBeInTheDocument();
      expect(screen.queryByRole('heading', { name: 'Create an asset for review' })).not.toBeInTheDocument();
    }
  );

  it('shows manual conversion only for a confirmed finding and submits the exact trimmed payload', async () => {
    const user = userEvent.setup();
    fetchDiscoveryFindingMock.mockResolvedValue(detailWithStatus('CONFIRMED'));
    createAssetFromDiscoveryFindingMock.mockResolvedValue(createdAsset);

    renderFindingDetail();

    expect(await screen.findByRole('heading', { name: 'Create an asset for review' })).toBeInTheDocument();
    await fillRequiredConversionFields(user, '  Former employer plan  ', '  Retirement  ');
    await user.type(screen.getByLabelText(/Institution/), '  Example Plan  ');
    await user.type(screen.getByLabelText(/Description/), '  User-entered follow-up  ');
    await user.type(screen.getByLabelText(/Estimated value/), '1250.50');
    await user.type(screen.getByLabelText(/Ownership type/), '  Individual  ');
    await user.type(screen.getByLabelText(/Account number/), '  1234  ');
    await user.type(screen.getByLabelText(/Policy number/), '  P-9  ');
    await user.type(screen.getByLabelText(/^Notes/), '  Verify with institution  ');
    await user.type(screen.getByLabelText(/Claim instructions/), '  Contact administrator  ');
    await user.click(screen.getByRole('button', { name: 'Create asset for review' }));

    expect(createAssetFromDiscoveryFindingMock).toHaveBeenCalledTimes(1);
    expect(createAssetFromDiscoveryFindingMock).toHaveBeenCalledWith('finding/123', {
      asset_name: 'Former employer plan',
      asset_category: 'Retirement',
      institution: 'Example Plan',
      description: 'User-entered follow-up',
      estimated_value: 1250.5,
      ownership_type: 'Individual',
      details: {
        account_number: '1234',
        policy_number: 'P-9',
        notes: 'Verify with institution',
        claim_instructions: 'Contact administrator',
      },
    });
    expect(await screen.findByRole('heading', { name: 'Asset created for review' })).toBeInTheDocument();
    expect(screen.getByText('asset/created-1')).toBeInTheDocument();
    expect(screen.getByText('Needs Review')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Create asset for review' })).not.toBeInTheDocument();
  });

  it('omits blank optional values from the conversion request', async () => {
    const user = userEvent.setup();
    fetchDiscoveryFindingMock.mockResolvedValue(detailWithStatus('CONFIRMED'));
    createAssetFromDiscoveryFindingMock.mockResolvedValue(createdAsset);

    renderFindingDetail();

    await fillRequiredConversionFields(user);
    await user.type(screen.getByLabelText(/Institution/), '   ');
    await user.type(screen.getByLabelText(/Account number/), '   ');
    await user.click(screen.getByRole('button', { name: 'Create asset for review' }));

    expect(createAssetFromDiscoveryFindingMock).toHaveBeenCalledWith('finding/123', {
      asset_name: 'Former employer plan',
      asset_category: 'Retirement',
    });
  });

  it('rejects blank required conversion fields before making a request', async () => {
    const user = userEvent.setup();
    fetchDiscoveryFindingMock.mockResolvedValue(detailWithStatus('CONFIRMED'));

    renderFindingDetail();

    await screen.findByRole('heading', { name: 'Create an asset for review' });
    await user.type(screen.getByLabelText(/Asset name/), '   ');
    await user.click(screen.getByRole('button', { name: 'Create asset for review' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Asset name and category are required.');
    expect(createAssetFromDiscoveryFindingMock).not.toHaveBeenCalled();
  });

  it('rejects a negative estimated value before making a request', async () => {
    const user = userEvent.setup();
    fetchDiscoveryFindingMock.mockResolvedValue(detailWithStatus('CONFIRMED'));

    renderFindingDetail();

    await fillRequiredConversionFields(user);
    fireEvent.change(screen.getByLabelText(/Estimated value/), { target: { value: '-1' } });
    await user.click(screen.getByRole('button', { name: 'Create asset for review' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Estimated value must be zero or greater.');
    expect(createAssetFromDiscoveryFindingMock).not.toHaveBeenCalled();
  });

  it.each([
    {
      detail: 'An asset has already been created from this finding',
      message: 'An asset has already been created from this finding.',
    },
    {
      detail: 'Only confirmed findings can be used to create an asset',
      message: 'This finding is no longer eligible for asset conversion.',
    },
  ])('shows sanitized conflict feedback: $message', async ({ detail, message }) => {
    const user = userEvent.setup();
    fetchDiscoveryFindingMock.mockResolvedValue(detailWithStatus('CONFIRMED'));
    createAssetFromDiscoveryFindingMock.mockRejectedValue(new ApiError(detail, 409, detail));

    renderFindingDetail();

    await fillRequiredConversionFields(user);
    await user.click(screen.getByRole('button', { name: 'Create asset for review' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(message);
  });

  it('sanitizes unexpected conversion failures', async () => {
    const user = userEvent.setup();
    fetchDiscoveryFindingMock.mockResolvedValue(detailWithStatus('CONFIRMED'));
    createAssetFromDiscoveryFindingMock.mockRejectedValue(
      new ApiError('C:\\private\\conversion-token.txt', 500)
    );

    renderFindingDetail();

    await fillRequiredConversionFields(user);
    await user.click(screen.getByRole('button', { name: 'Create asset for review' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to create this asset. Please try again.');
    expect(screen.queryByText(/conversion-token/i)).not.toBeInTheDocument();
  });

  it('prevents duplicate submissions while conversion is pending', async () => {
    fetchDiscoveryFindingMock.mockResolvedValue(detailWithStatus('CONFIRMED'));
    createAssetFromDiscoveryFindingMock.mockReturnValue(new Promise(() => undefined));

    renderFindingDetail();

    const user = userEvent.setup();
    await fillRequiredConversionFields(user);
    const button = screen.getByRole('button', { name: 'Create asset for review' });
    const form = button.closest('form');
    expect(form).not.toBeNull();
    fireEvent.submit(form!);
    fireEvent.submit(form!);

    await waitFor(() => expect(createAssetFromDiscoveryFindingMock).toHaveBeenCalledTimes(1));
    expect(screen.getByRole('button', { name: 'Creating asset…' })).toBeDisabled();
  });

  it('encodes the finding ID and uses the authenticated client for conversion', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(createdAsset), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      })
    );
    vi.stubGlobal('fetch', fetchMock);
    sessionStorage.setItem('legacyguard.access_token', 'test-token');
    const { createAssetFromDiscoveryFinding } = await vi.importActual<typeof import('../api/discovery')>(
      '../api/discovery'
    );

    await createAssetFromDiscoveryFinding('finding/with space', {
      asset_name: 'Plan',
      asset_category: 'Retirement',
    });

    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('http://localhost:8000/discovery/findings/finding%2Fwith%20space/assets');
    expect(options.method).toBe('POST');
    expect(options.body).toBe(JSON.stringify({ asset_name: 'Plan', asset_category: 'Retirement' }));
    expect(new Headers(options.headers).get('Authorization')).toBe('Bearer test-token');
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
