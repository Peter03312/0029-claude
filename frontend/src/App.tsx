import { useState } from "react";
import { ImportPanel } from "./components/ImportPanel";
import { ResultTable } from "./components/ResultTable";
import { verifyFiles } from "./lib/api";
import { downloadReport, type StatusFilter } from "./lib/report";
import type { ApiError, Report } from "./lib/types";

type PanelSource = "expected" | "actual";

function emptyErrors(): Record<PanelSource, ApiError["error"] | null> {
  return { expected: null, actual: null };
}

export function App() {
  const [files, setFiles] = useState<Record<PanelSource, File | null>>({
    expected: null,
    actual: null,
  });
  const [errors, setErrors] = useState<Record<PanelSource, ApiError["error"] | null>>(emptyErrors);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [submitting, setSubmitting] = useState(false);

  function selectFile(source: PanelSource, file: File) {
    setFiles((prev) => ({ ...prev, [source]: file }));
    setErrors((prev) => ({ ...prev, [source]: null }));
    setGlobalError(null);
    // 任一输入变化后，上一次结果与报告即失效
    setReport(null);
  }

  async function handleVerify() {
    if (!files.expected || !files.actual || submitting) return;
    setSubmitting(true);
    setErrors(emptyErrors());
    setGlobalError(null);
    setReport(null);
    try {
      const result = await verifyFiles(files.expected, files.actual);
      if (!result.ok) {
        if (result.source === "request") {
          // 请求本身畸形（缺上传字段等）：不归入任何导入区
          setGlobalError(result.error.message);
          return;
        }
        // 整次拒绝：仅在违约导入区报错，无结果、无报告
        setErrors({ ...emptyErrors(), [result.source]: result.error });
        setFilter("all");
        return;
      }
      setReport(result.report);
      setFilter("all");
    } catch (err) {
      setGlobalError(err instanceof Error ? `核验请求失败：${err.message}` : "核验请求失败");
    } finally {
      setSubmitting(false);
    }
  }

  function handleLocateFirst() {
    document
      .querySelector("[data-first-anomaly='true']")
      ?.scrollIntoView({ block: "center", behavior: "smooth" });
  }

  const first = report?.first_anomaly ?? null;

  return (
    <div className="app">
      <header className="app-header">
        <h1>锁线前配帖核验站</h1>
        <p>
          导入期望清单与书芯实扫 JSON（各不超过 400 项），按插入/删除/替换各代价 1 做动态规划对齐。
          帖标按 JSON 解码后的码点原样比较；任一文件解析失败或违约则整单拒绝。
        </p>
      </header>

      <div className="import-grid">
        <ImportPanel
          testId="expected-import"
          title="期望清单 JSON"
          hint="对象数组，每项仅含整数 slot 与非空字符串 mark；长度 n 时第 i 项 slot 必须为 i（数组顺序即对齐顺序）。"
          accept=".json,application/json"
          fileName={files.expected?.name ?? null}
          error={errors.expected}
          onSelect={(file) => selectFile("expected", file)}
        />
        <ImportPanel
          testId="actual-import"
          title="实扫 JSON"
          hint="书芯自上而下的非空字符串数组，例如 [「帖1」,「帖2」]；空白与大小写均按码点原样比较。"
          accept=".json,application/json"
          fileName={files.actual?.name ?? null}
          error={errors.actual}
          onSelect={(file) => selectFile("actual", file)}
        />
      </div>

      {globalError && (
        <div className="global-error" role="alert" data-testid="global-error">
          {globalError}
        </div>
      )}

      <div className="actions">
        <button
          type="button"
          data-testid="verify-button"
          disabled={!files.expected || !files.actual || submitting}
          onClick={handleVerify}
        >
          {submitting ? "核验中…" : "开始核验"}
        </button>
        {report && (
          <button
            type="button"
            className="secondary"
            data-testid="download-report"
            onClick={() => downloadReport(report)}
          >
            下载 JSON 报告
          </button>
        )}
      </div>

      {report && (
        <>
          <div className="result-header">
            <span
              className={`verdict ${report.summary.passed ? "pass" : "fail"}`}
              data-testid="verdict"
            >
              {report.summary.passed ? "核验通过：全部一致" : "核验不通过"}
            </span>
            <div className="summary-cards" data-testid="summary-cards">
              <span className="summary-card">一致<b>{report.summary.match}</b></span>
              <span className="summary-card">错帖<b>{report.summary.replace}</b></span>
              <span className="summary-card">漏帖<b>{report.summary.missing}</b></span>
              <span className="summary-card">多帖<b>{report.summary.extra}</b></span>
              <span className="summary-card">编辑代价<b>{report.summary.edit_cost}</b></span>
            </div>
          </div>

          {first && (
            <div className="first-anomaly-banner" data-testid="first-anomaly-banner">
              首个红色异常：第 {first.row_index + 1} 行 ·{" "}
              {first.slot !== null ? `期望槽位 ${first.slot}` : "无对应期望槽位"} ·{" "}
              {first.scan_index !== null ? `实扫第 ${first.scan_index} 件` : "无对应实扫件"} ·
              状态「{first.status === "replace" ? "错帖" : first.status === "missing" ? "漏帖" : "多帖"}」
              {first.expected_mark !== null && `，期望「${first.expected_mark}」`}
              {first.actual_mark !== null && `，实扫「${first.actual_mark}」`}
              <button type="button" className="locate" onClick={handleLocateFirst}>
                定位
              </button>
            </div>
          )}

          <ResultTable report={report} filter={filter} onFilterChange={setFilter} />
        </>
      )}
    </div>
  );
}
