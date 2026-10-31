# Local vertical slice — Excel sintetis ke PDF

Status: implementasi lokal single-process. Data dummy/sintetis saja. Bukan production-ready dan bukan
solusi deployment Vercel. Seluruh perubahan Phase 2.1/2.2 dan CLI/core Phase 1 dipertahankan.

## Penyesuaian roadmap yang diotorisasi pengguna

Local vertical slice memakai local private storage adapter untuk membuktikan UX Excel-to-PDF.
Provider-backed direct upload, durable database, history, dan deployment belum selesai.

Browser tetap memakai relative same-origin Next.js `/api/v1`; target FastAPI dan service secret hanya berada
di server. Production mode menolak in-memory/local storage. Tidak ada panggilan Gemini/provider AI.

## Menjalankan sekarang — Windows PowerShell

Dari root repository:

```powershell
conda run -n ai-excel-automation-py312 python -s -m pip install -e . -e 'apps/api[test]'
```

Terminal 1, dari root repository. Nilai secret berikut adalah **fake, khusus localhost** dan harus sama pada
dua terminal; jangan gunakan pada shared/public environment:

```powershell
$env:API_ENV = 'development'
$env:API_PROXY_SECRET = 'fake-local-development-proxy-value-00000000'
$env:API_FRONTEND_ORIGIN = 'http://localhost:3000'
$env:API_COOKIE_SECURE = 'false'
conda run --no-capture-output -n ai-excel-automation-py312 python -s -m uvicorn mining_api.app:create_app --factory --host 127.0.0.1 --port 8000 --no-proxy-headers --no-access-log
```

Terminal 2, dari root repository:

```powershell
$env:API_BACKEND_ORIGIN = 'http://127.0.0.1:8000'
$env:API_FRONTEND_ORIGIN = 'http://localhost:3000'
$env:API_PROXY_SECRET = 'fake-local-development-proxy-value-00000000'
$env:API_PROXY_LOCAL_HTTP = 'true'
$env:NEXT_TELEMETRY_DISABLED = '1'
Set-Location apps/web
npm ci
$env:PORT = '3000'
npm run dev:local
```

Buka `http://localhost:3000`. Unduh Template Sintetis atau pilih `data/raw/accounting_sample.xlsx`, centang
konfirmasi data dummy, klik **Buat Laporan**, lalu **Unduh PDF**. Markdown/Excel juga tersedia. **Proses File
Lain** memulai tindakan baru; tidak ada history UI. Hentikan masing-masing server dengan `Ctrl+C`.
Backend tidak membaca dotenv; tidak perlu mengubah `.env` existing.

Script `dev:local` menyimpan opsi hostname di `package.json`; port memakai environment `PORT`, menghindari
masalah forwarding opsi npm di PowerShell. Setelah `npm run build`, `npm run start:local` memakai origin
yang sama. Untuk port berbeda, ubah `PORT` dan sesuaikan origin kedua server. Jangan menaruh `PORT` di dotenv.

## Kontrak lokal

| Operasi | Endpoint |
|---|---|
| Bootstrap baru jika CSRF client tidak tersedia | `POST /api/v1/session/reset`, `{ "reset_ack": true }` |
| Template aman | `GET /api/v1/template` |
| Intent | `POST /api/v1/uploads/intents` |
| Local limited transport | `PUT /api/v1/uploads/{upload_id}/content` |
| Completion | `POST /api/v1/uploads/{upload_id}/complete`, `{}` |
| Synchronous report | `POST /api/v1/reports`, `upload_id`, `summary_mode=offline`, `Idempotency-Key` |
| Detail | `GET /api/v1/reports/{report_id}` |
| Download | `GET /api/v1/reports/{report_id}/download/{pdf|markdown|excel}` |

