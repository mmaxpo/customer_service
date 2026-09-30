import { BACKEND_URL, forwardJsonResponse } from "@/platform/backend";

type Params = {
  params: Promise<{ path: string[] }>;
};

function withCors(response: Response) {
  response.headers.set("Access-Control-Allow-Origin", "*");
  response.headers.set("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS");
  response.headers.set("Access-Control-Allow-Headers", "Content-Type, Authorization");
  return response;
}

async function proxy(req: Request, { params }: Params) {
  const { path } = await params;
  const targetPath = path.join("/");
  const url = new URL(req.url);
  const upstreamUrl = `${BACKEND_URL}/customer-service/${targetPath}${url.search}`;

  const body =
    req.method === "GET" || req.method === "HEAD" ? undefined : await req.arrayBuffer();

  const upstream = await fetch(upstreamUrl, {
    method: req.method,
    headers: {
      cookie: req.headers.get("cookie") ?? "",
      authorization: req.headers.get("authorization") ?? "",
      ...(req.headers.get("content-type") ? { "content-type": req.headers.get("content-type")! } : {}),
    },
    body,
    cache: "no-store",
  });

  const text = await upstream.text();
  return withCors(forwardJsonResponse(upstream, text));
}

export async function GET(req: Request, ctx: Params) {
  return proxy(req, ctx);
}

export async function POST(req: Request, ctx: Params) {
  return proxy(req, ctx);
}

export async function PATCH(req: Request, ctx: Params) {
  return proxy(req, ctx);
}

export async function DELETE(req: Request, ctx: Params) {
  return proxy(req, ctx);
}


export async function PUT(req: Request, ctx: Params) {
  return proxy(req, ctx);
}


export async function OPTIONS() {
  return withCors(new Response(null, { status: 204 }));
}
