import { useEffect, useMemo, useRef } from "react";
import type { AlignRow, Report } from "../lib/types";
import {
  STATUS_FILTERS,
  STATUS_LABEL,
  type StatusFilter,
  filterRows,
} from "../lib/report";

interface ResultTableProps {
  report: Report;
  filter: StatusFilter;
  onFilterChange: (filter: StatusFilter) => void;
}

function MarkCell({ mark, missing }: { mark: string | null; missing: boolean }) {
  if (mark === null) {
    return <td className="mark-cell cell-none">—</td>;
  }
  return (
    <td className={`mark-cell${missing ? " cell-missing" : ""}`} title={`码点数：${[...mark].length}`}>
      {mark}
    </td>
  );
}

/**
 * 双列对齐结果：左列为期望槽位（slot + 期望帖标），右列为实扫序号
 * （scan_index + 实扫帖标），中间为行状态。
 *
 * 首个红色异常行带 id 与 data-first-anomaly，挂载与结果变化时自动滚动定位。
 */
export function ResultTable({ report, filter, onFilterChange }: ResultTableProps) {
  const firstRowRef = useRef<HTMLTableRowElement>(null);
  const firstIndex = report.first_anomaly?.row_index ?? null;

  const rows = useMemo(() => filterRows(report.rows, filter), [report.rows, filter]);

  // 结果或筛选变化后，只要首异常行在当前视图中就定位过去。
  useEffect(() => {
    const visible =
      firstIndex !== null && (filter === "all" || filter === "anomaly" || report.rows[firstIndex]?.status === filter);
    if (visible) {
      firstRowRef.current?.scrollIntoView({ block: "center", behavior: "auto" });
    }
  }, [report, filter, firstIndex]);

  return (
    <section className="panel">
      <div className="toolbar">
        <label htmlFor="status-filter">异常筛选：</label>
        <select
          id="status-filter"
          data-testid="status-filter"
          value={filter}
          onChange={(event) => onFilterChange(event.target.value as StatusFilter)}
        >
          {STATUS_FILTERS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <span className="filter-count" data-testid="filter-count">
          显示 {rows.length} / 共 {report.rows.length} 行
        </span>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th colSpan={2}>期望（配帖顺序）</th>
              <th aria-label="状态" />
              <th colSpan={2}>实扫（书芯自上而下）</th>
            </tr>
            <tr>
              <th className="col-num">槽位</th>
              <th>期望帖标</th>
              <th className="col-num">状态</th>
              <th>实扫帖标</th>
              <th className="col-num">实扫序号</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={5} className="empty-filtered">
                  当前筛选下没有行
                </td>
              </tr>
            )}
            {rows.map((row: AlignRow) => {
              const absoluteIndex = report.rows.indexOf(row);
              const isFirst = absoluteIndex === firstIndex;
              return (
                <tr
                  key={absoluteIndex}
                  ref={isFirst ? firstRowRef : undefined}
                  className={isFirst ? "first-anomaly" : ""}
                  data-status={row.status}
                  data-row-index={absoluteIndex}
                  data-first-anomaly={isFirst ? "true" : undefined}
                >
                  <td className="col-num">{row.slot ?? "—"}</td>
                  <MarkCell mark={row.expected_mark} missing={row.status === "replace"} />
                  <td>
                    <span className={`status-badge status-${row.status}`}>
                      {STATUS_LABEL[row.status]}
                    </span>
                    {isFirst && <span className="first-flag">▲ 首个异常</span>}
                  </td>
                  <MarkCell mark={row.actual_mark} missing={row.status === "replace"} />
                  <td className="col-num">{row.scan_index ?? "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
