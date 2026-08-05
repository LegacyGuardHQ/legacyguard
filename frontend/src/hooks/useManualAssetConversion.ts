import { useRef } from 'react';
import { useMutation } from '@tanstack/react-query';
import { createAssetFromDiscoveryFinding } from '../api/discovery';
import type { AssetResponse, ManualAssetConversionRequest } from '../types/discovery';

export function useManualAssetConversion(findingId: string) {
  const activeRequest = useRef<Promise<AssetResponse> | null>(null);

  return useMutation({
    mutationFn: (payload: ManualAssetConversionRequest) => {
      if (activeRequest.current) return activeRequest.current;

      const request = createAssetFromDiscoveryFinding(findingId, payload).finally(() => {
        if (activeRequest.current === request) activeRequest.current = null;
      });
      activeRequest.current = request;
      return request;
    },
    retry: false,
  });
}
