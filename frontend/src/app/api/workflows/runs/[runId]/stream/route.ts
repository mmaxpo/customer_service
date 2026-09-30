import { BACKEND_URL } from "@/platform/backend";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(
    req: Request,
    { params }: { params: Promise<{ runId: string }> }
) {
    const { runId } = await params;

    const cookie = req.headers.get("cookie") ?? "";
    const url = new URL(req.url);
    const afterSeq = url.searchParams.get("after_seq") ?? "0";

    const lastEventId =
        req.headers.get("last-event-id") ||
        req.headers.get("Last-Event-ID") ||
        "0";

    const upstreamUrl =
        `${BACKEND_URL}/workflows_route/runs/${runId}/stream` +
        `?after_seq=${encodeURIComponent(afterSeq)}`;

    console.log("Proxy workflow SSE upstream:", upstreamUrl);

    const upstream = await fetch(upstreamUrl, {
        method: "GET",
        headers: {
            cookie,
            "Last-Event-ID": lastEventId,
        },
        cache: "no-store",
    });

    return new Response(upstream.body, {
        status: upstream.status,
        headers: {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache, no-transform",
            Connection: "keep-alive",
            "X-Accel-Buffering": "no",
        },
    });
}