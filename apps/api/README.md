# FastAPI backend foundation — Phase 2.2

Synthetic-only, single-process local development. Session in-memory hilang saat restart dan tidak mendukung
multi-instance/serverless release. `API_ENV=production` ditolak saat startup sampai durable repository dan
production security gates tersedia. Local vertical slice berikutnya sudah menambahkan upload/report/PDF dan
private filesystem; durable database/cloud storage/history/production auth belum tersedia. Panduan website
terkini: [Local vertical slice](../../docs/phase2/LOCAL_VERTICAL_SLICE.md).

## Struktur dan arah dependency

```text
src/mining_api/app.py           Application factory, middleware, safe errors
src/mining_api/config.py        Validated configuration; tidak membaca dotenv
src/mining_api/routes.py        /api/v1 health dan session lifecycle
src/mining_api/dependencies.py  Service/identity dependency injection
src/mining_api/sessions.py      Session service dan ownership guard
src/mining_api/repositories.py  Protocol + hash-only in-memory implementation
src/mining_api/core_adapter.py  Installed excel_report imports, tanpa sys.path/subprocess
tests/                         Behavioral tests + opt-in localhost smoke
```

Routes memanggil service/repository. Future application service memakai core adapter; core tetap di
`src/excel_report`, tidak bergantung pada API, dan tidak menduplikasi KPI. Package API terpisah dari core;
install keduanya dari root repository.

## Windows PowerShell

```powershell
conda run -n ai-excel-automation-py312 python -s -m pip install -e . -e 'apps/api[test]'
```

Terminal backend, dari root repository (nilai secret berikut **fake, khusus localhost**):

```powershell
$env:API_ENV = 'development'
$env:API_PROXY_SECRET = 'fake-local-development-proxy-value-00000000'
$env:API_FRONTEND_ORIGIN = 'http://localhost:3000'
$env:API_COOKIE_SECURE = 'false'
conda run --no-capture-output -n ai-excel-automation-py312 python -s -m uvicorn mining_api.app:create_app --factory --host 127.0.0.1 --port 8000 --no-proxy-headers --no-access-log
```

Terminal frontend terpisah:

```powershell
$env:API_BACKEND_ORIGIN = 'http://127.0.0.1:8000'
$env:API_FRONTEND_ORIGIN = 'http://localhost:3000'
$env:API_PROXY_SECRET = 'fake-local-development-proxy-value-00000000'
$env:API_PROXY_LOCAL_HTTP = 'true'
$env:NEXT_TELEMETRY_DISABLED = '1'
Set-Location apps/web
npm ci
$env:PORT = '3000'
npm run dev:local
```

Buka frontend melalui `http://localhost:3000`, konsisten dengan origin konfigurasi. Hentikan masing-masing
server dengan `Ctrl+C`. Backend hanya bind ke loopback. Jangan aktifkan Uvicorn proxy-header trust; controlled
proxy membuang header forwarding client. Frontend tidak membaca `.env` root; konfigurasi di atas memakai
environment terminal saja. Backend tidak membaca dotenv sama sekali.

Terminal pemeriksaan:

```powershell
Invoke-RestMethod http://localhost:3000/api/v1/health
conda run -n ai-excel-automation-py312 python -s -m unittest discover -s tests -v
conda run -n ai-excel-automation-py312 python -s -m unittest discover -s apps/api/tests -p 'test_*.py' -v
conda run -n ai-excel-automation-py312 python -s -m pip check
```

Ganti nama environment menjadi `ai-excel-automation` untuk Python 3.11. `-s` mengisolasi dari user-site Python
global (termasuk paket notebook user yang bukan dependency project).

Smoke opt-in setelah `npm run build` dari `apps/web`, jalankan dari root:

```powershell
conda run -n ai-excel-automation-py312 python -s apps/api/tests/smoke_local.py
```

