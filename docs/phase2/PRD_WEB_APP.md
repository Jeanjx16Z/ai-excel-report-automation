# Product Requirements Document — Web Application

## Product overview

### Masalah bisnis

Pembuatan laporan biaya dari Excel rawan kesalahan manual, sulit diaudit, dan lambat untuk dipresentasikan.
Phase 1 membuktikan engine deterministik; Phase 2 merancang pengalaman upload-to-report yang dapat didemokan
tanpa memberi LLM kendali atas angka.

### Tujuan dan value proposition

- Mengubah `.xlsx` sintetis menjadi dashboard dan report yang konsisten.
- Memberi validation feedback yang dapat ditindaklanjuti.
- Menyimpan history input/report secara private dan dapat dihapus.
- Mendemonstrasikan AI interpretation yang aman, fallback, dan auditability.
- Menjadi fondasi production tanpa menulis ulang core KPI.

### Pengguna

- **Finance/Accounting Staff:** upload, validasi, generate, download, dan history.
- **Department Manager:** melihat variance departemen/kategori dan rekomendasi.
- **Management:** membaca executive summary dan KPI dashboard.
- **System Administrator (future production):** policy, retention, audit, provider, dan access control.

### Demo mode versus production mode

| Area | Demo | Production gate |
|---|---|---|
| Data | Synthetic/dummy only | Data nyata setelah classification dan approval |
| Login | Tidak ada application login | Authentication + RBAC wajib |
| Ownership | `anonymous_session_id` sementara | `user_id`/organization ownership enforced |
| AI | Gemini hanya untuk aggregate sintetis | Paid/enterprise provider + DPA/policy approval |
| History | Synthetic only, risiko diketahui | Authorized per owner/role |
| Warning | Selalu tampil | Policy banner sesuai classification |

No-login demo tidak aman untuk data confidential dan tidak memenuhi production security gate.

## User journeys

1. Pengguna membuka app dan melihat warning demo.
2. Pengguna menyetujui bahwa file hanya sintetis.
3. Pengguna drag-and-drop satu `.xlsx` sesuai template.
4. Backend memvalidasi file, schema, row limit, serta mapping; UI menampilkan feedback aman.
5. Setelah upload `ready`, pengguna menjalankan report generation synchronous dengan `upload_id`.
6. UI menampilkan indeterminate loading sampai response `201` atau safe synchronous error; intermediate state
   direkam internal tetapi tidak dijanjikan realtime.
7. Setelah `completed`, pengguna melihat KPI/dashboard dan AI/offline source.
8. Pengguna mengunduh `markdown`, `excel`, atau `pdf` melalui endpoint terkontrol.
9. Pengguna membuka history milik anonymous session/demo atau account production.
10. Pengguna menghapus report; artifacts dan metadata ditandai/dihapus konsisten.

Semua session-bound API call browser menggunakan same-origin `/api/v1/...` pada frontend. Next.js meneruskan
request ke FastAPI melalui controlled rewrite/proxy; browser tidak memakai backend project URL langsung.

## Functional requirements

| ID | Requirement |
|---|---|
| FR-01 | Warning demo terlihat sebelum upload dan pada history/detail. |
| FR-02 | Drag-and-drop satu `.xlsx`; macro-enabled, encrypted, corrupt, atau format lain ditolak. |
| FR-03 | Validasi file dan schema memakai kontrak core Phase 1. |
| FR-04 | Preview aman hanya menampilkan field allowlisted dan jumlah baris terbatas. |
| FR-05 | Job menyimpan state internal eksplisit; synchronous V1 tidak mewajibkan polling. |
| FR-06 | Semua KPI dihitung Python/Pandas. |
| FR-07 | AI hanya menginterpretasi aggregate payload; kegagalan menghasilkan offline fallback. |
| FR-08 | Dashboard menampilkan KPI, variance, department/category summary, dan source summary. |
| FR-09 | History list/detail dibatasi validated server-side ownership/session. |
| FR-10 | Output Markdown, Excel, dan PDF dapat diunduh melalui controlled download. |
| FR-11 | Delete menghapus artifacts dan memperbarui metadata/audit secara konsisten. |
| FR-12 | UI V1 menampilkan loading, success, atau safe error; status endpoint untuk recovery/future async. |
| FR-13 | Health/status indicator hanya menampilkan status operasional aman. |
| FR-14 | Same-origin proxy meneruskan cookie, CSRF, request ID, status, safe error, dan streaming secara benar. |
| FR-15 | Create-report idempotency me-replay hasil original, menolak payload conflict, dan tidak membuat processing kedua. |
| FR-16 | Delete hanya menjadi `deleted` setelah object terverifikasi hilang; `202` hanya bila durable cleanup executor tersedia. |

