export interface MissionSession {
  workflowTemplateId: string | null;
  workflowRunId: string | null;

  conversationId: string | null;
  customerId: string | null;

  channel: string | null;

  missionName: string | null;

  startedAt: string | null;
}
