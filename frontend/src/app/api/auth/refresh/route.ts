import { BACKEND_URL, copySetCookies, forwardJsonResponse } from "@/platform/backend";

export async function POST(req: Request) {
    const cookie = req.headers.get("cookie") ?? "";
    const csrf = /(?:^|;\s*)csrf_token=([^;]*)/.exec(cookie)?.[1] ?? "";

    const upstream = await fetch(`${BACKEND_URL}/auth/refresh`, {
        method: "POST",
        headers: { cookie, "x-csrf-token": decodeURIComponent(csrf) },
    });

    // Forward the rotated access/refresh cookies back to the browser.
    const text = await upstream.text();
    const res = forwardJsonResponse(upstream, text);
    if (upstream.headers.get("set-cookie")) copySetCookies(upstream, res);

    return res;
}
