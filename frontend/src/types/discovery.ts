export type DiscoveryScanStatus =
  | 'PENDING'
  | 'RUNNING'
  | 'COMPLETE'
  | 'COMPLETED_WITH_WARNINGS'
  | 'FAILED';

export type DiscoveryReviewStatus = 'PENDING_REVIEW' | 'CONFIRMED' | 'DISMISSED';

export type DiscoveryScanStatusCounts = Record<DiscoveryScanStatus, number>;

export type DiscoveryReviewStatusCounts = Record<DiscoveryReviewStatus, number>;

export type DiscoveryScanSummary = {
  scan_id: string;
  status: DiscoveryScanStatus;
  documents_processed: number;
  created_at: string;
  completed_at: string | null;
};

export type DiscoveryDashboardResponse = {
  total_scans: number;
  scans_by_status: DiscoveryScanStatusCounts;
  total_findings: number;
  findings_by_category: Record<string, number>;
  findings_by_review_status: DiscoveryReviewStatusCounts;
  pending_reviews: number;
  recent_scans: DiscoveryScanSummary[];
};

export type PaginatedDiscoveryScansResponse = {
  items: DiscoveryScanSummary[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type DiscoveryDocumentStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'SKIPPED';

export type DiscoveryDocumentWarning = 'PROCESSING_FAILED' | 'UNSUPPORTED_EXTRACTION';

export type DiscoveryScanStatusResponse = {
  scan_id: string;
  status: DiscoveryScanStatus;
  documents_processed: number;
  created_at: string;
  completed_at: string | null;
};

export type DiscoveryReportSummaryResponse = {
  scan_id: string;
  status: DiscoveryScanStatus;
  total_findings: number;
  categories: Record<string, number>;
  review_statuses: Record<string, number>;
};

export type DiscoverySafeReportResponse = DiscoveryReportSummaryResponse & {
  documents_processed: number;
  created_at: string;
  completed_at: string | null;
};

export type DiscoveryScanDocumentResponse = {
  document_id: string;
  document_name: string;
  document_type: string;
  status: DiscoveryDocumentStatus;
  warning_code: DiscoveryDocumentWarning | null;
  created_at: string;
};

export type EvidenceFindingResponse = {
  finding_id: string;
  category: string;
  confidence_score: number;
  review_status: DiscoveryReviewStatus;
  created_at: string;
};

export type PaginatedEvidenceFindingResponse = {
  items: EvidenceFindingResponse[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type EvidenceFindingReviewRequest = {
  review_status: DiscoveryReviewStatus;
};
