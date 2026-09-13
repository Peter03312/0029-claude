"""导入契约：解析与校验期望清单 / 实扫两个 JSON。

任一违约都会抛出 :class:`ContractError`，其中 ``source`` 标明违约来源
（``expected`` / ``actual``），API 层据此把错误归到对应导入区。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

MAX_ITEMS = 400


@dataclass(frozen=True)
class ExpectedItem:
    """期望清单中的一项：槽位号与帖标。"""

    slot: int
    mark: str


class ContractError(ValueError):
    """输入文件解析失败或违反契约。

    ``source`` 取 ``expected`` 或 ``actual``，用于在对应导入区报错。
    """

    def __init__(self, source: str, code: str, message: str) -> None:
        super().__init__(message)
        self.source = source
        self.code = code
        self.message = message


def _decode_json(source: str, raw: bytes) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError(source, "not_utf8", "文件不是合法的 UTF-8 文本") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ContractError(
            source,
            "invalid_json",
            f"JSON 解析失败（第 {exc.lineno} 行第 {exc.colno} 列）：{exc.msg}",
        ) from exc
    except RecursionError as exc:
        # 深度嵌套（约上千层）会在 json 的 C/纯 Python 解码器里耗尽递归栈。
        # 这属于文件本身问题，必须归入对应导入区，而不是让请求 500。
        raise ContractError(
            source,
            "nesting_too_deep",
            "JSON 嵌套层数过深，无法解析（应为对象数组或字符串数组，请勿嵌套）",
        ) from exc


def parse_expected(raw: bytes) -> list[ExpectedItem]:
    """校验期望清单：对象数组，每项仅含整数 slot 与非空字符串 mark。

    长度为 n 时，第 i 项（从 1 起）的 slot 必须恰为 i；重复、跳号或
    超出 1..n 一律非法。整次校验失败即抛 :class:`ContractError`。
    """
    data = _decode_json("expected", raw)

    if not isinstance(data, list):
        raise ContractError("expected", "not_array", "期望清单顶层必须是数组")

    n = len(data)
    if n > MAX_ITEMS:
        raise ContractError(
            "expected", "too_many_items", f"期望清单最多 {MAX_ITEMS} 项，当前 {n} 项"
        )

    allowed = {"slot", "mark"}
    for index, entry in enumerate(data, start=1):
        where = f"第 {index} 项"
        if not isinstance(entry, dict):
            raise ContractError("expected", "entry_not_object", f"{where}不是对象")
        extra = set(entry) - allowed
        if extra:
            raise ContractError(
                "expected",
                "extra_field",
                f"{where}含非法字段 {sorted(extra)}，每项仅允许 slot 与 mark",
            )
        if "slot" not in entry:
            raise ContractError("expected", "missing_slot", f"{where}缺少 slot 字段")
        if "mark" not in entry:
            raise ContractError("expected", "missing_mark", f"{where}缺少 mark 字段")

        slot = entry["slot"]
        # bool 是 int 的子类，必须显式排除
        if isinstance(slot, bool) or not isinstance(slot, int):
            raise ContractError(
                "expected", "slot_not_integer", f"{where}的 slot 必须是整数"
            )
        mark = entry["mark"]
        if not isinstance(mark, str):
            raise ContractError(
                "expected", "mark_not_string", f"{where}的 mark 必须是字符串"
            )
        if mark == "":
            raise ContractError(
                "expected", "mark_empty", f"{where}的 mark 不能为空字符串"
            )
        if slot < 1 or slot > n:
            raise ContractError(
                "expected",
                "slot_out_of_range",
                f"{where}的 slot={slot} 超出范围 1..{n}",
            )
        if slot != index:
            raise ContractError(
                "expected",
                "slot_not_aligned",
                f"{where}的 slot 必须等于 {index}，实际为 {slot}（存在重复或跳号）",
            )

    return [ExpectedItem(slot=i, mark=entry["mark"]) for i, entry in enumerate(data, 1)]


def parse_actual(raw: bytes) -> list[str]:
    """校验实扫：书芯自上而下的非空字符串数组。"""
    data = _decode_json("actual", raw)

    if not isinstance(data, list):
        raise ContractError("actual", "not_array", "实扫顶层必须是数组")

    if len(data) > MAX_ITEMS:
        raise ContractError(
            "actual", "too_many_items", f"实扫最多 {MAX_ITEMS} 项，当前 {len(data)} 项"
        )

    for index, entry in enumerate(data, start=1):
        if not isinstance(entry, str):
            raise ContractError(
                "actual", "entry_not_string", f"第 {index} 项必须是字符串"
            )
        if entry == "":
            raise ContractError(
                "actual", "entry_empty", f"第 {index} 项不能为空字符串"
            )

    return list(data)
