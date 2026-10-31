# Phase 2 — Web Application Design

## Status

**Approved with implementation gates.** Folder ini adalah design baseline web application dan deployment untuk
melanjutkan core engine Phase 1. Approval awal mengizinkan implementasi dimulai dari Phase 2.1.
Status implementasi lokal tercatat di bawah dan pada [local vertical slice](LOCAL_VERTICAL_SLICE.md).
Durable database, provider-backed storage, production authentication, dan deployment belum tersedia.

## Approval note

- **Review date:** 2026-10-30
- **Status:** Approved with implementation gates
- **Implementation authorization:** Phase 2.1 only
- **Demo boundary:** synthetic data only
- **Real confidential data:** prohibited until production security gates pass
- **Production deployment:** not approved by this review
- **Proposed decisions:** remain milestone-specific blockers

Approval ini adalah persetujuan design baseline, bukan security approval untuk data nyata dan bukan production
release approval. Provider, quota, retention, cleanup executor, authentication, production AI, serta seluruh
keputusan berstatus **Proposed** harus diselesaikan sebelum milestone yang bergantung padanya dimulai.

Dokumen Phase 1 tetap menjadi historical source of truth untuk pipeline lokal:
[`../PRD.md`](../PRD.md) dan [`../ARCHITECTURE.md`](../ARCHITECTURE.md). Dokumen Phase 2
menambah application layer tanpa menggantikan kontrak KPI Phase 1.

## Urutan membaca

1. [`PRD_WEB_APP.md`](PRD_WEB_APP.md) — kebutuhan produk dan acceptance criteria.
2. [`TRD_WEB_APP.md`](TRD_WEB_APP.md) — keputusan teknologi dan quality attributes.
3. [`SYSTEM_ARCHITECTURE.md`](SYSTEM_ARCHITECTURE.md) — komponen, trust boundary, dan aliran data.
4. [`BACKEND_API_SPEC.md`](BACKEND_API_SPEC.md) — kontrak `/api/v1`.
5. [`DATA_MODEL.md`](DATA_MODEL.md) — model PostgreSQL dan ownership.
6. [`SECURITY_AND_PRIVACY.md`](SECURITY_AND_PRIVACY.md) — threat-informed controls.
7. [`DEPLOYMENT_AND_OPERATIONS.md`](DEPLOYMENT_AND_OPERATIONS.md) — environment dan operasi.
8. [`TEST_STRATEGY.md`](TEST_STRATEGY.md) — quality gates dan test matrix.
9. [`IMPLEMENTATION_ROADMAP.md`](IMPLEMENTATION_ROADMAP.md) — urutan implementasi.
10. [`DECISION_LOG.md`](DECISION_LOG.md) — status keputusan dan validation gate.

## Keputusan final untuk desain

- Next.js App Router + TypeScript menjadi frontend; FastAPI menjadi application/API layer.
- Python/Pandas core engine Phase 1 tetap satu-satunya numerical source of truth.
- LLM hanya menerima aggregate-only allowlisted payload dan tidak menghitung KPI.
- Demo hanya menerima data sintetis dan selalu menampilkan: **“Demo only — do not upload real
  confidential or personal company data.”**
- No-login demo bukan production security gate dan tidak boleh menerima data nyata.
- History memakai PostgreSQL untuk metadata dan private object storage untuk file; tidak ada public asset.
- Retention public anonymous demo direkomendasikan 7 hari; 30 hari hanya protected/internal demo. Keduanya
  masih Proposed, configurable, dan memiliki manual delete.
- V1 memproses synchronous setelah direct upload selesai; request tetap terbuka sampai report `completed` atau
  `failed`. `202 + polling` hanya future async mode dengan durable execution.
- Browser selalu memakai same-origin `/api/v1/...` pada frontend; Next.js rewrite/controlled proxy meneruskan
  ke FastAPI. URL backend project bukan browser API/session boundary.
