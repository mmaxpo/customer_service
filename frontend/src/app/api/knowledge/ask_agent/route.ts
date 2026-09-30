import { BACKEND_URL, forwardJsonResponse } from "@/platform/backend";

export async function POST(req: Request) {
    const cookie = req.headers.get("cookie") ?? "";
    const url = new URL(req.url);
    const debug = url.searchParams.get("debug") ?? "false";
    const body = await req.text();

    const upstream = await fetch(`${BACKEND_URL}/kb/ask_agent?debug=${encodeURIComponent(debug)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", cookie },
        body,
    });

    const text = await upstream.text();
    return forwardJsonResponse(upstream, text);
}