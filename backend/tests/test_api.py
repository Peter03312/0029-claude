"""API 端到端验收：

1. 完全一致 → 通过
2. 重复标漏帖 → 确定性行，异常可定位
3. 同次错帖 + 末尾多帖
4. 坏文件 / 违约 → 整单拒绝，无 rows、无报告，错误归入对应导入区
"""

import json

from tests.conftest import expected_json, post_raw, verify


def test_acceptance_perfect_match(client):
    resp = verify(client, expected_json(["甲", "乙", "丙"]), ["甲", "乙", "丙"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    report = body["report"]
    assert report["summary"] == {
        "expected_count": 3,
        "actual_count": 3,
        "match": 3,
        "replace": 0,
        "missing": 0,
        "extra": 0,
        "anomaly": 0,
        "edit_cost": 0,
        "passed": True,
    }
    assert report["first_anomaly"] is None
    assert [r["status"] for r in report["rows"]] == ["match"] * 3
    # 槽位与实扫序号
    assert [(r["slot"], r["scan_index"]) for r in report["rows"]] == [
        (1, 1), (2, 2), (3, 3)
    ]


def test_acceptance_duplicate_mark_missing_signature(client):
    expected = expected_json(["A", "B", "B", "D"])
    resp = verify(client, expected, ["A", "B", "D"])
    assert resp.status_code == 200
    report = resp.json()["report"]
    s = report["summary"]
    assert s["passed"] is False and s["edit_cost"] == 1
    assert s["match"] == 3 and s["missing"] == 1
    rows = report["rows"]
    # 确定行：slot3 的重复 B 漏帖
    assert [r["status"] for r in rows] == ["match", "match", "missing", "match"]
    bad = report["first_anomaly"]
    assert bad["row_index"] == 2 and bad["slot"] == 3
    assert bad["status"] == "missing" and bad["expected_mark"] == "B"
    assert bad["scan_index"] is None
    # 可按异常筛选（前端逻辑同源：status != match）
    anomalies = [r for r in rows if r["status"] != "match"]
    assert len(anomalies) == 1


def test_acceptance_wrong_signature_and_trailing_extra(client):
    resp = verify(client, expected_json(["A", "B", "C"]), ["A", "X", "C", "Z"])
    assert resp.status_code == 200
    report = resp.json()["report"]
    s = report["summary"]
    assert s["edit_cost"] == 2 and s["replace"] == 1 and s["extra"] == 1
    rows = report["rows"]
    assert [r["status"] for r in rows] == ["match", "replace", "match", "extra"]
    first = report["first_anomaly"]
    assert first["row_index"] == 1 and first["slot"] == 2 and first["scan_index"] == 2
    assert (first["expected_mark"], first["actual_mark"]) == ("B", "X")
    # 首个异常行可拆到出错书帖：槽位 2 / 实扫第 2 件
    extra = rows[3]
    assert extra["slot"] is None and extra["scan_index"] == 4
    assert extra["actual_mark"] == "Z"


def test_report_is_deterministic_across_requests(client):
    payload = (expected_json(["A", "B", "B", "C"]), ["A", "X", "C"])
    first = verify(client, *payload).json()
    second = verify(client, *payload).json()
    assert first == second


def test_broken_json_is_rejected_entirely(client):
    resp = post_raw(client, "expected_file", "bad.json", b"[{ not json")
    assert resp.status_code == 422
    body = resp.json()
    assert body["ok"] is False and body["source"] == "expected"
    assert body["error"]["code"] == "invalid_json"
    assert "report" not in body and "rows" not in body


def test_non_utf8_is_rejected(client):
    resp = post_raw(client, "actual_file", "a.json", b"[\xff\xfe]")
    assert resp.status_code == 422
    body = resp.json()
    assert body["source"] == "actual" and body["error"]["code"] == "not_utf8"


def test_expected_slot_gap_duplicate_out_of_range_rejected(client):
    # 跳号：长度 3 但 slot 序列为 1,2,4（4 同时超出 1..3，先报越界）
    resp = verify(
        client,
        [{"slot": 1, "mark": "A"}, {"slot": 2, "mark": "B"}, {"slot": 4, "mark": "D"}],
        ["A", "B", "D"],
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "slot_out_of_range"

    # 范围内的纯跳号 1,3,3 → 第 2 项不对齐
    resp = verify(
        client,
        [
            {"slot": 1, "mark": "A"},
            {"slot": 3, "mark": "C"},
            {"slot": 3, "mark": "C2"},
        ],
        ["A", "C", "C2"],
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "slot_not_aligned"

    # 重复 slot
    resp = verify(
        client,
        [{"slot": 1, "mark": "A"}, {"slot": 1, "mark": "B"}],
        ["A", "B"],
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "slot_not_aligned"

    # 超出 1..n：slot=0
    resp = verify(client, [{"slot": 0, "mark": "A"}], ["A"])
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "slot_out_of_range"

    # 顺序错位：数组顺序即对齐顺序，[2,1] 非法
    resp = verify(
        client,
        [{"slot": 2, "mark": "B"}, {"slot": 1, "mark": "A"}],
        ["B", "A"],
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "slot_not_aligned"


def test_expected_shape_violations_rejected(client):
    # 顶层不是数组
    resp = verify(client, {"slot": 1, "mark": "A"}, ["A"])
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "not_array"

    # 多余字段
    resp = verify(client, [{"slot": 1, "mark": "A", "seq": 1}], ["A"])
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "extra_field"

    # slot 非整数 / 布尔冒充整数
    resp = verify(client, [{"slot": "1", "mark": "A"}], ["A"])
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "slot_not_integer"
    resp = verify(client, [{"slot": True, "mark": "A"}], ["A"])
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "slot_not_integer"

    # 空 mark
    resp = verify(client, [{"slot": 1, "mark": ""}], ["A"])
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "mark_empty"

    # mark 非字符串
    resp = verify(client, [{"slot": 1, "mark": 1}], ["A"])
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "mark_not_string"


def test_actual_shape_violations_rejected(client):
    ok = expected_json(["A", "B"])

    resp = verify(client, ok, {"0": "A"})
    assert resp.status_code == 422
    assert resp.json()["source"] == "actual" and resp.json()["error"]["code"] == "not_array"

    resp = verify(client, ok, ["A", 1])
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "entry_not_string"

    resp = verify(client, ok, ["A", ""])
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "entry_empty"


def test_empty_lists_pass(client):
    resp = verify(client, [], [])
    assert resp.status_code == 200
    report = resp.json()["report"]
    assert report["summary"]["passed"] is True
    assert report["rows"] == [] and report["first_anomaly"] is None


def test_too_many_items_rejected(client):
    big_expected = expected_json([f"M{i}" for i in range(401)])
    resp = verify(client, big_expected, [])
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "too_many_items"

    resp = verify(client, [], [f"S{i}" for i in range(401)])
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "too_many_items"

    # 恰好 400 合法
    ok_expected = expected_json([f"M{i}" for i in range(1, 401)])
    ok_actual = [f"M{i}" for i in range(1, 401)]
    resp = verify(client, ok_expected, ok_actual)
    assert resp.status_code == 200
    assert resp.json()["report"]["summary"]["match"] == 400


def test_missing_upload_fields_uses_unified_error_shape(client):
    resp = client.post("/api/verify")
    assert resp.status_code == 422
    body = resp.json()
    assert body["ok"] is False and body["source"] == "request"
    assert body["error"]["code"] == "malformed_request"
    assert "report" not in body


def test_codepoint_exactness_end_to_end(client):
    # JSON 解码后的码点原样比较：U+00E9 vs e + U+0301
    raw_expected = json.dumps(expected_json(["\u00e9"])).encode("utf-8")
    raw_actual = json.dumps(["e\u0301"]).encode("utf-8")
    resp = client.post(
        "/api/verify",
        files=[
            ("expected_file", ("e.json", raw_expected, "application/json")),
            ("actual_file", ("a.json", raw_actual, "application/json")),
        ],
    )
    assert resp.status_code == 200
    rows = resp.json()["report"]["rows"]
    assert rows[0]["status"] == "replace"
