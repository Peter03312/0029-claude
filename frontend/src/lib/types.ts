/** 与后端 /api/verify 返回结构对应的共享类型（单一事实源）。 */

export type RowStatus = "match" | "replace" | "missing" | "extra";

export interface AlignRow {
  slot: number | null;
  scan_index: number | null;
  expected_mark: string | null;
  actual_mark: string | null;
  status: RowStatus;
}

export interface FirstAnomaly {
  row_index: number;
  slot: number | null;
  scan_index: number | null;
  status: RowStatus;
  expected_mark: string | null;
  actual_mark: string | null;
}

export interface ReportSummary {
  expected_count: number;
  actual_count: number;
  match: number;
  replace: number;
  // 漏帖
  missing: number;
  // 多帖
  extra: number;
  anomaly: number;
  edit_cost: number;
  passed: boolean;
}

export interface Report {
  summary: ReportSummary;
  first_anomaly: FirstAnomaly | null;
  rows: AlignRow[];
}

export type ImportSource = "expected" | "actual" | "request";

export interface ApiError {
  ok: false;
  source: ImportSource;
  error: { code: string; message: string };
}

export interface VerifyOk {
  ok: true;
  report: Report;
}

export type VerifyResponse = VerifyOk | ApiError;
