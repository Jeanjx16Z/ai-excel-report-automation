# System Architecture — Phase 2

## Prinsip

Core Phase 1 dipertahankan; Next.js tidak menghitung KPI; FastAPI adalah orchestrator; PostgreSQL hanya
menyimpan state/snapshot; LLM hanya menginterpretasi aggregate allowlist. Semua external service berada di
balik adapter. Demo tanpa login hanya untuk synthetic data.

## Context diagram

```mermaid
flowchart LR
    U[Browser] -->|same-origin /api/v1 + first-party cookie| W[Next.js Web App]
    W -->|controlled rewrite/proxy| A[FastAPI Backend Project]
    A --> C[Python/Pandas Core]
    A --> D[(PostgreSQL)]
    A --> S[(Private Object Storage)]
    A --> L[AI Provider Adapter]
    L --> G[Gemini paid demo / Enterprise candidate]
    O[Operator] --> M[Observability]
    A --> M
    W --> M
```

## Container/component diagram

```mermaid
flowchart TB
    subgraph Browser[Untrusted browser]
      UI[Next.js UI]
    end
    subgraph Frontend[Vercel Frontend Project]
      NX[Next.js App Router]
    end
    subgraph Backend[Vercel Backend Project candidate]
      API[FastAPI Routes]
      APP[Application Services]
      CORE[Core Engine Adapter]
      RENDER[Report Renderers]
      ADAPTERS[DB / Storage / AI Adapters]
    end
    UI --> NX --> API
    API --> APP
    APP --> CORE --> KPI[Existing Pandas KPI Engine]
    APP --> RENDER
    APP --> ADAPTERS
    ADAPTERS --> DB[(PostgreSQL)]
    ADAPTERS --> OBJ[(Private Storage)]
    ADAPTERS --> AI[Approved AI Provider]
```

## Responsibilities

- **Next.js:** warning, upload UX, typed API calls, state display, dashboard, history, downloads.
- **Next.js proxy:** same-origin API boundary; meneruskan cookie/CSRF/request ID/status/error/streaming.
- **FastAPI routes:** input boundary, identity/session context, rate limit hook, response/error mapping.
- **Application services:** state transitions, orchestration, idempotency, retention/delete coordination.
- **Core adapter:** map stored input ke existing validation/KPI engine.
- **AI adapter:** allowlist aggregate, classify/mask sensitive labels, provider timeout, validation, fallback.
- **Report renderer:** Markdown/Excel/PDF dari immutable snapshot.
- **PostgreSQL:** job state, ownership, metadata, snapshot, audit; bukan calculator.
- **Private storage:** raw upload dan artifacts; tidak ada public URL.
- **Observability:** redacted logs, traces, metrics, alerts.
- **Session service:** menerbitkan high-entropy cookie token, menyimpan hash, rotasi/expiry, CSRF context.

## Trust boundaries

```mermaid
flowchart LR
    B[Browser: untrusted] -->|validated HTTPS| F[Frontend boundary]
    F -->|CORS + session/identity| A[API boundary]
    A -->|allowlisted aggregate only| P[External AI boundary]
    A -->|least privilege| X[Data services boundary]
    X --> DB[(PostgreSQL)]
    X --> ST[(Private Storage)]
```

Upload, spreadsheet text, filenames, MIME, headers, anonymous session, AI response, dan external service
errors semuanya dianggap untrusted.

Backend hanya menerima trusted frontend proxy origin/host dan tidak mempercayai spoofed forwarding headers.
Browser tidak memakai direct backend URL untuk session-bound API. Backend URL bukan authorization control.

## Upload-to-report sequence

```mermaid
sequenceDiagram
    actor User
    participant UI as Next.js
    participant API as FastAPI
    participant Store as Private Storage
    participant DB as PostgreSQL
    participant Core as Pandas Core
    participant AI as AI Adapter
    participant Render as Renderers
    User->>UI: Select synthetic .xlsx
    UI->>API: Same-origin POST upload intent via Next.js proxy
    API->>DB: upload_intent=pending + owner
    API-->>UI: upload_id + limited instruction
    UI->>Store: Direct private upload without session cookie
    UI->>API: Complete upload_id
    API->>Store: Verify bound object/size/type/checksum
    API->>DB: upload_intent=ready
    UI->>API: POST report(upload_id), request remains open
    API->>DB: report_job=validating
    API->>Core: validate + calculate KPI
    Core-->>API: immutable aggregate snapshot
    API->>DB: processing + snapshot
    API->>AI: allowlisted aggregate only
    AI-->>API: validated summary or fallback
    API->>DB: rendering_reports
    API->>Render: snapshot + summary
    Render->>Store: private md/xlsx/pdf
    API->>DB: completed + artifact metadata
    API-->>UI: 201 completed report or safe synchronous error
```

## Synchronous v1