- Minimum anonymous session ownership adalah prerequisite seluruh upload/report/history/download/delete API.
- `202 deleting` hanya berlaku bila durable cleanup executor tersedia; tanpa executor partial delete tetap
  `deleting` dan mengembalikan safe `503` untuk retry idempotent.
- Production wajib memiliki authentication, RBAC/ownership, retention enforcement, audit, dan AI provider
  enterprise yang disetujui.

## Hubungan Phase 1 dan Phase 2

FastAPI memanggil core engine melalui adapter tipis. Route handler tidak memuat business logic;
frontend, database, dan LLM tidak boleh menghitung atau mengoreksi KPI. Perubahan core harus tetap
kompatibel dengan fixture dan test Phase 1.

## Open decisions

| Decision | Rekomendasi awal | Status |
|---|---|---|
| PostgreSQL provider | Neon/serverless-compatible Postgres, region dekat backend | Proposed |
| Private object storage | Vercel Blob Private; evaluasi status Beta dan auth delivery | Proposed |
| PDF renderer | Server-side deterministic HTML-to-PDF, benchmark bundle/runtime | Proposed |
| Chart library | Recharts atau library accessible dengan bundle kecil | Proposed |
| Authentication provider | Auth.js/managed IdP; production mengikuti corporate policy | Proposed |
| Corporate SSO | OIDC/SAML provider perusahaan | Proposed |
| Public demo retention | 7 hari; protected/internal demo 30 hari | Proposed |
| Production retention | Kebijakan perusahaan dan legal review | Proposed |
| Data residency | Region yang disetujui perusahaan | Proposed |
| Maximum production file size | Ditentukan benchmark dan policy; demo 10 MB logical limit | Proposed |
| Future async trigger/executor | Queue/workflow hanya setelah benchmark membuktikan kebutuhan | Proposed |
| Backend hosting | Vercel Python Functions jika compatibility gate lulus; alternatif container host | Proposed |
| AI provider | Fake/offline local; controlled synthetic Gemini; Vertex/local kandidat production | Proposed |
| Monitoring provider | Vercel observability + approved error tracker | Proposed |
| Production domain | Domain perusahaan setelah security approval | Proposed |
| Public demo quotas/CAPTCHA | Rate/concurrency/storage/AI budgets setelah load-cost test | Proposed |
| Cleanup executor | Scheduled job/cron, durable workflow, atau approved worker | Proposed |

## Readiness checklist

- [x] Product requirements approved
- [x] Technical design approved
- [x] Security model approved
- [x] API contract approved
- [x] Data model approved
- [x] Deployment plan approved
- [x] Implementation may begin — Phase 2.1 only

## Review notes

- Blocker synchronous V1 dan direct upload protocol dari architecture review sudah dialamatkan.
- Provider-specific upload/download token, storage API, function benchmark, quota, dan cost control belum
  dibuktikan melalui proof of concept.
- Final human review menyetujui Phase 2.0 sebagai design baseline dengan implementation gates. Authorization
  hanya mencakup Phase 2.1; seluruh milestone berikutnya tetap tunduk pada dependency dan Proposed decision gate.

## Phase 2.1 implementation status

Phase 2.1 telah diimplementasikan dan diverifikasi secara lokal pada 2026-10-30:

- existing core lulus 37/37 tests pada Python 3.11.18 dan Python 3.12.16;
- package `excel_report` dapat di-install editable dan di-import tanpa application-level `sys.path` mutation;
- offline CLI dan semantic JSON/CSV/Markdown/Excel comparison mempertahankan KPI baseline;
- Next.js 16 App Router + strict TypeScript foundation lulus typecheck, lint, dan production build;
- CI menyediakan matrix Python 3.11/3.12 dan frontend checks tanpa deployment atau secret;
- Phase 2.1 tidak menambahkan API, database, storage, auth, session, provider integration, atau deployment.

