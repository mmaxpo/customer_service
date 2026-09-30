import { BACKEND_URL, forwardJsonResponse } from "@/platform/backend";

type Ctx = { params: Promise<{ workflowId: string }> };

export async function GET(req: Request, ctx: Ctx) {
    const cookie = req.headers.get("cookie") ?? "";
    const { workflowId } = await ctx.params;

    const upstream = await fetch(`${BACKEND_URL}/workflows_route/runtime/${workflowId}`, {
        method: "GET",
        headers: { cookie },
    });

    const text = await upstream.text();
    return forwardJsonResponse(upstream, text);
}

export async function PUT(req: Request, ctx: Ctx) {
    const cookie = req.headers.get("cookie") ?? "";
    const { workflowId } = await ctx.params;
    const body = await req.text();

    const upstream = await fetch(`${BACKEND_URL}/workflows_route/runtime/${workflowId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", cookie },
        body,
    });

    const text = await upstream.text();
    return forwardJsonResponse(upstream, text);
}

export async function DELETE(req: Request, ctx: Ctx) {
    const cookie = req.headers.get("cookie") ?? "";
    const { workflowId } = await ctx.params;

    const upstream = await fetch(`${BACKEND_URL}/workflows_route/runtime/${workflowId}`, {
        method: "DELETE",
        headers: { cookie },
    });

    const text = await upstream.text();
    return forwardJsonResponse(upstream, text);
}