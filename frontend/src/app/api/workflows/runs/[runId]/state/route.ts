import { BACKEND_URL } from "@/platform/backend";

export async function GET(
    req: Request,
    { params }: { params: Promise<{ runId: string }> }
) {
    const { runId } = await params;

    const cookie = req.headers.get("cookie") ?? "";

    const upstream = await fetch(
        `${BACKEND_URL}/workflows_route/runs/${runId}/state`,
        {
            method: "GET",
            headers: { cookie },
        }
    );

    const text = await upstream.text();

    return new Response(text, {
        status: upstream.status,
        headers: {
            "Content-Type":
                upstream.headers.get("content-type") ?? "application/json",
        },
    });
}