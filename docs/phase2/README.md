# Phase 2 — Web Application Design

## Status

**Approved with implementation gates.** Folder ini adalah design baseline web application dan deployment untuk
melanjutkan core engine Phase 1. Approval hanya mengizinkan implementasi dimulai dari Phase 2.1. Tidak ada
frontend, API, database, storage, PDF, authentication, atau deployment yang telah diimplementasikan.

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

## Referensi resmi utama

- [Next.js App Router](https://nextjs.org/docs/app)
- [FastAPI deployment concepts](https://fastapi.tiangolo.com/deployment/)
- [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python)
- [Vercel Functions limits](https://vercel.com/docs/functions/limitations)
- [Vercel Blob private storage](https://vercel.com/docs/vercel-blob/private-storage)
- [Gemini API terms](https://ai.google.dev/gemini-api/terms)
- [Vertex AI generative AI documentation](https://cloud.google.com/vertex-ai/generative-ai/docs)
