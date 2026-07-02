import asyncio
import json

import pytest

from app.main import app
from app.services.preset_service import STORE_PATH


@pytest.fixture(autouse=True)
def _restore_preset_store():
    original = STORE_PATH.read_bytes()
    yield
    STORE_PATH.write_bytes(original)


def request(method, path, json_body=None, headers=None):
    body = b"" if json_body is None else json.dumps(json_body).encode("utf-8")
    header_list = [(b"content-type", b"application/json")]
    if headers:
        for key, value in headers.items():
            header_list.append((key.lower().encode("latin1"), value.encode("latin1")))
    messages = []

    async def run_app():
        sent_request = False
        response_done = asyncio.Event()

        async def receive():
            nonlocal sent_request
            if not sent_request:
                sent_request = True
                return {"type": "http.request", "body": body, "more_body": False}
            await response_done.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            messages.append(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                response_done.set()

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("utf-8"),
            "query_string": b"",
            "headers": header_list,
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }
        await app(scope, receive, send)

    asyncio.run(run_app())

    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    payload = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    body_json = json.loads(payload.decode("utf-8")) if payload else None
    return status, body_json


def _as_user(user):
    return {"X-User": user} if user else None


def json_request(method, path, json_body=None, user=None):
    return request(method, path, json_body, headers=_as_user(user))


def _sample_criteria(fab_step="CR860200"):
    return {
        "fab": {
            "products": ["KCAI"],
            "step_conditions": [
                {
                    "fab_step": fab_step,
                    "date_range": {"start": "2026-01-01", "end": "2026-06-19"},
                    "filter_expression": "",
                }
            ],
            "primary_step": fab_step,
        },
        "eds": None,
        "chart": None,
    }


# ---------------------------------------------------------------------------
# 시드 트리
# ---------------------------------------------------------------------------


def test_preset_tree_returns_seeded_folders_and_presets():
    status, body = json_request("GET", "/api/preset-tree")
    assert status == 200
    folder_names = {f["name"] for f in body["folders"]}
    assert {"Ch.Hole", "WLCUT"} <= folder_names
    ch_hole = next(f for f in body["folders"] if f["name"] == "Ch.Hole")
    preset_names = {p["name"] for p in ch_hole["presets"]}
    assert {"Mask", "ETCH"} <= preset_names
    etch = next(p for p in ch_hole["presets"] if p["name"] == "ETCH")
    assert etch["scope"] == "shared"
    assert etch["latest_rev"] == 1
    assert len(etch["revisions"]) == 2


# ---------------------------------------------------------------------------
# 폴더
# ---------------------------------------------------------------------------


def test_folder_create_duplicate_and_delete_with_children_conflict():
    status, folder = json_request("POST", "/api/preset-folders", {"name": "TestModule"})
    assert status == 200

    status, _ = json_request("POST", "/api/preset-folders", {"name": "TestModule"})
    assert status == 409

    status, preset = json_request(
        "POST",
        "/api/presets",
        {"folder_id": folder["id"], "name": "Cond", "scope": "personal", "note": "", "criteria": _sample_criteria()},
        user="me",
    )
    assert status == 200

    status, _ = json_request("DELETE", f"/api/preset-folders/{folder['id']}")
    assert status == 409

    status, _ = json_request("DELETE", f"/api/presets/{preset['id']}", user="me")
    assert status == 200
    status, _ = json_request("DELETE", f"/api/preset-folders/{folder['id']}")
    assert status == 200


# ---------------------------------------------------------------------------
# Preset 생성 -> rev 추가 -> 공유 전환 -> 타 사용자 403 -> 복제 -> 재로드 유지
# ---------------------------------------------------------------------------


