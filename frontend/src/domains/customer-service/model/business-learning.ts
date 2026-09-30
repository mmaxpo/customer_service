export type BusinessLearningInsightKind =
  | "positive_business_pattern"
  | "negative_business_pattern";

export type BusinessLearningCandidateStatus =
  | "validated"
  | "blocked"
  | "approved"
  | "rejected";

export type BusinessLearningApprovalStatus =
  | "pending"
  | "approved"
  | "rejected";

export type BusinessLearningReviewDecision =
  | "approve"
  | "reject";

export type BusinessLearningEvidenceLevel =
  | "low"
  | "moderate"
  | "high";

export type BusinessLearningCandidateScope = {
  tenant_id: string | null;
  objective_namespace: string;
  objective_type: string;
  decision: string;
};

export type BusinessLearningValidationCheck = {
  code: string;
  passed: boolean;
  explanation: string;
};

/**
 * The evidence snapshot remains immutable backend evidence.
 *
 * The frontend currently needs the fingerprint and preserves the
 * complete summaries/reports without interpreting their internal
 * aggregation fields. More specific view models can be introduced
 * when a UI consumes those fields.
 */
export type BusinessLearningEvidenceSnapshot = {
  historical_summary: Record<string, unknown>;
  recent_summary: Record<string, unknown>;
  trend_report: Record<string, unknown>;
  evidence_fingerprint: string;
};

export type BusinessLearningInsightCandidate = {
  candidate_id: string;
  candidate_version: number;

  kind: BusinessLearningInsightKind;
  scope: BusinessLearningCandidateScope;

  statement: string;
  recommended_review: string;
  limitations: string[];

  evidence: BusinessLearningEvidenceSnapshot;

  validation_checks: BusinessLearningValidationCheck[];
  validation_passed: boolean;

  approval_required: boolean;
  approval_status: BusinessLearningApprovalStatus;
  status: BusinessLearningCandidateStatus;

  blocking_reasons: string[];

  proposed_at: string;
  validated_at: string | null;
  reviewed_at: string | null;
  reviewed_by_user_id: string | null;
  review_reason: string | null;
};

export type BusinessLearningCandidateGenerateRequest = {
  tenant_id?: string | null;
  objective_namespace?: string | null;
  objective_type?: string | null;
  decision?: string | null;

  window_hours?: number;
  minimum_effective_sample_size?: number;

  meaningful_success_delta?: number;
  meaningful_failure_delta?: number;
  trend_contradiction_threshold?: number;

  minimum_summary_confidence?: number;
  maximum_candidate_contradiction_score?: number;

  require_high_evidence?: boolean;
  require_stable_trend?: boolean;
  approval_required?: boolean;
};

export type BusinessLearningCandidateReviewRequest = {
  decision: BusinessLearningReviewDecision;
  reason: string;
};

export type BusinessLearningCandidateGenerationItem = {
  candidate: BusinessLearningInsightCandidate;
  created: boolean;
};

export type BusinessLearningCandidateGenerationResult = {
  analyzed_reports: number;
  eligible_interpretations: number;
  created_candidates: number;
  existing_candidates: number;
  items: BusinessLearningCandidateGenerationItem[];
};

export type BusinessLearningCandidateListParams = {
  tenant_id?: string | null;
  objective_namespace?: string | null;
  objective_type?: string | null;
  decision?: string | null;
  status?: BusinessLearningCandidateStatus | null;
  approval_status?: BusinessLearningApprovalStatus | null;
  limit?: number;
  offset?: number;
};

export type BusinessLearningApprovedInsightScope = {
  tenant_id: string | null;
  objective_namespace: string;
  objective_type: string;
  decision: string;
};

export type BusinessLearningApprovedInsightEvidence = {
  window_start: string;
  window_end: string;

  summary_confidence: number;
  estimated_success_rate: number;
  estimated_failure_rate: number;
  effective_sample_size: number;

  evidence_level: BusinessLearningEvidenceLevel;

  contradiction_score: number;
  stability_score: number;
};

export type BusinessLearningApprovedInsightProvenance = {
  candidate_id: string;
  candidate_version: number;
  evidence_fingerprint: string;

  approved_at: string;
  approved_by_user_id: string;
  review_reason: string;
};

export type BusinessLearningApprovedInsight = {
  kind: BusinessLearningInsightKind;
  scope: BusinessLearningApprovedInsightScope;

  statement: string;
  recommended_review: string;
  limitations: string[];

  evidence: BusinessLearningApprovedInsightEvidence;
  provenance: BusinessLearningApprovedInsightProvenance;

  read_only: true;
  operator_review_only: true;

  affects_planning: false;
  affects_workflows: false;
  affects_routing: false;
  affects_runtime_policy: false;
  authorizes_business_action: false;
};

export type BusinessLearningApprovedInsightListParams = {
  tenant_id?: string | null;
  objective_namespace?: string | null;
  objective_type?: string | null;
  decision?: string | null;
  limit?: number;
  offset?: number;
};

export type BusinessLearningPage<T> = {
  limit: number;
  offset: number;
  items: T[];
};

export type BusinessLearningCandidatePage =
  BusinessLearningPage<BusinessLearningInsightCandidate>;

export type BusinessLearningApprovedInsightPage =
  BusinessLearningPage<BusinessLearningApprovedInsight>;
