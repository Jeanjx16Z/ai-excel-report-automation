# Backend API Specification

## Conventions

- Base path `/api/v1`; JSON UTF-8 kecuali artifact download.
- External ID adalah UUID string; timestamp RFC3339 UTC; currency ISO 4217.
- Count adalah JSON integer. Monetary amount adalah canonical decimal string, bukan binary float.
- Percentage adalah canonical decimal string atau `null`.
- Setiap KPI response memiliki `schema_version`; optional `display_value` dibuat backend.
- Frontend hanya menampilkan nilai backend dan tidak menghitung ulang KPI.
- Semua response dikorelasikan dengan `X-Request-ID`.

### Error envelope

```json
{
  "error": {
    "code": "INVALID_FILE_SCHEMA",
    "message": "Kolom wajib pada file tidak lengkap.",
    "request_id": "3b120bb8-6b2e-4aed-a17b-08d6156f1d04",
    "report_id": "optional-opaque-same-owner-uuid"
  }
}
```

`report_id` hanya boleh ada bila `report_job` sudah berhasil dibuat dan selalu opaque serta terikat owner yang
sama. Failure sebelum job dibuat tidak memiliki field tersebut. Tidak ada stack trace, local path, object
key/URL, raw value/payload, provider response, atau credential. Report gagal yang masih dalam retention dapat
diakses melalui history/status/delete oleh owner/session yang sama.

### Stable error codes

| Code | HTTP |
|---|---:|
| `INVALID_SESSION` | 401 |
| `UPLOAD_INTENT_EXPIRED` | 410 |
| `UPLOAD_NOT_FOUND` | 404 |
| `UPLOAD_NOT_READY` | 409 |
| `IDEMPOTENCY_CONFLICT` | 409 |
| `REPORT_IN_PROGRESS` | 409 |
| `INVALID_FILE_TYPE` | 415 |
| `FILE_TOO_LARGE` | 413 |
| `CORRUPT_WORKBOOK` | 422 |
| `ENCRYPTED_WORKBOOK` | 422 |
| `INVALID_FILE_SCHEMA` | 422 |
| `PROCESSING_FAILURE` | 500 |
| `ARTIFACT_UNAVAILABLE` | 409/404 |
| `REPORT_EXPIRED` | 410 |
| `REPORT_DELETED` | 410 |
| `RATE_LIMITED` | 429 |
| `SERVICE_UNAVAILABLE` | 503 |

Cross-owner resource selalu `404`, bukan `403`, untuk mengurangi enumeration.

## Anonymous session behavior

Server membuat random high-entropy token dan mengirimkannya sebagai cookie `HttpOnly`, `Secure`,
`SameSite=Lax` atau lebih ketat, dengan bounded TTL. Database hanya menyimpan hash. Client tidak pernah
mengirim `anonymous_session_id` dalam body dan tidak menyimpan token di `localStorage`. Session dirotasi saat
creation/policy event untuk mencegah fixation. Mutating request memakai CSRF protection bila cookie digunakan.
Expired session kehilangan akses history kecuali future migration ke authenticated account tersedia.

## KPI schema

```json
{
  "schema_version": 1,
  "currency": "IDR",
  "total_budget": {"value": "600.00", "display_value": "Rp600"},
  "total_actual_cost": {"value": "600.00", "display_value": "Rp600"},
  "variance": {"value": "0.00", "display_value": "Rp0"},
  "variance_pct": {"value": "0.00", "display_value": "0.00%"},
  "transaction_count": 3,
  "over_budget_count": 1,
  "under_budget_count": 1,
  "on_budget_count": 1
}
```

Summary row memakai bentuk yang sama untuk monetary/percentage/count. Label `department`/`category` hanya
dikembalikan setelah classification policy.

## Direct upload protocol

Storage adapter menerjemahkan limited upload instruction provider-neutral menjadi mekanisme provider aktual.
Desain tidak mengasumsikan API Vercel Blob/provider lain tersedia sebelum proof of concept.

### `POST /api/v1/uploads/intents`

Membuat ownership-bound upload intent. Auth demo berasal dari validated cookie session.

```json
{
  "filename": "synthetic-costs.xlsx",
  "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "size_bytes": 1048576,
  "synthetic_data_ack": true
}
```

Response `201 Created`:

```json
{
  "upload_id": "b45a4c61-a3c7-413e-b647-1d5d98b12e7e",
  "state": "pending",
  "upload_instruction": {
    "method": "provider-defined",
    "target": "opaque-provider-instruction",
    "headers": {},
    "expires_at": "2027-01-01T10:05:00Z",
    "max_size_bytes": 10485760,
    "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  }
}
```

