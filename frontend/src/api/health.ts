import { request } from './client';

export type HealthResponse = Record<string, unknown>;

export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health');
}
