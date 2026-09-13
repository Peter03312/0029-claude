import type { ApiError, VerifyResponse } from "./types";

/**
 * 上传两个 JSON 文件到 /api/verify。
 *
 * 422（解析失败 / 契约违约）时正常返回结构化 ApiError，由页面把错误
 * 归到对应导入区；网络层故障抛出异常，由页面作为通用错误提示。
 * 违约响应永远不携带报告。
 */
export async function verifyFiles(
  expected: File,
  actual: File,
): Promise<VerifyResponse> {
  const form = new FormData();
  form.append("expected_file", expected);
  form.append("actual_file", actual);

  const response = await fetch("/api/verify", { method: "POST", body: form });
  const body = (await response.json()) as VerifyResponse;

  if (response.status === 422 && !("ok" in body)) {
    // 理论上不会发生（后端始终返回 ok 字段），防御性处理。
    throw new Error("服务端返回了无法识别的错误结构");
  }
  if (!body.ok) {
    return body as ApiError;
  }
  return body;
}
