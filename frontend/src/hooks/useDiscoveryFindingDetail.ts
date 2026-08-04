import { useQuery } from '@tanstack/react-query';
import { fetchDiscoveryFinding } from '../api/discovery';

export const discoveryFindingDetailQueryKey = (findingId: string) =>
  ['discovery', 'finding', findingId] as const;

export function useDiscoveryFindingDetail(findingId: string) {
  return useQuery({
    queryKey: discoveryFindingDetailQueryKey(findingId),
    queryFn: () => fetchDiscoveryFinding(findingId),
    enabled: Boolean(findingId),
    refetchInterval: false,
  });
}
