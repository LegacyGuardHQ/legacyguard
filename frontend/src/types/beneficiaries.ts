export type BeneficiaryStatus = 'Active' | 'Archived' | 'Deceased';

export type BeneficiaryVerificationStatus = 'UNKNOWN' | 'VERIFIED' | 'NEEDS_REVIEW' | 'OUTDATED';

export type Beneficiary = {
  id: string;
  name: string;
  relationship_type: string | null;
  status: BeneficiaryStatus;
  verification_status: BeneficiaryVerificationStatus;
  verified_at: string | null;
  review_due_at: string | null;
  is_deceased: boolean;
  deceased_at: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type BeneficiaryCreate = {
  name: string;
  relationship_type?: string;
};
