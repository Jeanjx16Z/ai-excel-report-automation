export type Money = { value: string | null; display_value: string };
export type SummaryRow = {
  department?: string; category?: string;
  budget: Money; actual_cost: Money; variance: Money; variance_pct: Money;
  transaction_count: number;
};
export type Report = {
  report_id: string; state: "completed"; summary_source: "offline";
  metadata: { period_start: string; period_end: string; currency: string; synthetic_data: boolean };
  kpis: {
    total_budget: Money; total_actual_cost: Money; variance: Money; variance_pct: Money;
    transaction_count: number; over_budget_count: number; under_budget_count: number; on_budget_count: number;
  };
  department_summary: SummaryRow[]; category_summary: SummaryRow[];
  summary: {
    executive_summary: string; key_findings: string[];
    potential_risks: { statement: string; evidence_level: "fact" | "hypothesis" }[];
    actionable_recommendations: string[]; synthetic_data_disclaimer: string;
  };
};