Dataset kecil diproses dalam request yang tetap terbuka setelah verified `upload_id` berstatus `ready`. Sukses
mengembalikan `201 completed`; validation/business failure menyimpan `failed` dan mengembalikan safe error.
Frontend menampilkan indeterminate loading, bukan realtime intermediate state. Status endpoint hanya untuk
refresh/recovery dan future async compatibility. Jika benchmark mendekati function budget, future mode memakai
`202 + polling` **hanya** setelah durable queue/workflow tersedia; tidak boleh melanjutkan pekerjaan di luar
request tanpa durable executor.

## Report state machine

```mermaid
stateDiagram-v2
    [*] --> uploaded
    uploaded --> validating
    validating --> processing
    processing --> generating_summary
    generating_summary --> rendering_reports
    rendering_reports --> completed
    uploaded --> failed
    validating --> failed
    processing --> failed
    generating_summary --> rendering_reports: offline fallback
    generating_summary --> failed: unrecoverable internal error
    rendering_reports --> failed
    completed --> deleting: manual/expired/admin/policy
    failed --> deleting: manual/expired/admin/policy
    deleting --> deleting: retry partial cleanup
    deleting --> deleted: all objects verified deleted
    deleted --> [*]
```

`completed`/`failed` terminal untuk processing tetapi dapat masuk `deleting`; `deleted` terminal. Download
ditolak sejak `deleting`. Partial failure tetap `deleting`; expiration memakai flow yang sama. Repeated delete
idempotent. Reconciler hanya menjanjikan kelanjutan bila durable cleanup executor telah dikonfigurasi;
automatic expiration diblokir sebelum itu. Tombstone/audit retention berbeda dari file retention.

## Failure dan fallback

- Validation failure: `failed`, safe error code, input mengikuti retention/delete policy.
- AI timeout/provider error: offline summary, lanjut render, `completed`, record `summary_source=offline_fallback`.
- Renderer/storage/DB failure: `failed`; partial artifacts ditandai untuk cleanup.
- Error response tidak memuat stack, internal path, object key, prompt, raw values, atau credential.

## Download dan delete flow

Download memverifikasi owner/session, artifact state, format, expiry, lalu backend mengalirkan private object
atau memberi short-lived token scoped satu artifact; gunakan `Cache-Control: private, no-store`. Mekanisme final
streaming versus provider-authenticated delivery masih Proposed dan harus benchmark ukuran/response limit.
Delete merekam `deletion_reason`, masuk `deleting`, lalu mencoba menghapus dan memverifikasi seluruh object
dalam request. Sukses menghasilkan `200 deleted`. Incomplete cleanup menghasilkan `202 deleting` hanya dengan
durable cleanup executor; tanpa executor menghasilkan safe `503 deleting` dan repeated `DELETE` mencoba lagi.
Object yang masih ada melarang state `deleted`. Ini terpisah dari future async report-processing executor.

## Demo versus production

- Public demo: synthetic only, anonymous session, visible warning, Proposed retention 7 hari.
- Protected/internal demo: Proposed retention 30 hari.
- Production: auth/RBAC, enterprise AI, approved residency/DPA, audit, incident response, enforced retention.
- Anonymous session tidak pernah menjadi production authorization model.

## Anonymous session boundary

Server menghasilkan token high-entropy melalui cookie `HttpOnly`, `Secure`, `SameSite=Lax` atau lebih ketat,
bounded TTL. Database hanya menyimpan hash. Body tidak menerima `anonymous_session_id`; browser tidak memakai
`localStorage`. Server memvalidasi session sebelum ownership filter; cross-session menjadi `404`. Session
rotation/fixation prevention dan CSRF untuk mutating request wajib. Expiry memutus akses history.

Cookie adalah first-party pada frontend origin. Preview frontend rewrite harus menunjuk preview backend yang
sesuai; dua domain Vercel berbeda tidak diperlakukan sebagai same-site. Direct upload hanya membawa short-lived
scoped instruction. Storage CORS tidak menerima arbitrary origin/method/header dan tidak pernah menerima session
cookie atau permanent storage credential.

## Public demo abuse controls

Proposed: per-IP/per-session rate limit, active-job/stored-report/daily processing/concurrency/storage quotas,
short upload TTL, AI budget/circuit breaker, CAPTCHA/Turnstile, emergency upload/AI kill switches, dan optional
Deployment Protection preview. Angka final menunggu load/cost test.

## Deployment topology

```mermaid
flowchart LR
    GH[Git repository] --> VF[Vercel Project: frontend]
    GH --> VB[Vercel Project: backend]
    VF -->|HTTPS /api/v1| VB
    VB --> PG[(Serverless PostgreSQL)]
    VB --> BL[(Private Object Storage)]
    VB --> AP[AI Provider]
    VF --> OBS[Observability]
    VB --> OBS
```

Dua project dipilih untuk release boundary independen. Vercel Services hanya future option karena availability
harus diverifikasi. Backend hosting alternatif diperlukan bila Python runtime, upload flow, PDF dependency,
duration, atau bundle tidak memenuhi gate.

## Open decisions

Sync/queue threshold, backend host, database/storage region, PDF renderer, dan observability provider masih
**Proposed**.
