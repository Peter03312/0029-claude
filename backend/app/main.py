"""锁线前配帖核验站 API。

POST /api/verify 以 multipart 上传两个 JSON 文件：

* expected_file：期望清单（对象数组，slot+mark，slot 必须自 1 严格递增对齐）
* actual_file：实扫书芯帖标（自上而下的非空字符串数组）

解析或契约失败返回 422，错误体带 source（expected/actual），由前端归入
对应导入区；整次拒绝，不产生任何结果行或报告。
"""

from __future__ import annotations

from fastapi import FastAPI, File, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .alignment import align
from .contract import ContractError, parse_actual, parse_expected
from .report import build_report

app = FastAPI(title="锁线前配帖核验站", version="1.0.0")


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_, exc: RequestValidationError) -> JSONResponse:
    # multipart 字段缺失等框架级 422：统一成与契约违约相同的错误外形，
    # 但不归属任一导入区（source=request），调用方需修正请求本身。
    return JSONResponse(
        status_code=422,
        content={
            "ok": False,
            "source": "request",
            "error": {
                "code": "malformed_request",
                "message": "请求缺少 expected_file 或 actual_file 上传字段",
                "detail": exc.errors(),
            },
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/verify")
async def verify(
    expected_file: UploadFile = File(...),
    actual_file: UploadFile = File(...),
) -> JSONResponse:
    # 任一文件违约都在此捕获并整体拒绝，绝不返回部分结果。
    try:
        expected = parse_expected(await expected_file.read())
        actual = parse_actual(await actual_file.read())
    except ContractError as exc:
        return JSONResponse(
            status_code=422,
            content={
                "ok": False,
                "source": exc.source,
                "error": {"code": exc.code, "message": exc.message},
            },
        )

    result = align([item.mark for item in expected], actual)
    report = build_report(result, len(expected), len(actual))
    return JSONResponse(status_code=200, content={"ok": True, "report": report})
