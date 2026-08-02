import { request } from './client';
import type { DiscoveryDashboardResponse } from '../types/discovery';

export function fetchDiscoveryDashboard(): Promise<DiscoveryDashboardResponse> {
  return request<DiscoveryDashboardResponse>('/discovery/dashboard', {}, true);
}
