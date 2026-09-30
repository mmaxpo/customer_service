import type { WorkflowTemplate } from "@/domains/customer-service/api/customer-service";
import type {
  ComposerEdge,
  ComposerNode as ComposerNodeType,
} from "@/domains/workflow/composer/types/composer";

import {
  extractShopifyOrderResultFromText,
  isShopifyOrderResult,
} from "@/domains/workflow/composer/utils/shopifyResultParsing";

type Props = {
  loadedTemplate: WorkflowTemplate | null;
  nodes: ComposerNodeType[];
  edges: ComposerEdge[];
  runStatus: string;
  workflowRunId: string;
  runAnswer: string;
  runResult: any;
  runtime: unknown;
};

export function ComposerPreviewPanel({
  loadedTemplate,
  nodes,
  edges,
  runStatus,
  workflowRunId,
  runAnswer,
  runResult,
  runtime,
}: Props) {
  return (
                    <div className="overflow-hidden rounded-3xl border border-tajeran-100 bg-white shadow-sm shadow-tajeran-100/70">
                        <div className="bg-gradient-to-br from-tajeran-700 to-ai-950 p-4 text-white">
                            <div className="text-xs font-bold uppercase tracking-wide text-tajeran-100">
                                Automation preview
                            </div>
                            <div className="mt-1 text-lg font-extrabold tracking-tight">
                                {loadedTemplate?.name || "Merchant workflow"}
                            </div>
                            <div className="mt-2 text-xs leading-5 text-tajeran-100">
                                {nodes.length} step(s) connected by {edges.length} automation path(s).
                            </div>
                        </div>

                        <div className="space-y-3 p-4">
                            <div className="rounded-2xl bg-tajeran-50 p-3">
                                <div className="text-xs font-bold uppercase tracking-wide text-tajeran-700">
                                    What this automation does
                                </div>
                                <div className="mt-2 space-y-2">
                                    {nodes.length > 0 ? (
                                        nodes.slice(0, 5).map((node, index) => (
                                            <div key={node.id} className="flex gap-2 text-sm">
                                                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white text-xs font-bold text-tajeran-700 shadow-sm">
                                                    {index + 1}
                                                </span>
                                                <div className="min-w-0 flex-1">
                                                    <div className="truncate font-semibold text-slate-950">
                                                        {String(node.data.label || "Workflow step")}
                                                    </div>
                                                    <div className="mt-1 flex flex-wrap gap-1">
                                                        {node.data.businessInputs?.slice(0, 1).map((item) => (
                                                            <span
                                                                key={`in-${node.id}-${item}`}
                                                                className="rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-600"
                                                            >
                                                                Reads {item}
                                                            </span>
                                                        ))}
                                                        {node.data.businessOutputs?.slice(0, 2).map((item) => (
                                                            <span
                                                                key={`out-${node.id}-${item}`}
                                                                className="rounded-full bg-emerald-50 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700"
                                                            >
                                                                Produces {item}
                                                            </span>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="text-sm text-slate-500">
                                            Add blocks to preview the automation.
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 text-xs">
                                <div className="flex items-center justify-between gap-2">
                                    <div className="font-bold text-slate-950">Test run</div>
                                    <span className="rounded-full bg-white px-2 py-0.5 font-semibold text-slate-600">
                                        {runStatus || "Idle"}
                                    </span>
                                </div>
                                {workflowRunId && (
                                    <div className="mt-2 break-all text-slate-500">
                                        Run ID: {workflowRunId}
                                    </div>
                                )}
                                {extractShopifyOrderResultFromText(runAnswer) ? (
                                    <div className="mt-3 overflow-hidden rounded-3xl border border-emerald-100 bg-white shadow-sm shadow-emerald-100/70">
                                        {(() => {
                                            const order = extractShopifyOrderResultFromText(runAnswer)!;

                                            return (
                                                <>
                                                    <div className="bg-gradient-to-r from-emerald-500 to-emerald-700 px-4 py-3 text-white">
                                                        <div className="text-xs font-bold uppercase tracking-wide text-emerald-50">
                                                            Final Workflow Result
                                                        </div>
                                                        <div className="mt-1 text-xl font-extrabold tracking-tight">
                                                            Order {order.order_name || "#1001"}
                                                        </div>
                                                    </div>

                                                    <div className="space-y-3 p-4 text-sm">
                                                        <div className="grid grid-cols-2 gap-2">
                                                            <div className="rounded-2xl bg-emerald-50 p-3">
                                                                <div className="text-xs font-bold text-emerald-700">Payment</div>
                                                                <div className="mt-1 font-extrabold text-emerald-950">
                                                                    {order.is_paid ? "Paid" : order.financial_status || "Unknown"}
                                                                </div>
                                                            </div>

                                                            <div className="rounded-2xl bg-amber-50 p-3">
                                                                <div className="text-xs font-bold text-amber-700">Fulfillment</div>
                                                                <div className="mt-1 font-extrabold text-amber-950">
                                                                    {order.is_fulfilled ? "Fulfilled" : "Awaiting fulfillment"}
                                                                </div>
                                                            </div>
                                                        </div>

                                                        <div className="rounded-2xl bg-slate-50 p-3">
                                                            <div className="text-xs font-bold text-slate-500">Tracking</div>
                                                            <div className="mt-1 font-semibold text-slate-950">
                                                                {order.tracking_number || "Not available yet"}
                                                            </div>
                                                        </div>

                                                        <div className="rounded-2xl border border-slate-200 bg-white p-3">
                                                            <div className="text-xs font-bold text-slate-500">Order Total</div>
                                                            <div className="mt-1 text-2xl font-extrabold text-slate-950">
                                                                {order.total_price} {order.currency}
                                                            </div>
                                                        </div>

                                                        <div className="rounded-2xl bg-tajeran-50 p-3 text-sm leading-6 text-tajeran-900">
                                                            Payment has been received for this order. The order has not been fulfilled yet, so tracking is not available until shipment is created.
                                                        </div>
                                                    </div>
                                                </>
                                            );
                                        })()}
                                    </div>
                                ) : runResult && isShopifyOrderResult(runResult) ? (
                                    <div className="mt-3 overflow-hidden rounded-3xl border border-emerald-100 bg-white shadow-sm shadow-emerald-100/70">
                                        <div className="bg-gradient-to-r from-emerald-500 to-emerald-700 px-4 py-3 text-white">
                                            <div className="text-xs font-bold uppercase tracking-wide text-emerald-50">
                                                Shopify Order Result
                                            </div>
                                            <div className="mt-1 text-xl font-extrabold tracking-tight">
                                                {runResult.order_name}
                                            </div>
                                        </div>

                                        <div className="space-y-3 p-4 text-sm">
                                            <div className="grid grid-cols-2 gap-2">
                                                <div className="rounded-2xl bg-emerald-50 p-3">
                                                    <div className="text-xs font-bold text-emerald-700">Payment</div>
                                                    <div className="mt-1 font-extrabold text-emerald-950">
                                                        {runResult.context?.is_paid ? "Paid" : "Pending"}
                                                    </div>
                                                </div>

                                                <div className="rounded-2xl bg-amber-50 p-3">
                                                    <div className="text-xs font-bold text-amber-700">Fulfillment</div>
                                                    <div className="mt-1 font-extrabold text-amber-950">
                                                        {runResult.context?.is_fulfilled ? "Fulfilled" : "Awaiting"}
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="rounded-2xl bg-slate-50 p-3">
                                                <div className="flex items-center justify-between gap-3">
                                                    <div>
                                                        <div className="text-xs font-bold text-slate-500">Tracking</div>
                                                        <div className="mt-1 font-semibold text-slate-950">
                                                            {runResult.context?.tracking?.tracking_number || "Not available yet"}
                                                        </div>
                                                    </div>
                                                    <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-600 shadow-sm">
                                                        {runResult.context?.tracking?.carrier || "No carrier"}
                                                    </span>
                                                </div>
                                            </div>

                                            <div className="rounded-2xl border border-slate-200 bg-white p-3">
                                                <div className="text-xs font-bold text-slate-500">Order Total</div>
                                                <div className="mt-1 text-2xl font-extrabold text-slate-950">
                                                    {runResult.context?.total_price} {runResult.context?.currency}
                                                </div>
                                            </div>

                                            <div className="rounded-2xl bg-tajeran-50 p-3 text-xs leading-5 text-tajeran-800">
                                                {runResult.context?.is_paid && !runResult.context?.is_fulfilled
                                                    ? "Payment has been received, but the order has not been fulfilled yet. Tracking will become available after shipment."
                                                    : "Order context was retrieved successfully from Shopify."}
                                            </div>
                                        </div>
                                    </div>
                                ) : runAnswer ? (
                                    <div className="mt-3 whitespace-pre-wrap rounded-2xl bg-white p-3 text-sm leading-6 text-slate-900 shadow-sm">
                                        {runAnswer}
                                    </div>
                                ) : (
                                    <div className="mt-3 rounded-2xl bg-white p-3 text-sm text-slate-500 shadow-sm">
                                        Run the workflow to see the customer-facing result.
                                    </div>
                                )}
                            </div>

                            <details className="rounded-2xl border border-slate-200 bg-white p-3">
                                <summary className="cursor-pointer text-xs font-bold uppercase tracking-wide text-slate-500">
                                    Developer details
                                </summary>
                                <pre className="mt-3 max-h-[360px] overflow-auto rounded-2xl bg-slate-950 p-4 text-xs text-slate-100">
                                    {JSON.stringify(runtime, null, 2)}
                                </pre>
                            </details>
                        </div>
                    </div>
  );
}
