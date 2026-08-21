import { request } from './client';
import type { Asset, AssetCreate } from '../types/assets';

export function fetchAssets(): Promise<Asset[]> {
  return request<Asset[]>('/assets', {}, true);
}

export function createAsset(payload: AssetCreate): Promise<Asset> {
  return request<Asset>('/assets', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, true);
}
