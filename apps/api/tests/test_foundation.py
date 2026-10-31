"""Behavioral API foundation tests using in-process HTTP transport and fake secrets."""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import unittest
from contextlib import ExitStack
from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi import Request
from fastapi.testclient import TestClient
from pydantic import ValidationError

from mining_api.app import create_app
from mining_api.config import Settings
from mining_api.core_adapter import analyze_workbook
from mining_api.dependencies import get_identity
from mining_api.errors import ApiError
from mining_api.repositories import InMemorySessionRepository
from mining_api.sessions import COOKIE_NAME, digest, require_same_owner

FAKE_SECRET = "fake-local-unit-test-value-000000000000"
ORIGIN = "http://localhost:3000"
guards = ExitStack()


def setUpModule():
    # Windows asyncio uses a loopback socketpair internally; block outbound HTTP transports
    # instead of socket.socket.connect so the in-process ASGI transport remains usable.
    guards.enter_context(patch("httpx.HTTPTransport.handle_request", side_effect=AssertionError("Network disabled in API tests")))
    guards.enter_context(patch("httpx.AsyncHTTPTransport.handle_async_request", side_effect=AssertionError("Network disabled in API tests")))
    guards.enter_context(patch("socket.create_connection", side_effect=AssertionError("Network disabled in API tests")))
    guards.enter_context(patch("dotenv.load_dotenv", side_effect=AssertionError("Dotenv disabled in API tests")))


