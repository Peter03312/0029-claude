"""配帖对齐：以插入、删除、替换各代价 1 做动态规划。

* 相同帖标必须匹配（代价 0）。
* 其余同成本路径从末端回溯时，依次优先：替换 → 缺失（删除期望项）
  → 额外（插入实扫项）。
"""

from __future__ import annotations

from dataclasses import dataclass

# 行状态：match 一致 / replace 错帖 / missing 漏帖 / extra 多帖
MATCH = "match"
REPLACE = "replace"
MISSING = "missing"
EXTRA = "extra"


@dataclass(frozen=True)
class AlignRow:
    slot: int | None  # 期望槽位，1 起；额外行为 None
    scan_index: int | None  # 实扫序号，1 起；缺失行为 None
    expected_mark: str | None
    actual_mark: str | None
    status: str
    cost: int  # 该行代价：一致 0，替换/缺失/额外 1


@dataclass(frozen=True)
class AlignResult:
    rows: list[AlignRow]
    cost: int


def align(expected: list[str], actual: list[str]) -> AlignResult:
    """返回按书芯自上而下顺序的对齐行与总代价。"""
    n, m = len(expected), len(actual)

    # dp[i][j]：expected[i:] 与 actual[j:] 的最小编辑代价
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][m] = n - i
    for j in range(m + 1):
        dp[n][j] = m - j

    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            if expected[i] == actual[j]:
                # 相同项必须匹配
                dp[i][j] = dp[i + 1][j + 1]
            else:
                replace_cost = 1 + dp[i + 1][j + 1]
                delete_cost = 1 + dp[i + 1][j]  # 缺失：期望项被删除
                insert_cost = 1 + dp[i][j + 1]  # 额外：插入实扫项
                dp[i][j] = min(replace_cost, delete_cost, insert_cost)

    # 从末端构造的 DP 表在 (0,0) 回溯，逐步得到自上而下的对齐行；
    # 同成本时依次优先：替换 → 缺失 → 额外
    rows: list[AlignRow] = []
    i, j = 0, 0
    while i < n and j < m:
        if expected[i] == actual[j]:
            rows.append(
                AlignRow(i + 1, j + 1, expected[i], actual[j], MATCH, 0)
            )
            i += 1
            j += 1
            continue
        if dp[i][j] == 1 + dp[i + 1][j + 1]:
            # 同成本路径优先替换
            rows.append(
                AlignRow(i + 1, j + 1, expected[i], actual[j], REPLACE, 1)
            )
            i += 1
            j += 1
        elif dp[i][j] == 1 + dp[i + 1][j]:
            rows.append(
                AlignRow(i + 1, None, expected[i], None, MISSING, 1)
            )
            i += 1
        else:
            rows.append(
                AlignRow(None, j + 1, None, actual[j], EXTRA, 1)
            )
            j += 1

    while i < n:
        rows.append(AlignRow(i + 1, None, expected[i], None, MISSING, 1))
        i += 1
    while j < m:
        rows.append(AlignRow(None, j + 1, None, actual[j], EXTRA, 1))
        j += 1

    return AlignResult(rows=rows, cost=dp[0][0])
