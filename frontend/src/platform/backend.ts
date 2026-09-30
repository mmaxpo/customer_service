export const BACKEND_URL =
    process.env.BACKEND_URL ??
    process.env.NEXT_PUBLIC_BACKEND_URL ??
    "http://127.0.0.1:8000";

export function forwardJsonResponse(upstream: Response, text: string) {
    if (upstream.status === 204 || upstream.status === 304) {
        return new Response(null, {
            status: upstream.status,
        });
    }

    return new Response(text, {
        status: upstream.status,
        headers: {
            "Content-Type": upstream.headers.get("content-type") ?? "application/json",
        },
    });
}

export function copySetCookies(upstream: Response, response: Response) {
    const cookies = upstream.headers.getSetCookie?.() ?? [];
    if (cookies.length > 0) {
        for (const cookie of cookies) response.headers.append("set-cookie", cookie);
        return response;
    }
    const cookie = upstream.headers.get("set-cookie");
    if (cookie) response.headers.set("set-cookie", cookie);
    return response;
}
