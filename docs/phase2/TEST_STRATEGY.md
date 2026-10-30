# Test Strategy — Phase 2

## Principles dan test data policy

- Testing pyramid: banyak unit, cukup integration/contract, sedikit critical browser E2E.
- Synthetic only; tidak ada real company data.
- Deterministic fixtures dan expected KPI manual.
- Unit/integration tidak melakukan network; DB/storage/AI memakai fake, emulator, atau isolated test resource.
- Real provider test hanya manual, controlled, opt-in, dan tidak memakai confidential data.
- Test tidak membaca developer `.env` atau mencetak secret.

## Pyramid dan matrix

| Layer | Scope | Contoh gate |
|---|---|---|
| Core unit | Existing validation, cleaning, KPI, renderer | Semua Phase 1 tests lulus 3.11/3.12 |
| FastAPI unit | Services, transitions, error mapping, ownership filters | No DB/network |
| API integration | upload intent/complete, sync report, OpenAPI contract | Isolated DB/storage fake |
| Repository | constraints, pagination, idempotency, migrations | Ephemeral PostgreSQL |
| Storage adapter | private put/get/delete, expiry, orphan behavior | Fake + provider sandbox |
| AI adapter | allowlist, structured response, timeout/fallback | Fake/mock only |
| Report consistency | Snapshot vs dashboard/MD/XLSX/PDF | Exact numeric fixture |
| Frontend component | warning, upload, error, status, tables | Accessible queries |
| Frontend integration | typed API, indeterminate request, status recovery, download/delete | Fake API |
| Browser E2E | critical journeys | Preview synthetic environment |
| Security/privacy | upload abuse, authz, secret/raw leakage | Required release gate |
| Performance | 10 MB/10k rows, concurrency, duration/memory | Target platform-like env |
| Deployment smoke | health, create, complete, download, delete | Preview/staged production |

## Critical end-to-end flows

1. Intent → direct private upload → complete → synchronous `201 completed` → dashboard/download.
2. Invalid schema/corrupt/encrypted/macro → actionable safe error.
3. Gemini timeout/server/invalid response → completed offline fallback.
4. KPI konsisten pada API, dashboard, Markdown, Excel, PDF.
5. History list/detail/download/delete dalam owner/session yang sama.
6. Expired/deleted file → `410`/safe behavior dan no storage access.
7. Production unauthorized/cross-owner access → deny/404 dan audit.
8. Captured request/log/report/bundle tidak memiliki secret/raw LLM payload.
9. Delete `completed|failed → deleting → deleted`, termasuk retry partial failure.

10. Same-origin frontend API meneruskan cookie/CSRF/`Set-Cookie`/request ID/status; direct backend browser call
    dan spoofed forwarding ditolak.
11. Direct storage upload memakai restrictive CORS tanpa session cookie atau permanent credential.

## Upload security tests

Extension spoof, MIME mismatch, corrupt ZIP, encrypted workbook, `.xlsm`, external links, formulas beginning
with dangerous prefixes, zip bomb simulation, excessive sheets/rows, oversized file, malformed XML, traversal
filename, Unicode filename, parser timeout, and concurrent uploads.

Workbook tests membedakan Current Phase 1 dari Proposed hardening: first worksheet/default name, additional
sheets ignored, exact required columns, formula cached/missing behavior, external-link non-inspection,
date/numeric rules, normalization, dan duplicate fail-fast. Encrypted/macro/external-link rejection menjadi
acceptance gate hanya setelah explicit Phase 2 implementation.

Direct-upload tests: expired intent, wrong owner, arbitrary URL/key, prefix mismatch, wrong size/type/checksum,
reused upload, token scope/TTL, serta bukti 10 MB tidak melewati API body.

## Failure tests

DB/storage unavailable, partial object write, AI timeout/429/5xx, renderer failure, function deadline,
duplicate idempotency key, delete partial failure, cleanup retry, stale state, expired session, and provider
response containing sensitive-looking text.

Idempotency contract tests mencakup: key/request sama saat in-progress menghasilkan `REPORT_IN_PROGRESS` tanpa
job kedua; completed dan failed me-replay original safe result/report ID; key sama dengan canonical payload
berbeda menghasilkan `IDEMPOTENCY_CONFLICT`; key baru setelah failure tetap tidak dapat memakai consumed
upload; expiry record configurable; frontend tidak otomatis membuat key baru. Failure tests memastikan
optional opaque same-owner `report_id` hanya muncul setelah job dibuat dan tidak ada raw/provider detail.

## Authorization tests (production gate)

Anonymous access disabled, invalid/expired token, role matrix, same-owner success, cross-owner deny, organization
boundary, download/delete authorization, admin audit, revoked user, session fixation/CSRF where applicable.
Demo session tests memverifikasi cookie flags, hash-only storage, no body/localStorage session, rotation, expiry,
cross-session `404`, dan inaccessible history setelah expiry.

Proxy/storage tests memverifikasi cookie terkirim melalui same-origin route, direct backend browser request
ditolak, `Set-Cookie` dan CSRF bertahan melalui rewrite, spoofed forwarding ditolak, storage CORS tidak menerima
origin arbitrer, serta session cookie tidak terkirim pada direct upload.

Deletion tests mencakup synchronous `200 deleted`, partial delete tetap `deleting`, repeated delete, unavailable
executor menghasilkan safe `503`, configured reconciler retry dan expired cleanup, object masih ada melarang
`deleted`, download saat `deleting` ditolak, serta cross-owner delete menjadi `404`.

## Performance tests

Capture p50/p95/p99 duration, peak memory, bundle, cold start, DB connections, storage throughput, PDF time,
AI latency/fallback, and concurrency. Sync v1 diterima hanya jika worst-case memiliki margin aman terhadap
documented function limits.

## Quality gates

| Milestone | Exit gate |
|---|---|
| 2.1 | Python 3.12 compatibility + core regression + CI green |
| 2.2 | Health/error/OpenAPI + minimum session/same-origin ownership contract |
| 2.3 | Test-only upload-to-MD/XLSX fake-AI E2E + security inputs |
| 2.4 | Provider migration/storage/history/delete/retention + release-readiness tests |
| 2.5 | PDF numeric/layout consistency |
| 2.6 | Accessible responsive frontend + browser critical flows |
| 2.7 | AI allowlist/fallback/privacy/provider controlled test |
| 2.8 | Authz/security regression and threat review |
| 2.9 | Preview smoke/E2E/performance and rollback rehearsal |
| 2.10 | All critical gates green; synthetic demo only |

## Coverage expectations

Coverage percentage bukan satu-satunya gate. Setiap state transition, error code, ownership path, output KPI,
external adapter failure, dan security invariant harus memiliki behavioral test.

Regression tambahan: monetary/percentage JSON decimal string/null; counts integer; frontend tidak menghitung KPI;
sensitive vendor/person/project labels dimasking sebelum unapproved AI; formula injection prefix `= + - @`;
unsafe Markdown/HTML, PDF external asset, permanent token/URL leakage, quota/circuit breaker/kill switches.

## Open decisions

Browser test runner, accessibility tooling, load tool, ephemeral PostgreSQL strategy, PDF visual comparison,
dan security scanner masih **Proposed**.
