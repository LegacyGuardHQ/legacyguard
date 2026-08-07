import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import {
  fetchDiscoveryScan,
  fetchDiscoveryScanDocuments,
  fetchDiscoveryScanFindings,
  fetchDiscoveryScanReport,
  fetchDiscoveryScanSummary,
} from '../api/discovery';
import { AuthProvider } from '../context/AuthContext';
import App from '../pages/App';
import ScanDetailPage from '../pages/ScanDetailPage';
import type {
  DiscoveryReportSummaryResponse,
  DiscoverySafeReportResponse,
  DiscoveryScanDocumentResponse,
  DiscoveryScanStatusResponse,
  PaginatedEvidenceFindingResponse,
} from '../types/discovery';

vi.mock('../api/discovery', () => ({
  fetchDiscoveryDashboard: vi.fn(),
  fetchDiscoveryScans: vi.fn(),
  fetchDiscoveryScan: vi.fn(),
  fetchDiscoveryScanSummary: vi.fn(),
  fetchDiscoveryScanReport: vi.fn(),
  fetchDiscoveryScanDocuments: vi.fn(),
  fetchDiscoveryScanFindings: vi.fn(),
}));

const fetchScanMock = vi.mocked(fetchDiscoveryScan);
const fetchSummaryMock = vi.mocked(fetchDiscoveryScanSummary);
const fetchReportMock = vi.mocked(fetchDiscoveryScanReport);
const fetchDocumentsMock = vi.mocked(fetchDiscoveryScanDocuments);
const fetchFindingsMock = vi.mocked(fetchDiscoveryScanFindings);

const sampleScan: DiscoveryScanStatusResponse = {
  scan_id: 'scan-123',
  status: 'COMPLETE',
  documents_processed: 2,
  created_at: '2026-08-01T10:00:00Z',
  completed_at: '2026-08-01T10:05:00Z',
  lifecycle_state: 'COMPLETED',
  recovered_from_stale: false,
  recovered_at: null,
  processing_outcome: 'COMPLETED',
  processing_outcome_message: 'Completed successfully',
};

const sampleRunningScan: DiscoveryScanStatusResponse = {
  scan_id: 'scan-123',
  status: 'RUNNING',
  documents_processed: 1,
  created_at: '2026-08-01T10:00:00Z',
  completed_at: null,
  lifecycle_state: 'RUNNING',
  recovered_from_stale: false,
  recovered_at: null,
  processing_outcome: 'IN_PROGRESS',
  processing_outcome_message: 'Processing is active',
};

const sampleRecoveredScan: DiscoveryScanStatusResponse = {
  ...sampleScan,
  status: 'COMPLETE',
  lifecycle_state: 'COMPLETED',
  recovered_from_stale: true,
  recovered_at: '2026-08-01T10:06:00Z',
};

const sampleSummary: DiscoveryReportSummaryResponse = {
  scan_id: 'scan-123',
  status: 'COMPLETE',
  total_findings: 3,
  categories: { RETIREMENT_ACCOUNT: 2, INSURANCE_POLICY: 1 },
  review_statuses: { PENDING_REVIEW: 2, CONFIRMED: 1 },
};

const sampleReport: DiscoverySafeReportResponse = {
  ...sampleSummary,
  documents_processed: 2,
  created_at: '2026-08-01T10:00:00Z',
  completed_at: '2026-08-01T10:05:00Z',
};

const sampleDocuments: DiscoveryScanDocumentResponse[] = [
  {
    document_id: 'doc-1',
    document_name: '401k_Statement.pdf',
    document_type: 'STATEMENT',
    status: 'COMPLETED',
    warning_code: null,
    created_at: '2026-08-01T10:01:00Z',
  },
  {
    document_id: 'doc-2',
    document_name: 'Policy_Scan.png',
    document_type: 'IMAGE',
    status: 'SKIPPED',
    warning_code: 'UNSUPPORTED_EXTRACTION',
    created_at: '2026-08-01T10:02:00Z',
  },
];

const sampleFindings: PaginatedEvidenceFindingResponse = {
  items: [
    {
      finding_id: 'finding-101',
      category: 'RETIREMENT_ACCOUNT',
      confidence_score: 0.88,
      review_status: 'PENDING_REVIEW',
      created_at: '2026-08-01T10:03:00Z',
    },
    {
      finding_id: 'finding-102',
      category: 'INSURANCE_POLICY',
      confidence_score: 0.75,
      review_status: 'CONFIRMED',
      created_at: '2026-08-01T10:04:00Z',
    },
  ],
  total_count: 2,
  page: 1,
  page_size: 10,
  total_pages: 1,
};

function createQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderScanDetailPage(scanId = 'scan-123') {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/discovery/scans/${scanId}`]}>
        <Routes>
          <Route path="/discovery/scans/:scanId" element={<ScanDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe('ScanDetailPage', () => {
  it('shows an accessible loading state without making unmocked requests', () => {
    fetchScanMock.mockReturnValue(new Promise(() => undefined));
    vi.stubGlobal('fetch', vi.fn());

    renderScanDetailPage();

    expect(screen.getByRole('heading', { name: 'Securely loading your discovery activity.' })).toBeInTheDocument();
    expect(fetchScanMock).toHaveBeenCalledWith('scan-123');
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it('renders scan details, summary, report, documents, and findings successfully', async () => {
    fetchScanMock.mockResolvedValue(sampleScan);
    fetchSummaryMock.mockResolvedValue(sampleSummary);
    fetchReportMock.mockResolvedValue(sampleReport);
    fetchDocumentsMock.mockResolvedValue(sampleDocuments);
    fetchFindingsMock.mockResolvedValue(sampleFindings);

    renderScanDetailPage('scan-123');

    expect(await screen.findByRole('heading', { name: 'Scan scan-123' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Processing timeline' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Findings summary' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Scan report summary' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Processed documents' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Findings list' })).toBeInTheDocument();

    // Verify document items
    expect(screen.getByText('401k_Statement.pdf')).toBeInTheDocument();
    expect(screen.getByText('Policy_Scan.png')).toBeInTheDocument();
    expect(screen.getByText('Content format limitation')).toBeInTheDocument();

    // Verify finding items & confidence signal
    expect(screen.getAllByText('Retirement Account').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Signal strength: 88%')).toBeInTheDocument();
    expect(screen.getByText('ID: finding-101')).toBeInTheDocument();

    // Verify privacy-safe notice text
    expect(screen.getByText(/Trust & Privacy Notice:/i)).toBeInTheDocument();
    expect(screen.queryByText(/secret|extracted_text|storage_path/i)).not.toBeInTheDocument();
  });

  it('handles empty documents and findings gracefully', async () => {
    fetchScanMock.mockResolvedValue(sampleScan);
    fetchSummaryMock.mockResolvedValue({
      scan_id: 'scan-123',
      status: 'COMPLETE',
      total_findings: 0,
      categories: {},
      review_statuses: {},
    });
    fetchReportMock.mockResolvedValue({
      ...sampleReport,
      total_findings: 0,
      categories: {},
      review_statuses: {},
    });
    fetchDocumentsMock.mockResolvedValue([]);
    fetchFindingsMock.mockResolvedValue({
      items: [],
      total_count: 0,
      page: 1,
      page_size: 10,
      total_pages: 0,
    });

    renderScanDetailPage('scan-123');

    expect(await screen.findByText('No document tracking records found for this scan.')).toBeInTheDocument();
    expect(screen.getByText('No findings recorded for this scan.')).toBeInTheDocument();
  });

  it('sanitizes error messages and allows retrying', async () => {
    const user = userEvent.setup();
    fetchScanMock.mockRejectedValueOnce(new ApiError('C:\\private\\db.sqlite', 500)).mockResolvedValueOnce(sampleScan);
    fetchSummaryMock.mockResolvedValue(sampleSummary);
    fetchReportMock.mockResolvedValue(sampleReport);
    fetchDocumentsMock.mockResolvedValue(sampleDocuments);
    fetchFindingsMock.mockResolvedValue(sampleFindings);

    renderScanDetailPage();

    expect(await screen.findByRole('alert')).toHaveTextContent('Your saved information has not been changed');
    expect(screen.queryByText(/db\.sqlite/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('heading', { name: 'Scan scan-123' })).toBeInTheDocument();
  });

  it('displays active processing banner when status is RUNNING', async () => {
    fetchScanMock.mockResolvedValue(sampleRunningScan);
    fetchSummaryMock.mockResolvedValue(sampleSummary);
    fetchReportMock.mockResolvedValue(sampleReport);
    fetchDocumentsMock.mockResolvedValue(sampleDocuments);
    fetchFindingsMock.mockResolvedValue(sampleFindings);

    renderScanDetailPage();

    expect(await screen.findByRole('status')).toHaveTextContent('Discovery processing is active');
  });

  it('renders lifecycle and recovery messaging without technical error details', async () => {
    fetchScanMock.mockResolvedValue(sampleRecoveredScan);
    fetchSummaryMock.mockResolvedValue(sampleSummary);
    fetchReportMock.mockResolvedValue(sampleReport);
    fetchDocumentsMock.mockResolvedValue(sampleDocuments);
    fetchFindingsMock.mockResolvedValue(sampleFindings);

    renderScanDetailPage();

    expect(await screen.findByText('Completed successfully')).toBeInTheDocument();
    expect(screen.getByText('Recovered and completed')).toBeInTheDocument();
    expect(screen.getByText(/Recovered at/i)).toBeInTheDocument();
    expect(screen.queryByText(/Traceback|Exception|internal error/i)).not.toBeInTheDocument();
  });

  it('stays behind authentication boundary for protected routes', async () => {
    const queryClient = createQueryClient();
    vi.stubGlobal('fetch', vi.fn());

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/discovery/scans/scan-123']}>
          <AuthProvider>
            <App />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
    expect(fetchScanMock).not.toHaveBeenCalled();
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });
});