Instruction/token dibatasi server-generated object key, owner/session, content type, size, dan short TTL. Tidak
pernah berupa permanent credential/unrestricted token. Endpoint memvalidasi extension, declared size, content
type, session, acknowledgement, quota, dan rate limit. Audit: `upload.intent_created`.

### Direct browser upload

Browser mengunggah langsung ke private object storage memakai limited instruction. File 10 MB tidak melewati
FastAPI/Vercel body. Object key dibuat server, bukan user filename. Object tetap private.

### `POST /api/v1/uploads/{upload_id}/complete`

Body opsional hanya memuat provider-neutral proof/checksum bila diperlukan; arbitrary object URL/key ditolak.

```json
{
  "upload_id": "b45a4c61-a3c7-413e-b647-1d5d98b12e7e",
  "state": "ready",
  "size_bytes": 1048576,
  "checksum": "sha256:opaque-verified-value",
  "completed_at": "2027-01-01T10:02:00Z"
}
```

Server memverifikasi session owner, expiry, private object existence, expected prefix/reference, size, content
type, dan checksum bila tersedia. Status: `200`, `401`, `404`, `409`, `410`, `413`, `415`, `429`, `503`.

## Report endpoints

### `POST /api/v1/reports`

Menjalankan synchronous V1. `Idempotency-Key` wajib: 16–128 karakter ASCII dari allowlist
`A-Z a-z 0-9 . _ : -`. Server hanya menyimpan hash key dan men-scope-nya ke owner/session serta operation
`create_report`. Canonical request hash mencakup `upload_id` dan options yang sudah dinormalisasi; raw key dan
raw request tidak disimpan pada idempotency record. Request tetap terbuka sampai selesai/gagal. V1 tidak
mengembalikan `202` untuk report processing dan tidak menjalankan processing setelah response dikirim.

```json
{
  "upload_id": "b45a4c61-a3c7-413e-b647-1d5d98b12e7e",
  "summary_mode": "offline_or_configured_provider"
}
```

Backend memverifikasi upload `ready`, owner, expiry, dan belum diproses. Opaque `upload_id` adalah satu-satunya
file reference. Response sukses `201 Created`:

```json
{
  "report_id": "e5dcc190-116a-45af-a7da-97db33b4fd8f",
  "state": "completed",
  "summary_source": "offline_fallback",
  "schema_version": 1,
  "created_at": "2027-01-01T10:02:01Z",
  "completed_at": "2027-01-01T10:02:08Z",
  "expires_at": "2027-01-08T10:02:08Z",
  "kpis": {"schema_version": 1, "currency": "IDR"},
  "artifacts": []
}
```

Gemini failure tetap `201 completed` dengan `offline_fallback`. Validation/business failure setelah job dibuat
menyimpan state `failed` dan mengembalikan safe `4xx/5xx` dengan optional same-owner `report_id`; failure sebelum
job dibuat tidak memiliki ID tersebut.

Kontrak replay idempotency:

- Key sama + canonical request sama tidak pernah memulai processing kedua.
- Bila original masih berjalan, response `409 REPORT_IN_PROGRESS` memberi safe retry guidance dengan key yang
  sama; tidak ada job kedua.
- Bila original `completed`, server me-replay response sukses/report yang sama dengan `report_id` yang sama.
- Bila original `failed`, server me-replay safe failure/result yang sama selama record masih berlaku; tidak
  memproses ulang diam-diam.
- Key sama + canonical request berbeda menghasilkan `409 IDEMPOTENCY_CONFLICT`.
- Retry baru setelah failure memerlukan key baru. Upload yang sudah `consumed` tetap tidak boleh dipakai lagi;
  V1 tidak menyediakan retry contract untuk consumed upload sehingga user harus membuat upload intent baru.
- Retention/expiry idempotency record bersifat configurable dan minimal mencakup retry window serta report
  retention yang relevan. Setelah expiry, aturan consumed-upload tetap mencegah duplicate processing.

Frontend tidak boleh otomatis mengulang mutating request dengan key baru. Key baru hanya dibuat oleh explicit
user action atau policy yang terdokumentasi. Future async report boleh memakai `202` hanya setelah durable
queue/workflow tersedia; aturan ini terpisah dari `202` deletion di bawah.

### `GET /api/v1/reports`

Query: opaque `cursor`, `limit` 1–100, optional `state`.

```json
{
  "items": [
    {
      "report_id": "e5dcc190-116a-45af-a7da-97db33b4fd8f",
      "state": "completed",
      "summary_source": "offline",
      "created_at": "2027-01-01T10:02:01Z",
      "expires_at": "2027-01-08T10:02:08Z"
    }
  ],
  "next_cursor": "opaque-base64url-cursor-or-null"
}
```

Cursor menyandikan sort key secara opaque dan ditandatangani bila perlu; tidak memuat secret. History selalu
difilter oleh server-validated session/user.