Reset session adalah tambahan kontrak eksplisit: exact Origin + JSON + service proxy wajib. Ia membuat owner
baru dan mencabut token sebelumnya; tidak memigrasikan atau memberikan akses owner lama. Client hanya
menyimpan CSRF di memory. Refresh halaman dapat kehilangan CSRF; bootstrap/reset berikutnya kehilangan akses
laporan owner sebelumnya. Rotation existing tetap memerlukan CSRF dan mempertahankan owner.

Limited instruction berisi target relatif, method PUT, dan header `X-Upload-Capability` acak 32 byte. Capability
disimpan sebagai hash, sekali pakai, TTL 120 detik, terikat session/owner dan expected size. Upload intent TTL
300 detik. Seluruh mutation tetap memerlukan CSRF/Origin/proxy. Transport biner **melewati body Next.js dan
FastAPI secara lokal**, maksimum 10 MiB. Ini **bukan solusi upload 10 MB pada Vercel**; provider-neutral
instruction kelak diganti adapter direct storage setelah provider PoC, tanpa mengganti report contract.

Report memakai upload `ready` satu kali dan mempertahankan request hingga `201 completed` atau safe error.
Key sama/request sama me-replay result original; duplicate in-progress `409 REPORT_IN_PROGRESS`, payload
berbeda `409 IDEMPOTENCY_CONFLICT`. Failure setelah job dibuat memiliki opaque same-owner report_id, tanpa
path/raw value/exception. Retry baru perlu upload baru + key baru. Frontend **Periksa Hasil** memakai key lama
untuk hasil yang belum pasti; tidak ada retry otomatis dengan key baru. Source selalu `offline`.

API monetary/percentage memakai decimal string atau null dan display_value server; counts integer.
PDF, Markdown, Excel, dan halaman hasil berasal dari snapshot KPI yang sama. Frontend tidak menghitung KPI.

## Batas input dan resource yang benar-benar diterapkan

- `.xlsx`, satu sheet, lima kolom persis `date`, `department`, `category`, `budget`, `actual_cost`.
- Maksimum 10 MiB compressed, 10.000 data rows, lima kolom, 128 ZIP members, 40 MiB total uncompressed,
  20 MiB per member, dan compression ratio maksimum 200. Dimensi/cell references diperiksa sebelum reader.
- Reject OLE/encrypted ZIP, proteksi aktif, macro content, external relationships/data connections,
  formula cells, embedded objects/ActiveX, DTD/entity, duplicate ZIP members, dan path traversal ZIP.
  XML package lokal harus UTF-8. Elemen protection kosong bawaan openpyxl tidak dianggap proteksi aktif.
- Date, schema, nominal non-negatif, department/category mapping, cleaning dan duplicate memakai core existing.
- Maksimum 50 upload/50 report aktif per proses dan dua operasi validasi serta dua processing secara bersamaan.
- Parser berjalan sinkron dalam thread server. **Tidak ada hard parser timeout atau process sandbox.**
  Timeout proxy/client hanya membatasi waktu tunggu HTTP, tidak membunuh pekerjaan Python.
- File name hanya divalidasi extension/panjang dan tidak disimpan sebagai object key/path/report metadata.
  Local object key acak server, tidak pernah ditampilkan atau dilayani sebagai static/public asset.

## Runtime storage dan cleanup

Private files: `.runtime/private/<random-run-id>/`; `.runtime/` seluruhnya di-ignore Git. Hanya service yang
memiliki object key. User read/download dicek owner dan session; cleanup memakai internal lifecycle policy.

- Partial/invalid upload dihapus saat gagal. Input consumed dihapus setelah report sukses maupun gagal.
- Artifact parsial dibersihkan saat report gagal. Jika delete gagal, key tercatat pada pending cleanup dan
  dicoba lagi pada aktivitas cleanup berikutnya; tidak ada janji background executor.
- Report/artifact dan idempotency default TTL 3600 detik, configurable `API_REPORT_TTL_SECONDS` 300–3600.
  Expiry diverifikasi saat akses. Cleanup opportunistik berjalan saat intent/report baru, bukan scheduler.
