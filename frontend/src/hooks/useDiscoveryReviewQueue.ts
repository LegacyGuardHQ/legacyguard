import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchDiscoveryReviewQueue, updateDiscoveryFindingStatus } from '../api/discovery';
import type { DiscoveryReviewStatus, EvidenceFindingDetailResponse } from '../types/discovery';
import { discoveryFindingDetailQueryKey } from './useDiscoveryFindingDetail';

export const discoveryReviewQueueQueryKey = (
  page: number,
  pageSize: number,
  reviewStatus: DiscoveryReviewStatus
) => ['discovery', 'review-queue', { page, pageSize, reviewStatus }] as const;

export function useDiscoveryReviewQueue(
  page: number,
  pageSize: number,
  reviewStatus: DiscoveryReviewStatus
) {
  return useQuery({
    queryKey: discoveryReviewQueueQueryKey(page, pageSize, reviewStatus),
    queryFn: () => fetchDiscoveryReviewQueue(page, pageSize, reviewStatus),
    refetchInterval: false,
  });
}

export function useUpdateFindingStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      findingId,
      reviewStatus,
    }: {
      findingId: string;
      reviewStatus: DiscoveryReviewStatus;
    }) => updateDiscoveryFindingStatus(findingId, reviewStatus),
    onSuccess: (finding, variables) => {
      const detailQueryKey = discoveryFindingDetailQueryKey(variables.findingId);
      queryClient.setQueryData<EvidenceFindingDetailResponse>(detailQueryKey, (current) =>
        current ? { ...current, ...finding } : current
      );
      queryClient.invalidateQueries({ queryKey: detailQueryKey });
      queryClient.invalidateQueries({ queryKey: ['discovery', 'review-queue'] });
      queryClient.invalidateQueries({ queryKey: ['discovery', 'dashboard'] });
    },
  });
}
