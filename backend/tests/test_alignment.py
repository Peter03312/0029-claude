"""对齐算法单测：确定性、相同必匹配、同成本优先级 替换 > 缺失 > 额外。"""

import random

from app.alignment import EXTRA, MATCH, MISSING, REPLACE, align


def statuses(rows):
    return [(r.slot, r.scan_index, r.status, r.expected_mark, r.actual_mark) for r in rows]


def test_perfect_match_is_cost_zero():
    result = align(["A", "B", "C"], ["A", "B", "C"])
    assert result.cost == 0
    assert [r.status for r in result.rows] == [MATCH, MATCH, MATCH]
    assert [(r.slot, r.scan_index) for r in result.rows] == [(1, 1), (2, 2), (3, 3)]


def test_duplicate_mark_actual_extra_pinned_to_top_of_run():
    # 实扫在书芯上方多扫了一件重复帖 A（A,B,C → A,A,B,C）。
    # 从末端回溯把相同项锚在重复段下边界，多出的 A 必须定位到实扫 1 号位
    # （重复段上边界），而不是 2 号位；若落在 2 号位，拆书位置会下移一件。
    result = align(["A", "B", "C"], ["A", "A", "B", "C"])
    assert result.cost == 1
    assert statuses(result.rows) == [
        (None, 1, EXTRA, None, "A"),
        (1, 2, MATCH, "A", "A"),
        (2, 3, MATCH, "B", "B"),
        (3, 4, MATCH, "C", "C"),
    ]


def test_duplicate_mark_expected_missing_pinned_to_top_of_run():
    # 期望清单里 B 重复（slot 2、3），实扫漏掉一个 B（A,B,D）。
    # 末端回溯从段的下边界锚起，缺失落在槽位 2（重复段上边界），
    # 不能把首个异常压到槽位 3 造成拆书位置偏移。
    result = align(["A", "B", "B", "D"], ["A", "B", "D"])
    assert result.cost == 1
    assert statuses(result.rows) == [
        (1, 1, MATCH, "A", "A"),
        (2, None, MISSING, "B", None),
        (3, 2, MATCH, "B", "B"),
        (4, 3, MATCH, "D", "D"),
    ]


def test_long_duplicate_run_does_not_shift_first_anomaly():
    # 长重复段：期望 4 个 B、实扫 5 个 B。首异常不得被推到段的下边界
    # （旧实现会落在实扫 5 号位），应位于上边界实扫 2 号位，偏移不随段长放大。
    result = align(["A", "B", "B", "B", "C"], ["A", "B", "B", "B", "B", "C"])
    assert result.cost == 1
    first = next(r for r in result.rows if r.status != MATCH)
    assert first.status == EXTRA and first.scan_index == 2
    # 末端的 C 必须锚在最后一件实扫上
    tail = result.rows[-1]
    assert tail.status == MATCH and tail.slot == 5 and tail.scan_index == 6

    # 反向：期望 4 个 B、实扫 3 个 B，缺失落在槽位 2
    result2 = align(["A", "B", "B", "B", "C"], ["A", "B", "B", "C"])
    assert result2.cost == 1
    first2 = next(r for r in result2.rows if r.status != MATCH)
    assert first2.status == MISSING and first2.slot == 2


def test_wrong_signature_plus_trailing_extra():
    # 同次错帖：B 处扫成 X；末尾又多一帖 Z
    result = align(["A", "B", "C"], ["A", "X", "C", "Z"])
    assert result.cost == 2
    assert statuses(result.rows) == [
        (1, 1, MATCH, "A", "A"),
        (2, 2, REPLACE, "B", "X"),
        (3, 3, MATCH, "C", "C"),
        (None, 4, EXTRA, None, "Z"),
    ]


