import { BACKEND_URL, forwardJsonResponse } from "@/platform/backend";

export async function POST(req: Request) {
    const cookie = req.headers.get("cookie") ?? "";
    const upstream = await fetch(`${BACKEND_URL}/auth/email-verification/request`, {
        method: "POST",
        headers: { cookie },
    });
    return forwardJsonResponse(upstream, await upstream.text());
}
