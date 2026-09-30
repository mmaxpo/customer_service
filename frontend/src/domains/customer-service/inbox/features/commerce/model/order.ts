import type {
  ShopifyOrder,
} from "@/domains/customer-service/model";

export type CommerceOrder = ShopifyOrder;

export function orderDisplayName(
  order: CommerceOrder | null,
) {
  if (!order) return "No order";

  return (
    order.order_name ??
    order.order_id ??
    "Unknown Order"
  );
}

export function financialStatus(
    order: CommerceOrder | null,
): string {
  if (!order) return "Unknown";

  const value = order.context?.financial_status;

  return typeof value === "string"
      ? value
      : "Unknown";
}

export function fulfillmentStatus(
    order: CommerceOrder | null,
): string {
  if (!order) return "Unknown";

  const value = order.context?.fulfillment_status;

  return typeof value === "string"
      ? value
      : "Unknown";
}

export function totalPrice(
    order: CommerceOrder | null,
): string {
  if (!order) return "—";

  const total =
      typeof order.context?.total_price === "string"
          ? order.context.total_price
          : "";

  const currency =
      typeof order.context?.currency === "string"
          ? order.context.currency
          : "";

  return [total, currency].filter(Boolean).join(" ") || "—";
}
