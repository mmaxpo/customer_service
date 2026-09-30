import { BACKEND_URL } from "@/platform/backend";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

async function proxy(req: Request) {
  const cookie = req.headers.get("cookie") ?? "";
  const url = new URL(req.url);

  const upstream = await fetch(`${BACKEND_URL}/workflow-waits${url.search}`, {
    method: req.method,
    headers: {
      cookie,
      "content-type": req.headers.get("content-type") ?? "application/json",
    },
    body: req.method === "GET" ? undefined : await req.text(),
    cache: "no-store",
  });

  const text = await upstream.text();

  return new Response(text, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "application/json",
    },
  });
}

export const GET = proxy;
export const POST = proxy;
