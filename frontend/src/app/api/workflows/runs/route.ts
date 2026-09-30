import { BACKEND_URL, forwardJsonResponse } from "@/platform/backend";

export async function GET(req: Request) {
    const cookie = req.headers.get("cookie") ?? "";
    const url = new URL(req.url);

    const qs = url.searchParams.toString();
    const upstream = await fetch(`${BACKEND_URL}/workflows_route/runs${qs ? `?${qs}` : ""}`, {
        method: "GET",
        headers: { cookie },
    });

    const text = await upstream.text();
    return forwardJsonResponse(upstream, text);
}