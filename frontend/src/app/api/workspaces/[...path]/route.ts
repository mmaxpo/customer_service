import { BACKEND_URL, forwardJsonResponse } from "@/platform/backend";

type Params = { params: Promise<{ path: string[] }> };

async function proxy(req: Request, { params }: Params) {
  const { path } = await params;
  const url = new URL(req.url);
  const upstream = await fetch(
    `${BACKEND_URL}/workspaces/${path.join("/")}${url.search}`,
    {
      method: req.method,
      headers: {
        cookie: req.headers.get("cookie") ?? "",
        authorization: req.headers.get("authorization") ?? "",
        "content-type": req.headers.get("content-type") ?? "application/json",
      },
      body: req.method === "GET" || req.method === "HEAD" ? undefined : await req.text(),
      cache: "no-store",
    },
  );

  return forwardJsonResponse(upstream, await upstream.text());
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
