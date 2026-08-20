import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createAsset, fetchAssets } from '../api/assets';

const assetsQueryKey = ['assets'] as const;

export function useAssets() {
  return useQuery({ queryKey: assetsQueryKey, queryFn: fetchAssets });
}

export function useCreateAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createAsset,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: assetsQueryKey });
    },
  });
}
