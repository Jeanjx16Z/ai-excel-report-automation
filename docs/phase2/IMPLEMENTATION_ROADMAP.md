# Implementation Roadmap — Phase 2

Roadmap ini tidak memberi estimasi hari/minggu. Complexity bersifat relatif dan implementation hanya dimulai
setelah Phase 2.0 disetujui.

## Phase 2.0 — Design approval

- **Goal:** menyepakati product, architecture, security, API, data, deployment, dan test contract.
- **Scope/components:** seluruh `docs/phase2/`; resolve open decisions dan decision log.
- **Dependencies:** reviewer product, engineering, security, data/legal/platform.
- **Acceptance criteria:** checklist readiness disetujui; contradiction dan blocker memiliki owner.
- **Tests/review:** link/Mermaid/consistency review; threat-model workshop.
- **Security checks:** no-login limitation dan production gates diterima eksplisit.
- **Exit criteria:** “Implementation may begin” dicentang oleh approver.
- **Risk:** keputusan platform prematur. **Complexity:** Medium.

## Phase 2.1 — Runtime and repository foundation

- **Goal:** membuktikan Python 3.12 dan menyiapkan monorepo tanpa merusak core.
- **Scope/files:** proposed `apps/web`, `apps/api`, `packages`/core packaging, commands, CI.
- **Dependencies:** Node/Next/Python versions dan dependency policy disetujui.
- **Acceptance criteria:** 3.12 gate lulus; dependency frontend/backend terpisah; local commands reproducible.
- **Tests:** Phase 1 suite, report fixtures, build/syntax/type/lint.
- **Security:** secret scan, lockfile review, no production credential.
- **Exit:** CI green pada clean checkout; KPI unchanged.
- **Risk:** packaging/import dan native dependency incompatibility. **Complexity:** High.

## Phase 2.2 — FastAPI dan minimum session foundation

**Local implementation evidence (2026-10-31):** health/session/proxy/core-adapter tests lulus lokal; session
in-memory diizinkan eksplisit pengguna untuk foundation single-process. PostgreSQL durability, browser E2E,
GitHub CI run dan deploy-build target belum dibuktikan. Milestone berikutnya tidak otomatis dimulai.

- **Goal:** API skeleton modular dengan ownership minimum sebelum endpoint data dibuat.
- **Scope/files:** app factory, `/api/v1`, config, error model, health, core adapter, same-origin Next.js
  rewrite/proxy, serta minimum anonymous session: high-entropy server token, `HttpOnly`/`Secure`/
  `SameSite=Lax` cookie, hash-only PostgreSQL storage, bounded TTL, server-side owner resolution,
  cross-session `404`, CSRF untuk mutating request, dan fixation prevention/rotation minimum.
- **Dependencies:** Phase 2.1, API spec approved.
- **Acceptance criteria:** health/error contract stabil; cookie first-party melalui same-origin `/api/v1`;
  ownership session dapat di-resolve dan tidak dapat dipalsukan. Tidak ada upload/report/history/download/delete
  endpoint yang release-ready sebelum gate ini lulus.
- **Tests:** unit error/config/service, API health/contract, cookie/proxy/CSRF/rotation/TTL/cross-session tests.
- **Security:** exact origin/host allowlist, spoofed forwarding rejection, safe errors/log redaction,
  server-only secrets.
- **Exit:** app imports/deploy-builds pada target candidate dan all tests green.
- **Risk:** serverless framework/runtime mismatch. **Complexity:** Medium.

## Phase 2.3 — Upload and report API prototype

**Penyesuaian lokal yang diotorisasi:** Local vertical slice memakai local private storage adapter untuk
membuktikan UX Excel-to-PDF. Provider-backed direct upload, durable database, history, dan deployment belum
selesai. Transport upload lokal melalui same-origin API body, bukan solusi 10 MB Vercel. Local PDF memakai
ReportLab; keputusan renderer/provider production tetap memiliki gate tersendiri. Lihat
[`LOCAL_VERTICAL_SLICE.md`](LOCAL_VERTICAL_SLICE.md).

