import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { fetchDiscoveryScans } from '../api/discovery';

export const discoveryScansQueryKey = (page: number, pageSize: number) =>
  ['discovery', 'scans', { page, pageSize }] as const;

export function useDiscoveryScans(page: number, pageSize: number) {
  return useQuery({
    queryKey: discoveryScansQueryKey(page, pageSize),
    queryFn: () => fetchDiscoveryScans(page, pageSize),
    placeholderData: keepPreviousData,
    refetchInterval: false,
  });
}