## File constraints

Semua nilai berikut configurable dan harus diverifikasi dengan benchmark/platform limit:

- `.xlsx` only; reject `.xlsm` dan macro-enabled workbook.
- Maksimum logical input **10 MB** dan 10.000 baris.
- Satu logical dataset per upload.
- Kolom wajib: `date`, `department`, `category`, `budget`, `actual_cost`.
- Duplicate handling tetap fail-fast.
- Reject encrypted, corrupt, external-link berisiko, atau workbook di luar resource budget.

Catatan: Vercel Functions mendokumentasikan request body limit 4,5 MB. Karena target logical file 10 MB,
browser meminta limited upload instruction, mengunggah langsung ke private storage, lalu menyelesaikan upload.
FastAPI hanya mempercayai opaque `upload_id` yang sudah diverifikasi, bukan URL/key dari client. Storage token
aktual tetap provider-specific Proposed dan menunggu proof of concept.

## Workbook contract

Kontrak **Current Phase 1**:

- `pandas.read_excel(..., engine="openpyxl")` membaca worksheet pertama secara default.
- Tidak ada mandatory sheet name; worksheet tambahan tidak ditolak dan tidak diproses.
- Required columns tepat `date`, `department`, `category`, `budget`, `actual_cost`; extra column ditolak.
- Empty/missing/blank, invalid date, non-numeric dtype, negative amount, invalid mapping, dan duplicate ditolak.
- Department/category di-trim; date dinormalisasi; duplicate diperiksa setelah normalisasi.
- Aplikasi tidak mengevaluasi formula sendiri dan belum menginspeksi formula/external links secara eksplisit.
  Nilai dari reader tetap divalidasi; hardening formula/external-link adalah Proposed change.

Pembatasan one logical dataset, encrypted/macro rejection, formula/external-link inspection, sheet count, dan
resource limits adalah Proposed Phase 2 hardening dan tidak boleh diklaim sebagai perilaku core saat ini.

Local vertical slice kini menerapkan hardening tersebut pada API adapter saja (bukan perubahan core),
dengan private filesystem dan PDF offline. Status lokal tidak memenuhi provider-backed deployment atau
production data gate; lihat [`LOCAL_VERTICAL_SLICE.md`](LOCAL_VERTICAL_SLICE.md).

## Public demo abuse controls

Proposed controls: rate limit per-IP/per-session, active-job limit, stored-report limit, daily processing quota,
concurrency limit, storage quota, short upload-token TTL, AI budget/circuit breaker, CAPTCHA/Turnstile equivalent,
emergency kill switch upload/AI, dan optional Vercel Deployment Protection pada preview. Nilai quota belum
Approved sampai load/cost test. Public production demo tetap synthetic-only.

Retention juga belum Approved: rekomendasi public anonymous demo 7 hari dan protected/internal demo 30 hari;
manual delete tetap tersedia. Production mengikuti legal/company policy.

## Non-functional requirements

