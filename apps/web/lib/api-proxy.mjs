// Server-only use through the route handler. Environment values never enter client components.
import { randomUUID } from "node:crypto";

const validId = (value) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value ?? "");
const safeHeaders = ["accept", "content-type", "cookie", "origin", "x-csrf-token", "x-upload-capability", "idempotency-key"];

function failure(code, status, requestId) {
  const message = code === "INVALID_REQUEST" ? "Format permintaan tidak valid." : "Layanan sementara tidak tersedia.";
  return Response.json({ error: { code, message, request_id: requestId } }, {
    status, headers: { "X-Request-ID": requestId, "Cache-Control": "no-store" },
  });
}

export function proxyConfig(environment) {
  const target = new URL(environment.API_BACKEND_ORIGIN);
  const frontend = new URL(environment.API_FRONTEND_ORIGIN);
  const secret = environment.API_PROXY_SECRET;
  for (const url of [target, frontend]) {
    if (url.pathname !== "/" || url.search || url.hash || url.username || url.password) {
      throw new Error("Invalid proxy origin configuration");
    }
    const local = ["localhost", "127.0.0.1"].includes(url.hostname);
    if (url.protocol !== "https:" && !(url.protocol === "http:" && local && environment.API_PROXY_LOCAL_HTTP === "true")) {
      throw new Error("Proxy origin requires HTTPS or explicit loopback HTTP");
    }
  }
  if (!/^[A-Za-z0-9_-]{32,256}$/.test(secret ?? "")) throw new Error("Missing proxy configuration");
  return { backendOrigin: target.origin, frontendOrigin: frontend.origin, secret };
}

export async function forwardApi(request, segments, environment, fetcher = fetch) {
  const incomingId = request.headers.get("x-request-id");
  const requestId = validId(incomingId) ? incomingId.toLowerCase() : randomUUID();
  let config;
  try { config = proxyConfig(environment); } catch { return failure("SERVICE_UNAVAILABLE", 503, requestId); }
  if (!segments.length || segments.some((part) => !/^[A-Za-z0-9_-]+$/.test(part))) {
    return failure("INVALID_REQUEST", 422, requestId);
  }
  // Target authority is fixed in server configuration, never derived from user URL/headers/query.
  const incoming = new URL(request.url);
  // Next.js may construct request.url with an internal hostname. Validate the public Host
  // against explicit configuration; never use Host/forwarding headers to choose the target.
  const publicHost = request.headers.get("host") ?? incoming.host;
  if (publicHost !== new URL(config.frontendOrigin).host) return failure("INVALID_REQUEST", 422, requestId);
  const target = new URL(`/api/v1/${segments.join("/")}`, config.backendOrigin);
  target.search = incoming.search;
  const headers = new Headers();
  for (const name of safeHeaders) {
    if (request.headers.has(name)) headers.set(name, request.headers.get(name));
  }
  headers.set("x-request-id", requestId);
  headers.set("x-api-proxy-secret", config.secret);
  let body;
  if (!["GET", "HEAD"].includes(request.method) && request.body) {
    try {
      // Explicit LOCAL transport only. This is not a cloud/serverless direct-upload solution.
      const localUpload = request.method === "PUT" && segments.length === 3
        && segments[0] === "uploads" && segments[2] === "content";
      const limit = localUpload ? 10 * 1024 * 1024 : 16384;
      const reader = request.body.getReader();
      const chunks = [];
      let size = 0;
      while (true) {
        const chunk = await reader.read();
        if (chunk.done) break;
        size += chunk.value.byteLength;
        if (size > limit) { await reader.cancel(); return failure("INVALID_REQUEST", 422, requestId); }
        chunks.push(chunk.value);
      }
      body = Buffer.concat(chunks);
    } catch {
      return failure("INVALID_REQUEST", 422, requestId);
    }
  }
  try {
    const upstream = await fetcher(target, {
      method: request.method, headers, body, redirect: "manual", cache: "no-store",
      signal: AbortSignal.timeout(120000),
    });
    // Redirect targets are never relayed: avoids leaking backend URL or service credentials.
    if (upstream.status >= 300 && upstream.status < 400) {
      await upstream.body?.cancel();
      return failure("SERVICE_UNAVAILABLE", 503, requestId);
    }
    const outgoing = new Headers({ "Cache-Control": "no-store", "X-Request-ID": requestId });
    for (const name of ["content-type", "content-disposition", "allow", "x-csrf-token"]) {
      if (upstream.headers.has(name)) outgoing.set(name, upstream.headers.get(name));
    }
    // Preserve individual Set-Cookie values without comma-joining them.
    for (const cookie of upstream.headers.getSetCookie()) outgoing.append("set-cookie", cookie);
    return new Response(upstream.body, { status: upstream.status, headers: outgoing });
  } catch {
    return failure("SERVICE_UNAVAILABLE", 503, requestId);
  }
}
