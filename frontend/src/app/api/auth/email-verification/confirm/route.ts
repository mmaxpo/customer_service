import { BACKEND_URL, forwardJsonResponse } from "@/platform/backend";

export async function POST(req: Request) {
    const body = await req.text();
    const upstream = await fetch(`${BACKEND_URL}/auth/email-verification/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
    });
    return forwardJsonResponse(upstream, await upstream.text());
}
