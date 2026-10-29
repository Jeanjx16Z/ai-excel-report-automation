# Architecture

## 1. Prinsip Arsitektur

- Python 3.11 sebagai runtime.
- Pandas menjadi sumber kebenaran untuk cleaning, agregasi, dan seluruh perhitungan KPI.
- Gemini hanya menginterpretasikan ringkasan hasil analisis, bukan data mentah dan bukan kalkulator numerik.
- Pipeline dibagi menjadi fungsi kecil dengan kontrak input/output yang jelas agar mudah diuji serta dapat digunakan kembali oleh CLI, AI Agent, atau n8n.
- Kegagalan layanan eksternal tidak boleh menghilangkan laporan numerik deterministik.

## 2. Technology Stack

| Teknologi | Kegunaan |
|---|---|
| Python 3.11 | Runtime aplikasi |
| `pandas` | Cleaning, transformasi, agregasi, dan KPI |
| `openpyxl` | Membaca dan menulis file Excel `.xlsx` |
| `python-dotenv` | Memuat konfigurasi lokal dari environment tanpa hard-coded secret |
| `google-genai` | Client resmi untuk Gemini API |

### Dataset Demo

Dataset input demo berada di `data/raw/accounting_sample.xlsx` dan mempertahankan schema `date`, `department`, `category`, `budget`, dan `actual_cost`. Generator menggunakan seed tetap serta relasi department-category yang eksplisit untuk domain mining operational expenses. Nominal `budget` dan `actual_cost` menggunakan IDR.

Setiap baris adalah satu pos biaya/transaksi anggaran operasional sintetis. Data ini hanya untuk demonstrasi, tidak berasal dari perusahaan nyata, tidak mengandung informasi rahasia, dan tidak dimaksudkan sebagai benchmark faktual biaya pertambangan.

## 3. Aliran Data

```text
Excel (.xlsx)
    |
    v
Validation ---------> Validation error yang dapat ditindaklanjuti
    |
    v
Cleaning
    |
    v
Pandas KPI Engine
    |
    +----> Deterministic analysis result ----> Markdown/Excel Report
    |
    v
Structured summary (aggregates only)
    |
    v
Gemini Summary ------> Fallback summary/status jika API gagal
    |
    v
Markdown/Excel Report
```

Urutan pipeline utama: **Excel -> Validation -> Pandas KPI Engine -> Gemini Summary -> Markdown/Excel Report**. Cleaning dilakukan setelah validasi struktur dasar dan sebelum kalkulasi KPI.

## 4. Struktur Folder Usulan

```text
ai-excel-report-automation/
├── AGENTS.md
├── README.md
├── docs/
│   ├── PRD.md
│   └── ARCHITECTURE.md
├── data/
│   ├── input/
│   └── output/
├── src/
│   └── excel_report/
│       ├── __init__.py
│       ├── config.py
│       ├── models.py
│       ├── excel_io.py
│       ├── validation.py
│       ├── cleaning.py
│       ├── kpi.py
│       ├── summarizer.py
│       ├── reporting.py
│       └── pipeline.py
├── tests/
│   ├── fixtures/
│   ├── test_validation.py
│   ├── test_cleaning.py
│   ├── test_kpi.py
│   ├── test_summarizer.py
│   └── test_pipeline.py
├── .env.example
├── .gitignore
└── requirements.txt atau pyproject.toml
```

Struktur ini adalah target implementasi; file dan folder aplikasi belum dibuat pada tahap dokumentasi.

## 5. Tanggung Jawab Modul

- `config.py`: membaca konfigurasi dan nama environment variable tanpa mengekspos nilainya.
- `models.py`: mendefinisikan struktur hasil validasi, KPI, payload LLM, dan hasil pipeline (misalnya dengan dataclass/TypedDict sederhana).
- `excel_io.py`: membaca input dan menulis workbook laporan.
- `validation.py`: memeriksa file, sheet, kolom wajib, tipe/nilai, dan duplikasi.
- `cleaning.py`: menormalisasi tanggal, teks, serta nilai numerik sesuai aturan eksplisit.
- `kpi.py`: menghitung KPI global dan agregasi departemen/kategori secara deterministik.
- `summarizer.py`: membangun payload agregat, memanggil Gemini, dan menyediakan fallback.
- `reporting.py`: merender laporan Markdown dan Excel dari hasil analisis yang sama.
- `pipeline.py`: mengorkestrasi tahapan tanpa menyimpan business logic detail.

