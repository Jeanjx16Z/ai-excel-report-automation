# Decision Log — Phase 2

Status: `Approved`, `Proposed`, `Rejected`, atau `Superseded`. Approved berarti keputusan desain, bukan bukti
bahwa implementasi/deployment tersedia.

| ID | Topic | Status | Decision | Rationale | Consequences | Validation gate | Owner |
|---|---|---|---|---|---|---|---|
| D-001 | Frontend | Approved | Next.js App Router + TypeScript | Typed modern web UI | Node toolchain dan browser tests | Build/accessibility PoC | TBD |
| D-002 | API layer | Approved | FastAPI sebagai application/orchestration layer | Reuse Python ecosystem | Route tidak boleh memuat business logic | API contract tests | TBD |
| D-003 | Numerical engine | Approved | Existing Python/Pandas core adalah source of truth | Sudah deterministik/teruji | Semua output harus berasal dari snapshot | Phase 1 regression | TBD |
| D-004 | LLM role | Approved | Aggregate-only interpretation, bukan calculator | Cegah KPI hallucination/raw leakage | Allowlist, validation, fallback | Captured-payload tests | TBD |
| D-005 | Metadata store | Approved | PostgreSQL menyimpan state/metadata/history | Constraints dan audit relational | Provider/connection masih dipilih | Repository/migration PoC | TBD |
| D-006 | File storage | Approved | Private object storage | File tidak menjadi public asset | Auth delivery dan deletion wajib | Provider upload/download PoC | TBD |
| D-007 | Deployment topology | Approved | Dua Vercel projects dari satu repository | Release boundary frontend/backend | Compatibility belum terbukti | Preview deployment PoC | TBD |
| D-008 | Demo boundary | Approved | No-login demo hanya synthetic data | Portfolio tanpa production auth | Warning dan abuse controls wajib | Security review | TBD |
| D-009 | Real data gate | Approved | Auth/RBAC wajib sebelum company data | Ownership dan audit requirement | Production fail-closed | Authorization tests | TBD |
| D-010 | Python runtime | Approved | Python 3.12 hanya setelah compatibility gate | Phase 1 baseline 3.11 | Runtime tidak berubah sebelum tests | Full gate/benchmark | TBD |
| D-011 | External services | Approved | Semua provider di balik adapter/interface | Portability/testability | Provider-specific behavior isolated | Contract tests | TBD |
| D-012 | Processing V1 | Approved | Synchronous request after verified upload; `201 completed`/safe error | Contract konsisten tanpa orphan work | UI loading; states internal; async future only durable | Worst-case benchmark | TBD |
| D-013 | PostgreSQL provider | Proposed | Neon/serverless candidate | Vercel fit | Residency/pooling/cost unknown | Provider PoC | TBD |
| D-014 | Object storage provider | Proposed | Vercel Blob Private candidate | Platform integration | Token/private Beta fit unknown | Scoped upload/download PoC | TBD |
| D-015 | Public demo retention | Proposed | 7 days; protected/internal 30 days | Reduce abuse/cost | History expiry and cleanup | Product/security approval | TBD |
| D-016 | Public demo quota | Proposed | Per-IP/session/job/storage/AI limits + CAPTCHA | Abuse/cost control | UX friction | Load/cost test | TBD |
| D-017 | PDF renderer | Proposed | Deterministic server-side renderer | Consistent artifact | Bundle/runtime risk | PDF PoC | TBD |
| D-018 | Authentication | Proposed | Managed OIDC-compatible provider | Future production | Provider lock-in/cost | Corporate security review | TBD |
| D-019 | Async processing | Proposed | Queue/workflow only if benchmark requires | Avoid premature complexity | Requires durable executor | Sync benchmark | TBD |
| D-020 | Monitoring | Proposed | Vercel observability + approved tracker | Operational visibility | Data/log governance | Preview PoC | TBD |
| D-021 | Production AI | Proposed | Approved enterprise provider; Vertex/local candidates | DPA/residency/no-egress needs | Provider-specific integration | Legal/security review | TBD |
| D-022 | Download delivery | Proposed | Auth streaming or scoped short-lived delivery | Private artifacts | Function response limits | Size/bandwidth PoC | TBD |
| D-023 | Chart library | Proposed | Accessible small-bundle library | Dashboard usability | Bundle/accessibility trade-off | Frontend spike | TBD |
| D-024 | Production domain | Proposed | Company-approved domain | Trust/branding | DNS/security ownership | Platform approval | TBD |
| D-025 | Browser API routing | Approved | Session-bound browser request memakai same-origin `/api/v1` melalui controlled Next.js rewrite/proxy | Cookie tetap first-party dan boundary konsisten | Proxy wajib meneruskan cookie/CSRF/status/error/request ID dan backend menolak direct browser origin | Proxy/session contract tests | TBD |
| D-026 | Minimum anonymous session | Approved | Secure session ownership adalah prerequisite upload/report/history/download/delete | Cegah endpoint tanpa owner boundary | Memerlukan hash-only persistence, TTL, CSRF, rotation, cross-session 404 sejak Phase 2.2 | Session/security tests | TBD |
| D-027 | Idempotency replay | Approved | Owner+operation scoped key mereplay original safe completed/failed result; conflict/in-progress adalah stable 409 | Hindari duplicate processing dan retry ambigu | Record retention configurable; retry failure perlu key dan upload baru | Idempotency contract tests | TBD |
| D-028 | Cleanup executor | Proposed | Scheduled job/cron, durable workflow, atau approved worker | Deletion/expiration durable terpisah dari report processing | Automatic retention/public demo release diblokir sampai dipilih dan diuji | Partial-delete/reconciler rehearsal | TBD |
| D-029 | Phase 2.0 design approval | Approved | Phase 2.0 design baseline disetujui untuk memulai Phase 2.1 saja | Final human review menerima desain dengan implementation gates | Tidak mengizinkan confidential production data atau production release; semua Proposed decision tetap menjadi gate bagi milestone terkait | Final human documentation review completed | Human reviewer |

## Review rule

Perubahan keputusan harus menambah row baru atau mengubah status dengan rationale; jangan diam-diam mengubah
Approved contract. Provider/quota/retention/PDF/auth/queue/monitoring/production AI tetap Proposed sampai
validation gate dan owner menyetujui.
