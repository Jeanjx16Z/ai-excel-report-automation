# Security and Privacy Design

## Data classification

| Class | Contoh | Policy |
|---|---|---|
| Public | Dokumentasi publik, template kosong | Boleh dipublikasikan setelah review |
| Internal | Metadata operasional non-sensitive | Authenticated internal access |
| Confidential | Financial aggregates, reports, filenames | Encryption, private access, retention |
| Restricted | Credentials, personal data, highly sensitive raw records | Dedicated controls; demo menolak |

Synthetic demo data tetap diperlakukan seolah confidential untuk membuktikan controls.

## Demo policy

- Synthetic/dummy only; dilarang mengunggah real confidential/personal company data.
- UI wajib menampilkan: **“Demo only — do not upload real confidential or personal company data.”**
- No-login dan anonymous history memiliki risiko session theft/enumeration; hanya dapat diterima untuk demo.
- Demo tidak memenuhi production security gate.
- Public anonymous demo retention rekomendasi 7 hari; 30 hari hanya protected/internal demo. Keduanya Proposed.

## Production security gate

Sebelum data nyata: authentication, RBAC, ownership enforcement, enterprise/paid AI provider yang disetujui,
DPA dan data residency review, retention enforcement, audit, incident response, threat model/security review,
backup/recovery, vulnerability management, dan company approval wajib selesai.

## Upload security

Local slice mengimplementasikan pre-parse ZIP/XML inspection, reject formula/macro/external link, serta
sheet/row/column/size limits di API adapter. Core Phase 1 tidak diubah. Detail enforcement dan batas tanpa
hard parser timeout/sandbox ada pada [`LOCAL_VERTICAL_SLICE.md`](LOCAL_VERTICAL_SLICE.md).

- Allowlist `.xlsx`; reject `.xlsm`, encrypted, corrupt, macro-enabled, dan unexpected content.
- Validasi extension, MIME, ZIP signature/structure, workbook parser result, size, row count, sheet count.
- Random opaque internal filenames; jangan gabungkan user filename ke path/object key.
- Cegah traversal, external links/data connections, formula injection pada exported CSV/Excel, dan unsafe XML.
- Batasi decompression ratio, ZIP members, CPU, memory, parser timeout, dan concurrent jobs.
- Jangan mengeksekusi macro/formula; treat formulas/cell text sebagai data, bukan instruction.
- Malware scanning menjadi production requirement jika provider/tool disetujui.
- Upload 10 MB harus memakai architecture yang tidak melanggar Function body limit 4,5 MB.
- Direct upload memakai short-lived instruction scoped ke server-generated object key, owner, size, type, dan
  TTL. Completion memverifikasi private object; client URL/key tidak dipercaya langsung.

## Application security

- HTTPS only, HSTS, CSP, `X-Content-Type-Options`, frame protection, referrer policy.
- CORS exact allowlist; CSRF token/SameSite jika cookie session dipakai.
- Rate limit per actor/IP, request validation, output encoding, safe filenames.
- Stable safe errors; stack trace hanya private observability dengan redaction.
- Dependency/license/security scanning; pinned versions; least-privilege DB/storage/provider credentials.
- Production authorization dilakukan server-side pada setiap list/detail/status/download/delete.

### Anonymous session dan abuse controls

- Server menghasilkan token high-entropy dalam cookie `HttpOnly`, `Secure`, `SameSite=Lax` atau lebih ketat,
  bounded TTL; database hanya menyimpan hash.
- `anonymous_session_id` tidak diterima dari body dan token tidak disimpan di `localStorage`.
- Rotation/fixation prevention dan CSRF untuk mutating cookie request wajib.
- History difilter dari server-validated session; cross-session menjadi `404`; expiry memutus history.
- Browser memakai frontend same-origin `/api/v1`; controlled proxy meneruskan cookie, CSRF, request ID, status,
  dan safe error ke backend. Backend menolak origin/host yang tidak diizinkan, direct browser call, serta
  spoofed forwarding headers. Dua preview `*.vercel.app` terpisah tidak dianggap same-site; setiap preview
  frontend harus dipasangkan ke backend melalui rewrite yang dikontrol.
- Direct upload storage tidak membawa session cookie atau permanent credential. Storage CORS hanya menerima
  frontend origin, method, dan header minimum untuk short-lived scoped instruction.
- Proposed public-demo controls: per-IP/per-session rate limit, active-job/stored-report/daily/concurrency/storage
  quotas, short upload TTL, AI budget/circuit breaker, CAPTCHA/Turnstile, upload/AI kill switches, dan optional
  Deployment Protection preview. Angka final menunggu load/cost test.

## File security

- Private object storage; no public object URLs/assets.
- Encryption in transit dan at rest; authenticated/signed short-lived download.
- `Cache-Control: private, no-store` untuk report sensitive.
- Public demo retention rekomendasi 7 hari; protected/internal demo 30 hari; manual delete tersedia.
- Immutable artifacts, checksum, backup policy, deletion verification, orphan cleanup.
- Backup production harus mengikuti residency, encryption, retention, dan restore tests.

