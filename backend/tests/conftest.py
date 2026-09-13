import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402


def expected_json(marks):
    return [{"slot": i, "mark": m} for i, m in enumerate(marks, 1)]


@pytest.fixture
def client():
    return TestClient(app)


def verify(client, expected, actual, expected_filename="expected.json", actual_filename="actual.json"):
    import json

    return client.post(
        "/api/verify",
        files=[
            ("expected_file", (expected_filename, json.dumps(expected).encode(), "application/json")),
            ("actual_file", (actual_filename, json.dumps(actual).encode(), "application/json")),
        ],
    )


def post_raw(client, field, filename, raw, other_field=None, other_raw=b"[]", other_name="other.json"):
    """上传原始字节，其余字段给一个合法空数组。"""
    files = []
    if field == "expected_file":
        files.append(("expected_file", (filename, raw, "application/json")))
        files.append(("actual_file", ("actual.json", other_raw, "application/json")))
    else:
        files.append(("expected_file", ("expected.json", other_raw, "application/json")))
        files.append(("actual_file", (filename, raw, "application/json")))
    return client.post("/api/verify", files=files)
