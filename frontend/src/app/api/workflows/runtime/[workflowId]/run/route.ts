import { BACKEND_URL, forwardJsonResponse } from "@/platform/backend";

type Ctx = { params: Promise<{ workflowId: string }> };

export async function POST(req: Request, ctx: Ctx) {
    const cookie = req.headers.get("cookie") ?? "";
    const { workflowId } = await ctx.params;
    const body = await req.text();

    const upstream = await fetch(`${BACKEND_URL}/workflows_route/runtime/${workflowId}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json", cookie },
        body,
    });

    const text = await upstream.text();
    return forwardJsonResponse(upstream, text);
}