def tearDownModule():
    guards.close()


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 31, tzinfo=timezone.utc)
        self.settings = Settings(proxy_secret=FAKE_SECRET, cookie_secure=False)
        self.repository = InMemorySessionRepository()
        self.app = create_app(self.settings, self.repository, lambda: self.now)
        self.client = TestClient(self.app, base_url="http://localhost",
                                 raise_server_exceptions=False,
                                 headers={"x-api-proxy-secret": FAKE_SECRET})

    def bootstrap(self):
        response = self.client.post("/api/v1/session", json={}, headers={"origin": ORIGIN})
        self.assertEqual(201, response.status_code)
        return response

    def assert_error(self, response, code, status):
        self.assertEqual(status, response.status_code)
        body = response.json()["error"]
        self.assertEqual(code, body["code"])
        self.assertEqual({"code", "message", "request_id"}, set(body))
        self.assertEqual(body["request_id"], response.headers["x-request-id"])
        UUID(body["request_id"])
        self.assertNotIn(FAKE_SECRET, response.text)

    def test_health_is_minimal(self):
        response = self.client.get("/api/v1/health")
        self.assertEqual(200, response.status_code)
        self.assertEqual({"status": "ok"}, response.json())
        self.assertEqual("no-store", response.headers["cache-control"])

    def test_unknown_route_and_method_have_safe_errors(self):
        self.assert_error(self.client.get("/api/v1/missing?secret=private"), "NOT_FOUND", 404)
        self.assert_error(self.client.post("/api/v1/health", json={}, headers={"origin": ORIGIN}),
                          "METHOD_NOT_ALLOWED", 405)

    def test_request_id_is_validated_or_generated(self):
        valid = str(uuid4())
        response = self.client.get("/api/v1/health", headers={"x-request-id": valid})
        self.assertEqual(valid, response.headers["x-request-id"])
        for invalid in ["private-value", "a" * 1000, "", "not-a-uuid"]:
            response = self.client.get("/api/v1/health", headers={"x-request-id": invalid})
            self.assertNotEqual(invalid, response.headers["x-request-id"])
            UUID(response.headers["x-request-id"])

    def test_internal_exception_does_not_leak_to_error_or_logs(self):
        @self.app.get("/api/v1/test-only-crash")
        def crash():
            raise RuntimeError("private-financial-value " + FAKE_SECRET)

        with self.assertLogs("mining_api", level="INFO") as logs:
            response = self.client.get("/api/v1/test-only-crash?secret=private")
        self.assert_error(response, "PROCESSING_FAILURE", 500)
        self.assertNotIn("private-financial-value", response.text + str(logs.output))
        self.assertNotIn(FAKE_SECRET, str(logs.output))
        self.assertNotIn("secret=private", str(logs.output))

    def test_validation_errors_hide_input_and_forbid_owner_body(self):
        for body in [{"owner_id": "private-owner"}, {"anonymous_session_id": "attacker"}, []]:
            response = self.client.post("/api/v1/session", json=body, headers={"origin": ORIGIN})
            self.assert_error(response, "INVALID_REQUEST", 422)
            self.assertNotIn("private-owner", response.text)

    def test_malformed_json_is_safe(self):
        response = self.client.post("/api/v1/session", content="{private",
                                    headers={"origin": ORIGIN, "content-type": "application/json"})
        self.assert_error(response, "INVALID_REQUEST", 422)

    def test_trusted_proxy_secret_is_required(self):
        for secret in ["", "wrong"]:
            self.assert_error(self.client.get("/api/v1/health", headers={"x-api-proxy-secret": secret}),
                              "UNTRUSTED_PROXY", 403)

    def test_origin_and_host_do_not_replace_service_auth(self):
        self.assert_error(self.client.get("/api/v1/health", headers={"origin": ORIGIN,
                          "x-api-proxy-secret": ""}), "UNTRUSTED_PROXY", 403)
        self.assert_error(self.client.get("/api/v1/health", headers={"host": "evil.example"}),
                          "UNTRUSTED_PROXY", 403)
        self.assert_error(self.client.get("/api/v1/health", headers={"origin": "https://evil.example"}),
                          "UNTRUSTED_PROXY", 403)

    def test_forwarded_headers_rejected(self):
        for name in ["forwarded", "x-forwarded-for", "x-forwarded-proto", "x-forwarded-host"]:
            self.assert_error(self.client.get("/api/v1/health", headers={name: "spoofed"}),
                              "UNTRUSTED_PROXY", 403)

    def test_session_cookie_flags_and_hash_only_storage(self):
        response = self.bootstrap()
        cookie = response.headers["set-cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=lax", cookie)
        self.assertIn("Path=/api/v1", cookie)
        self.assertIn("Max-Age=3600", cookie)
        token = self.client.cookies.get(COOKIE_NAME)
        self.assertEqual(43, len(token))
        record = self.repository.get(digest(token))
        serialized = repr(record)
        self.assertNotIn(token, serialized)
        self.assertNotIn(response.json()["csrf_token"], serialized)
        self.assertNotIn(token, response.text)
        self.assertEqual({"active", "expires_at", "csrf_token"}, set(response.json()))

    def test_https_cookie_is_secure(self):
        app = create_app(Settings(proxy_secret=FAKE_SECRET, frontend_origin="https://localhost:3000"))
        with TestClient(app, base_url="https://localhost", headers={"x-api-proxy-secret": FAKE_SECRET}) as client:
            response = client.post("/api/v1/session", json={}, headers={"origin": "https://localhost:3000"})
            self.assertIn("Secure", response.headers["set-cookie"])

    def test_current_session_and_expiry(self):
        self.bootstrap()
        self.assertEqual(200, self.client.get("/api/v1/session").status_code)
        self.now += timedelta(seconds=3600)
        self.assert_error(self.client.get("/api/v1/session"), "INVALID_SESSION", 401)

    def test_missing_or_invalid_session(self):
        self.assert_error(self.client.get("/api/v1/session"), "INVALID_SESSION", 401)
        self.client.cookies.set(COOKIE_NAME, "attacker-chosen-token")
        self.assert_error(self.client.get("/api/v1/session"), "INVALID_SESSION", 401)

    def test_fixation_never_adopts_unknown_cookie(self):
        self.client.cookies.set(COOKIE_NAME, "attacker-chosen-token")
        response = self.client.post("/api/v1/session", json={}, headers={"origin": ORIGIN})
        self.assert_error(response, "INVALID_SESSION", 401)
        self.assertNotIn("set-cookie", response.headers)

    def test_rotation_requires_csrf(self):
        self.bootstrap()
        for headers in [{"origin": ORIGIN}, {"origin": ORIGIN, "x-csrf-token": "wrong"}]:
            self.assert_error(self.client.post("/api/v1/session/rotate", json={}, headers=headers),
                              "CSRF_REJECTED", 403)

    def test_rotation_revokes_old_token_preserves_owner_and_absolute_expiry(self):
        first = self.bootstrap()
        old_token = self.client.cookies.get(COOKIE_NAME)
        old = self.repository.get(digest(old_token))
        self.now += timedelta(seconds=30)
        response = self.client.post("/api/v1/session/rotate", json={}, headers={
            "origin": ORIGIN, "x-csrf-token": first.json()["csrf_token"]})
        self.assertEqual(200, response.status_code)
        new_token = self.client.cookies.get(COOKIE_NAME)
        new = self.repository.get(digest(new_token))
        self.assertNotEqual(old_token, new_token)
        self.assertIsNone(self.repository.get(digest(old_token)))
        self.assertEqual(old.owner_id, new.owner_id)
        self.assertEqual(old.expires_at, new.expires_at)
        with self.assertRaises(ApiError):
            self.app.state.sessions.resolve(old_token)
        with self.assertRaises(ApiError):
            self.app.state.sessions.verify_csrf(new, first.json()["csrf_token"])

    def test_existing_bootstrap_cannot_bypass_csrf(self):
        self.bootstrap()
        self.assert_error(self.client.post("/api/v1/session", json={}, headers={"origin": ORIGIN}),
                          "CSRF_REJECTED", 403)

    def test_mutations_require_exact_origin_and_json(self):
        self.assert_error(self.client.post("/api/v1/session", json={}), "CSRF_REJECTED", 403)
        response = self.client.post("/api/v1/session", content="{}", headers={
            "origin": ORIGIN, "content-type": "text/plain"})
        self.assert_error(response, "INVALID_REQUEST", 422)

    def test_revocation_rejects_old_cookie(self):
        response = self.bootstrap()
        token = self.client.cookies.get(COOKIE_NAME)
        revoked = self.client.delete("/api/v1/session", headers={"origin": ORIGIN,
                                      "x-csrf-token": response.json()["csrf_token"]})
        self.assertEqual(204, revoked.status_code)
        with self.assertRaises(ApiError):
            self.app.state.sessions.resolve(token)
        self.assertTrue(self.repository.get(digest(token)).revoked)

    def test_same_owner_succeeds_and_cross_session_is_not_found(self):
        first, _, _ = self.app.state.sessions.issue()
        second, _, _ = self.app.state.sessions.issue()
        require_same_owner(first, first.owner_id)
        with self.assertRaises(ApiError) as error:
            require_same_owner(second, first.owner_id)
        self.assertEqual("NOT_FOUND", error.exception.code)

    def test_repository_capacity_and_atomic_duplicate_rotation(self):
        service = self.app.state.sessions
        old, _, _ = service.issue()
        service.issue(old)
        with self.assertRaises(ApiError):
            service.issue(old)
        repo = InMemorySessionRepository(capacity=0)
        with self.assertRaises(ApiError) as error:
            repo.save(old, self.now)
        self.assertEqual("SERVICE_UNAVAILABLE", error.exception.code)

    def test_application_has_only_documented_local_routes(self):
        paths = set(self.app.openapi()["paths"])
        self.assertEqual({"/api/v1/health", "/api/v1/session", "/api/v1/session/rotate", "/api/v1/session/reset",
                          "/api/v1/template", "/api/v1/uploads/intents", "/api/v1/uploads/{upload_id}/content",
                          "/api/v1/uploads/{upload_id}/complete", "/api/v1/reports", "/api/v1/reports/{report_id}",
                          "/api/v1/reports/{report_id}/download/{format_name}"}, paths)
        self.assertIn("/api/v1/health", self.app.openapi()["paths"])
        schema = self.app.openapi()
        self.assertNotIn("HTTPValidationError", schema["components"]["schemas"])
        self.assertEqual("#/components/schemas/ErrorEnvelope", schema["paths"]["/api/v1/session"]
                         ["post"]["responses"]["422"]["content"]["application/json"]["schema"]["$ref"])

    def test_cross_owner_lookup_is_http_404(self):
        from fastapi import Depends
        first, _, _ = self.app.state.sessions.issue()

        @self.app.get("/api/v1/test-only-owned-resource")
        def owned(identity=Depends(get_identity)):
            require_same_owner(identity, first.owner_id)
            return {"available": True}

        self.bootstrap()
        self.assert_error(self.client.get("/api/v1/test-only-owned-resource"), "NOT_FOUND", 404)


