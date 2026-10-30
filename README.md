# ai-excel-report-automation

Otomatisasi laporan biaya operasional pertambangan berbasis Excel menggunakan Python dan Gemini. KPI dihitung secara deterministik; Gemini hanya menjadi lapisan interpretasi opsional untuk management report.

## Prasyarat

- Python 3.11
- `pip`
- Anaconda atau Miniconda (direkomendasikan untuk environment terisolasi)

## Setup dengan Conda

Buat environment dari konfigurasi repository:

```powershell
conda env create -f environment.yml
conda activate ai-excel-automation
```

Jika environment sudah dibuat, sinkronkan dependency dengan:

```powershell
conda run -n ai-excel-automation python -m pip install -r requirements.txt
```

Verifikasi interpreter dan SDK Gemini:

```powershell
python --version
python -c "from google import genai; print('google-genai import OK')"
```

### Memilih Interpreter di VS Code

1. Tekan `Ctrl+Shift+P`.
2. Pilih **Python: Select Interpreter**.
3. Pilih interpreter Conda `ai-excel-automation` dengan Python 3.11.
4. Buka terminal baru dan jalankan `python --version` untuk memastikan environment aktif.

Jika interpreter tidak muncul, pilih **Enter interpreter path** dan arahkan ke:

```text
C:\Users\<username>\anaconda3\envs\ai-excel-automation\python.exe
```

## Setup

Jalankan perintah berikut dari root repository pada PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Salin konfigurasi contoh jika diperlukan pada milestone berikutnya:

```powershell
Copy-Item .env.example .env
```

Jangan masukkan API key asli ke `.env.example` atau source control.

Untuk mode Gemini, isi `.env` lokal sebagai berikut:

```dotenv
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Mode offline tidak membutuhkan API key.

## Generate Dataset Sintetis

```powershell
python src/generate_sample_data.py
```

Perintah tersebut membuat `data/raw/accounting_sample.xlsx` dengan seed tetap dan minimal 120 transaksi sintetis. Dataset berisi kolom:

- `date`
- `department`
- `category`
- `budget`
- `actual_cost`

Departemen demo mencakup Mining Operations, Heavy Equipment, Logistics, HSE, dan Site Infrastructure. Kategori biaya dipasangkan secara realistis dengan departemennya, misalnya Diesel Fuel, Equipment Maintenance, Hauling Transportation, Safety Equipment, Road Maintenance, Spare Parts, Site Utilities, dan Equipment Rental.

Nilai `budget` dan `actual_cost` menggunakan nominal IDR. Setiap baris merepresentasikan satu pos biaya/transaksi anggaran operasional pertambangan. Seluruh angka dan transaksi dibuat secara sintetis untuk demonstrasi; dataset ini bukan data nyata, bukan informasi rahasia, dan tidak merepresentasikan perusahaan tertentu.

File dataset sintetis sengaja tidak diabaikan oleh Git agar dapat digunakan untuk demo.

## Menjalankan Pipeline Analisis

Jalankan pipeline menggunakan input dan output default:

```powershell
python src/analyze_costs.py
```

Path dapat ditentukan secara eksplisit:

```powershell
python src/analyze_costs.py --input data/raw/accounting_sample.xlsx --output-dir data/processed
```

Pipeline melakukan validasi fail-fast, menghitung KPI dengan konvensi `variance = actual_cost - budget`, lalu membuat:

- `data/processed/analysis_summary.json`: metadata, KPI total, dan agregasi terstruktur untuk milestone Gemini berikutnya;
- `data/processed/department_summary.csv`: agregasi per departemen;
- `data/processed/category_summary.csv`: agregasi per kategori.

Validasi menolak file yang hilang/rusak, ekstensi selain `.xlsx`, schema atau nilai
invalid, nilai negatif, kombinasi department-category yang tidak dikenal, dan transaksi
duplikat. Tahap cleaning menormalisasi tanggal serta memangkas whitespace awal/akhir pada
teks tanpa mengubah input asli.

`variance_pct` dihitung dengan rumus `variance / budget * 100`. Variance positif berarti over-budget, variance negatif berarti under-budget, dan variance nol berarti on-budget. Jika budget nol, `variance_pct` bernilai null/kosong karena persentase tidak terdefinisi. JSON tidak memuat transaksi mentah.

## Membuat Management Report

Mode default adalah offline dan tidak melakukan network call:

```powershell
python src/analyze_costs.py
```

Mode Gemini harus dipilih secara eksplisit:

```powershell
python src/analyze_costs.py --mode gemini
```

Laporan dibuat di:

- `reports/management_report.md`: management report yang mudah dibaca;
- `reports/management_report.xlsx`: workbook dengan sheet KPI, agregasi departemen,
  agregasi kategori, dan executive summary. Nilai KPI pada workbook disimpan sebagai
  angka agar dapat diproses kembali.

Path keduanya dapat ditentukan secara eksplisit:

```powershell
python src/analyze_costs.py --report-path reports/custom_report.md --excel-report-path reports/custom_report.xlsx
```

Jika Gemini gagal atau konfigurasi API tidak tersedia, pipeline tetap membuat kedua
laporan menggunakan template offline dan menandainya sebagai fallback, bukan sebagai
output AI.

Gemini hanya menerima isi agregat `data/processed/analysis_summary.json`, bukan transaksi mentah. Structured output dibatasi pada executive summary, maksimal tiga findings, maksimal tiga potential risks, dan maksimal tiga recommendations. Prompt melarang model mengarang nominal, penyebab pembengkakan, atau fakta operasional. Semua angka KPI pada laporan selalu dirender langsung dari hasil Python; interpretasi AI tidak boleh mengubahnya. Data tetap dinyatakan sintetis dan bukan data asli perusahaan.

## Menjalankan Tests

```powershell
python -m unittest discover -s tests -v
```

Test suite menggunakan dataset sintetis dan temporary directory. Jalur Gemini diuji
dengan fake/mock client sehingga automated tests tidak melakukan network call. Verifikasi
Milestone 4 terakhir menghasilkan 37 test lulus.

## Pemeriksaan Sintaks

```powershell
python -m compileall -q src tests
```

## Batasan MVP

MVP mencakup input Excel `.xlsx`, validasi dan cleaning terkontrol, KPI deterministik,
output JSON/CSV, laporan Markdown dan Excel, serta interpretasi Gemini opsional dengan
structured output dan fallback. Python/Pandas tetap menjadi satu-satunya sumber kebenaran
angka; Gemini hanya menerima agregat dan tidak menerima transaksi mentah.

AI Agent, tool calling, n8n, PDF, web interface, FastAPI, Next.js, authentication,
database, Docker, dan deployment belum termasuk dalam MVP.
