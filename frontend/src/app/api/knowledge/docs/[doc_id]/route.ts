import { BACKEND_URL, forwardJsonResponse } from "@/platform/backend";

export async function DELETE(
    req: Request,
    { params }: { params: Promise<{ doc_id: string }> }
) {
    const { doc_id } = await params;

    const cookie = req.headers.get("cookie") ?? "";

    const upstream = await fetch(
        `${BACKEND_URL}/kb/docs/${encodeURIComponent(doc_id)}`,
        {
            method: "DELETE",
            headers: { cookie },
        }
    );

    const text = await upstream.text();

    return forwardJsonResponse(upstream, text);
}