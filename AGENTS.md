# AGENTS.md

Panduan ini berlaku untuk seluruh repository `ai-excel-report-automation`.

## Sebelum Melakukan Perubahan

1. Baca `docs/PRD.md` dan `docs/ARCHITECTURE.md` sampai selesai sebelum mengubah kode.
2. Periksa kondisi repository dan pertahankan perubahan pengguna yang sudah ada.
3. Pastikan pekerjaan hanya mencakup satu milestone yang secara eksplisit diminta pengguna.
4. Jika instruksi bertentangan dengan PRD atau arsitektur, jelaskan perbedaannya dan minta arahan sebelum memperluas scope.

## Aturan Implementasi

- Gunakan Python 3.11.
- Tulis modular code yang sederhana, mudah dibaca, dan mudah diuji; hindari abstraksi yang belum diperlukan.
- Gunakan English untuk nama variable, function, class, module, dan istilah teknis dalam kode.
- Gunakan bahasa Indonesia untuk komunikasi dengan pengguna dan laporan hasil pekerjaan.
- Pertahankan pemisahan tegas: Python/Pandas menghitung seluruh KPI; LLM hanya menyusun interpretasi dari ringkasan terstruktur.
- Jangan mengirim data mentah sensitif ke LLM.
- Jangan menambah fitur, dependency, integrasi, atau refactor di luar scope milestone yang diminta.
- AI Agent tool calling dan n8n adalah rencana pasca-MVP; jangan mengimplementasikannya kecuali pengguna memberi instruksi baru yang eksplisit.

## Keamanan dan External Actions

- Jangan menyimpan, hard-code, mencetak, atau menampilkan API key maupun secret lainnya.
- Gunakan environment variable untuk secret dan hanya sediakan placeholder aman pada contoh konfigurasi.
- Jangan menjalankan panggilan Gemini API nyata tanpa izin eksplisit pengguna. Gunakan mock/fake pada tests lokal.
- Jangan commit, push, membuat pull request, atau mengubah remote Git tanpa izin eksplisit pengguna.
- Jangan mengubah file di luar repository.

## Validasi Pekerjaan

- Setelah perubahan kode, wajib jalankan pemeriksaan sintaks Python dan tests lokal yang relevan jika environment memungkinkan.
- Utamakan tests deterministik untuk validation, cleaning, KPI, reporting, dan failure path.
- Jangan menyatakan tests berhasil bila tidak dijalankan. Jika pemeriksaan tidak dapat dijalankan, sebutkan alasan dan risiko yang tersisa.
- Pastikan tests tidak melakukan network call nyata dan tidak mengekspos credential atau data sensitif.

## Laporan Setelah Milestone

Setelah menyelesaikan setiap milestone, jelaskan secara ringkas:

- file dan perilaku yang berubah;
- keputusan atau asumsi penting;
- pemeriksaan sintaks dan tests yang dijalankan beserta hasilnya;
- pemeriksaan yang tidak dapat dijalankan dan alasannya;
- batas scope yang sengaja tidak dikerjakan;
- langkah berikutnya, lalu tunggu instruksi pengguna.
