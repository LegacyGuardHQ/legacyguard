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
