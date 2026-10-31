import { forwardApi } from "../../../../lib/api-proxy.mjs";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Context = { params: Promise<{ path: string[] }> };

async function proxy(request: Request, context: Context) {
  const { path } = await context.params;
  return forwardApi(request, path, {
    API_BACKEND_ORIGIN: process.env.API_BACKEND_ORIGIN,
    API_FRONTEND_ORIGIN: process.env.API_FRONTEND_ORIGIN,
    API_PROXY_SECRET: process.env.API_PROXY_SECRET,
    API_PROXY_LOCAL_HTTP: process.env.API_PROXY_LOCAL_HTTP,
  });
}

export { proxy as GET, proxy as HEAD, proxy as POST, proxy as PUT, proxy as PATCH,
  proxy as DELETE, proxy as OPTIONS };