Vercel Blob Private adalah kandidat, bukan keputusan final. Private storage membutuhkan authenticated access dan
delivery melalui Function: [official documentation](https://vercel.com/docs/vercel-blob/private-storage).

## AI security

- Builder payload melakukan explicit allowlist: metadata, overall KPI, department/category aggregate.
- Tidak mengirim file mentah, rows, PII, local path, storage key, atau credential.
- Scanner/masking/rejection berjalan sebelum external AI call untuk sensitive fields.
- Spreadsheet cell tidak pernah dimasukkan sebagai system/user instruction.
- Allowlisted field name tidak otomatis aman: label department/category dapat berisi vendor, orang, proyek, atau
  informasi confidential. Demo hanya synthetic labels. Production mengklasifikasi dan masking/pseudonymizing
  label untuk unapproved provider; mapping server-side tidak dikirim ke provider.
- Structured response divalidasi; KPI final selalu dari snapshot Python.
- Timeout dan provider error menghasilkan offline fallback; raw provider response tidak masuk user error/log.
- Local/test memakai offline/fake AI default. Controlled demo boleh Gemini hanya dengan synthetic data; paid
  Gemini direkomendasikan untuk hosted demo bila billing/cost control disetujui. Gemini unpaid/free services
  dilarang untuk confidential/personal data. Terms resmi menyatakan content pada unpaid
  services dapat digunakan untuk improvement dan human review serta memperingatkan agar tidak mengirim sensitive
  information: [Gemini API terms](https://ai.google.dev/gemini-api/terms).
- Production memakai paid/enterprise provider yang lolos DPA/residency/retention review. Vertex AI menjadi
  kandidat bila dibutuhkan governance enterprise; review
  [Vertex AI data governance](https://cloud.google.com/vertex-ai/generative-ai/docs/data-governance).
  Untuk no-egress policy gunakan approved local/on-prem model.

## Secret management

- Secret hanya server-side environment/managed secret store, dipisah preview/production.
- Tidak ada secret di Git, docs, database, browser bundle, report, log, prompt, atau URL.
- Rotation schedule dan emergency rotation; least privilege per project/provider.
- `NEXT_PUBLIC_*` hanya non-secret. Runtime identity/OIDC diprioritaskan bila tersedia.

## Logging dan audit

Log: `request_id`, actor/session ID terhash/pseudonymous, report ID, action, timestamp, stage, duration, outcome,
safe error code. Jangan log raw financial values, file content, filename mentah, API key, signed URL, complete
prompt, provider raw response, atau local path. Audit event bersifat append-only sesuai approved retention.

## Output dan deletion security

- User-controlled text disanitasi sesuai Excel/CSV/PDF/Markdown/HTML context.
- Cegah formula injection untuk prefix `=`, `+`, `-`, `@`; AI Markdown tidak trusted HTML; frontend output
  encoding wajib; PDF tidak memuat external asset tak terpercaya.
- Delete selalu `completed|failed → deleting → deleted`; download ditolak sejak `deleting`.
- Partial failure tetap `deleting`; bila durable reconciler tersedia ia mengulang cleanup. Tanpa executor,
  request mengembalikan safe `503` dan repeated owner `DELETE` mencoba lagi—tidak ada klaim background work.
- Expiration memakai flow sama dengan `deletion_reason`; automatic expiration membutuhkan durable cleanup
  executor yang dipilih dan diuji. Audit/tombstone retention terpisah dari file retention.

## Risk register

| Risk | Likelihood | Impact | Mitigation | Owner | Production blocking |
|---|---|---|---|---|---|
| Real data uploaded ke no-login demo | Medium | High | Warning, acknowledgement, synthetic-only policy, scanning | Product/Security | Yes |
| Cross-session/history access | Medium | High | Opaque tokens, owner filtering; auth/RBAC production | Backend/Security | Yes |
| Public file exposure | Low | Critical | Private store, auth download, no public URL | Platform | Yes |
| Malicious/corrupt workbook | High | High | Inspection, limits, sandbox/resource controls, malware scan | Backend/Security | Yes |
| Raw transaction sent to LLM | Low | Critical | Allowlist builder, regression capture tests | AI/Backend | Yes |
| Free-tier AI used for confidential data | Medium | Critical | Provider policy gate, billing/config enforcement | Security/AI | Yes |
| Prompt injection via cells | Medium | High | Never prompt raw cells; structured aggregates only | AI | Yes |
| Function timeout/memory/bundle | Medium | Medium | Benchmark gate; alternative hosting/queue | Platform | No for demo, Yes production |
| Incomplete delete/orphan | Medium | High | State machine, idempotency, reconciler, audit | Backend/Platform | Yes |
| Secret leaked in logs/bundle | Low | Critical | secret scanning, redaction, server-only config | All | Yes |
| Provider/data residency mismatch | Medium | Critical | legal/security review and region controls | Legal/Security | Yes |
| Public demo resource abuse/cost | High | High | quotas, rate limit, CAPTCHA, circuit breaker, kill switch | Platform/Product | Yes |
| Sensitive aggregate label leakage | Medium | High | classification, masking/pseudonymization, regression tests | Data/AI | Yes |

## Open decisions

Auth/SSO, scanner, malware tooling, enterprise AI, residency, retention, incident tooling, and security owner
assignments are **Proposed**.
