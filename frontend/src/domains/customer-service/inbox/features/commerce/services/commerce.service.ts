import { customerServiceApi } from "@/domains/customer-service/api";

export const CommerceService = {
  order(orderRef: string) {
    return customerServiceApi.shopifyOrder(orderRef);
  },

  shippingStatus(orderRef: string) {
    return customerServiceApi.shopifyShippingStatus(orderRef);
  },
};
