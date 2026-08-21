import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createBeneficiary, fetchBeneficiaries } from '../api/beneficiaries';

const beneficiariesQueryKey = ['beneficiaries'] as const;

export function useBeneficiaries() {
  return useQuery({ queryKey: beneficiariesQueryKey, queryFn: fetchBeneficiaries });
}

export function useCreateBeneficiary() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createBeneficiary,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: beneficiariesQueryKey });
    },
  });
}