- Saat startup, adapter menghapus direktori run terdahulu yang berumur lebih dari satu jam. File dari run
  muda tetap ada sampai startup berikutnya atau manual cleanup; metadata/session tidak dapat dipulihkan.
- Setelah server dihentikan, hapus seluruh file demo lokal secara manual dari root repository:

```powershell
Remove-Item -LiteralPath '.runtime/private' -Recurse -Force
```

Perintah tersebut menghapus input/artifact demo lokal dan tidak dapat di-undo melalui aplikasi. Jangan
menjalankannya saat server masih aktif. `.runtime/verification` menyimpan bukti smoke/browser/PDF yang juga
ignored. Local storage belum menyediakan encryption-at-rest, disk-wide quota, durable retention, atau backup.

## Renderer dan verification

ReportLab `5.1.0` dipilih untuk local PDF dengan A4, Paragraph escaped, LongTable/repeated headers, page breaks,
footer halaman, dan font Bitstream Vera bawaan ReportLab yang di-embed tanpa font/image fetch. PDF metadata memakai judul/author demo tetap,
tanpa filename/path user. Decimal display memakai formatter server yang sama; renderer tidak menghitung KPI.
Teks rata kiri, nominal/count rata kanan, heading berbahasa Indonesia, dan lebar tabel berada dalam frame A4.
Font sesuai label demo Latin; multilingual fonts dan platform performance belum digate.

Dependency test `pypdf==6.21.4` memverifikasi PDF/text/KPI. Alat lokal opsional pypdfium2 `5.14.0` merender PDF
menjadi PNG untuk inspeksi visual; Playwright Core `1.64.1` dipasang hanya di `.runtime/browser` untuk Chrome
lokal. Keduanya bukan dependency runtime aplikasi. Tidak ada browser SDK pada frontend bundle.

```powershell
conda run -n ai-excel-automation-py312 python -s -m compileall -q src tests apps/api
conda run -n ai-excel-automation-py312 python -s -m unittest discover -s tests -v
conda run -n ai-excel-automation-py312 python -s -m unittest discover -s apps/api/tests -p 'test_*.py' -v
Set-Location apps/web
npm test
npm run typecheck
npm run lint
npm run build
Set-Location ../..
conda run -n ai-excel-automation-py312 python -s apps/api/tests/smoke_local.py
```

Untuk browser opt-in pada Windows yang sudah memiliki Chrome/Edge:

```powershell
npm install --prefix .runtime/browser --no-save --package-lock=false --ignore-scripts playwright-core@1.64.1
conda run -n ai-excel-automation-py312 python -s apps/api/tests/smoke_local.py --browser
```

