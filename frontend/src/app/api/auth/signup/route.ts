import { BACKEND_URL, forwardJsonResponse } from "@/platform/backend";

export async function POST(req: Request) {
    const upstream = await fetch(`${BACKEND_URL}/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: await req.text(),
    });
    return forwardJsonResponse(upstream, await upstream.text());
}
