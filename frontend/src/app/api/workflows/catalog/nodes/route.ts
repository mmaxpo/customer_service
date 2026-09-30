import { BACKEND_URL } from "@/platform/backend";

export async function GET(req: Request) {
    const cookie = req.headers.get("cookie") ?? "";

    const upstream = await fetch(`${BACKEND_URL}/workflows_route/catalog/nodes`, {
        method: "GET",
        headers: { cookie },
    });

    return new Response(await upstream.text(), {
        status: upstream.status,
        headers: {
            "content-type": upstream.headers.get("content-type") ?? "application/json",
        },
    });
}