## 6. Pemisahan Numerical Engine dan LLM

`kpi.py` menghasilkan satu objek hasil analisis terstruktur, misalnya total, variance, percentage, dan daftar agregat over-budget. Objek ini menjadi sumber tunggal bagi seluruh output.

`summarizer.py` menerima versi terpilih dari objek tersebut yang hanya berisi agregat yang diperlukan. Prompt harus menyatakan bahwa angka adalah fakta tetap: Gemini boleh menjelaskan pola dan prioritas, tetapi tidak boleh menghitung ulang atau mengubah nilai. Respons LLM diperlakukan sebagai teks interpretatif, bukan sumber data KPI.

Manfaat pemisahan ini:

- hasil numerik reproducible dan mudah diuji;
- risiko hallucination tidak memengaruhi KPI;
- data mentah sensitif tidak dikirim ke provider LLM;
- pipeline numerik tetap berfungsi tanpa Gemini.

## 7. Kontrak Fungsi yang Disarankan

Nama dan tipe final ditentukan saat implementasi, dengan bentuk konseptual berikut:

```python
read_excel(path) -> DataFrame
validate_data(dataframe) -> ValidationResult
clean_data(dataframe) -> DataFrame
calculate_kpis(dataframe) -> AnalysisResult
build_summary_payload(analysis) -> SummaryPayload
generate_executive_summary(payload) -> SummaryResult
export_markdown(analysis, summary, output_path) -> Path
export_excel(analysis, summary, output_path) -> Path
run_pipeline(input_path, output_dir, include_ai_summary=True) -> PipelineResult
```

Karakteristik kontrak:

- menerima parameter eksplisit dan mengembalikan hasil terstruktur;
- business logic tidak bergantung pada `input()` atau state global;
- fungsi inti tidak melakukan network call, kecuali adapter Gemini;
- output serializable agar dapat dipakai sebagai JSON oleh AI Agent/n8n;
- error domain memiliki kategori stabil agar caller dapat menentukan retry atau menghentikan workflow;
- opsi `include_ai_summary` memungkinkan eksekusi deterministik tanpa API.

## 8. Error Handling

### Excel dan Data Invalid

- Periksa keberadaan file, ekstensi `.xlsx`, kemampuan membuka workbook, dan sheet yang dibutuhkan.
- Tolak input yang kehilangan kolom wajib dengan daftar kolom yang hilang.
- Laporkan baris/kolom bermasalah untuk tanggal atau angka invalid tanpa menampilkan data sensitif yang tidak diperlukan.
- Definisikan aturan eksplisit untuk nilai kosong, duplikasi, budget nol, dan nilai negatif; hindari silent correction.
- Jangan menulis laporan final seolah berhasil jika validation atau KPI engine gagal.
- Gunakan exception domain (misalnya `InputFileError`, `DataValidationError`, `ReportExportError`) yang dibungkus menjadi hasil/pesan yang ramah pengguna pada batas pipeline.

### Kegagalan Gemini API

- Validasi konfigurasi API sebelum request tanpa mencetak API key.
- Tangani authentication error, rate limit, timeout, response kosong/invalid, dan network error.
- Terapkan timeout dan retry terbatas hanya untuk error transient; jangan retry authentication atau payload invalid.
- Catat tipe kegagalan secara aman tanpa payload mentah atau credential.
- Kembalikan `SummaryResult` berstatus gagal/fallback dan tetap ekspor laporan numerik.
- Tests menggunakan mock/fake client; panggilan Gemini nyata hanya dijalankan dengan izin pengguna.

## 9. Kesiapan untuk AI Agent dan n8n

Fungsi pipeline dirancang sebagai API internal yang stateless dan composable. Kelak, wrapper tool atau endpoint dapat:

1. menerima path/file reference dan opsi terstruktur;
2. memanggil `run_pipeline` atau fungsi tahap tertentu;
3. mengembalikan status, KPI ringkas, lokasi output, dan error code dalam bentuk serializable;
4. membatasi akses file serta menjaga idempotency untuk retry workflow.

AI Agent atau n8n hanya menjadi lapisan orkestrasi. Keduanya tidak mengambil alih validation, cleaning, atau perhitungan KPI. Integrasi tersebut tidak termasuk implementasi MVP.
