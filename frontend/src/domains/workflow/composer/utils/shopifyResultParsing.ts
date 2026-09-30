export type ParsedShopifyOrderResult = {
  order_name: string | boolean | null;
  total_price: string | boolean | null;
  currency: string | boolean | null;
  financial_status: string | boolean | null;
  fulfillment_status: string | boolean | null;
  is_paid: string | boolean | null;
  is_fulfilled: string | boolean | null;
  tracking_number: string | boolean | null;
};

export function readPythonDictValue(
  text: string,
  key: string,
) {
  const pattern = new RegExp(
    `'${key}':\\s*(None|True|False|'([^']*)'|"([^"]*)"|[0-9.]+)`,
  );

  const match = text.match(pattern);

  if (!match) return null;
  if (match[1] === "None") return null;
  if (match[1] === "True") return true;
  if (match[1] === "False") return false;

  return match[2] ?? match[3] ?? match[1];
}

export function extractShopifyOrderResultFromText(
  text: string,
): ParsedShopifyOrderResult | null {
  if (!text.includes("'order_id'") || !text.includes("'context'")) {
    return null;
  }

  return {
    order_name: readPythonDictValue(text, "order_name"),
    total_price: readPythonDictValue(text, "total_price"),
    currency: readPythonDictValue(text, "currency"),
    financial_status: readPythonDictValue(text, "financial_status"),
    fulfillment_status: readPythonDictValue(text, "fulfillment_status"),
    is_paid: readPythonDictValue(text, "is_paid"),
    is_fulfilled: readPythonDictValue(text, "is_fulfilled"),
    tracking_number: readPythonDictValue(text, "tracking_number"),
  };
}

export function isShopifyOrderResult(value: unknown) {
  return (
    Boolean(value) &&
    typeof value === "object" &&
    "order_id" in value &&
    "context" in value
  );
}
