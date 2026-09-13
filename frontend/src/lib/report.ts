/** 与后端契约同源的纯函数：筛选、定位首个异常、报告下载。 */

import type { AlignRow, Report, RowStatus } from "./types";

export const STATUS_LABEL: Record<RowStatus, string> = {
  match: "一致",
  replace: "错帖",
  missing: "漏帖",
  extra: "多帖",
};

export const STATUS_FILTERS: ReadonlyArray<{ value: "all" | "anomaly" | RowStatus; label: string }> = [
  { value: "all", label: "全部行" },
  { value: "anomaly", label: "仅异常" },
  { value: "replace", label: "仅错帖" },
  { value: "missing", label: "仅漏帖" },
  { value: "extra", label: "仅多帖" },
];

export function isAnomaly(status: RowStatus): boolean {
  return status !== "match";
}

export type StatusFilter = "all" | "anomaly" | RowStatus;

export function filterRows(rows: readonly AlignRow[], filter: StatusFilter): AlignRow[] {
  if (filter === "all") return [...rows];
  if (filter === "anomaly") return rows.filter((row) => isAnomaly(row.status));
  return rows.filter((row) => row.status === filter);
}

/** 确定性序列化：键序固定，无时间戳，便于复现与追溯。 */
export function serializeReport(report: Report): string {
  return JSON.stringify(report, null, 2);
}

export function reportFileName(report: Report): string {
  const { passed } = report.summary;
  const first = report.first_anomaly;
  if (passed || !first) return "verify-report-pass.json";
  const slotPart = first.slot === null ? "extra" : `slot-${first.slot}`;
  const scanPart = first.scan_index === null ? "-" : `scan-${first.scan_index}`;
  return `verify-report-${first.status}-${slotPart}-${scanPart}.json`;
}

/**
 * 下载 JSON 报告。返回的 Blob URL 在点击后立即回收。
 */
export function downloadReport(report: Report): void {
  const blob = new Blob([serializeReport(report)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = reportFileName(report);
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