- **Goal:** membuktikan synthetic Excel menjadi Markdown/Excel melalui API dengan fake AI.
- **Scope:** upload intent/complete, provider-neutral limited instruction, direct private upload, synchronous
  processing by `upload_id`, file inspection, orchestration, states, core adapter, storage abstraction.
- **Dependencies:** minimum session foundation Phase 2.2 dan direct-upload decision/prototype.
- **Acceptance criteria:** `201 completed` or safe error; UI indeterminate loading; AI failure completes fallback;
  synchronous report tidak memakai `202`; idempotency mencegah duplicate processing. Future async report baru
  boleh memakai `202` setelah durable report executor tersedia.
- **Tests:** integration E2E, corrupt/encrypted/macro/oversize/zip-bomb limits, consistency.
- **Security:** scoped upload TTL, ownership/object verification, quotas/kill switch, resource limits, raw file never to AI.
- **Exit:** target-size benchmark and failure cleanup lulus. Jika repository/storage masih fake/in-memory,
  milestone ini eksplisit **test-only dan belum deployable**; durable history, private provider upload, download,
  retention, dan cleanup belum dianggap selesai atau release-ready.
- **Risk:** provider token PoC, 4,5 MB request body, synchronous timeout. **Complexity:** High.

## Phase 2.4 — Provider-backed persistence, storage, and history

- **Goal:** durable report history dan private artifacts.
- **Scope:** PostgreSQL migrations/repositories, `upload_intents`, private storage, jobs, snapshots, retention,
  `deleting` workflow, reconciler, audit/system actor.
- **Dependencies:** provider/region choices, data model approval, dan minimum session foundation lulus.
- **Acceptance criteria:** ownership-scoped history/download; 7-day public and 30-day protected retention remain
  configurable Proposed; verified deletion before `deleted`.
- **Tests:** owner XOR, one input, idempotency, state checks, storage integration, partial delete/reconciliation.
- **Security:** private objects, random keys, no public URL, encryption, least privilege.
- **Exit:** provider PoC, restore/delete/cleanup rehearsal, dan cross-session isolation lulus. Upload/report/
  history/download/delete baru boleh dianggap release-ready setelah exit ini dan seluruh provider decision gate.
- **Risk:** partial delete dan serverless DB connection exhaustion. **Complexity:** High.

## Phase 2.5 — PDF report

- **Goal:** deterministic PDF yang konsisten dengan snapshot.
- **Scope:** renderer adapter, template/layout, fonts, storage artifact metadata.
- **Dependencies:** renderer choice, runtime/bundle benchmark.
- **Acceptance criteria:** PDF dapat dibuka, angka/metadata/disclaimer cocok, accessible text bila feasible.
- **Tests:** numeric/semantic extraction, visual fixtures, long content/page breaks.
- **Security:** no external assets, injection-safe templates, private artifact.
- **Exit:** consistency dan function resource gate lulus.
- **Risk:** native/browser dependency meningkatkan bundle/duration. **Complexity:** High.

## Phase 2.6 — Next.js frontend

- **Goal:** upload, status, dashboard, history, download/delete UX.
- **Scope:** App Router pages/components, typed client, warning, indeterminate synchronous loading, status
  recovery, charts, responsive/accessibility.
- **Dependencies:** stable API, chart decision, preview environment.
- **Acceptance criteria:** seluruh user journey demo selesai; warning selalu terlihat; no KPI calculation client-side.
- **Tests:** component, integration, accessibility, browser E2E, responsive.
- **Security:** output encoding dan CSRF; browser tidak menerima permanent storage credential atau memilih
  arbitrary object key. Short-lived scoped upload instruction boleh diterima dengan TTL, owner, method,
  content-type, dan size limit ketat.
- **Exit:** WCAG target checks dan critical E2E green.
- **Risk:** API/frontend schema drift dan misleading chart. **Complexity:** High.

## Phase 2.7 — AI integration hardening

