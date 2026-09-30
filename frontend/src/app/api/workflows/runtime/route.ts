import { BACKEND_URL, forwardJsonResponse } from "@/platform/backend";

export async function GET(req: Request) {
    const cookie = req.headers.get("cookie") ?? "";

    const upstream = await fetch(`${BACKEND_URL}/workflows_route/runtime`, {
        method: "GET",
        headers: { cookie },
    });

    const text = await upstream.text();
    return forwardJsonResponse(upstream, text);
}

export async function POST(req: Request) {
    const cookie = req.headers.get("cookie") ?? "";
    const body = await req.text();

    const upstream = await fetch(`${BACKEND_URL}/workflows_route/runtime`, {
        method: "POST",
        headers: { "Content-Type": "application/json", cookie },
        body,
    });

    const text = await upstream.text();

    return forwardJsonResponse(upstream, text);
}