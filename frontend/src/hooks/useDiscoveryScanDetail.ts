import { keepPreviousData, useQuery } from '@tanstack/react-query';
import {
  fetchDiscoveryScan,
  fetchDiscoveryScanDocuments,
  fetchDiscoveryScanFindings,
  fetchDiscoveryScanReport,
  fetchDiscoveryScanSummary,
} from '../api/discovery';
import type { DiscoveryScanStatus } from '../types/discovery';

export const discoveryScanQueryKey = (scanId: string) => ['discovery', 'scan', scanId] as const;
export const discoveryScanSummaryQueryKey = (scanId: string) => ['discovery', 'scan', scanId, 'summary'] as const;
export const discoveryScanReportQueryKey = (scanId: string) => ['discovery', 'scan', scanId, 'report'] as const;
export const discoveryScanDocumentsQueryKey = (scanId: string) => ['discovery', 'scan', scanId, 'documents'] as const;
export const discoveryScanFindingsQueryKey = (scanId: string, page: number, pageSize: number) =>
  ['discovery', 'scan', scanId, 'findings', { page, pageSize }] as const;

export function isScanActiveStatus(status?: DiscoveryScanStatus): boolean {
  return status === 'PENDING' || status === 'RUNNING';
}

export function useDiscoveryScan(scanId: string) {
  return useQuery({
    queryKey: discoveryScanQueryKey(scanId),
    queryFn: () => fetchDiscoveryScan(scanId),
    enabled: Boolean(scanId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return isScanActiveStatus(status) ? 3000 : false;
    },
  });
}

export function useDiscoveryScanSummary(scanId: string, scanStatus?: DiscoveryScanStatus) {
  return useQuery({
    queryKey: discoveryScanSummaryQueryKey(scanId),
    queryFn: () => fetchDiscoveryScanSummary(scanId),
    enabled: Boolean(scanId),
    refetchInterval: () => (isScanActiveStatus(scanStatus) ? 3000 : false),
  });
}

export function useDiscoveryScanReport(scanId: string, scanStatus?: DiscoveryScanStatus) {
  return useQuery({
    queryKey: discoveryScanReportQueryKey(scanId),
    queryFn: () => fetchDiscoveryScanReport(scanId),
    enabled: Boolean(scanId),
    refetchInterval: () => (isScanActiveStatus(scanStatus) ? 3000 : false),
  });
}

export function useDiscoveryScanDocuments(scanId: string, scanStatus?: DiscoveryScanStatus) {
  return useQuery({
    queryKey: discoveryScanDocumentsQueryKey(scanId),
    queryFn: () => fetchDiscoveryScanDocuments(scanId),
    enabled: Boolean(scanId),
    refetchInterval: () => (isScanActiveStatus(scanStatus) ? 3000 : false),
  });
}

export function useDiscoveryScanFindings(
  scanId: string,
  page: number,
  pageSize: number,
  scanStatus?: DiscoveryScanStatus
) {
  return useQuery({
    queryKey: discoveryScanFindingsQueryKey(scanId, page, pageSize),
    queryFn: () => fetchDiscoveryScanFindings(scanId, page, pageSize),
    enabled: Boolean(scanId),
    placeholderData: keepPreviousData,
    refetchInterval: () => (isScanActiveStatus(scanStatus) ? 3000 : false),
  });
}