Smoke membuat secret ephemeral, menjalankan dua server localhost sementara, memeriksa health/session melalui
proxy, dan selalu menghentikan proses pada exit. Ini HTTP smoke, bukan verifikasi browser/cookie policy browser.

## Kontrak HTTP

| Endpoint | Hasil |
|---|---|
| `GET /api/v1/health` | `200 {"status":"ok"}`; tidak membuat session |
| `POST /api/v1/session` | Body `{}`; `201` + cookie dan CSRF token baru |
| `GET /api/v1/session` | `200` active/expiry atau safe `401` |
| `POST /api/v1/session/rotate` | Body `{}`, cookie + CSRF; `200` token/cookie baru |
| `DELETE /api/v1/session` | Cookie + CSRF; `204`, revocation dan cookie dihapus |

Cookie `mining_session`: host-only, `HttpOnly`, `SameSite=Lax`, `Path=/api/v1`, bounded `Max-Age`.
`Secure=true` default; hanya boleh false untuk explicit loopback HTTP development/test. Token dan CSRF memakai
32 random bytes; repository menyimpan SHA-256 hash saja. TTL default 3600 detik, range 60–86400. Rotation
mempertahankan owner internal dan expiry absolut, mencabut token lama secara atomik. Unknown/expired/revoked
cookie menghasilkan `401`; hapus cookie invalid sebelum bootstrap baru. Bootstrap dengan cookie valid wajib
CSRF dan melakukan rotation, sehingga tidak menjadi jalan pintas CSRF. Body owner ID ditolak.

Mutating request memerlukan exact frontend `Origin`; POST juga memerlukan JSON. Setelah session ada,
`X-CSRF-Token` wajib pada mutation. CSRF token hanya dikembalikan saat issuance/rotation, disimpan di memory
client (jangan localStorage/log); kehilangan token dapat dipulihkan dengan menghapus cookie dan bootstrap baru,
dengan konsekuensi kehilangan akses owner lama. Tidak ada owner ID, raw session token, atau internal session
ID dalam JSON; CSRF token adalah field issuance/rotation yang disengaja.

Semua request, termasuk health, memerlukan secret server-side `X-API-Proxy-Secret`; direct backend browser
request tanpa secret ditolak `403`. Origin/Host bukan satu-satunya authorization. Frontend proxy memiliki
fixed configured authority, allowlisted headers, no redirect following, timeout 10 detik, dan body limit 16 KiB
untuk JSON foundation dan 10 MiB untuk limited PUT upload lokal. Timeout proxy kini 120 detik (bukan hard
parser timeout). Ia meneruskan status, JSON, cookie/CSRF/request ID, Content-Disposition dan response stream. Backend menolak
spoofed `Forwarded`/`X-Forwarded-*`. Tidak ada CORS grant untuk cross-origin browser access.

Error envelope selalu `error.code`, safe `message`, dan UUID `request_id`; unknown route/method dan malformed
request juga memakai envelope. Foundation errors tanpa `report_id`; processing failure setelah report job
dibuat memiliki optional same-owner `report_id`. UUID request ID invalid
diganti server-generated UUID. Log API hanya mencatat request ID, event tetap, dan status; tidak mencatat raw
exception/header/path/query/body/token. Docs/OpenAPI HTTP endpoint dinonaktifkan; schema tersedia melalui
`app.openapi()` untuk contract tests.

## Dependency dan gate

`pyproject.toml` API mem-pin FastAPI (routing/DI), Uvicorn (ASGI lokal), Pydantic (config/schema), serta extra
test HTTPX. Core di-install secara terpisah; API tidak menambah SDK database/storage/AI. Warning deprecation
HTTPX TestClient dari Starlette dicatat; test transport saat ini tetap valid dan tidak melakukan provider call.
Session foundation lokal belum memenuhi target hash-only PostgreSQL persistence; durable session repository,
provider decision, browser verification, abuse controls, dan deployment gate tetap terbuka.
