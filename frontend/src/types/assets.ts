export type AssetVerificationStatus = 'UNKNOWN' | 'VERIFIED' | 'NEEDS_REVIEW' | 'CLOSED';

export type Asset = {
  id: string;
  asset_category: string;
  asset_name: string;
  institution: string | null;
  description: string | null;
  estimated_value: string | null;
  ownership_type: string | null;
  status: 'Active' | 'Archived';
  is_verified: boolean;
  verification_status: AssetVerificationStatus;
  verified_at: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AssetCreate = {
  asset_name: string;
  asset_category: string;
  institution?: string;
  description?: string;
  estimated_value?: string;
  ownership_type?: string;
};