def test_equal_cost_prefers_replace_over_missing_extra():
    # X vs B：替换代价 1，缺失+额外代价 2，此处替换更优
    result = align(["A", "B"], ["A", "X"])
    assert [r.status for r in result.rows] == [MATCH, REPLACE]

    # 真正同成本：["X","C"] 对 ["A","B","C"]
    # 末端回溯先锚定末端相同的 C；在 (2,1) 处替换 B->X 与 缺B/多X 同价，
    # 按 替换 > 缺失 > 额外 的顺序选替换：得到 缺A + 换B + 配C。
    result = align(["A", "B", "C"], ["X", "C"])
    assert result.cost == 2
    assert [r.status for r in result.rows] == [MISSING, REPLACE, MATCH]
    assert result.rows[0].expected_mark == "A" and result.rows[0].actual_mark is None
    assert result.rows[1].expected_mark == "B" and result.rows[1].actual_mark == "X"


def test_equal_cost_prefers_missing_over_extra():
    # ["A","B","C"] 对 ["C"]：末端 C 强制匹配，A、B 只能缺失。
    result = align(["A", "B", "C"], ["C"])
    assert result.cost == 2
    assert [r.status for r in result.rows] == [MISSING, MISSING, MATCH]

    # 重复段内的缺失优先于额外：["A","C","C"] 对 ["C"]，
    # 末端回溯把保留的 C 锚在槽位 3（下边界），缺失暴露在上方槽位 2，
    # 不会选成 额外C + 缺失A,C 的等价路径。
    result = align(["A", "C", "C"], ["C"])
    assert result.cost == 2
    assert statuses(result.rows) == [
        (1, None, MISSING, "A", None),
        (2, None, MISSING, "C", None),
        (3, 1, MATCH, "C", "C"),
    ]


def test_same_mark_must_match_even_if_shift_is_equal_cost():
    # 若 A 不与 A 匹配而错位，代价会更大或相等；强制匹配不得被破坏。
    # ["A","B"] vs ["B"]：B 必须匹配 B，A 缺失（而非 A->B 替换 + B 缺失）
    result = align(["A", "B"], ["B"])
    assert result.cost == 1
    assert statuses(result.rows) == [
        (1, None, MISSING, "A", None),
        (2, 1, MATCH, "B", "B"),
    ]


def test_codepoint_exact_comparison():
    # 全角Ａ(U+FF21) 与半角 A(U+0041) 是不同码点，算替换不是一致
    result = align(["Ａ"], ["A"])
    assert result.cost == 1
    assert result.rows[0].status == REPLACE

    # 末尾空白不做任何修剪
    result2 = align(["A"], ["A "])
    assert result2.rows[0].status == REPLACE

    # 预组合 é(U+00E9) 与分解形式 e+U+0301 码点不同，即便显示相同也必须替换
    result3 = align(["\u00e9"], ["e\u0301"])
    assert result3.rows[0].status == REPLACE
    assert result3.rows[0].expected_mark != result3.rows[0].actual_mark


def test_empty_sides():
    result = align([], ["X", "Y"])
    assert result.cost == 2
    assert [r.status for r in result.rows] == [EXTRA, EXTRA]
    assert [r.scan_index for r in result.rows] == [1, 2]

    result2 = align(["P", "Q"], [])
    assert result2.cost == 2
    assert [r.status for r in result2.rows] == [MISSING, MISSING]
    assert [r.slot for r in result2.rows] == [1, 2]


def test_result_is_deterministic():
    rng = random.Random(20260913)
    alphabet = ["A", "B", "C", "D", "E"]
    for _ in range(60):
        expected = [rng.choice(alphabet) for _ in range(rng.randrange(0, 14))]
        actual = [rng.choice(alphabet) for _ in range(rng.randrange(0, 14))]
        first = align(expected, actual)
        for _ in range(3):
            again = align(expected, actual)
            assert statuses(again.rows) == statuses(first.rows)
            assert again.cost == first.cost


