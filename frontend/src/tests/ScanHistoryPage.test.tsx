import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import { fetchDiscoveryScans } from '../api/discovery';
import App from '../pages/App';
import ScanHistoryPage from '../pages/ScanHistoryPage';
import { AuthProvider } from '../context/AuthContext';
import type { PaginatedDiscoveryScansResponse } from '../types/discovery';

vi.mock('../api/discovery', () => ({
  fetchDiscoveryDashboard: vi.fn(),
  fetchDiscoveryScans: vi.fn(),
}));

const fetchDiscoveryScansMock = vi.mocked(fetchDiscoveryScans);

const firstPage: PaginatedDiscoveryScansResponse = {
  items: [
    { scan_id: 'scan/one', status: 'COMPLETED_WITH_WARNINGS', documents_processed: 3, created_at: '2026-08-01T12:30:00Z', completed_at: '2026-08-01T12:31:00Z' },
    { scan_id: 'scan-two', status: 'RUNNING', documents_processed: 1, created_at: '2026-08-02T09:00:00Z', completed_at: null },
  ],
  total_count: 12, page: 1, page_size: 10, total_pages: 2,
};

const secondPage: PaginatedDiscoveryScansResponse = {
  items: [
    { scan_id: 'scan-last', status: 'COMPLETE', documents_processed: 2, created_at: '2026-07-01T10:00:00Z', completed_at: '2026-07-01T10:01:00Z' },
  ],
  total_count: 12, page: 2, page_size: 10, total_pages: 2,
};

function expectedTimestamp(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function createQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderHistory() {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/discovery/scans']}><ScanHistoryPage /></MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe('ScanHistoryPage', () => {
  it('shows an accessible loading state without making an unmocked request', () => {
    fetchDiscoveryScansMock.mockReturnValue(new Promise(() => undefined));
    vi.stubGlobal('fetch', vi.fn());
    renderHistory();
    expect(screen.getByRole('heading', { name: 'Securely loading your discovery activity.' })).toBeInTheDocument();
    expect(fetchDiscoveryScansMock).toHaveBeenCalledWith(1, 10);
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it('renders statuses, timestamps, document counts, and deterministic links', async () => {
    fetchDiscoveryScansMock.mockResolvedValue(firstPage);
    renderHistory();
    expect(await screen.findByText('Complete with warnings')).toBeInTheDocument();
    expect(screen.getByText('Processing')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText(`Created ${expectedTimestamp('2026-08-01T12:30:00Z')}`)).toBeInTheDocument();
    expect(screen.getByText(expectedTimestamp('2026-08-01T12:31:00Z'))).toBeInTheDocument();
    expect(screen.getByText('Not completed')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Scan scan\/one/ })).toHaveAttribute('href', '/discovery/scans/scan%2Fone');
  });

  it('shows a safe empty state', async () => {
    fetchDiscoveryScansMock.mockResolvedValue({ items: [], total_count: 0, page: 1, page_size: 10, total_pages: 0 });
    renderHistory();
    expect(await screen.findByRole('heading', { name: 'No discovery activity yet' })).toBeInTheDocument();
  });

  it('sanitizes errors and retries', async () => {
    const user = userEvent.setup();
    fetchDiscoveryScansMock.mockRejectedValueOnce(new ApiError('C:\\private\\secret.txt', 500)).mockResolvedValueOnce(firstPage);
    renderHistory();
    expect(await screen.findByRole('alert')).toHaveTextContent('Your saved information has not been changed');
    expect(screen.queryByText(/secret\.txt/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText('Complete with warnings')).toBeInTheDocument();
  });

  it('requests the next page and updates navigation controls', async () => {
    const user = userEvent.setup();
    fetchDiscoveryScansMock.mockResolvedValueOnce(firstPage).mockResolvedValueOnce(secondPage);
    renderHistory();
    await user.click(await screen.findByRole('button', { name: 'Next' }));
    expect(await screen.findByText('Scan scan-last')).toBeInTheDocument();
    expect(fetchDiscoveryScansMock).toHaveBeenLastCalledWith(2, 10);
    expect(screen.getByText('Page 2 of 2')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();
  });

  it('returns to the first page with correct data and boundary controls', async () => {
    const user = userEvent.setup();
    fetchDiscoveryScansMock
      .mockResolvedValueOnce(firstPage)
      .mockResolvedValueOnce(secondPage)
      .mockResolvedValueOnce(firstPage);
    renderHistory();

    await user.click(await screen.findByRole('button', { name: 'Next' }));
    expect(await screen.findByText('Scan scan-last')).toBeInTheDocument();
    expect(fetchDiscoveryScansMock).toHaveBeenLastCalledWith(2, 10);

    await user.click(screen.getByRole('button', { name: 'Previous' }));

    await waitFor(() => expect(fetchDiscoveryScansMock).toHaveBeenLastCalledWith(1, 10));
    expect(await screen.findByText('Scan scan/one')).toBeInTheDocument();
    expect(screen.queryByText('Scan scan-last')).not.toBeInTheDocument();
    expect(screen.getByText('Page 1 of 2')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Next' })).toBeEnabled();
  });

  it('stays behind the existing authentication boundary with isolated routing and queries', async () => {
    const queryClient = createQueryClient();
    vi.stubGlobal('fetch', vi.fn());
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/discovery/scans']}><AuthProvider><App /></AuthProvider></MemoryRouter>
      </QueryClientProvider>,
    );
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
    expect(fetchDiscoveryScansMock).not.toHaveBeenCalled();
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });
});
