import { BACKEND_URL, forwardJsonResponse } from "@/platform/backend";

export async function GET(req: Request) {
    const cookie = req.headers.get("cookie") ?? "";

    const upstream = await fetch(`${BACKEND_URL}/auth/me`, {
        method: "GET",
        headers: { cookie },
    });

    const text = await upstream.text();
    return forwardJsonResponse(upstream, text);
}