import { customerServiceApi } from "@/domains/customer-service/api";

export const ApprovalsService = {
  listWaiting() {
    return customerServiceApi.workflowApprovals("waiting");
  },

  approve(waitId: string) {
    return customerServiceApi.approveWorkflowApproval(waitId);
  },

  reject(waitId: string) {
    return customerServiceApi.rejectWorkflowApproval(waitId);
  },
};
