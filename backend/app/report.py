"""核验报告组装：把对齐结果整理为可序列化、可下载的确定性 JSON。"""

from __future__ import annotations

from typing import Any

from .alignment import EXTRA, MATCH, MISSING, REPLACE, AlignResult


def build_report(result: AlignResult, expected_count: int, actual_count: int) -> dict[str, Any]:
    """生成结构固定、不含时间戳等随机量的报告对象。"""
    counts = {MATCH: 0, REPLACE: 0, MISSING: 0, EXTRA: 0}
    rows_payload: list[dict[str, Any]] = []

    for row in result.rows:
        counts[row.status] += 1
        rows_payload.append(
            {
                "slot": row.slot,
                "scan_index": row.scan_index,
                "expected_mark": row.expected_mark,
                "actual_mark": row.actual_mark,
                "status": row.status,
            }
        )

    first_anomaly = next(
        (
            {
                "row_index": idx,
                "slot": row.slot,
                "scan_index": row.scan_index,
                "status": row.status,
                "expected_mark": row.expected_mark,
                "actual_mark": row.actual_mark,
            }
            for idx, row in enumerate(result.rows)
            if row.status != MATCH
        ),
        None,
    )

    return {
        "summary": {
            "expected_count": expected_count,
            "actual_count": actual_count,
            "match": counts[MATCH],
            "replace": counts[REPLACE],
            "missing": counts[MISSING],
            "extra": counts[EXTRA],
            "anomaly": counts[REPLACE] + counts[MISSING] + counts[EXTRA],
            "edit_cost": result.cost,
            "passed": result.cost == 0,
        },
        "first_anomaly": first_anomaly,
        "rows": rows_payload,
    }