| Attribute | Requirement awal |
|---|---|
| Correctness | KPI identik antar structured result, dashboard, Markdown, Excel, PDF. |
| Security/privacy | No secret di browser; raw file tidak ke LLM; private storage; safe errors. |
| Reliability | Fallback tetap menghasilkan numerical report; delete idempotent. |
| Performance | p95 demo hingga 10.000 rows memenuhi budget yang ditentukan benchmark; tidak timeout. |
| Usability | Actionable validation; progress state; download jelas. |
| Accessibility | WCAG 2.2 AA target untuk keyboard, labels, contrast, status announcements. |
| Observability | `request_id`, job state duration, safe errors, metrics tanpa raw values. |
| Maintainability | Layer modular, adapter external services, versioned API. |
| Scalability | Stateless API; storage/database external; queue-ready setelah evidence. |
| Testability | External services fake/mock; deterministic synthetic fixtures. |
| Compatibility | Modern Chrome/Edge/Firefox/Safari sesuai dukungan Next.js; Python 3.12 gated. |

## Output requirements

- Dashboard preview dari structured KPI.
- Markdown, Excel, dan deterministic PDF.
- Metadata: period, currency, synthetic flag, summary source.
- Semua output berasal dari satu immutable KPI snapshot.

## Acceptance criteria

### Demo

- 100% file valid pada fixture batas diterima; invalid file memberi error code dan pesan aman.
- 100% KPI fixture sama pada API, dashboard, Markdown, Excel, dan PDF.
- Zero raw transaction dalam captured AI requests; zero secret pada bundle/log/report.
- Sensitive aggregate labels dimasking/pseudonymized sebelum provider yang belum disetujui.
- Gemini timeout/provider error tetap menghasilkan `offline_fallback` report.
- Download ketiga format berhasil dan file dapat dibaca kembali.
- History/detail/delete hanya bekerja dalam anonymous session yang sama.
- Direct backend browser call ditolak; preview frontend/backend tidak mengandalkan dua domain `*.vercel.app`
  sebagai same-site cookie topology.
- Warning demo terlihat sebelum upload; synthetic flag tampil di detail/report.
- Benchmark 10.000 rows lulus function duration, memory, bundle, dan request architecture gate.
- Create report mengembalikan `201 completed`; AI failure tetap `201 completed` dengan `offline_fallback`;
  validation/business failure menghasilkan safe error dan persisted `failed` state.
- Duplicate report request memiliki stable in-progress/completed/failed replay; payload conflict menjadi `409`.
  Failed job boleh memberi opaque same-owner `report_id`, sedangkan pre-job failure tidak.
- Delete synchronous sukses menjadi `200 deleted`; partial cleanup tetap `deleting`, menghasilkan `202` hanya
  dengan durable executor atau safe `503` tanpa executor. Download sejak `deleting` ditolak.
- Current workbook contract dan setiap Proposed hardening memiliki fixture terpisah.
- Formula injection (`=`, `+`, `-`, `@`), unsafe HTML/Markdown, dan PDF external asset memiliki regression test.

### Production readiness

- Authentication, RBAC, ownership, retention, audit, incident response, dan security review disetujui.
- Enterprise/paid AI terms, DPA, residency, dan retention provider disetujui.
- Unauthorized cross-owner access selalu ditolak dan diuji.
- SLO, backup/recovery, monitoring, alert, rollback, dan migration runbook tersedia.

## Out of scope

ERP, email/Slack automation, autonomous decision, forecasting, ML anomaly detection, multi-company tenancy,
real confidential data pada demo, production SSO pada demo pertama, AI Agent, dan n8n.

## Success metrics

- Valid-file success rate ≥99% untuk fixture yang memenuhi kontrak.
- 100% validation failures memiliki stable error code dan actionable message.
- 100% report consistency fixtures lulus.
- Zero secret/raw-transaction leakage pada automated security regression.
- ≥99% successful downloads pada smoke/load test target.
- Critical flows memiliki automated test dan deployment gate.

## Open decisions

PDF renderer, chart library, production limits, auth/SSO, retention, provider AI, quotas, dan future sync/queue tetap
**Proposed**; lihat [`README.md`](README.md).
