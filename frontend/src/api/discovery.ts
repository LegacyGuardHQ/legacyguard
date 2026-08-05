import { request } from './client';
import type {
  DiscoveryDashboardResponse,
  DiscoveryFindingCategory,
  DiscoveryReportSummaryResponse,
  DiscoveryReviewStatus,
  DiscoverySafeReportResponse,
  DiscoveryScanDocumentResponse,
  DiscoveryScanStatusResponse,
  EvidenceFindingDetailResponse,
  EvidenceFindingResponse,
  PaginatedDiscoveryScansResponse,
  PaginatedEvidenceFindingResponse,
} from '../types/discovery';

export function fetchDiscoveryDashboard(): Promise<DiscoveryDashboardResponse> {
  return request<DiscoveryDashboardResponse>('/discovery/dashboard', {}, true);
}

export function fetchDiscoveryScans(page: number, pageSize: number): Promise<PaginatedDiscoveryScansResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  return request<PaginatedDiscoveryScansResponse>(`/discovery/scans?${params.toString()}`, {}, true);
}

export function fetchDiscoveryScan(scanId: string): Promise<DiscoveryScanStatusResponse> {
  return request<DiscoveryScanStatusResponse>(`/discovery/scans/${encodeURIComponent(scanId)}`, {}, true);
}

export function fetchDiscoveryScanSummary(scanId: string): Promise<DiscoveryReportSummaryResponse> {
  return request<DiscoveryReportSummaryResponse>(`/discovery/scans/${encodeURIComponent(scanId)}/summary`, {}, true);
}

export function fetchDiscoveryScanReport(scanId: string): Promise<DiscoverySafeReportResponse> {
  return request<DiscoverySafeReportResponse>(`/discovery/scans/${encodeURIComponent(scanId)}/report`, {}, true);
}

export function fetchDiscoveryScanDocuments(scanId: string): Promise<DiscoveryScanDocumentResponse[]> {
  return request<DiscoveryScanDocumentResponse[]>(`/discovery/scans/${encodeURIComponent(scanId)}/documents`, {}, true);
}

export function fetchDiscoveryScanFindings(
  scanId: string,
  page: number,
  pageSize: number
): Promise<PaginatedEvidenceFindingResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  return request<PaginatedEvidenceFindingResponse>(
    `/discovery/scans/${encodeURIComponent(scanId)}/findings?${params.toString()}`,
    {},
    true
  );
}

export function fetchDiscoveryFinding(findingId: string): Promise<EvidenceFindingDetailResponse> {
  return request<EvidenceFindingDetailResponse>(
    `/discovery/findings/${encodeURIComponent(findingId)}`,
    {},
    true
  );
}

export function fetchDiscoveryReviewQueue(
  page: number,
  pageSize: number,
  reviewStatus: DiscoveryReviewStatus = 'PENDING_REVIEW',
  category?: DiscoveryFindingCategory | null
): Promise<PaginatedEvidenceFindingResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    review_status: reviewStatus,
  });
  if (category) {
    params.set('category', category);
  }
  return request<PaginatedEvidenceFindingResponse>(`/discovery/findings/review-queue?${params.toString()}`, {}, true);
}

export function updateDiscoveryFindingStatus(
  findingId: string,
  reviewStatus: DiscoveryReviewStatus
): Promise<EvidenceFindingResponse> {
  return request<EvidenceFindingResponse>(
    `/discovery/findings/${encodeURIComponent(findingId)}`,
    {
      method: 'PATCH',
      body: JSON.stringify({ review_status: reviewStatus }),
    },
    true
  );
}
