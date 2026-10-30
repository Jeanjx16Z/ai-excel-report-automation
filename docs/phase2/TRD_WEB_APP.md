# Technical Requirements Document — Web Application

## Technology decisions

| Layer | Target | Alasan dan trade-off |
|---|---|---|
| Frontend | Next.js App Router + TypeScript | Modern SSR/client composition; menambah Node toolchain. |
| API | FastAPI | Selaras Python core; serverless compatibility harus dibuktikan. |
| Core | Existing Python/Pandas engine | Sudah deterministik dan teruji; hindari rewrite. |
| Metadata | PostgreSQL serverless-compatible | Relational constraints/history; perlu pooling dan migrations. |
| Files | Private object storage | Persisten dan controlled access; provider final belum disetujui. |
| AI | `AIProvider` adapter | Offline/fake local; controlled synthetic Gemini demo; enterprise/Vertex/local production candidates. |
| Hosting | Dua Vercel projects | Release boundary frontend/backend jelas; konfigurasi ganda. |

Referensi: [Next.js App Router](https://nextjs.org/docs/app),
[FastAPI deployment](https://fastapi.tiangolo.com/deployment/),
[Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python).

## Runtime dan compatibility

- Frontend: Node.js versi yang didukung release Next.js terpilih; pin setelah implementation approval.
- Backend development baseline: Python 3.11.18 sampai compatibility gate selesai.
- Deployment target: Python 3.12, **belum terbukti kompatibel**.
- Browser target awal: current stable dan baseline resmi Next.js (Chrome/Edge/Firefox 111+, Safari 16.4+),
  lalu diselaraskan dengan policy perusahaan.

### Python 3.11 → 3.12 compatibility gate

1. Buat environment 3.12 terpisah.
2. Install dependency backend/core yang dipin.
3. Jalankan syntax check.
4. Jalankan full suite.
5. Generate Markdown, Excel, PDF, dan structured output.
6. Bandingkan deterministic KPI fixtures byte/semantic sesuai format.
7. Benchmark memory, duration, dan bundle.
8. Baru ubah deployment runtime setelah semua gate lulus.

## Frontend requirements

- App Router, TypeScript strict, server/client boundary eksplisit.
- API client typed dari OpenAPI atau contract yang dipin.
- Tidak menghitung KPI di browser.
- Upload warning, accessible forms, progress state, dashboard, history, detail, download/delete.
- Tidak ada server secret pada `NEXT_PUBLIC_*` atau browser bundle.
- Browser memanggil same-origin `/api/v1`; Next.js rewrite/controlled proxy meneruskan ke FastAPI dan menjaga
  `Set-Cookie`, CSRF header/token, request ID, status, error body, serta streaming semantics.

## Backend requirements

- App factory, dependency injection, versioned router `/api/v1`, domain services, repository/adapters.
- Route handler hanya parsing, authorization context, orchestration, dan response mapping.
- Core adapter memanggil validation/KPI Phase 1 tanpa fork logic.
- Explicit timeouts, resource limits, safe exception mapping, request correlation.
- Synchronous V1 menerima verified `upload_id`, menahan request sampai selesai/gagal, lalu mengembalikan
  `201 completed` atau safe synchronous error. Report processing tidak memakai `202`; future async report
  hanya boleh melanjutkan pekerjaan setelah `202` bila durable report executor tersedia.
- FastAPI mengizinkan trusted proxy/origin/host saja, memvalidasi forwarding chain, dan tidak mempercayai
  spoofed `Forwarded`/`X-Forwarded-*` dari client.

## Database dan storage requirements

- UUID external identifiers, foreign keys, indexes, migrations forward-compatible.
- Serverless-safe connection/pool; region dekat compute.
- File private, random internal pathname, immutable artifacts, checksum, content type, size.
- Delete/retention transactional secara logis dan idempotent; orphan cleanup tersedia.
- Vercel Blob Private masih kandidat dan status/fit harus diverifikasi:
  [private storage](https://vercel.com/docs/vercel-blob/private-storage).

## Report generation dan AI

- Satu `kpi_snapshot` menjadi source semua renderer.
- Markdown/Excel/PDF adapter tidak mengubah KPI.
- `AIProvider.generate(allowlisted_payload)` menerima display-safe aggregate only.
- Aggregate labels diklasifikasi; unapproved provider hanya menerima masked/pseudonymous labels dan tidak
  menerima server-side mapping.
- Provider configurable per environment; timeout/fallback wajib; no provider retry storm.
- Cell content tidak pernah diperlakukan sebagai prompt instruction.

## API, error, dan configuration

- API version: `/api/v1`; breaking change memerlukan `/api/v2` atau deprecation plan.
- Error envelope: stable `code`, safe `message`, `request_id`, dan optional opaque same-owner `report_id` hanya
  untuk failure setelah job dibuat; tanpa stack/path/raw value/payload/provider error.
- Idempotency record menyimpan hash key dan canonical request, scoped owner+operation. Replay original
  completed/failed result, in-progress dan payload conflict memakai stable `409`; tidak ada duplicate job.
- Config tervalidasi saat startup; secret hanya server environment/secret manager.
- Environment terpisah: local, test, preview, production; tidak berbagi production data/secrets.

## Performance dan reliability budgets

- Logical limit demo: 10 MB/10.000 rows; physical upload flow harus mengatasi 4,5 MB Function body limit.
- Tetapkan benchmark p50/p95, memory peak, bundle size, DB connections sebelum deployment approval.
- Job state dipersist sebelum/sesudah tahap utama; processing berakhir `completed|failed`, deletion melalui
  `deleting`, dan `deleted` adalah terminal akhir.
- Synchronous v1 hanya jika worst-case berada aman di bawah platform limit. Jika tidak, pilih queue/workflow
  berdasarkan measurement, bukan asumsi.
- Internal states direkam untuk audit/diagnosis, bukan dijanjikan sebagai realtime progress UI.
- Rujukan: [Vercel Functions limits](https://vercel.com/docs/functions/limitations).

## Observability dan security requirements

- Structured logs: `request_id`, `report_id`, state, duration, outcome; no raw file/value/prompt/secret.
- Metrics: requests, validation failures, job duration, fallback rate, renderer failures, cleanup backlog.
- Trace API→core→storage/DB/AI dengan redaction.
- HTTPS, CORS allowlist, secure headers, rate limit, upload inspection, least privilege.

## Dependency, migration, dan backward compatibility

- Dependency dipin dan ditinjau; lockfile per ecosystem saat implementasi.
- Tidak menambah package sebelum threat/size/license review.
- DB migrations versioned, backward-compatible untuk staged deploy, dengan rollback/data backup plan.
- Core public contract dan KPI fixtures Phase 1 tidak boleh berubah tanpa explicit versioning.

## Environment separation

Preview memakai database bucket/store dan secrets terpisah dari production. Synthetic fixtures boleh tersedia
di test/preview; real production data tidak pernah disalin ke preview.

## API financial serialization

External ID adalah UUID string, timestamp RFC3339 UTC, currency ISO 4217, count JSON integer, monetary amount
canonical decimal string, dan percentage canonical decimal string atau `null`. Optional `display_value` dibuat
backend. Browser tidak memakai binary floating-point untuk financial contract dan tidak menghitung ulang KPI.

## Output context security

User-controlled text disanitasi per output context. Excel/CSV mencegah formula injection untuk prefix `=`, `+`,
`-`, `@`; Markdown/AI output tidak dirender sebagai trusted HTML; frontend melakukan output encoding; PDF tidak
memuat external asset tak terpercaya.

## Same-origin session topology

Anonymous cookie adalah first-party terhadap frontend origin. Browser tidak direct-call backend project untuk
session-bound API. Backend origin bukan authorization mechanism; authorization selalu berasal dari validated
server session. Direct storage upload tetap diizinkan memakai scoped instruction, tetapi session cookie dan
permanent credential tidak dikirim ke storage. Storage CORS hanya mengizinkan frontend origin, upload method,
dan header yang diperlukan. Setiap preview frontend harus memiliki rewrite menuju preview backend yang dipasangkan;
dua URL `*.vercel.app` berbeda tidak dianggap same-site solution.

## Deletion execution

Durable report processing dan durable cleanup adalah concern berbeda. Delete mempersist `deleting` lebih dulu,
lalu mencoba delete+verify dalam request. Semua object hilang menghasilkan `200 deleted`; incomplete cleanup
hanya menghasilkan `202` bila durable executor tersedia. Tanpa executor, safe `503` mempertahankan `deleting`
dan repeated same-owner `DELETE` mencoba lagi. Cross-owner `404`; download diblokir sejak `deleting`.

## Open decisions

Provider database/storage, ORM, PDF renderer, chart library, auth, monitoring, hosting backend, dan provider AI
masih **Proposed**. Python runtime Vercel dan Functions limits harus diverifikasi ulang saat implementasi.