Smoke memulai/menghentikan kedua server sendiri. Unit/API/proxy tests memakai in-process transport/fake fetch
tanpa external provider call. Checkpoint `6d99798` sudah di-push; keempat job
[GitHub CI run 1](https://github.com/Jeanjx16Z/ai-excel-report-automation/actions/runs/41209976063) selesai success.

Hasil lokal: Python 3.11.18 dan 3.12.16 masing-masing lulus 37 regression Phase 1 dan 45 API tests;
compile serta isolated pip check lulus. Frontend 8 proxy tests, typecheck, lint, dan production build lulus.
HTTP smoke serta Chrome browser verification lulus pada Next start dan Next dev: template, baseline 120 baris,
KPI, PDF download, tampilan 390px, dan penolakan workbook invalid. Uncaught JavaScript error 0; satu console
422 adalah hasil uji invalid workbook yang disengaja. PDF baseline dua halaman lolos ekstraksi KPI dan visual
review, termasuk repeated table header dan nomor halaman. Full tests tidak menjalankan browser/provider call.

`next dev` versi terpasang otomatis menambahkan `apps/web/AGENTS.md` berisi petunjuk framework; file root
`AGENTS.md` tidak diubah. Generated `.next`, `node_modules`, dan artifact verification tetap tersedia lokal
serta di-ignore Git.

## Gate menuju deployment

Provider-backed direct upload/download, durable session/report persistence, approved retention/cleanup
executor, production auth/RBAC, disk/storage quotas, malware/sandbox review, load/resource benchmarks, PDF
runtime/font checks, observability, serta production security/deployment approval masih belum selesai.
Tidak ada PostgreSQL/cloud storage/auth provider/RAG, history UI, atau integrasi Gemini baru pada slice ini.

## Audit checkpoint menuju hosted demo — 2026-10-31

- `.gitignore` generic `lib/` sempat menyembunyikan modul `apps/web/lib`; exception spesifik memastikan proxy,
  declaration TypeScript, dan tipe report ikut checkpoint. `.env`, `.runtime`, dependency/cache tetap ignored.
- PowerShell menyelesaikan `npm` ke `npm.ps1`. Penyebab forwarding opsi pada terminal pengguna belum dapat
  direproduksi secara pasti. Command terdokumentasi kini tidak memerlukan forwarding: `PORT` + `dev:local`
  atau `start:local`. Keduanya diuji melalui PowerShell dan browser dengan port terpisah dari server pengguna.
- Smoke opt-in `--npm-local` menjalankan script PowerShell pada port sementara; contoh:
  `python -s apps/api/tests/smoke_local.py --npm-local --browser`. Jangan jalankan dua `next dev` pada direktori
  yang sama; Next mempunyai development lock. Verifikasi development audit memakai salinan temporary terisolasi
  agar server pengguna tetap berjalan. Tidak ada perubahan pada dataset atau numerical core.
- Smoke kini memeriksa heading terbaru dan embedded font pada PDF unduhan, bukan hanya signature PDF.
  Pemeriksaan awal yang sempat mengenai server lama di port 3000 tidak dihitung sebagai bukti renderer terbaru.
- Renderer sebelumnya menggunakan Type1 Helvetica tanpa embedding dan angka rata kiri. Penyebab spacing pada
  viewer pengguna belum dapat dipastikan; mitigasi sekarang memakai embedded Vera dan alignment eksplisit.
  PDF hasil pipeline dua halaman telah dirender dan diperiksa visual; nominal/header/footer utuh.
- `npm audit --json` mengonfirmasi **16 moderate**, semuanya pada dependency development ESLint. Akar advisory:
  [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249), `minimatch <11.0.1`.
  Path mencakup ESLint/config-array/eslintrc dan eslint-config-next → React/import/a11y/typescript-eslint.
  Lockfile saat audit memakai minimatch 3.1.5 dan 10.2.6. Ini satu advisory yang merambat ke 16 package entries.
  `npm audit --omit=dev --json` menghasilkan **0 vulnerability runtime** saat audit.
- Tidak ada compatible in-range fix pada dependency path terpasang: ESLint 9 terbaru saat audit tetap 9.39.5;
  eslint-config-next 16.4.3 masih memakai plugin dengan minimatch major lama. Saran npm menurunkan major
  ESLint/config-next; tidak diterapkan. Tidak memakai force fix atau override lintas major yang belum kompatibel.
  Risiko tooling belum ditutup: jalankan lint hanya atas repository tepercaya, jangan menerima glob dari upload.
- Syntax, full regression/API tests di dua Python, pip check, proxy tests, typecheck/lint/build lulus.
  Browser mencakup template, 120 transaksi, KPI baseline, PDF, mobile 390px, dan invalid workbook; uncaught error 0.
  File credential existing tidak dibaca; scan candidate Git menampilkan lokasi saja bila ada potensi secret.

Audit lokal ini bukan hosted proof of concept atau production security approval. Deployment tetap memerlukan
akses akun, durable database/private object provider, cleanup executor, kuota, serta preview E2E.
