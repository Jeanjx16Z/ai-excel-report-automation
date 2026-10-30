# Deployment and Operations

## Target demo topology

- Next.js frontend pada Vercel project terpisah.
- FastAPI pada Vercel Python Functions **hanya jika** runtime/limits/benchmark gate lulus.
- Satu monorepo/repository, dua project dengan root/build configuration independen.
- Serverless-compatible PostgreSQL dan private object storage di region yang sesuai.
- Synthetic data only, no app login, warning wajib.
- Vercel Services hanya future option setelah availability/fit diverifikasi.

Browser hanya memakai frontend origin `/api/v1/...`. Next.js/Vercel rewrite atau controlled proxy meneruskan
request ke backend project; backend URL bukan authorization mechanism dan tidak menjadi browser session API.
Proxy harus mempertahankan `Set-Cookie`, CSRF header/token, `X-Request-ID`, status, safe error, dan streaming.
Backend menerapkan exact origin/host allowlist dan trusted-proxy policy serta menolak spoofed forwarding header.
Preview frontend wajib dipasangkan eksplisit ke preview backend; dua URL `*.vercel.app` berbeda tidak boleh
dianggap same-site cookie topology.

Neon adalah kandidat awal, bukan pilihan final. Connection model/pooling wajib mengikuti dokumentasi provider:
[Neon connection pooling](https://neon.com/docs/connect/connection-pooling).

Vercel Python runtime saat desain ini berstatus Beta dan 3.12 adalah default yang tersedia; deployment tetap
harus melewati compatibility gate: [Python runtime](https://vercel.com/docs/functions/runtimes/python).

## Production candidate

Menambahkan authentication/RBAC, enterprise AI, approved database/storage, residency review, retention
enforcement, incident response, monitoring/alerting, backup/restore, security approval, dan production SLO.
Jika Vercel Functions tidak cocok untuk Pandas/PDF workload, gunakan approved container/server platform.

## Environments

| Environment | Data | Purpose | Isolation |
|---|---|---|---|
| local | Synthetic | Development | Local services/emulators |
| test | Deterministic synthetic | Automated tests | Ephemeral |
| preview | Synthetic only | PR review/E2E | Separate DB/store/secrets |
| production | Demo synthetic initially | Released demo | Dedicated resources/secrets |

Production confidential mode tidak aktif sampai security gate lulus. Vercel menyediakan Local, Preview, dan
Production deployment environments: [deployments](https://vercel.com/docs/deployments).

## CI/CD

1. Lint/type/syntax dan secret scan.
2. Core, backend, frontend unit tests.
3. API/DB/storage integration tests memakai isolated resources/fakes.
4. Build frontend/backend dan bundle/runtime checks.
5. Preview deployment per PR dengan preview-only secrets/resources.
6. Browser E2E, upload security, report consistency, smoke/health.
7. Staged production build, approval, smoke, lalu promotion.
8. Rollback ke tested immutable deployment bila verification gagal.

Gunakan Git integration/deployment checks atau staged production flow; jangan menganggap preview promotion
menghasilkan build identik jika production env memicu rebuild. Referensi:
[Vercel Git deployments](https://vercel.com/docs/git),
[promoting deployments](https://vercel.com/docs/deployments/promoting-a-deployment), dan
[rollback](https://vercel.com/docs/cli/rollback).

## Environment variable inventory

| Name | Class | Owner | Rotation/notes |
|---|---|---|---|
| `APP_ENV` | Non-secret | Platform | Per environment |
| `FRONTEND_ORIGIN` | Non-secret | Platform | Exact allowlist |
| `DATABASE_URL` | Secret | Data/Platform | Provider rotation |
| `OBJECT_STORAGE_PROVIDER` | Non-secret | Platform | Adapter selector |
| `BLOB_READ_WRITE_TOKEN` / equivalent | Secret | Platform | Least privilege, rotate |
| `AI_PROVIDER` | Non-secret | AI/Platform | Adapter selector |
| `GEMINI_API_KEY` | Secret | AI/Platform | Demo paid only; rotate |
| `VERTEX_PROJECT_ID`, `VERTEX_LOCATION` | Non-secret/config | AI/Platform | Production candidate |
| Workload identity credentials | Secret/identity | Platform | Prefer short-lived/OIDC |
| `SESSION_SIGNING_KEY` | Secret | Security | Separate env, emergency rotation |
| `LOG_LEVEL` | Non-secret | SRE | No debug production |
| `ERROR_MONITOR_DSN` | Secret/config | SRE | Provider policy |
| `RETENTION_DAYS_INPUT`, `RETENTION_DAYS_REPORT` | Non-secret | Product/Security | Proposed public 7/protected 30 |

Nama dapat berubah saat adapter dipilih. Nilai tidak boleh dicontohkan dalam repository.

## Health, logs, metrics, alerts

- `/api/v1/health`: liveness/readiness minimal, no config leakage.
- Structured logs + `request_id`; trace across API/core/adapters with redaction.
- Metrics: request/error rate, validation code, state duration, fallback rate, timeout, artifact failure,
  DB pool saturation, storage errors, cleanup backlog.
- Alerts: elevated failure/latency, stuck jobs, provider outage, cleanup backlog, DB/storage availability,
  security events dan secret-scan failure.
- Public demo: per-IP/session quotas, concurrency, stored-report/storage limits, AI budget/circuit breaker,
  upload/AI kill switch; numeric limits Proposed setelah load/cost test.

## Function compatibility gates

- Verify Python 3.12 tests, Pandas/openpyxl/PDF native dependencies, cold start, bundle ≤ documented limit.
- Verify worst-case duration/memory and concurrency.
- Request/response body documented limit 4,5 MB berarti 10 MB upload membutuhkan direct storage flow.
- Verify region dan DB pooling. Official limits harus dibaca ulang sebelum implementasi:
  [Vercel Functions limits](https://vercel.com/docs/functions/limitations).

## Database migrations

Versioned, reviewed, backward-compatible expand/migrate/contract. Backup sebelum risky migration; migration
job hanya sekali per release; app deploy tidak boleh membuat destructive schema change otomatis. Rollback app
harus tetap kompatibel dengan schema baru.

## Retention cleanup dan disaster recovery

- Proposed retention: public anonymous 7 hari, protected/internal 30 hari; production legal/company policy.
- Durable cleanup executor masih **Proposed**: candidate berupa scheduled job/cron, durable workflow, atau
  approved worker. Automatic expiration/public demo release diblokir sampai candidate dipilih dan diuji.
- Executor mengubah expired job ke `deleting`, menghapus/verifikasi objects, baru `deleted`; reconciliation
  idempotent menangani orphan dan partial failure. Durable report processing dan cleanup adalah concern berbeda.
- Backup encrypted, region/policy compliant, restore diuji berkala; RPO/RTO ditetapkan sebelum production.
- Incident runbook: contain, revoke credentials, disable upload/provider, assess data, recover, notify.

## Rollback

Rollback frontend/backend ke known-good deployment; DB migrations memakai forward fix kecuali rollback telah
diuji. Setelah rollback, jalankan health, synthetic smoke, access control, download, dan cleanup checks.

## Synchronous processing dan direct upload

Browser memperoleh short-lived scoped instruction dari upload-intent endpoint, mengunggah langsung ke private
storage, lalu backend memverifikasi completion. `POST /reports` menerima `upload_id` dan tetap terbuka sampai
`201 completed` atau safe error. Internal states direkam tetapi UI hanya indeterminate loading. `202` hanya
future async **report processing** dengan durable queue/workflow. Deletion dapat mengembalikan `202` hanya bila
durable cleanup executor sudah tersedia. Provider-specific instruction Proposed sampai PoC. Storage CORS exact
allowlist; direct upload tidak membawa session cookie/permanent credential dan browser tidak memilih object key.

## Download delivery

Backend authorization-check sebelum streaming atau menerbitkan short-lived token scoped satu artifact.
Permanent public URL dilarang; `Cache-Control: private, no-store` wajib. Benchmark Excel/PDF size, function
response, dan bandwidth; gunakan provider-authenticated delivery bila proxy melewati limit. Pilihan final Proposed.

## AI operation policy

Local/test memakai fake/offline. Controlled synthetic demo dapat memakai Gemini; paid quota direkomendasikan
untuk hosted demo setelah cost controls. Production confidential memerlukan approved enterprise provider dengan
DPA/retention/residency review. Vertex AI/local model tetap kandidat. Public demo memiliki AI budget/rate limit,
circuit breaker, fallback, dan kill switch.

## Open decisions

Vercel Functions versus alternative host, PostgreSQL/storage provider, upload/download protocol, quotas,
retention, regions, monitoring, domain, CI provider, RPO/RTO, dan promotion model masih **Proposed**.
