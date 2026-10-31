import type { Report, SummaryRow } from "../../lib/report-types";

function SummaryTable({ rows, title, field }: { rows: SummaryRow[]; title: string; field: "department" | "category" }) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      <div className="table-scroll" tabIndex={0} role="region" aria-label={title}>
        <table>
          <caption>Diurutkan berdasarkan variance terbesar oleh Python/Pandas.</caption>
          <thead><tr><th scope="col">Nama</th><th scope="col">Budget</th><th scope="col">Actual cost</th><th scope="col">Variance</th><th scope="col">Variance %</th><th scope="col">Transaksi</th></tr></thead>
          <tbody>{rows.map((row) => <tr key={row[field]}>
            <th scope="row">{row[field]}</th><td>{row.budget.display_value}</td><td>{row.actual_cost.display_value}</td>
            <td>{row.variance.display_value}</td><td>{row.variance_pct.display_value}</td><td>{row.transaction_count}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </section>
  );
}

export default function ReportResult({ report }: { report: Report }) {
  const base = `/api/v1/reports/${report.report_id}/download`;
  const kpis = report.kpis;
  return <div id="report-result" className="result" aria-label="Hasil laporan">
    <section className="panel result-heading">
      <div><p className="eyebrow">Laporan selesai · data sintetis</p><h2>Rekap biaya operasional</h2>
        <p>Periode {report.metadata.period_start} sampai {report.metadata.period_end} · {report.metadata.currency}</p></div>
      <a className="button primary" href={`${base}/pdf`} download>Unduh PDF</a>
    </section>
    <dl className="kpi-grid">
      {([ ["Total Budget", kpis.total_budget.display_value], ["Total Actual Cost", kpis.total_actual_cost.display_value],
        ["Variance", kpis.variance.display_value], ["Variance %", kpis.variance_pct.display_value] ]).map(([label, value]) =>
        <div className="kpi" key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
    </dl>
    <p className="counts">Total transaksi: <strong>{kpis.transaction_count}</strong> · Over-budget: <strong>{kpis.over_budget_count}</strong> · Under-budget: <strong>{kpis.under_budget_count}</strong> · On-budget: <strong>{kpis.on_budget_count}</strong></p>
    <p className="muted">Variance positif = over-budget; negatif = under-budget; nol = on-budget. Semua angka berasal dari Python/Pandas.</p>
    <section className="panel"><p className="eyebrow">Summary source: offline</p><h2>Executive Summary</h2>
      <p>{report.summary.executive_summary}</p><p className="muted">{report.summary.synthetic_data_disclaimer}</p>
      <h3>Temuan utama</h3><ul>{report.summary.key_findings.map((text) => <li key={text}>{text}</li>)}</ul>
      <h3>Risiko potensial</h3><ul>{report.summary.potential_risks.map((risk) => <li key={risk.statement}><strong>{risk.evidence_level === "fact" ? "Fakta" : "Hipotesis"}:</strong> {risk.statement}</li>)}</ul>
      <h3>Rekomendasi</h3><ol>{report.summary.actionable_recommendations.map((text) => <li key={text}>{text}</li>)}</ol>
    </section>
    <SummaryTable rows={report.department_summary} title="Ringkasan Departemen" field="department" />
    <SummaryTable rows={report.category_summary} title="Ringkasan Kategori" field="category" />
    <p className="download-links">Format lain: <a href={`${base}/markdown`} download>Markdown</a><a href={`${base}/excel`} download>Excel</a></p>
  </div>;
}