Hasil gate ini tidak mengubah batas approval: data tetap synthetic-only, production deployment belum
disetujui, dan Phase 2.2 belum otomatis diotorisasi tanpa instruksi berikutnya.

## Phase 2.2 implementation status — 2026-10-31

Instruksi pengguna 2026-10-31 secara eksplisit mengotorisasi foundation Phase 2.2 dan session repository
in-memory lokal sambil menunggu provider PostgreSQL. Perubahan Phase 2.1 yang belum di-commit dipertahankan.

- Factory FastAPI, config tervalidasi tanpa dotenv, DI, safe errors, request ID, safe log fields, core adapter.
- Endpoint health dan bootstrap/current/rotate/revoke session saja; tidak ada upload/report/history/PDF API.
- Controlled Next.js same-origin proxy dengan service secret, fixed target, host/origin checks, header
  allowlist, cookie/CSRF/status/stream forwarding, dan no-redirect policy.
- Session token/CSRF hash-only, expiry/revocation, rotation/fixation guard, ownership isolation `404`.
- Local evidence: Phase 1 37/37 serta API 27/27 tests pada Python 3.11.18 dan 3.12.16; pip check isolated lulus.
  Proxy tests 7/7, typecheck/lint/build lulus. HTTP smoke localhost melalui Next.js health/session lulus.
- Browser verification belum dilakukan. GitHub CI belum dijalankan; workflow baru direview/disiapkan lokal.
- Durable session PostgreSQL, multi-instance/serverless safety, provider PoC, abuse controls, deployment
  validation, dan production security gates tetap belum selesai. `production` ditolak saat startup.

Gate lokal Phase 2.2 terverifikasi dengan keterbatasan di atas. Ini tidak mengotorisasi implementasi milestone
selanjutnya, real confidential data, atau deployment. Kontrak session tambahan ada pada
[`BACKEND_API_SPEC.md`](BACKEND_API_SPEC.md); command pada [`../../apps/api/README.md`](../../apps/api/README.md).

## Local vertical slice — hasil implementasi

Instruksi pengguna berikutnya mengotorisasi UX lokal Excel sintetis ke PDF. Endpoint intent/limited local
upload/complete/report/detail/download, UI Indonesia, template aman, dan PDF offline sudah diimplementasikan.
Browser Chrome lokal memverifikasi file 120 baris, KPI, PDF download, layout 390px, dan invalid workbook.
PDF dua halaman dirender/diperiksa visual: angka utuh, header tabel berulang, footer dan teks tidak terpotong.
Kontrak, command PowerShell, cleanup, serta batas lokal ada pada [`LOCAL_VERTICAL_SLICE.md`](LOCAL_VERTICAL_SLICE.md).
Approval ini tidak mengganti provider-backed architecture atau production/deployment gates.

## Hosted demo audit — 2026-10-31

Pengguna mengotorisasi persiapan/deployment synthetic-only serta checkpoint/push. Checkpoint `6d99798`
telah di-push; empat job GitHub CI run 1 selesai success. Protected Vercel runtime proof berhasil untuk fixture
120 baris, tetapi provider PostgreSQL/private storage, distributed controls, cleanup, dan aplikasi preview
belum tersedia. Pemasangan akun/integrasi Neon Free menunggu izin. Website publik belum dirilis.
Detail bukti, batas platform, dan gate: [HOSTED_DEMO_GATE.md](HOSTED_DEMO_GATE.md).

## Referensi resmi utama

- [Next.js App Router](https://nextjs.org/docs/app)
- [FastAPI deployment concepts](https://fastapi.tiangolo.com/deployment/)
- [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python)
- [Vercel Functions limits](https://vercel.com/docs/functions/limitations)
- [Vercel Blob private storage](https://vercel.com/docs/vercel-blob/private-storage)
- [Gemini API terms](https://ai.google.dev/gemini-api/terms)
- [Vertex AI generative AI documentation](https://cloud.google.com/vertex-ai/generative-ai/docs)
