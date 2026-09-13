"""配帖对齐：以插入、删除、替换各代价 1 做动态规划。

填表方向为标准前缀 DP（自左向右、自上而下）：

* ``dp[i][j]`` 是期望前 i 项与实扫前 j 项的最小编辑代价；
* 相同帖标必须匹配（沿对角代价 0，且必为唯一最优走法）；
* 回溯从表末端 ``(n, m)`` 开始沿前驱回到 ``(0, 0)``，逆序收集后翻转为
  书芯自上而下的行顺序。

同一格若多条路径代价相同，按规格规定的顺序选择前驱：

1. 对角：替换（错帖）；
2. 向上：删除期望项（漏帖 / 缺失）；
3. 向左：插入实扫项（多帖 / 额外）。

从末端回溯的关键效果：当帖标段出现重复（无论期望清单里的重复标，还是
实扫重复扫入），相等匹配从段的下边界锚起，多/漏的一份暴露在重复段的
**上边界**，首个异常指向更靠近书芯上方的实际拆书位，而不会被整段重复
推到段的下端。
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

    # 前缀 DP：dp[i][j] = expected[:i] 与 actual[:j] 的最小编辑代价
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if expected[i - 1] == actual[j - 1]:
                # 相同项必须匹配：对角代价 0，必为最优
                dp[i][j] = dp[i - 1][j - 1]
            else:
                replace_cost = dp[i - 1][j - 1] + 1
                missing_cost = dp[i - 1][j] + 1  # 删除期望项：漏帖
                extra_cost = dp[i][j - 1] + 1    # 插入实扫项：多帖
                dp[i][j] = min(replace_cost, missing_cost, extra_cost)

    # 从末端 (n, m) 沿前驱回溯；逆序记录行，最后翻转成自上而下。
    reversed_rows: list[AlignRow] = []
    i, j = n, m
    while i > 0 and j > 0:
        if expected[i - 1] == actual[j - 1]:
            reversed_rows.append(
                AlignRow(i, j, expected[i - 1], actual[j - 1], MATCH, 0)
            )
            i -= 1
            j -= 1
            continue
        if dp[i][j] == dp[i - 1][j - 1] + 1:
            # 同成本路径优先替换
            reversed_rows.append(
                AlignRow(i, j, expected[i - 1], actual[j - 1], REPLACE, 1)
            )
            i -= 1
            j -= 1
        elif dp[i][j] == dp[i - 1][j] + 1:
            # 其次缺失（漏帖）
            reversed_rows.append(
                AlignRow(i, None, expected[i - 1], None, MISSING, 1)
            )
            i -= 1
        else:
            # 最后额外（多帖）
            reversed_rows.append(
                AlignRow(None, j, None, actual[j - 1], EXTRA, 1)
            )
            j -= 1

    while i > 0:
        reversed_rows.append(AlignRow(i, None, expected[i - 1], None, MISSING, 1))
        i -= 1
    while j > 0:
        reversed_rows.append(AlignRow(None, j, None, actual[j - 1], EXTRA, 1))
        j -= 1

    rows = list(reversed(reversed_rows))
    return AlignResult(rows=rows, cost=dp[n][m])
