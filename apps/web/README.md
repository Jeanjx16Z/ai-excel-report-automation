# Web foundation

Minimal Next.js App Router + TypeScript foundation untuk Phase 2.1. Halaman ini hanya menjelaskan status
foundation dan batas synthetic-only; Phase 2.2 menyediakan controlled server proxy `/api/v1/*`.
Local vertical slice kini menyediakan upload/template, hasil KPI/ringkasan offline, dan PDF/Markdown/Excel
download. Tidak ada production authentication, durable database/cloud storage, Gemini SDK, atau KPI logic
di browser. Panduan terbaru: [Local vertical slice](../../docs/phase2/LOCAL_VERTICAL_SLICE.md).

## Windows PowerShell

```powershell
Set-Location apps/web
npm ci
$env:PORT = '3000'
npm run dev:local
```

Quality checks:

```powershell
npm run typecheck
npm test
npm run lint
npm run build
```

Gunakan Node.js 22 sesuai `.nvmrc` repository. Jangan menaruh secret pada `NEXT_PUBLIC_*` atau client bundle.

`dev:local` menetapkan `--hostname localhost` di script, sedangkan `PORT` menentukan port tanpa forwarding
opsi npm. Sesudah build, gunakan `npm run start:local`. Untuk port lain, ubah `PORT` dan sesuaikan origin
kedua server. `PORT` tidak ditaruh dalam dotenv karena Next.js membutuhkannya saat server mulai.

`typecheck` menjalankan `next typegen` sebelum `tsc` agar fresh checkout dapat menghasilkan `.next/types`.
Folder `.next` dan `node_modules` adalah generated artifacts yang diabaikan Git; tidak perlu dihapus setelah
development karena VS Code memakai generated types. Konfigurasi server proxy dan smoke localhost mengikuti
[backend guide](../api/README.md). Test proxy memakai fake fetch tanpa network.
