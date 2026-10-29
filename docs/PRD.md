# Product Requirements Document (PRD)

## 1. Ringkasan

**Project A: ai-excel-report-automation** mengotomatisasi analisis dan pembuatan laporan biaya operasional pertambangan dari file Excel. Sistem membaca data biaya, memvalidasi dan membersihkannya, menghitung KPI secara deterministik, lalu menggunakan Gemini API untuk menyusun executive summary berdasarkan ringkasan analisis yang terstruktur.

Proyek ini ditujukan sebagai portfolio AI Engineer dan bahan demonstrasi pada user interview Staff AI.

## 2. Tujuan

- Mengurangi pekerjaan manual dalam menyusun laporan budget versus actual.
- Menghasilkan KPI dan variance analysis yang konsisten serta dapat diaudit.
- Mengidentifikasi departemen atau kategori yang over-budget.
- Menghasilkan laporan Markdown dan Excel yang mudah dibaca.
- Mendemonstrasikan penggunaan LLM yang aman: LLM hanya menginterpretasikan ringkasan terstruktur, bukan menghitung KPI atau menerima data mentah sensitif.

## 3. Pengguna Utama

- Finance atau accounting staff.
- Department manager.
- Management yang membutuhkan executive summary biaya operasional.

## 4. Dataset

MVP menggunakan dataset sintetis biaya operasional pertambangan dengan kolom wajib:

| Kolom | Tipe yang diharapkan | Deskripsi |
|---|---|---|
| `date` | date/datetime | Tanggal transaksi atau periode biaya |
| `department` | string | Nama departemen |
| `category` | string | Kategori biaya |
| `budget` | numeric | Anggaran biaya dalam IDR |
| `actual_cost` | numeric | Realisasi biaya dalam IDR |

Setiap baris merepresentasikan satu pos biaya/transaksi anggaran operasional. Departemen sintetis terdiri dari Mining Operations, Heavy Equipment, Logistics, HSE, dan Site Infrastructure. Kategori mengikuti konteks tiap departemen, termasuk Diesel Fuel, Equipment Maintenance, Hauling Transportation, Safety Equipment, Road Maintenance, Spare Parts, Site Utilities, dan Equipment Rental.

Seluruh transaksi, tanggal, dan nominal adalah data sintetis untuk demonstrasi. Dataset bukan data nyata atau rahasia, tidak merepresentasikan perusahaan tertentu, dan tidak boleh digunakan sebagai klaim fakta operasional industri atau perusahaan.

## 5. Scope MVP

### 5.1 Functional Requirements

1. Sistem dapat membaca file Excel `.xlsx` dari lokasi input yang ditentukan.
2. Sistem memvalidasi keberadaan kolom wajib, tipe data, nilai kosong, nilai numerik invalid, dan baris duplikat.
3. Sistem melakukan data cleaning yang terdokumentasi, termasuk normalisasi tanggal dan teks serta penanganan nilai kosong/invalid.
4. Sistem menghitung KPI dengan Python dan Pandas, minimal:
   - total budget;
   - total actual cost;
   - variance nominal (`actual_cost - budget`);
   - variance percentage (`variance / budget * 100`), dengan nilai `null` ketika budget nol karena persentase tidak terdefinisi;
   - agregasi per departemen dan kategori;
   - jumlah dan daftar kelompok over-budget.
5. Sistem menggunakan konvensi status variance berikut secara konsisten pada transaksi, agregasi, dan total:
   - variance positif (`actual_cost > budget`) berarti over-budget;
   - variance negatif (`actual_cost < budget`) berarti under-budget;
   - variance nol (`actual_cost == budget`) berarti on-budget.
6. Seluruh perhitungan numerik bersifat deterministik dan tidak dilakukan oleh LLM.
7. Sistem membentuk ringkasan terstruktur dari hasil analisis sebelum memanggil Gemini API.
8. Gemini hanya menerima agregat/KPI terstruktur yang diperlukan dan tidak menerima baris data mentah sensitif.
9. Gemini menghasilkan executive summary yang menjelaskan temuan utama, area over-budget, dan insight manajerial tanpa mengubah nilai KPI.
10. Sistem mengekspor laporan Markdown dan Excel yang memuat KPI, variance analysis, temuan over-budget, dan executive summary.
11. Jika Gemini tidak tersedia, sistem tetap dapat menghasilkan laporan deterministik dengan status/keterangan bahwa executive summary AI gagal dibuat.

### 5.2 Non-Functional Requirements

