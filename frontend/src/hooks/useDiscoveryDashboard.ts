import { useQuery } from '@tanstack/react-query';
import { fetchDiscoveryDashboard } from '../api/discovery';

export const discoveryDashboardQueryKey = ['discovery', 'dashboard'] as const;

export function useDiscoveryDashboard() {
  return useQuery({
    queryKey: discoveryDashboardQueryKey,
    queryFn: fetchDiscoveryDashboard,
    refetchInterval: false,
  });
}