def test_edit_cost_matches_independent_levenshtein():
    """与独立实现的经典 Levenshtein 距离交叉验证总代价。"""

    def lev(a, b):
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            cur = [i]
            for j, cb in enumerate(b, 1):
                cur.append(
                    min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
                )
            prev = cur
        return prev[-1]

    rng = random.Random(4242)
    for _ in range(100):
        expected = [rng.choice("XY") for _ in range(rng.randrange(0, 10))]
        actual = [rng.choice("XY") for _ in range(rng.randrange(0, 10))]
        result = align(expected, actual)
        assert result.cost == lev(expected, actual)
        assert sum(r.cost for r in result.rows) == result.cost
        # 行内序列一致性：scan_index / slot 在各自维度上保持 1 起递增或 None
        scan_seen = [r.scan_index for r in result.rows if r.scan_index is not None]
        slot_seen = [r.slot for r in result.rows if r.slot is not None]
        assert scan_seen == list(range(1, len(scan_seen) + 1))
        assert slot_seen == list(range(1, len(slot_seen) + 1))


def test_end_trace_rows_match_independent_reversed_walker():
    """用结构独立的实现交叉验证「末端回溯 + 同成本 替换>缺失>额外」的行序列。

    参考实现把两序列整体反转，在后缀代价表上做正向贪心（等价于原序列上的
    末端回溯），再把行序与下标映射回原序列。
    """

    def reference(expected, actual):
        e, a = expected[::-1], actual[::-1]
        n, m = len(e), len(a)
        d = [[0] * (m + 1) for _ in range(n + 1)]
        for i in range(n + 1):
            d[i][m] = n - i
        for j in range(m + 1):
            d[n][j] = m - j
        for i in range(n - 1, -1, -1):
            for j in range(m - 1, -1, -1):
                if e[i] == a[j]:
                    d[i][j] = d[i + 1][j + 1]
                else:
                    d[i][j] = 1 + min(d[i + 1][j + 1], d[i + 1][j], d[i][j + 1])

        bottom_up: list[tuple] = []
        i = j = 0
        while i < n and j < m:
            if e[i] == a[j]:
                bottom_up.append((MATCH, n - i, m - j, e[i], a[j]))
                i += 1
                j += 1
            elif d[i][j] == 1 + d[i + 1][j + 1]:
                bottom_up.append((REPLACE, n - i, m - j, e[i], a[j]))
                i += 1
                j += 1
            elif d[i][j] == 1 + d[i + 1][j]:
                bottom_up.append((MISSING, n - i, None, e[i], None))
                i += 1
            else:
                bottom_up.append((EXTRA, None, m - j, None, a[j]))
                j += 1
        while i < n:
            bottom_up.append((MISSING, n - i, None, e[i], None))
            i += 1
        while j < m:
            bottom_up.append((EXTRA, None, m - j, None, a[j]))
            j += 1

        # 参考元组按 (status, slot, scan, expected_mark, actual_mark) 组织，
        # 先翻回自上而下，再统一成被测函数的 (slot, scan, status, emark, amark)。
        return [
            (slot, scan, status, emark, amark)
            for status, slot, scan, emark, amark in reversed(bottom_up)
        ]

    structured = [
        (["A", "B", "C"], ["A", "A", "B", "C"]),
        (["A", "B", "B", "D"], ["A", "B", "D"]),
        (["A", "B", "B", "B", "C"], ["A", "B", "B", "B", "B", "C"]),
        (["A", "B", "C"], ["X", "C"]),
        (["A", "B", "C"], ["B", "A", "B", "C"]),
    ]
    rng = random.Random(7)
    random_cases = [
        ([rng.choice("ABC") for _ in range(rng.randrange(0, 12))],
         [rng.choice("ABC") for _ in range(rng.randrange(0, 12))])
        for _ in range(150)
    ]
    for expected, actual in structured + random_cases:
        result = align(expected, actual)
        assert statuses(result.rows) == reference(expected, actual), (expected, actual)


def test_row_cost_and_marks_per_status():
    result = align(["A", "B"], ["A", "X"])
    match_row, replace_row = result.rows
    assert match_row.cost == 0 and replace_row.cost == 1
    assert replace_row.expected_mark == "B" and replace_row.actual_mark == "X"
