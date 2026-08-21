import { request } from './client';
import type { Beneficiary, BeneficiaryCreate } from '../types/beneficiaries';

export function fetchBeneficiaries(): Promise<Beneficiary[]> {
  return request<Beneficiary[]>('/beneficiaries', {}, true);
}

export function createBeneficiary(payload: BeneficiaryCreate): Promise<Beneficiary> {
  return request<Beneficiary>('/beneficiaries', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, true);
}
