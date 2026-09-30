"use client";

import { ConversationService } from "../services";
import { useCaseResource } from "./useCaseResource";

const loadContext = (id: string) => ConversationService.context(id);
const loadActivity = (id: string) => ConversationService.activity(id);
const loadCustomerSummary = (id: string) => ConversationService.customerSummary(id);

export function useCaseContext(conversationId: string | null) {
  return useCaseResource(conversationId, loadContext, "Could not load case details");
}

export function useCaseActivity(conversationId: string | null) {
  return useCaseResource(conversationId, loadActivity, "Could not load case activity");
}

export function useCustomerSummary(customerId: string | null, conversationId: string | null) {
  return useCaseResource(customerId, loadCustomerSummary, "Could not load customer", conversationId);
}
