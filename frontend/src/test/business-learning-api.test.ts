import {
  describe,
  expect,
  it,
} from "vitest";

import {
  buildBusinessLearningQuery,
} from "@/domains/customer-service/api/business-learning";

describe("buildBusinessLearningQuery", () => {
  it("returns an empty query for empty parameters", () => {
    expect(
      buildBusinessLearningQuery(),
    ).toBe("");
  });

  it("encodes scope and pagination parameters", () => {
    const result = buildBusinessLearningQuery({
      tenant_id: "tenant/a",
      objective_namespace:
        "customer_service.support",
      objective_type: "multi operation",
      decision: "approved",
      limit: 25,
      offset: 5,
    });

    const params = new URLSearchParams(
      result.slice(1),
    );

    expect(params.get("tenant_id")).toBe(
      "tenant/a",
    );
    expect(
      params.get("objective_namespace"),
    ).toBe("customer_service.support");
    expect(params.get("objective_type")).toBe(
      "multi operation",
    );
    expect(params.get("decision")).toBe(
      "approved",
    );
    expect(params.get("limit")).toBe("25");
    expect(params.get("offset")).toBe("5");
  });

  it("preserves candidate review filters", () => {
    const result = buildBusinessLearningQuery({
      status: "validated",
      approval_status: "pending",
    });

    expect(result).toContain(
      "status=validated",
    );
    expect(result).toContain(
      "approval_status=pending",
    );
  });

  it("omits null, undefined, and empty values", () => {
    const result = buildBusinessLearningQuery({
      tenant_id: null,
      objective_namespace: undefined,
      objective_type: "",
      decision: "approved",
      offset: 0,
    });

    expect(result).toBe(
      "?decision=approved&offset=0",
    );
  });

  it("preserves explicit boolean values", () => {
    const result = buildBusinessLearningQuery({
      require_high_evidence: false,
      approval_required: true,
    });

    expect(result).toBe(
      "?require_high_evidence=false&approval_required=true",
    );
  });
});
