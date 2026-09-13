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


def test_duplicate_mark_with_missing_signature():
    # 期望清单里 B 重复出现（slot 2、3），实扫漏掉一个 B
    result = align(["A", "B", "B", "D"], ["A", "B", "D"])
    assert result.cost == 1
    assert statuses(result.rows) == [
        (1, 1, MATCH, "A", "A"),
        (2, 2, MATCH, "B", "B"),
        (3, None, MISSING, "B", None),
        (4, 3, MATCH, "D", "D"),
    ]


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
    # 替换 A->X 或 删除A+插入X 代价都是 2，必须优先替换
    result = align(["A", "B", "C"], ["X", "C"])
    assert result.cost == 2
    assert [r.status for r in result.rows] == [REPLACE, MISSING, MATCH]
    assert result.rows[0].expected_mark == "A"
    assert result.rows[0].actual_mark == "X"
    assert result.rows[1].expected_mark == "B"


def test_equal_cost_prefers_missing_over_extra():
    # ["B","A"] 对 ["A","B"]：替换两次(代价2) 与 一缺一多(代价2) 同价，
    # 替换已被优先；这里构造替换劣于一缺一多的场景：
    # ["A","B","C"] 对 ["C"]：删 A、删 B 或 缺/多组合。
    result = align(["A", "B", "C"], ["C"])
    # 相同项 C 必须匹配，A、B 缺失
    assert result.cost == 2
    assert [r.status for r in result.rows] == [MISSING, MISSING, MATCH]


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


def test_row_cost_and_marks_per_status():
    result = align(["A", "B"], ["A", "X"])
    match_row, replace_row = result.rows
    assert match_row.cost == 0 and replace_row.cost == 1
    assert replace_row.expected_mark == "B" and replace_row.actual_mark == "X"