- **Correctness:** hasil KPI untuk input yang sama harus selalu sama dan dapat diverifikasi dari data sumber.
- **Security & privacy:** API key dibaca dari environment variable, tidak dicatat ke log/laporan, dan data mentah tidak dikirim ke LLM.
- **Maintainability:** kode modular, sederhana, memiliki fungsi dengan tanggung jawab tunggal, dan kompatibel dengan Python 3.11.
- **Reliability:** error input dan API ditangani dengan pesan yang jelas; kegagalan Gemini tidak boleh menghilangkan hasil analisis numerik.
- **Testability:** validation, cleaning, KPI, dan report generation dapat diuji secara terpisah tanpa panggilan API nyata.
- **Observability:** proses utama dan kegagalan dicatat secukupnya tanpa membocorkan data sensitif atau credential.
- **Usability:** perintah penggunaan dan format input/output mudah dipahami oleh pengguna non-developer.
- **Performance:** MVP harus memproses dataset sintetis skala laporan operasional biasa secara lokal tanpa optimasi terdistribusi.

## 6. Acceptance Criteria

- File Excel valid dengan lima kolom wajib berhasil diproses sampai menghasilkan laporan `.md` dan `.xlsx`.
- File tanpa kolom wajib, file rusak, sheet tidak dapat dibaca, atau nilai yang tidak dapat diproses menghasilkan error yang spesifik dan mudah ditindaklanjuti.
- Total budget, actual cost, variance, variance percentage, agregasi, dan status over-budget sesuai dengan expected result pada tests.
- Nilai KPI pada Markdown, Excel, dan payload ringkasan untuk Gemini konsisten.
- Tidak ada KPI yang dihitung atau dikoreksi oleh Gemini.
- Payload Gemini hanya berisi ringkasan/agregat terstruktur dan tidak berisi baris transaksi mentah.
- API key tidak muncul di source code, log, payload output, atau laporan.
- Kegagalan/timeout Gemini tetap menghasilkan laporan numerik dan pesan fallback yang jelas.
- Test lokal relevan dan pemeriksaan sintaks berhasil dijalankan pada Python 3.11.
- Dokumentasi penggunaan menjelaskan input, output, asumsi cleaning, konfigurasi environment, dan batasan sistem.

## 7. Out of Scope MVP

- Integrasi langsung ke ERP, database produksi, email, Slack, atau cloud storage.
- Dashboard web atau antarmuka grafis.
- Authentication, authorization, dan multi-tenant deployment.
- Forecasting, anomaly detection berbasis ML, atau rekomendasi keputusan otomatis.
- Pemrosesan data perusahaan nyata atau data pribadi/sensitif.
- AI Agent, tool calling, autonomous action, dan workflow n8n.
- Real-time/streaming processing dan distributed computing.
- Format input selain Excel `.xlsx` atau format laporan selain Markdown dan Excel.

## 8. Milestone

### Milestone 1 — Foundation

- Menyiapkan struktur proyek modular dan konfigurasi environment.
- Mendefinisikan kontrak input/output serta dependencies.
- Menyediakan dokumentasi penggunaan dasar dan rencana pengujian.

### Milestone 2 — Data Processing

- Menyediakan dataset sintetis.
- Mengimplementasikan Excel reader, validation, dan cleaning.
- Mengimplementasikan KPI engine, variance analysis, dan deteksi over-budget.
- Menghasilkan report data deterministik dan tests terkait.

### Milestone 3 — Gemini Reporting

- Membentuk payload ringkasan terstruktur yang aman.
- Mengintegrasikan Gemini API untuk executive summary.
- Menambahkan fallback ketika API gagal.
- Mengekspor laporan Markdown dan Excel.

### Milestone 4 — Testing

- Melengkapi unit dan integration tests lokal.
- Menguji happy path, data invalid, edge cases numerik, serta kegagalan API dengan mock.
- Memverifikasi konsistensi KPI antar-output dan memastikan credential/data mentah tidak bocor.
- Menyempurnakan dokumentasi implementasi dan penggunaan.

## 9. Pengembangan Setelah MVP

- **AI Agent Tool Calling:** mengekspos fungsi validasi, analisis, dan report generation sebagai tools dengan input/output terstruktur. Agent mengorkestrasi fungsi, tetapi KPI tetap dihitung oleh Pandas.
- **n8n:** menambahkan workflow terjadwal atau event-driven untuk mengambil file, memanggil pipeline, menyimpan laporan, dan mengirim notifikasi.

Keduanya hanya arah pengembangan berikutnya dan tidak diimplementasikan dalam MVP.
