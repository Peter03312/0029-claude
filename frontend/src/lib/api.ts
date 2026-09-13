import type { ApiError, VerifyResponse } from "./types";

/**
 * 上传两个 JSON 文件到 /api/verify。
 *
 * 契约/解析失败（422，带 source）正常返回结构化 ApiError，由页面把错误
 * 归到对应导入区；网络故障、网关错误（500/502）或响应体不是 JSON 时
 * 抛出带可读信息的 Error，由页面作为通用错误提示。违约响应永远不携带
 * 报告，因此这里也不会构造出报告。
 */
export async function verifyFiles(
  expected: File,
  actual: File,
): Promise<VerifyResponse> {
  const form = new FormData();
  form.append("expected_file", expected);
  form.append("actual_file", actual);

  let response: Response;
  try {
    response = await fetch("/api/verify", { method: "POST", body: form });
  } catch (err) {
    throw new Error(
      err instanceof Error ? `网络请求失败：${err.message}` : "网络请求失败",
    );
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new Error(`服务端返回了无法解析的响应（HTTP ${response.status}）`);
  }

  if (
    typeof body !== "object" ||
    body === null ||
    !("ok" in body) ||
    typeof (body as { ok?: unknown }).ok !== "boolean"
  ) {
    throw new Error(`服务端返回了无法识别的错误结构（HTTP ${response.status}）`);
  }

  const parsed = body as VerifyResponse;
  if (!parsed.ok) {
    // 统一错误外形：source + error.code/message
    if (
      parsed.source === undefined ||
      typeof parsed.error?.message !== "string"
    ) {
      throw new Error(`服务端返回了无法识别的错误结构（HTTP ${response.status}）`);
    }
    return parsed as ApiError;
  }
  return parsed;
}