def test_preset_lifecycle_revision_share_forbidden_and_duplicate_persists():
    status, preset = json_request(
        "POST",
        "/api/presets",
        {
            "folder_id": "PF001",
            "name": "Lifecycle Test",
            "scope": "personal",
            "note": "초기",
            "criteria": _sample_criteria(),
        },
        user="me",
    )
    assert status == 200
    assert preset["owner"] == "me"
    assert preset["revisions"][0]["rev"] == 0
    preset_id = preset["id"]

    status, preset = json_request(
        "POST",
        f"/api/presets/{preset_id}/revisions",
        {"note": "rev1 변경", "criteria": _sample_criteria(fab_step="CR380020")},
        user="me",
    )
    assert status == 200
    assert [rev["rev"] for rev in preset["revisions"]] == [0, 1]

    status, preset = json_request("PATCH", f"/api/presets/{preset_id}", {"scope": "shared"}, user="me")
    assert status == 200
    assert preset["scope"] == "shared"

    status, _ = json_request(
        "POST",
        f"/api/presets/{preset_id}/revisions",
        {"note": "타인 시도", "criteria": _sample_criteria()},
        user="other",
    )
    assert status == 403

    status, duplicate = json_request(
        "POST",
        f"/api/presets/{preset_id}/duplicate",
        {"name": "Other's Copy"},
        user="other",
    )
    assert status == 200
    assert duplicate["owner"] == "other"
    assert duplicate["revisions"][0]["rev"] == 0
    assert duplicate["revisions"][0]["criteria"]["fab"]["step_conditions"][0]["fab_step"] == "CR380020"

    # 파일 재로드(다시 조회)해도 변경 사항이 유지되는지 확인
    status, tree = json_request("GET", "/api/preset-tree")
    assert status == 200
    all_presets = [p for f in tree["folders"] for p in f["presets"]]
    reloaded = next(p for p in all_presets if p["id"] == preset_id)
    assert reloaded["scope"] == "shared"
    assert reloaded["latest_rev"] == 1
    reloaded_dup = next(p for p in all_presets if p["id"] == duplicate["id"])
    assert reloaded_dup["owner"] == "other"


def test_add_revision_to_missing_preset_returns_404():
    status, _ = json_request(
        "POST", "/api/presets/PS999/revisions", {"note": "", "criteria": _sample_criteria()}, user="me"
    )
    assert status == 404


# ---------------------------------------------------------------------------
# 커스텀 EDS 아이템: 생성 -> 중복409 -> 타인삭제403 -> 재로드 유지 -> 삭제
# ---------------------------------------------------------------------------


def test_custom_eds_item_create_duplicate_conflict_forbidden_delete_and_persistence():
    payload = {
        "name": "H2H_TEST_ITEM",
        "category": "BIN",
        "terms": [{"item": "BIN_014", "sign": 1}, {"item": "BIN_208", "sign": -1}],
    }
    status, item = json_request("POST", "/api/custom-eds-items", payload, user="me")
    assert status == 200
    assert item["owner"] == "me"

    status, _ = json_request("POST", "/api/custom-eds-items", payload, user="me")
    assert status == 409

    # 서버 재기동 없이도(파일 재조회) 유지되는지 확인
    status, items = json_request("GET", "/api/custom-eds-items")
    assert status == 200
    assert any(i["name"] == "H2H_TEST_ITEM" for i in items)

    status, _ = json_request("DELETE", "/api/custom-eds-items/H2H_TEST_ITEM", user="other")
    assert status == 403

    status, _ = json_request("DELETE", "/api/custom-eds-items/H2H_TEST_ITEM", user="me")
    assert status == 200

    status, items = json_request("GET", "/api/custom-eds-items")
    assert status == 200
    assert not any(i["name"] == "H2H_TEST_ITEM" for i in items)


def test_seed_custom_eds_item_present():
    status, items = json_request("GET", "/api/custom-eds-items")
    assert status == 200
    seed = next(i for i in items if i["name"] == "H2H_SUM")
    assert seed["category"] == "BIN"
    assert seed["owner"] == "me"
    assert len(seed["terms"]) == 3