class ConfigurationTests(unittest.TestCase):
    def test_configuration_fails_closed(self):
        for config in [
            {}, {"proxy_secret": "short"}, {"environment": "production"},
            {"frontend_origin": "http://external.example", "cookie_secure": False},
            {"frontend_origin": "http://localhost:3000/path"},
            {"session_ttl_seconds": 0}, {"session_ttl_seconds": 86401},
            {"allowed_hosts": ("*",)},
        ]:
            values = {"proxy_secret": FAKE_SECRET} | config
            if not config:
                values = {}
            with self.subTest(config=config), self.assertRaises(ValidationError):
                Settings(**values)

    def test_configuration_does_not_read_dotenv(self):
        with patch.dict("os.environ", {"API_PROXY_SECRET": FAKE_SECRET}, clear=True), \
                patch("dotenv.load_dotenv", side_effect=AssertionError("dotenv must not be read")):
            self.assertTrue(Settings.from_environment().cookie_secure)

    def test_secrets_hidden_in_repr_and_validation(self):
        self.assertNotIn(FAKE_SECRET, repr(Settings(proxy_secret=FAKE_SECRET)))
        try:
            Settings(proxy_secret=FAKE_SECRET, session_ttl_seconds=0)
        except ValidationError as error:
            self.assertNotIn(FAKE_SECRET, str(error))


class CoreAdapterTests(unittest.TestCase):
    def test_installed_core_adapter_preserves_synthetic_baseline(self):
        root = Path(__file__).resolve().parents[3]
        analysis = analyze_workbook(root / "data/raw/accounting_sample.xlsx")
        expected = json.loads((root / "data/processed/analysis_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(expected["overall_kpis"], analysis.overall_kpis)


if __name__ == "__main__":
    unittest.main()
