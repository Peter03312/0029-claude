import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import type { Report } from "./lib/types";

function expectedPayload(marks: string[]) {
  return marks.map((mark, i) => ({ slot: i + 1, mark }));
}

function jsonFile(name: string, value: unknown) {
  return new File([JSON.stringify(value)], name, { type: "application/json" });
}

function reportBody(report: Report) {
  return { ok: true as const, report };
}

const perfectReport: Report = {
  summary: {
    expected_count: 3,
    actual_count: 3,
    match: 3,
    replace: 0,
    missing: 0,
    extra: 0,
    anomaly: 0,
    edit_cost: 0,
    passed: true,
  },
  first_anomaly: null,
  rows: [
    { slot: 1, scan_index: 1, expected_mark: "甲", actual_mark: "甲", status: "match" },
    { slot: 2, scan_index: 2, expected_mark: "乙", actual_mark: "乙", status: "match" },
    { slot: 3, scan_index: 3, expected_mark: "丙", actual_mark: "丙", status: "match" },
  ],
};

const duplicateMissingReport: Report = {
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

const wrongAndExtraReport: Report = {
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

async function uploadBoth(
  user: ReturnType<typeof userEvent.setup>,
  expectedValue: unknown,
  actualValue: unknown,
) {
  await user.upload(
    screen.getByTestId("expected-import-input"),
    jsonFile("expected.json", expectedValue),
  );
  await user.upload(
    screen.getByTestId("actual-import-input"),
    jsonFile("actual.json", actualValue),
  );
}

describe("配帖核验站页面", () => {
  let fetchMock: ReturnType<typeof vi.fn>;
  let scrollIntoViewMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    scrollIntoViewMock = vi.fn();
    Element.prototype.scrollIntoView = scrollIntoViewMock;
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("验收1：完全一致时显示通过、双列三行均为一致，并以 multipart 上传两个文件", async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue({
      status: 200,
      json: async () => structuredClone(reportBody(perfectReport)),
    });

    render(<App />);
    expect(screen.getByTestId("verify-button")).toBeDisabled();

    await uploadBoth(user, expectedPayload(["甲", "乙", "丙"]), ["甲", "乙", "丙"]);
    expect(screen.getByTestId("verify-button")).toBeEnabled();
    await user.click(screen.getByTestId("verify-button"));

    // 上传契约：multipart 两个文件字段
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/verify");
    expect(init.method).toBe("POST");
    const form = init.body as FormData;
    expect(form).toBeInstanceOf(FormData);
    expect(form.get("expected_file")).toBeInstanceOf(File);
    expect((form.get("expected_file") as File).name).toBe("expected.json");
    expect(form.get("actual_file")).toBeInstanceOf(File);

    expect(screen.getByTestId("verdict")).toHaveTextContent("核验通过");
    const tableRows = document.querySelectorAll("tbody tr");
    expect(tableRows).toHaveLength(3);
    tableRows.forEach((row) => {
      expect(within(row as HTMLElement).getByText("一致")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("first-anomaly-banner")).not.toBeInTheDocument();
  });

  it("验收2：重复标漏帖给出确定行，定位首个红色异常（槽位3），且可仅筛异常", async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue({
      status: 200,
      json: async () => structuredClone(reportBody(duplicateMissingReport)),
    });

    render(<App />);
    await uploadBoth(user, expectedPayload(["A", "B", "B", "D"]), ["A", "B", "D"]);
    await user.click(screen.getByTestId("verify-button"));

    expect(screen.getByTestId("verdict")).toHaveTextContent("核验不通过");
    const banner = screen.getByTestId("first-anomaly-banner");
    expect(banner).toHaveTextContent("期望槽位 3");
    expect(banner).toHaveTextContent("漏帖");

    const firstRow = document.querySelector("tr[data-first-anomaly='true']") as HTMLElement;
    expect(firstRow).toBeTruthy();
    expect(firstRow.dataset.rowIndex).toBe("2");
    expect(firstRow.dataset.status).toBe("missing");
    expect(within(firstRow).getByText("漏帖")).toBeInTheDocument();
    // 挂载后自动滚动定位到首个异常行
    expect(scrollIntoViewMock).toHaveBeenCalled();

    // 双列内容：左列期望槽位与帖标，右列实扫序号，漏帖行右列为空占位
    expect(within(firstRow).getByText("3")).toBeInTheDocument();
    expect(within(firstRow).getByText("B")).toBeInTheDocument();

    // 异常筛选：仅异常
    await user.selectOptions(screen.getByTestId("status-filter"), "anomaly");
    expect(document.querySelectorAll("tbody tr")).toHaveLength(1);
    expect(screen.getByTestId("filter-count")).toHaveTextContent("显示 1 / 共 4 行");
    expect(document.querySelector("tbody tr")?.getAttribute("data-row-index")).toBe("2");

    // 仅漏帖
    await user.selectOptions(screen.getByTestId("status-filter"), "missing");
    expect(document.querySelectorAll("tbody tr")).toHaveLength(1);

    // 切回全部恢复四行
    await user.selectOptions(screen.getByTestId("status-filter"), "all");
    expect(document.querySelectorAll("tbody tr")).toHaveLength(4);
  });

  it("验收3：同次错帖加末尾多帖，首异常为槽位2错帖，末行为实扫第4件多帖", async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue({
      status: 200,
      json: async () => structuredClone(reportBody(wrongAndExtraReport)),
    });

    render(<App />);
    await uploadBoth(user, expectedPayload(["A", "B", "C"]), ["A", "X", "C", "Z"]);
    await user.click(screen.getByTestId("verify-button"));

    const firstRow = document.querySelector("tr[data-first-anomaly='true']") as HTMLElement;
    expect(firstRow.dataset.rowIndex).toBe("1");
    expect(within(firstRow).getByText("错帖")).toBeInTheDocument();
    expect(within(firstRow).getByText("B")).toBeInTheDocument();
    expect(within(firstRow).getByText("X")).toBeInTheDocument();
    expect(screen.getByTestId("first-anomaly-banner")).toHaveTextContent("实扫第 2 件");

    const tableRows = document.querySelectorAll("tbody tr");
    const extraRow = tableRows[3] as HTMLElement;
    expect(extraRow.dataset.status).toBe("extra");
    expect(within(extraRow).getByText("多帖")).toBeInTheDocument();
    expect(within(extraRow).getByText("Z")).toBeInTheDocument();
    // 多帖行无期望槽位
    expect(within(extraRow).getAllByText("—").length).toBeGreaterThan(0);

    await user.selectOptions(screen.getByTestId("status-filter"), "extra");
    expect(document.querySelectorAll("tbody tr")).toHaveLength(1);
  });

  it("验收4：期望清单坏文件在期望导入区报错，整单拒绝无结果、无报告按钮", async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue({
      status: 422,
      json: async () => ({
        ok: false,
        source: "expected",
        error: { code: "invalid_json", message: "JSON 解析失败（第 1 行第 3 列）：Expecting value" },
      }),
    });

    render(<App />);
    await uploadBoth(user, "not-json-content", ["A"]);
    await user.click(screen.getByTestId("verify-button"));

    const expectedPanel = screen.getByTestId("expected-import");
    expect(within(expectedPanel).getByTestId("expected-import-error")).toHaveTextContent(
      "invalid_json",
    );
    expect(within(expectedPanel).getByTestId("expected-import-error")).toHaveTextContent(
      "JSON 解析失败",
    );
    // 实扫导入区不显示错误
    expect(within(screen.getByTestId("actual-import")).queryByRole("alert")).toBeNull();
    // 整次拒绝：无结论行、无表格、无下载入口
    expect(screen.queryByTestId("verdict")).not.toBeInTheDocument();
    expect(screen.queryByTestId("download-report")).not.toBeInTheDocument();
    expect(document.querySelector("tbody tr")).toBeNull();
  });

  it("实扫契约违约时错误归入实扫导入区，更换文件后错误与旧结果同时清除", async () => {
    const user = userEvent.setup();
    fetchMock
      .mockResolvedValueOnce({
        status: 422,
        json: async () => ({
          ok: false,
          source: "actual",
          error: { code: "entry_empty", message: "第 2 项不能为空字符串" },
        }),
      })
      .mockResolvedValueOnce({
        status: 200,
        json: async () => structuredClone(reportBody(perfectReport)),
      });

    render(<App />);
    await uploadBoth(user, expectedPayload(["甲", "乙", "丙"]), ["甲", ""]);
    await user.click(screen.getByTestId("verify-button"));

    const actualPanel = screen.getByTestId("actual-import");
    expect(within(actualPanel).getByTestId("actual-import-error")).toHaveTextContent(
      "第 2 项不能为空字符串",
    );
    expect(screen.queryByTestId("verdict")).not.toBeInTheDocument();

    // 重新选择文件即清除本区错误
    await user.upload(
      screen.getByTestId("actual-import-input"),
      jsonFile("actual-fixed.json", ["甲", "乙", "丙"]),
    );
    expect(within(actualPanel).queryByRole("alert")).toBeNull();
  });

  it("网络故障显示通用错误且不产生结果", async () => {
    const user = userEvent.setup();
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    render(<App />);
    await uploadBoth(user, expectedPayload(["A"]), ["A"]);
    await user.click(screen.getByTestId("verify-button"));

    expect(screen.getByTestId("global-error")).toHaveTextContent("核验请求失败");
    expect(screen.queryByTestId("verdict")).not.toBeInTheDocument();
  });

  it("点击下载按钮产出 JSON 报告文件", async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue({
      status: 200,
      json: async () => structuredClone(reportBody(wrongAndExtraReport)),
    });

    render(<App />);
    await uploadBoth(user, expectedPayload(["A", "B", "C"]), ["A", "X", "C", "Z"]);
    await user.click(screen.getByTestId("verify-button"));

    const clickSpy = vi.fn();
    const appendSpy = vi
      .spyOn(document.body, "appendChild")
      .mockImplementation((node) => {
        (node as HTMLAnchorElement).click = clickSpy;
        return node;
      });
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:download");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});

    await user.click(screen.getByTestId("download-report"));
    expect(clickSpy).toHaveBeenCalledTimes(1);
    const anchor = appendSpy.mock.calls[0][0] as HTMLAnchorElement;
    expect(anchor.download).toBe("verify-report-replace-slot-2-scan-2.json");
  });
});