- **Goal:** provider adapter yang privacy-aware dan resilient.
- **Scope:** fake/offline default, controlled synthetic Gemini, paid hosted-demo candidate, Vertex/local candidate,
  sensitive-label classification/masking, allowlist, AI budget/circuit breaker, timeout/fallback.
- **Dependencies:** provider/legal policy, aggregate schema.
- **Acceptance criteria:** captured payload aggregate-only; structured validation; provider failure completes fallback.
- **Tests:** fake 4xx/5xx/timeout/malformed, sensitive-label leakage, budget/kill switch, controlled synthetic test.
- **Security:** no unpaid confidential use, DPA/residency review, no complete prompt logs.
- **Exit:** privacy/security approval untuk demo configuration.
- **Risk:** provider policy drift dan hallucinated interpretation. **Complexity:** Medium.

## Phase 2.8 — Security hardening

- **Goal:** menutup production-boundary gaps dan mempersiapkan auth.
- **Scope:** production auth/RBAC readiness, advanced session hardening, rate limit, quota/CAPTCHA proposal,
  output sanitization, headers, secrets, audit, scanning, independent security review, abuse controls, dan
  incident runbook. Minimum anonymous cookie/ownership/CSRF/rotation sudah menjadi prerequisite Phase 2.2.
- **Dependencies:** auth/SSO/provider decisions dan threat model update.
- **Acceptance criteria:** demo boundary jelas; production mode fail-closed tanpa required controls.
- **Tests:** upload abuse, authz matrix, CSRF/session, secret scans, dependency/security regression.
- **Security:** independent review dan incident/rotation runbook.
- **Exit:** no production-blocking risk tanpa mitigation/owner.
- **Risk:** false sense of security pada anonymous demo. **Complexity:** High.

## Phase 2.9 — Vercel preview deployment

- **Goal:** membuktikan frontend/backend candidate topology dalam isolated preview.
- **Scope:** dua project, env configuration, preview DB/storage, health/logs, deployment checks.
- **Dependencies:** Vercel compatibility gates dan platform account approval.
- **Acceptance criteria:** preview build, smoke/E2E, resource benchmark, no production data/secrets.
- **Tests:** post-deploy health, upload/report/download/delete, failure fallback, rollback rehearsal.
- **Security:** environment isolation, protected preview if needed, least privilege, log review.
- **Exit:** documented deploy/promote/rollback dan observed limits acceptable.
- **Risk:** Beta Python/private storage behavior dan function limits. **Complexity:** High.

## Phase 2.10 — Demo release

- **Goal:** portfolio/interview demo yang repeatable dan aman.
- **Scope:** synthetic dataset, warning, demo documentation/script, observability, rollback verification.
- **Dependencies:** all earlier demo gates.
- **Acceptance criteria:** critical flows green, download formats consistent, fallback demonstrable, no real data.
- **Tests:** staged-production E2E/smoke, manual UX/security checklist.
- **Security:** synthetic-only enforcement, secret/log scan, delete/retention verified.
- **Exit:** release approval, support/rollback owner, known limitations published.
- **Risk:** user ignores warning atau external provider outage. **Complexity:** Medium.

## Future production phase

- **Goal:** izin memproses confidential company data.
- **Scope:** corporate SSO, RBAC, enterprise AI, DPA/residency, incident response, SLA/SLO, monitoring,
  approved retention/legal hold, penetration/security assessment.
- **Dependencies:** company governance dan vendor contracts.
- **Acceptance:** seluruh production gate pada PRD/security docs disetujui dan diuji.
- **Tests/security:** authorization isolation, DR, incident tabletop, load/soak, compliance evidence.
- **Exit:** written production approval; fail-closed configuration.
- **Risk:** regulatory/vendor/data governance mismatch. **Complexity:** High.

## Open decisions

Semua keputusan pada [`README.md`](README.md) harus memiliki decision record, owner, dan status berubah dari
`Proposed` menjadi `Approved` sebelum milestone yang bergantung padanya dimulai.
