# Hosted synthetic demo — audit dan release gate

Tanggal pemeriksaan: 2026-10-31. **Website demo online belum dirilis.** Dokumen ini membedakan hasil aktual
dari pekerjaan provider-backed yang masih diblokir keputusan akun. Tidak ada izin confidential production data.

## Checkpoint dan CI aktual

- Checkpoint `6d99798b29fac4d27bbf0fcc86c3c3543658fca6`: `feat: simpan fondasi web dan demo Excel ke PDF`.
- 59 file foundation/local slice terdahulu dan perbaikan audit disimpan; push `origin/main` berhasil.
- [GitHub CI run 1](https://github.com/Jeanjx16Z/ai-excel-report-automation/actions/runs/41209976063)
  benar-benar selesai **success**, event `push`, pada commit tersebut. Empat job: Frontend, Python 3.11,
  Python 3.12, Repository safety. Ini bukan bukti deployment atau provider integration.
- Audit/local commands, vulnerability, PDF, dan test evidence: [Local vertical slice](LOCAL_VERTICAL_SLICE.md).

## Akun dan provider

- Koneksi Vercel menggunakan paket Hobby. Scope `jeanjeasen-4849s-projects` sempat menolak akses `403`;
  authorization team kemudian berhasil. Proyek lain milik pengguna tidak diubah.
- Daftar integration configuration account setelah authorization kosong; belum ada PostgreSQL integration.
  Ini tidak membuktikan pengguna tidak mempunyai akun database eksternal.
- API Marketplace mengonfirmasi Neon `free_v3`: gratis, `paymentMethodRequired=false`, tanpa kartu kredit.
  Pemasangan dapat membuat akun/integrasi provider baru; **belum dilakukan, menunggu izin pengguna**.
- Usulan: Neon Free untuk database demo dan preview yang terisolasi; Vercel Blob Private untuk input/artifact,
  store dan secrets preview/demo terpisah. Provider belum dipilih final dan belum memiliki integration PoC.
- [Blob Hobby](https://vercel.com/docs/vercel-blob/usage-and-pricing) gratis dalam included allowance;
  akses dihentikan saat quota terlampaui. Tidak ada upgrade, trial berbayar, atau billing yang diaktifkan.
  Tidak ada database atau Blob store yang dibuat pada audit ini.

## Compatibility proof di Vercel — terbatas

Proyek baru khusus probe: `mining-excel-api-compatibility` (`prj_CmjmNl3SiRZt1xjMBJlS1ep5JMK2`).
Deployment `dpl_CH7HP2LYppDmEFoxRGiCCK5hHjdZ` berstatus `READY`, region `iad1`, framework FastAPI.
URL [probe terproteksi](https://mining-excel-api-compatibility-336gf51cm.vercel.app/compatibility) **bukan website
demo**. Vercel Authentication tetap aktif untuk semua deployment. Tidak menerima file, session, atau data user.

Probe hanya membaca salinan fixture sintetis tetap, memakai core existing, summary offline dan renderer PDF
terbaru; scratch PDF dihapus setelah request. Tidak memakai disk atau memory sebagai hosted persistence.
Source probe dan manifest verifikasi berada dalam `.runtime/` ignored; tidak menjadi entrypoint aplikasi.

| Pengukuran aktual | Hasil |
|---|---|
| Runtime | Python 3.12.15 di Vercel |
| Build | Berhasil; log menunjukkan build 11 detik |
| HTTP `/compatibility` melalui akses Vercel terproteksi | 200, tiga request |
| Waktu analisis + render per request | 0,3064 / 0,0822 / 0,0816 detik |
| Peak RSS proses yang dilaporkan OS | Maksimum 113.584 KiB pada tiga sample |
| PDF dengan font lokal embedded | 46.161 byte, ketiga request |
| Total budget / actual | Rp170.410.000.000 / Rp172.583.200.000 |
| Variance / persen | Rp2.173.200.000 / 1.28% |
| Transaksi / over / under / on | 120 / 60 / 60 / 0 |
| Summary source | offline; tidak memanggil Gemini |

Waktu di atas mengecualikan startup/import modul dan bukan p95/cold-start measurement. Peak RSS bukan batas
memori worst-case. Log cache upload 51,91 MB **bukan ukuran function bundle**; ukuran bundle final belum diukur.
Tidak membuktikan 10 MB/10.000 rows, concurrency, proxy, DB, storage, expiry, atau browser E2E di hosting.

**Catatan environment:** request create deployment meminta preview, tetapi metadata deployment pertama
dikembalikan sebagai `target=production`. Probe tetap protected dan tidak menjadi public release aplikasi.
Preview aktual harus diverifikasi eksplisit sebelum release; jangan menafsirkan probe ini sebagai gate preview
atau staged-production E2E yang sudah lulus. Belum ada promotion atau domain demo stabil.

## Batas platform yang diverifikasi

[Vercel Functions limits](https://vercel.com/docs/functions/limitations): body 4,5 MB; Hobby 300 detik dan 2 GB;
bundle Python standar 500 MB. [Python runtime](https://vercel.com/docs/functions/runtimes/python) mendukung
3.12/3.13/3.14. Karena itu local PUT 10 MiB tidak dapat langsung menjadi upload hosted.

[Hobby Cron](https://vercel.com/docs/cron-jobs/usage-and-pricing) minimum sekali sehari, dengan presisi per jam.
TTL akses satu jam tidak berarti object terhapus dalam satu jam jika executor hanya cron harian. Retention,
delete SLA, retry cadence, dan executor perlu dipilih bersama; jangan menjanjikan cleanup singkat tanpa executor.

## Pekerjaan sebelum preview aplikasi

1. Izin membuat integrasi/akun Neon Free, atau akses ke PostgreSQL existing melalui managed secrets.
2. PoC PostgreSQL dan private object store: put/get/head/delete, token scope, expiry, ownership, size limits,
   least-privilege credential, region, dan environment isolation. Tidak membaca `.env` existing.
3. Migration reproducible: sessions/hash, uploads, reports, idempotency, snapshots, artifacts, cleanup tasks,
   quotas/rate limits. Unique constraints dan atomic reservation/transaction menggantikan process-local lock.
   Migration belum diimplementasikan; app deploy tidak menjalankan destructive migration otomatis.
4. Provider adapters dan verified upload instruction/complete; `upload_id` opaque; no arbitrary URL/key.
   Hosted file/row limit ditentukan benchmark aktual; 10 MiB/10.000 rows belum boleh diiklankan untuk hosting.
5. Durable deleting → delete+verify → deleted; failed/expired/partial object reconciliation; executor nyata.
6. IP/session rate limit dengan trusted platform IP, persistent concurrency/upload/report/storage quota,
   kill switch upload/processing, no AI, same-origin proxy/cookie/CSRF dan cross-owner 404.
7. Preview frontend/backend terpasang eksplisit, terpisah dari released demo; deployed browser E2E seluruh
   download, invalid workbook, cross-owner, expiry/delete, log/secret checks. Baru kemudian staged release.

Kuota dan retention hosted **belum aktif/belum final**. Batas lokal 10 MiB, 10.000 rows, 50 upload/report,
dua processing per proses, dan TTL 3.600 detik bukan kontrol distribusi atau kapasitas hosted yang terbukti.

## Konfigurasi, operasi, dan rollback

Nama konfigurasi kandidat (bukan nilai): `DATABASE_URL`, `BLOB_STORE_ID`/provider secret bila diperlukan,
`API_ENV`, `API_FRONTEND_ORIGIN`, `API_BACKEND_ORIGIN`, `API_PROXY_SECRET`, retention/cleanup settings,
upload/processing kill switches dan quota settings. Nama final menunggu adapter. Tidak ada `NEXT_PUBLIC_*`
untuk secret. Preview/demo tidak berbagi credential atau data. `GEMINI_API_KEY` tidak diperlukan hosted offline.

Belum ada konfigurasi deployment aplikasi/migration yang dapat dijalankan sebagai release. Rollback aplikasi
kelak memilih immutable deployment yang sudah diuji, dengan schema backward-compatible, kemudian smoke
synthetic upload/download/ownership/cleanup. Jangan mempromosikan probe sebagai aplikasi.

## Panduan interview sementara dan batas berikutnya

Demo yang benar-benar siap dipakai saat ini adalah lokal: ikuti [dua terminal PowerShell](LOCAL_VERTICAL_SLICE.md),
unduh template atau gunakan fixture 120 baris, konfirmasi sintetis, buat laporan, periksa variance dan unduh
PDF/Excel/Markdown. KPI tetap Python/Pandas; ringkasan offline. Stop dengan `Ctrl+C`, cleanup mengikuti panduan.

Format hanya satu sheet dengan `date`, `department`, `category`, `budget`, `actual_cost` dan mapping pertambangan.
Multi-sheet, laba rugi, dan neraca adalah milestone berikutnya; belum tersedia. Warning/acknowledgement tidak
dapat membuktikan data sintetis. Real confidential/personal data tetap dilarang; production security approval
belum diberikan. `.env` existing tidak dibaca/diubah, tidak ada Gemini call atau billing activation.
