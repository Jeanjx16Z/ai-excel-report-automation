"""Opt-in localhost HTTP smoke; starts two temporary processes and always stops them.

Run after npm run build. This is not browser or external-provider verification.
"""

from http.cookiejar import CookieJar
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, ProxyHandler, Request, build_opener


def available_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", action="store_true")
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--npm-local", action="store_true", help="Verify the documented PowerShell npm script on an isolated PORT")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    backend_port, frontend_port = available_port(), available_port()
    if arguments.npm_local and os.name != "nt":
        parser.error("--npm-local verifies Windows PowerShell only")
    while frontend_port == backend_port:
        frontend_port = available_port()
    frontend_host = "localhost" if arguments.dev or arguments.npm_local else "127.0.0.1"
    frontend = f"http://{frontend_host}:{frontend_port}"
    backend = f"http://127.0.0.1:{backend_port}"
    environment = os.environ.copy()
    environment.update({
        "API_PROXY_SECRET": secrets.token_urlsafe(48), "API_ENV": "development",
        "API_COOKIE_SECURE": "false", "API_FRONTEND_ORIGIN": frontend,
        "API_BACKEND_ORIGIN": backend, "API_PROXY_LOCAL_HTTP": "true",
        "NEXT_TELEMETRY_DISABLED": "1", "PYTHONNOUSERSITE": "1",
        "PORT": str(frontend_port),
    })
    jar = CookieJar()
    client = build_opener(ProxyHandler({}), HTTPCookieProcessor(jar))
    processes = []

    def send(path, method="GET", data=None, csrf=None, origin=True, raw=None, extra=None):
        headers = {"Origin": frontend} if origin else {}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if csrf:
            headers["X-CSRF-Token"] = csrf
        headers.update(extra or {})
        request = Request(frontend + path, method=method, headers=headers,
                          data=raw if raw is not None else json.dumps(data).encode() if data is not None else None)
        try:
            return client.open(request, timeout=125)
        except HTTPError as response:
            return response

    try:
        processes.append(subprocess.Popen(
            [sys.executable, "-s", "-m", "uvicorn", "mining_api.app:create_app", "--factory",
             "--host", "127.0.0.1", "--port", str(backend_port), "--no-proxy-headers",
             "--no-access-log", "--log-level", "critical"],
            cwd=root, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ))
        frontend_command = (
            ["powershell.exe", "-NoProfile", "-Command", "npm.cmd run " + ("dev:local" if arguments.dev else "start:local")]
            if arguments.npm_local else
            [shutil.which("node"), str(root / "apps/web/node_modules/next/dist/bin/next"),
             "dev" if arguments.dev else "start", "--hostname", frontend_host, "--port", str(frontend_port)]
        )
        processes.append(subprocess.Popen(
            frontend_command,
            cwd=root / "apps/web", env=environment,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ))
        deadline = time.monotonic() + 45
        last_status = "unreachable"
        while time.monotonic() < deadline:
            if any(process.poll() is not None for process in processes):
                raise RuntimeError("A local service exited before smoke verification")
            try:
                health = send("/api/v1/health", origin=False)
                last_status = str(health.status)
                if health.status == 200:
                    break
            except (OSError, TimeoutError):
                pass
            time.sleep(0.25)
        else:
            # Status only: no response headers, configuration, credentials, or raw body.
            raise RuntimeError(f"Local same-origin health timed out (HTTP {last_status})")

        assert json.load(health) == {"status": "ok"}
        assert health.headers["X-Request-ID"]
        bootstrap = send("/api/v1/session", "POST", {})
        assert bootstrap.status == 201
        cookie = bootstrap.headers["Set-Cookie"]
        assert "HttpOnly" in cookie and "Path=/api/v1" in cookie and "SameSite=lax" in cookie
        csrf = json.load(bootstrap)["csrf_token"]
        assert send("/api/v1/session").status == 200
        assert send("/api/v1/session/rotate", "POST", {}).status == 403
        rotated = send("/api/v1/session/rotate", "POST", {}, csrf=csrf)
        assert rotated.status == 200
        csrf = json.load(rotated)["csrf_token"]
        assert send("/api/v1/session", "DELETE", csrf=csrf).status == 204
        assert send("/api/v1/session").status == 401
        direct = build_opener(ProxyHandler({}))
        try:
            direct.open(backend + "/api/v1/health", timeout=5)
            raise AssertionError("Direct backend request was accepted")
        except HTTPError as error:
            assert error.code == 403
        csrf = json.load(send("/api/v1/session", "POST", {}))["csrf_token"]
        template = send("/api/v1/template")
        assert template.status == 200 and template.read().startswith(b"PK")
        source = (root / "data/raw/accounting_sample.xlsx").read_bytes()
        from mining_api.report_service import XLSX_TYPE
        def upload(data):
            intent = json.load(send("/api/v1/uploads/intents", "POST", {
                "filename": "synthetic.xlsx", "size_bytes": len(data),
                "content_type": XLSX_TYPE, "synthetic_data_ack": True,
            }, csrf=csrf))
            instruction = intent["upload_instruction"]
            assert send(instruction["target"], "PUT", raw=data, csrf=csrf, extra=instruction["headers"]).status == 200
            completed = send(f"/api/v1/uploads/{intent['upload_id']}/complete", "POST", {}, csrf=csrf)
            return intent, completed
        intent, completed = upload(source)
        assert completed.status == 200
        key = secrets.token_urlsafe(24)
        report = send("/api/v1/reports", "POST", {"upload_id": intent["upload_id"]}, csrf=csrf, extra={"Idempotency-Key": key})
        assert report.status == 201
        report = json.load(report)
        assert report["summary_source"] == "offline" and report["kpis"]["transaction_count"] == 120
        assert report["kpis"]["total_budget"]["display_value"] == "Rp170.410.000.000"
        assert report["kpis"]["total_actual_cost"]["display_value"] == "Rp172.583.200.000"
        assert report["kpis"]["variance"]["display_value"] == "Rp2.173.200.000"
        assert report["kpis"]["variance_pct"]["display_value"] == "1.28%"
        assert send(f"/api/v1/reports/{report['report_id']}").status == 200
        outputs = root / ".runtime/verification"
        outputs.mkdir(parents=True, exist_ok=True)
        for format_name, extension in [("pdf", "pdf"), ("markdown", "md"), ("excel", "xlsx")]:
            artifact = send(f"/api/v1/reports/{report['report_id']}/download/{format_name}")
            assert artifact.status == 200 and "attachment" in artifact.headers["Content-Disposition"]
            (outputs / f"http_report.{extension}").write_bytes(artifact.read())
        from pypdf import PdfReader
        reader = PdfReader(outputs / "http_report.pdf")
        pdf_text = " ".join(page.extract_text() for page in reader.pages)
        assert "Ringkasan Eksekutif" in pdf_text, "Downloaded PDF is not the current renderer"
        assert any(
            font.get_object().get("/FontDescriptor")
            and "/FontFile2" in font.get_object()["/FontDescriptor"]
            for page in reader.pages for font in page["/Resources"]["/Font"].values()
        ), "Downloaded PDF does not embed its fonts"
        _, invalid = upload(b"corrupt synthetic workbook")
        assert invalid.status == 422
        print("Local HTTP smoke PASS: actual Excel upload -> validation -> KPI/offline summary -> PDF/Markdown/Excel download; invalid workbook rejected")
        if arguments.browser:
            subprocess.run([shutil.which("node"), str(root / "apps/web/tests/browser-local.mjs"), frontend],
                           cwd=root, env=environment, check=True, timeout=120)
        else:
            print("Browser verification NOT performed; use --browser for opt-in browser checks.")
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                if os.name == "nt":
                    # Next dev may create child workers; stop only the tree we started.
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    main()
