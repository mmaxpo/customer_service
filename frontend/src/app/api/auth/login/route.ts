import { BACKEND_URL, copySetCookies, forwardJsonResponse } from "@/platform/backend";

export async function POST(req: Request) {
    const body = await req.text();

    const upstream = await fetch(`${BACKEND_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
    });

    // IMPORTANT: forward Set-Cookie back to browser
    const text = await upstream.text();
    const res = forwardJsonResponse(upstream, text);

    const setCookie = upstream.headers.get("set-cookie");
    if (setCookie) copySetCookies(upstream, res);

    return res;
}
