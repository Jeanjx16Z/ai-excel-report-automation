import assert from "node:assert/strict";
import test from "node:test";
import { forwardApi, proxyConfig } from "../lib/api-proxy.mjs";

const environment = {
  API_BACKEND_ORIGIN: "http://127.0.0.1:8000", API_FRONTEND_ORIGIN: "http://localhost:3000",
  API_PROXY_SECRET: "fake-unit-test-proxy-value-000000000", API_PROXY_LOCAL_HTTP: "true",
};

test("proxy preserves status, cookies, CSRF, request ID and streams, strips spoofing", async () => {
  const id = "e5dcc190-116a-45af-a7da-97db33b4fd8f";
  const request = new Request("http://localhost:3000/api/v1/session", {
    method: "POST", body: "{}", headers: {
      origin: "http://localhost:3000", "content-type": "application/json",
      cookie: "mining_session=fake", "x-csrf-token": "fake-csrf", "x-request-id": id,
      "x-forwarded-host": "attacker.example", forwarded: "host=attacker.example",
      "x-api-proxy-secret": "attacker-value",
    },
  });
  const response = await forwardApi(request, ["session"], environment, async (url, options) => {
    assert.equal(url.origin, "http://127.0.0.1:8000");
    assert.equal(url.pathname, "/api/v1/session");
    assert.equal(options.headers.get("cookie"), "mining_session=fake");
    assert.equal(options.headers.get("x-csrf-token"), "fake-csrf");
    assert.equal(options.headers.get("x-api-proxy-secret"), environment.API_PROXY_SECRET);
    assert.equal(options.headers.has("x-forwarded-host"), false);
    assert.equal(options.headers.has("forwarded"), false);
    const headers = new Headers({ "content-type": "application/json" });
    headers.append("set-cookie", "mining_session=example; HttpOnly; Path=/api/v1");
    headers.append("set-cookie", "other=example; HttpOnly; Path=/api/v1");
    return new Response('{"csrf_token":"fake"}', { status: 201, headers });
  });
  assert.equal(response.status, 201);
  assert.equal(response.headers.get("x-request-id"), id);
  assert.equal(response.headers.getSetCookie().length, 2);
  assert.equal((await response.json()).csrf_token, "fake");
});

test("user path cannot change upstream authority", async () => {
  for (const path of [[".."], ["https://attacker.example"], ["%2f%2fexample"], []]) {
    const response = await forwardApi(new Request("http://localhost:3000/api/v1/health"), path,
      environment, () => { throw new Error("fetch must not be called"); });
    assert.equal(response.status, 422);
  }
});

test("missing/unsafe configuration fails closed without leaking configuration", async () => {
  assert.throws(() => proxyConfig({ ...environment, API_PROXY_LOCAL_HTTP: "false" }));
  assert.throws(() => proxyConfig({ ...environment, API_BACKEND_ORIGIN: "http://external.example" }));
  const response = await forwardApi(new Request("http://localhost:3000/api/v1/health"), ["health"], {});
  assert.equal(response.status, 503);
  assert.equal((await response.json()).error.code, "SERVICE_UNAVAILABLE");
});

test("upstream errors and redirect are safe, no automatic retry", async () => {
  for (const failure of ["throw", "redirect"]) {
    let calls = 0;
    const response = await forwardApi(new Request("http://localhost:3000/api/v1/health"), ["health"],
      environment, async () => {
        calls++;
        if (failure === "throw") throw new Error(environment.API_PROXY_SECRET);
        return new Response(null, { status: 307, headers: { location: "https://private.example" } });
      });
    assert.equal(calls, 1);
    assert.equal(response.status, 503);
    assert.equal((await response.text()).includes(environment.API_PROXY_SECRET), false);
  }
});

test("safe backend error envelope and status are preserved", async () => {
  const body = { error: { code: "INVALID_SESSION", message: "Sesi invalid", request_id: "example" } };
  const response = await forwardApi(new Request("http://localhost:3000/api/v1/session"), ["session"],
    environment, async () => Response.json(body, { status: 401 }));
  assert.equal(response.status, 401);
  assert.deepEqual(await response.json(), body);
});

test("Next internal URL hostname does not override the configured public Host", async () => {
  const request = new Request("http://internal-next-host:3000/api/v1/health", {
    headers: { host: "localhost:3000" },
  });
  const response = await forwardApi(request, ["health"], environment,
    async (target) => {
      assert.equal(target.origin, "http://127.0.0.1:8000");
      return Response.json({ status: "ok" });
    });
  assert.equal(response.status, 200);
  const invalidHost = new Request("http://localhost:3000/api/v1/health", { headers: { host: "evil.example" } });
  assert.equal((await forwardApi(invalidHost, ["health"], environment)).status, 422);
});

test("oversized or interrupted request bodies fail safely before upstream call", async () => {
  const oversized = new Request("http://localhost:3000/api/v1/session", {
    method: "POST", body: "x".repeat(16385),
  });
  const broken = new Request("http://localhost:3000/api/v1/session", {
    method: "POST", duplex: "half", body: new ReadableStream({
      start(controller) { controller.error(new Error("private-body-value")); },
    }),
  });
  for (const request of [oversized, broken]) {
    const response = await forwardApi(request, ["session"], environment,
      () => { throw new Error("upstream must not be called"); });
    assert.equal(response.status, 422);
    assert.equal((await response.text()).includes("private-body-value"), false);
  }
});

test("local upload uses bounded binary transport and forwards capability/idempotency headers", async () => {
  const request = new Request("http://localhost:3000/api/v1/uploads/example/content", {
    method: "PUT", body: new Uint8Array(20000), headers: { "content-type": "application/octet-stream",
      "x-upload-capability": "fake-capability", "idempotency-key": "fake-idempotency-key" },
  });
  const response = await forwardApi(request, ["uploads", "example", "content"], environment,
    async (target, options) => {
      assert.equal(options.body.length, 20000);
      assert.equal(options.headers.get("x-upload-capability"), "fake-capability");
      assert.equal(options.headers.get("idempotency-key"), "fake-idempotency-key");
      return new Response(new Uint8Array([37, 80, 68, 70]), { headers: {
        "content-type": "application/pdf", "content-disposition": 'attachment; filename="report.pdf"',
      } });
    });
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("content-disposition"), 'attachment; filename="report.pdf"');
});
