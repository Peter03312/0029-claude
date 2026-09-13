import { describe, expect, it, vi, afterEach } from "vitest";
import {
  STATUS_LABEL,
  downloadReport,
  filterRows,
  isAnomaly,
  reportFileName,
  serializeReport,
} from "./report";
import type { Report } from "./types";

function makeReport(): Report {
  return {
    summary: {
      expected_count: 3,
      actual_count: 4,
      match: 2,
      replace: 1,
      missing: 0,
      extra: 1,
      anomaly: 2,
      edit_cost: 2,
      passed: false,
    },
    first_anomaly: {
      row_index: 1,
      slot: 2,
      scan_index: 2,
      status: "replace",
      expected_mark: "B",
      actual_mark: "X",
    },
    rows: [
      { slot: 1, scan_index: 1, expected_mark: "A", actual_mark: "A", status: "match" },
      { slot: 2, scan_index: 2, expected_mark: "B", actual_mark: "X", status: "replace" },
      { slot: 3, scan_index: 3, expected_mark: "C", actual_mark: "C", status: "match" },
      { slot: null, scan_index: 4, expected_mark: null, actual_mark: "Z", status: "extra" },
    ],
  };
}

describe("filterRows", () => {
  it("全部 / 仅异常 / 按单状态筛选均确定且不修改原数组", () => {
    const report = makeReport();
    expect(filterRows(report.rows, "all").map((r) => r.status)).toEqual([
      "match",
      "replace",
      "match",
      "extra",
    ]);
    expect(filterRows(report.rows, "anomaly").map((r) => r.status)).toEqual(["replace", "extra"]);
    expect(filterRows(report.rows, "replace")).toHaveLength(1);
    expect(filterRows(report.rows, "missing")).toHaveLength(0);
    expect(isAnomaly("match")).toBe(false);
  });

  it("重复标漏帖场景只筛出漏帖行", () => {
    const report: Report = {
      summary: {
        expected_count: 4,
        actual_count: 3,
        match: 3,
        replace: 0,
        missing: 1,
        extra: 0,
        anomaly: 1,
        edit_cost: 1,
        passed: false,
      },
      first_anomaly: {
        row_index: 2,
        slot: 3,
        scan_index: null,
        status: "missing",
        expected_mark: "B",
        actual_mark: null,
      },
      rows: [
        { slot: 1, scan_index: 1, expected_mark: "A", actual_mark: "A", status: "match" },
        { slot: 2, scan_index: 2, expected_mark: "B", actual_mark: "B", status: "match" },
        { slot: 3, scan_index: null, expected_mark: "B", actual_mark: null, status: "missing" },
        { slot: 4, scan_index: 3, expected_mark: "D", actual_mark: "D", status: "match" },
      ],
    };
    const anomalies = filterRows(report.rows, "anomaly");
    expect(anomalies).toHaveLength(1);
    expect(anomalies[0]).toMatchObject({ slot: 3, status: "missing", expected_mark: "B" });
    expect(STATUS_LABEL.missing).toBe("漏帖");
  });
});

describe("serializeReport", () => {
  it("序列化结果确定（无时间戳等易变量）", () => {
    expect(serializeReport(makeReport())).toBe(serializeReport(makeReport()));
    const parsed = JSON.parse(serializeReport(makeReport())) as Report;
    expect(parsed.first_anomaly?.row_index).toBe(1);
  });
});

describe("downloadReport", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("以 application/json 下载且文件名体现首个异常", () => {
    const click = vi.fn();
    const remove = vi.fn();
    const appendChild = vi.spyOn(document.body, "appendChild").mockImplementation((node) => {
      const anchor = node as HTMLAnchorElement;
      anchor.click = click;
      anchor.remove = remove;
      return node;
    });
    const createObjectURL = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:test");
    const revokeObjectURL = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});

    downloadReport(makeReport());

    expect(appendChild).toHaveBeenCalledTimes(1);
    const anchor = appendChild.mock.calls[0][0] as HTMLAnchorElement;
    expect(anchor.download).toBe("verify-report-replace-slot-2-scan-2.json");
    expect(click).toHaveBeenCalledTimes(1);
    expect(remove).toHaveBeenCalledTimes(1);
    expect(createObjectURL.mock.calls[0][0]).toBeInstanceOf(Blob);
    expect((createObjectURL.mock.calls[0][0] as Blob).type).toBe("application/json");
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:test");
  });

  it("通过场景下载文件名标记 pass", () => {
    const report = makeReport();
    report.summary.passed = true;
    report.first_anomaly = null;
    expect(reportFileName(report)).toBe("verify-report-pass.json");
  });
});