### `GET /api/v1/reports/{report_id}`

```json
{
  "report_id": "e5dcc190-116a-45af-a7da-97db33b4fd8f",
  "state": "completed",
  "summary_source": "offline",
  "schema_version": 1,
  "metadata": {
    "period_start": "2025-01-01",
    "period_end": "2025-01-03",
    "currency": "IDR",
    "synthetic_data": true
  },
  "kpis": {"schema_version": 1, "currency": "IDR"},
  "department_summary": [],
  "category_summary": [],
  "artifacts": [
    {
      "artifact_id": "6d851f5f-211e-4093-9e3a-1fb184fe20bf",
      "format": "excel",
      "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "size_bytes": 24000,
      "generation_version": 1,
      "available": true
    }
  ],
  "created_at": "2027-01-01T10:02:01Z",
  "expires_at": "2027-01-08T10:02:08Z"
}
```

Generic detail tidak mengembalikan `object_key`, upload token, signed URL, atau raw transactions.

### `GET /api/v1/reports/{report_id}/status`

Untuk refresh/recovery dan future async compatibility, bukan mandatory polling V1.

```json
{
  "report_id": "e5dcc190-116a-45af-a7da-97db33b4fd8f",
  "state": "completed",
  "summary_source": "offline",
  "safe_error": null,
  "updated_at": "2027-01-01T10:02:08Z"
}
```

### `GET /api/v1/reports/{report_id}/download/{format}`

Format `markdown|excel|pdf`. Backend memverifikasi owner dan artifact. Adapter memilih authenticated streaming
atau short-lived restricted delivery scoped ke satu artifact. Tidak ada permanent public URL; token tidak masuk
log. Gunakan safe filename dan `Cache-Control: private, no-store`. Download ditolak sejak `deleting`.
Ukuran Excel/PDF dan Function response/bandwidth wajib dibenchmark. Jika proxy melanggar limit, gunakan
provider-supported authenticated delivery setelah ownership check. Mekanisme final **Proposed**.

### `DELETE /api/v1/reports/{report_id}`

Memulai `completed|failed → deleting → deleted`.

```json
{
  "report_id": "e5dcc190-116a-45af-a7da-97db33b4fd8f",
  "state": "deleted",
  "deletion_reason": "manual",
  "requested_at": "2027-01-02T08:00:00Z"
}
```

Backend lebih dahulu mempersist state `deleting`, memblokir download, lalu mencoba menghapus dan memverifikasi
seluruh object di dalam request selama time budget aman.

- Seluruh object terverifikasi hilang: `200 OK`, state `deleted`.
- Cleanup belum selesai dan durable cleanup executor/reconciler telah dikonfigurasi: `202 Accepted`, state
  tetap `deleting`. Ini bukan `202` untuk report processing.
- Cleanup belum selesai dan durable executor belum tersedia: safe `503 SERVICE_UNAVAILABLE`, state tetap
  `deleting`; response tidak mengklaim background work akan berjalan.

Repeated `DELETE` dari owner yang sama saat `deleting` bersifat idempotent dan mencoba cleanup/verifikasi lagi.
Repeated `DELETE` setelah `deleted` mengembalikan hasil idempotent konsisten. Cross-owner selalu `404`.
Object yang masih ada melarang transisi ke `deleted`. Reasons: `manual|expired|admin|policy`. Automatic
expiration hanya boleh diaktifkan jika durable cleanup executor tersedia.

## Common controls

- Per-IP/per-session rate limit, active jobs, stored reports, daily processing, concurrency, storage quota.
- AI call budget/circuit breaker dan emergency kill switches upload/AI.
- CAPTCHA/Turnstile equivalent dan Deployment Protection preview berstatus Proposed.
- CORS exact allowlist; CSRF wajib untuk mutating cookie-session request.
- Sensitive logging melarang session token/hash, object key, upload/download token, raw cell, prompt, financial
  detail, dan provider raw response.
- Output writers melakukan context-aware sanitization; Excel/CSV formula prefix `= + - @` dinetralisasi,
  Markdown tidak trusted HTML, frontend meng-encode output, dan PDF tidak memuat untrusted external asset.

## Report states

`uploaded`, `validating`, `processing`, `generating_summary`, `rendering_reports`, `completed`, `failed`,
`deleting`, `deleted`. `completed`/`failed` terminal untuk processing tetapi dapat masuk `deleting`; `deleted`
terminal. Internal states bukan realtime UI contract synchronous V1.

## Open decisions

Provider upload/download instruction, quota/rate limit, CAPTCHA, auth provider, cursor encoding, artifact
delivery, future async report executor, durable cleanup executor, dan idempotency retention masih **Proposed**.
