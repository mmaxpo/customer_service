import {
  apiJson,
  jsonBody,
} from "@/platform/api/client";

import type {
  BusinessLearningApprovedInsight,
  BusinessLearningApprovedInsightListParams,
  BusinessLearningApprovedInsightPage,
  BusinessLearningCandidateGenerateRequest,
  BusinessLearningCandidateGenerationResult,
  BusinessLearningCandidateListParams,
  BusinessLearningCandidatePage,
  BusinessLearningCandidateReviewRequest,
  BusinessLearningInsightCandidate,
} from "@/domains/customer-service/model/business-learning";

const base =
  "/api/customer-service/analytics/business-learning";

type QueryValue =
  | string
  | number
  | boolean
  | null
  | undefined;

export function buildBusinessLearningQuery(
  params: Record<string, QueryValue> = {},
): string {
  const query = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (
      value === undefined ||
      value === null ||
      value === ""
    ) {
      continue;
    }

    query.set(key, String(value));
  }

  const encoded = query.toString();

  return encoded ? `?${encoded}` : "";
}

export const businessLearningApi = {
  generateCandidates(
    payload: BusinessLearningCandidateGenerateRequest = {},
  ) {
    return apiJson<BusinessLearningCandidateGenerationResult>(
      `${base}/insight-candidates/generate`,
      {
        method: "POST",
        body: jsonBody(payload),
      },
    );
  },

  listCandidates(
    params: BusinessLearningCandidateListParams = {},
  ) {
    return apiJson<BusinessLearningCandidatePage>(
      `${base}/insight-candidates${buildBusinessLearningQuery(
        params,
      )}`,
    );
  },

  getCandidate(candidateId: string) {
    return apiJson<BusinessLearningInsightCandidate>(
      `${base}/insight-candidates/${encodeURIComponent(
        candidateId,
      )}`,
    );
  },

  candidateHistory(candidateId: string) {
    return apiJson<BusinessLearningInsightCandidate[]>(
      `${base}/insight-candidates/${encodeURIComponent(
        candidateId,
      )}/history`,
    );
  },

  reviewCandidate(
    candidateId: string,
    payload: BusinessLearningCandidateReviewRequest,
  ) {
    return apiJson<BusinessLearningInsightCandidate>(
      `${base}/insight-candidates/${encodeURIComponent(
        candidateId,
      )}/review`,
      {
        method: "POST",
        body: jsonBody(payload),
      },
    );
  },

  listApprovedInsights(
    params: BusinessLearningApprovedInsightListParams = {},
  ) {
    return apiJson<BusinessLearningApprovedInsightPage>(
      `${base}/approved-insights${buildBusinessLearningQuery(
        params,
      )}`,
    );
  },

  getApprovedInsight(candidateId: string) {
    return apiJson<BusinessLearningApprovedInsight>(
      `${base}/approved-insights/${encodeURIComponent(
        candidateId,
      )}`,
    );
  },
};
