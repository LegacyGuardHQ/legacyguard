export const documentTypes = [
  'WILL',
  'TRUST',
  'LIFE_INSURANCE_POLICY',
  'BENEFICIARY_FORM',
  'ACCOUNT_STATEMENT',
  'RETIREMENT_DOCUMENT',
  'DEED',
  'VEHICLE_TITLE',
  'TAX_DOCUMENT',
  'IDENTIFICATION',
  'POWER_OF_ATTORNEY',
  'HEALTHCARE_DIRECTIVE',
  'EMPLOYER_BENEFIT_DOCUMENT',
  'GOVERNMENT_BENEFIT_DOCUMENT',
  'DIGITAL_ASSET_INSTRUCTIONS',
  'OTHER',
] as const;

export type DocumentType = typeof documentTypes[number];
export type DocumentStatus = 'ACTIVE' | 'ARCHIVED' | 'REPLACED' | 'DELETED_PENDING_PURGE';
export type DocumentVerificationStatus = 'UNKNOWN' | 'VERIFIED' | 'NEEDS_REVIEW' | 'EXPIRED' | 'REPLACED';
export type DiscoveryScanStatus = 'PENDING' | 'RUNNING' | 'COMPLETE' | 'COMPLETED_WITH_WARNINGS' | 'FAILED';

export type VaultDocument = {
  id: string;
  asset_id: string | null;
  beneficiary_id: string | null;
  document_type: DocumentType;
  document_name: string;
  original_filename: string | null;
  mime_type: string | null;
  file_size: number | null;
  status: DocumentStatus;
  verification_status: DocumentVerificationStatus;
  verified_at: string | null;
  review_due_at: string | null;
  effective_date: string | null;
  expiration_date: string | null;
  archived_at: string | null;
  version_number: number;
  created_at: string;
  updated_at: string;
};

export type DocumentCreate = {
  document_type: DocumentType;
  document_name: string;
};

export type DocumentUploadResponse = {
  id: string;
  document_type: DocumentType;
  document_name: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  upload_status: 'COMPLETED';
  updated_at: string;
  discovery_scan: { scan_id: string; status: DiscoveryScanStatus } | null;
};
