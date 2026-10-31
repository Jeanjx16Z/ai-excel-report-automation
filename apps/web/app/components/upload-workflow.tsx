"use client";

import { useRef, useState } from "react";
import type { FormEvent } from "react";
import type { Report } from "../../lib/report-types";
import ReportResult from "./report-result";

const XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
type Pending = { upload_id: string; key: string };

class RequestError extends Error {
  constructor(message: string, public code: string) { super(message); }
}

async function api(path: string, options: RequestInit = {}) {
  let response: Response;
  try {
    response = await fetch(path, { ...options, credentials: "same-origin", cache: "no-store", signal: AbortSignal.timeout(125000) });
  } catch {
    throw new RequestError("Koneksi terputus atau waktu tunggu habis. Status pemrosesan belum dapat dipastikan. Gunakan Periksa Hasil untuk request yang sama.", "NETWORK_FAILURE");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new RequestError(body?.error?.message ?? "Permintaan gagal. Periksa konfigurasi server lokal.", body?.error?.code ?? "REQUEST_FAILED");
  }
  return response;
}

function saveBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = name;
  document.body.appendChild(anchor); anchor.click(); anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 3000);
}

export default function UploadWorkflow() {
  const [file, setFile] = useState<File | null>(null);
  const [ack, setAck] = useState(false);
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState("");
  const [error, setError] = useState("");
  const [report, setReport] = useState<Report | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);
  const csrf = useRef<string | null>(null);
  const inFlight = useRef(false);
  const picker = useRef<HTMLInputElement>(null);

  async function ensureSession() {
    if (csrf.current) return csrf.current;
    // Explicit new workflow bootstraps a fresh owner when client-memory CSRF is unavailable.
    const response = await api("/api/v1/session/reset", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reset_ack: true }) });
    const session = await response.json();
    csrf.current = session.csrf_token;
    return session.csrf_token as string;
  }

  function handleError(caught: unknown) {
    if (caught instanceof RequestError && caught.code === "INVALID_SESSION") {
      csrf.current = null;
      setError("Sesi sudah berakhir. Pilih Proses File Lain untuk memulai sesi baru. Laporan lama tidak dapat diakses setelah sesi berakhir.");
    } else setError(caught instanceof RequestError ? caught.message : "Respons belum dapat dipastikan. Periksa server lokal dan gunakan Periksa Hasil bila request sudah dikirim.");
  }

  async function downloadTemplate() {
    if (inFlight.current) return;
    inFlight.current = true; setBusy(true); setError(""); setStage("Menyiapkan template sintetis…");
    try {
      await ensureSession();
      const response = await api("/api/v1/template");
      saveBlob(await response.blob(), "template_synthetic.xlsx");
    } catch (caught) { handleError(caught); }
    finally { inFlight.current = false; setBusy(false); setStage(""); }
  }

  function selectFile(selected: File | null) {
    if (inFlight.current || pending) return;
    setError(""); setAck(false);
    if (selected && (!selected.name.toLowerCase().endsWith(".xlsx") || selected.size > 10 * 1024 * 1024 || selected.size === 0)) {
      setFile(null); setError("Pilih file .xlsx yang tidak kosong dengan ukuran maksimum 10 MB."); return;
    }
    setFile(selected);
  }

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inFlight.current || !file || !ack) return;
    inFlight.current = true; setBusy(true); setError("");
    try {
      const token = await ensureSession();
      const headers = { "Content-Type": "application/json", "X-CSRF-Token": token };
      let attempt = pending;
      if (!attempt) {
        setStage("Mengunggah file sintetis…");
        const intentResponse = await api("/api/v1/uploads/intents", { method: "POST", headers,
          body: JSON.stringify({ filename: file.name, size_bytes: file.size, content_type: XLSX_TYPE, synthetic_data_ack: true }) });
        const intent = await intentResponse.json();
        const expectedTarget = `/api/v1/uploads/${intent.upload_id}/content`;
        if (intent.upload_instruction.target !== expectedTarget) throw new Error("Instruksi upload tidak valid.");
        await api(expectedTarget, { method: "PUT", headers: { ...intent.upload_instruction.headers, "X-CSRF-Token": token }, body: file });
        setStage("Memvalidasi struktur dan keamanan workbook…");
        await api(`/api/v1/uploads/${intent.upload_id}/complete`, { method: "POST", headers, body: "{}" });
        attempt = { upload_id: intent.upload_id, key: crypto.randomUUID() };
        setPending(attempt);
      }
      setStage("Menghitung KPI dan menyusun laporan offline. Mohon tunggu…");
      const response = await api("/api/v1/reports", { method: "POST", headers: { ...headers, "Idempotency-Key": attempt.key },
        body: JSON.stringify({ upload_id: attempt.upload_id, summary_mode: "offline" }) });
      const completed = await response.json();
      if (completed.state !== "completed" || completed.summary_source !== "offline") throw new Error("Laporan belum selesai. Periksa hasil dengan request yang sama.");
      setReport(completed); setPending(null);
      setStage("Laporan selesai. PDF siap diunduh.");
    } catch (caught) { handleError(caught); setStage(""); }
    finally { inFlight.current = false; setBusy(false); }
  }

  function reset() {
    if (inFlight.current) return;
    setFile(null); setAck(false); setReport(null); setPending(null); setStage(""); setError("");
    if (picker.current) picker.current.value = "";
  }

  return <>
    {!report ? <section className="panel upload-panel" aria-labelledby="upload-title">
      <div className="section-heading"><div><p className="eyebrow">01 · Input Excel</p><h2 id="upload-title">Mulai dari file sintetis Anda</h2></div>
        <button type="button" className="button secondary" onClick={downloadTemplate} disabled={busy || !!pending}>Unduh Template Sintetis</button></div>
      <p>Gunakan satu sheet dengan lima kolom persis berikut. Maksimum 10 MB dan 10.000 baris data; tanpa formula, macro, atau external link.</p>
      <div className="schema" aria-label="Kolom wajib"><code>date</code><code>department</code><code>category</code><code>budget</code><code>actual_cost</code></div>
      <p className="muted">Mode ini hanya untuk rekap anggaran dan biaya operasional. Workbook multi-sheet, laporan laba rugi, dan neraca belum didukung.</p>
      <p className="muted">Departemen: Mining Operations, Heavy Equipment, Logistics, HSE, Site Infrastructure. Gunakan pasangan kategori pada template/core pertambangan. Tanggal harus valid dan nominal IDR non-negatif.</p>
      <p className="muted">Unduh hasil sebelum refresh/menutup halaman. Sesi demo baru dapat membuat laporan sesi sebelumnya tidak dapat diakses.</p>
      <form onSubmit={generate} aria-busy={busy}>
        <div className="drop-zone" onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); if (!busy) selectFile(event.dataTransfer.files.item(0)); }}>
          <label htmlFor="workbook">Pilih Excel sintetis atau tarik file ke area ini</label>
          <input ref={picker} id="workbook" name="workbook" type="file" accept=".xlsx" disabled={busy || !!pending} onChange={(event) => selectFile(event.target.files?.item(0) ?? null)} aria-describedby="file-help" />
          <p id="file-help">{file ? `${file.name} · ${file.size.toLocaleString("id-ID")} byte` : "Belum ada file dipilih."}</p>
        </div>
        <label className="confirmation"><input type="checkbox" checked={ack} disabled={busy || !!pending} onChange={(event) => setAck(event.target.checked)} required />
          <span>Saya memastikan file ini hanya berisi data dummy/sintetis, bukan data perusahaan atau data pribadi nyata.</span></label>
        <p className="muted">Konfirmasi ini bukan pemeriksaan otomatis yang dapat membuktikan keaslian atau sifat sintetis isi file.</p>
        <div className="actions"><button className="button primary" type="submit" disabled={busy || !file || !ack}>{busy ? "Sedang Memproses…" : pending ? "Periksa Hasil" : "Buat Laporan"}</button>
          {pending ? <button className="button secondary" type="button" onClick={reset} disabled={busy}>Proses File Lain</button> : null}</div>
        {pending ? <p className="muted">Periksa Hasil memakai request/key yang sama. Proses File Lain adalah tindakan eksplisit untuk memulai upload baru; tidak ada retry otomatis.</p> : null}
      </form>
    </section> : <ReportResult report={report} />}
    {error ? <div role="alert" className="error-box"><strong>Permintaan belum berhasil.</strong><p>{error}</p>
      {!pending && !report ? <button type="button" className="button secondary" onClick={reset} disabled={busy}>Proses File Lain</button> : null}</div> : null}
    <p role="status" aria-live="polite" className="progress">{busy ? <span className="spinner" aria-hidden="true" /> : null}{stage}</p>
    {report ? <button className="button secondary" type="button" onClick={reset}>Proses File Lain</button> : null}
  </>;
}
