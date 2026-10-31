import UploadWorkflow from "./components/upload-workflow";

export default function Home() {
  return (
    <main>
      <header className="hero" aria-labelledby="project-title">
        <p className="eyebrow">Mining operations · demo lokal</p>
        <h1 id="project-title">Dari Excel ke laporan yang siap dibaca.</h1>
        <p className="intro">Rekap anggaran dan biaya operasional pertambangan dengan KPI Python/Pandas dan ringkasan offline. Unggah, periksa hasil, lalu unduh PDF.</p>
        <aside aria-label="Peringatan data demo" className="warning"><strong>Hanya data sintetis.</strong>
          <span>Jangan unggah data perusahaan rahasia atau data pribadi nyata. Demo only — do not upload real confidential or personal company data.</span></aside>
      </header>
      <UploadWorkflow />
      <footer className="page-footer">Demo single-process lokal · Session dan metadata hilang saat restart · Belum untuk production atau deployment Vercel.</footer>
    </main>
  );
}
