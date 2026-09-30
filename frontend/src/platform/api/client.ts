export type JsonBody = Record<string, unknown> | unknown[] | string | number | boolean | null;

export class ApiError extends Error {
    status: number;
    body: string;

    constructor(status: number, body: string) {
        super(`API request failed: ${status} ${body}`);
        this.name = "ApiError";
        this.status = status;
        this.body = body;
    }
}

export async function apiFetch(path: string, init: RequestInit = {}) {
    if (!path.startsWith("/api/")) {
        throw new Error(`Client API path must start with /api/. Got: ${path}`);
    }

    return fetch(path, {
        credentials: "include",
        ...init,
        headers: {
            ...(init.body && !(typeof FormData !== "undefined" && init.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
            ...(init.headers ?? {}),
        },
    });
}

export async function apiJson<T = any>(path: string, init: RequestInit = {}): Promise<T> {
    const res = await apiFetch(path, init);
    const text = await res.text();

    if (!res.ok) {
        if (res.status === 401 && typeof window !== "undefined") {
            const current = window.location.pathname;

            if (
                current.startsWith("/workflow-builder") ||
                current.startsWith("/runs") ||
                current.startsWith("/composer-test")
            ) {
                window.location.href = "/dev-console";
            } else if (current.startsWith("/app")) {
                window.location.href = "/login";
            }
        }

        throw new ApiError(res.status, text);
    }

    return text ? (JSON.parse(text) as T) : ({} as T);
}

export function apiErrorMessage(err: unknown, fallback: string): string {
    if (err instanceof ApiError) {
        try {
            const detail = JSON.parse(err.body)?.detail;
            if (typeof detail === "string" && detail.trim()) return detail;
        } catch {
            // Non-JSON error body; fall through to the fallback.
        }
        return fallback;
    }
    return err instanceof Error && err.message ? err.message : fallback;
}

export function jsonBody(body: JsonBody) {
    return JSON.stringify(body);
}

export function apiSseUrl(path: string) {
    if (!path.startsWith("/api/")) {
        throw new Error(`SSE API path must start with /api/. Got: ${path}`);
    }

    return new URL(path, window.location.origin).toString();
}
