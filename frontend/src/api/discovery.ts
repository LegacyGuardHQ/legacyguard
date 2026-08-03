import { request } from './client';
import type { DiscoveryDashboardResponse, PaginatedDiscoveryScansResponse } from '../types/discovery';

export function fetchDiscoveryDashboard(): Promise<DiscoveryDashboardResponse> {
  return request<DiscoveryDashboardResponse>('/discovery/dashboard', {}, true);
}

export function fetchDiscoveryScans(page: number, pageSize: number): Promise<PaginatedDiscoveryScansResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  return request<PaginatedDiscoveryScansResponse>(`/discovery/scans?${params.toString()}`, {}, true);
}
