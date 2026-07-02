from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.models.schemas import (
    CustomEdsItemCreate,
    PresetCreate,
    PresetDuplicate,
    PresetPatch,
    PresetRevisionCreate,
)
from app.services.mock_data_service import metadata as mock_metadata

STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "preset_store.json"


def _load() -> dict[str, Any]:
    with STORE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict[str, Any]) -> None:
    tmp_path = STORE_PATH.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, STORE_PATH)


def _next_id(data: dict[str, Any], kind: str, prefix: str) -> str:
    data["counters"][kind] += 1
    return f"{prefix}{data['counters'][kind]:03d}"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _find_folder(data: dict[str, Any], folder_id: str) -> dict[str, Any]:
    for folder in data["folders"]:
        if folder["id"] == folder_id:
            return folder
    raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다")


def _find_preset(data: dict[str, Any], preset_id: str) -> dict[str, Any]:
    for preset in data["presets"]:
        if preset["id"] == preset_id:
            return preset
    raise HTTPException(status_code=404, detail="조건을 찾을 수 없습니다")


def _require_owner(preset: dict[str, Any], user: str) -> None:
    if preset["owner"] != user:
        raise HTTPException(status_code=403, detail="소유자만 수행할 수 있습니다")


# ---------------------------------------------------------------------------
# 폴더
# ---------------------------------------------------------------------------


def create_folder(name: str) -> dict[str, Any]:
    data = _load()
    if any(folder["name"] == name for folder in data["folders"]):
        raise HTTPException(status_code=409, detail="이미 존재하는 폴더 이름입니다")
    folder = {"id": _next_id(data, "folder", "PF"), "name": name, "order": len(data["folders"]) + 1}
    data["folders"].append(folder)
    _save(data)
    return folder


def rename_folder(folder_id: str, name: str) -> dict[str, Any]:
    data = _load()
    folder = _find_folder(data, folder_id)
    if any(f["name"] == name for f in data["folders"] if f["id"] != folder_id):
        raise HTTPException(status_code=409, detail="이미 존재하는 폴더 이름입니다")
    folder["name"] = name
    _save(data)
    return folder


def delete_folder(folder_id: str) -> dict[str, Any]:
    data = _load()
    folder = _find_folder(data, folder_id)
    if any(preset["folder_id"] == folder_id for preset in data["presets"]):
        raise HTTPException(status_code=409, detail="하위 조건이 있어 삭제할 수 없습니다")
    data["folders"] = [f for f in data["folders"] if f["id"] != folder_id]
    _save(data)
    return {"deleted": folder["id"]}


# ---------------------------------------------------------------------------
# 조회
# ---------------------------------------------------------------------------


def get_preset_tree() -> dict[str, Any]:
    data = _load()
    folders = sorted(data["folders"], key=lambda f: f["order"])
    result = []
    for folder in folders:
        presets = []
        for preset in data["presets"]:
            if preset["folder_id"] != folder["id"]:
                continue
            revisions = preset["revisions"]
            presets.append(
                {
                    "id": preset["id"],
                    "name": preset["name"],
                    "scope": preset["scope"],
                    "owner": preset["owner"],
                    "latest_rev": revisions[-1]["rev"],
                    "revisions": [
                        {"rev": rev["rev"], "note": rev["note"], "created_at": rev["created_at"]}
                        for rev in revisions
                    ],
                }
            )
        result.append({"id": folder["id"], "name": folder["name"], "presets": presets})
    return {"folders": result}


# ---------------------------------------------------------------------------
# Preset / Revision
# ---------------------------------------------------------------------------


def create_preset(payload: PresetCreate, user: str) -> dict[str, Any]:
    data = _load()
    _find_folder(data, payload.folder_id)
    preset = {
        "id": _next_id(data, "preset", "PS"),
        "folder_id": payload.folder_id,
        "name": payload.name,
        "scope": payload.scope,
        "owner": user,
        "created_at": _now(),
        "revisions": [
            {
                "rev": 0,
                "note": payload.note,
                "created_at": _now(),
                "created_by": user,
                "criteria": payload.criteria.model_dump(),
            }
        ],
    }
    data["presets"].append(preset)
    _save(data)
    return preset


def add_revision(preset_id: str, payload: PresetRevisionCreate, user: str) -> dict[str, Any]:
    data = _load()
    preset = _find_preset(data, preset_id)
    _require_owner(preset, user)
    next_rev = max(rev["rev"] for rev in preset["revisions"]) + 1
    revision = {
        "rev": next_rev,
        "note": payload.note,
        "created_at": _now(),
        "created_by": user,
        "criteria": payload.criteria.model_dump(),
    }
    preset["revisions"].append(revision)
    _save(data)
    return preset


def get_revision(preset_id: str, rev: int) -> dict[str, Any]:
    data = _load()
    preset = _find_preset(data, preset_id)
    for revision in preset["revisions"]:
        if revision["rev"] == rev:
            return {
                "criteria": revision["criteria"],
                "note": revision["note"],
                "created_at": revision["created_at"],
                "created_by": revision["created_by"],
            }
    raise HTTPException(status_code=404, detail="리비전을 찾을 수 없습니다")


def patch_preset(preset_id: str, payload: PresetPatch, user: str) -> dict[str, Any]:
    data = _load()
    preset = _find_preset(data, preset_id)
    _require_owner(preset, user)
    if payload.scope is not None:
        preset["scope"] = payload.scope
    if payload.name is not None:
        preset["name"] = payload.name
    _save(data)
    return preset


def duplicate_preset(preset_id: str, payload: PresetDuplicate, user: str) -> dict[str, Any]:
    data = _load()
    source = _find_preset(data, preset_id)
    latest = source["revisions"][-1]
    folder_id = payload.folder_id or source["folder_id"]
    _find_folder(data, folder_id)
    new_preset = {
        "id": _next_id(data, "preset", "PS"),
        "folder_id": folder_id,
        "name": payload.name,
        "scope": "personal",
        "owner": user,
        "created_at": _now(),
        "revisions": [
            {
                "rev": 0,
                "note": latest["note"],
                "created_at": _now(),
                "created_by": user,
                "criteria": latest["criteria"],
            }
        ],
    }
    data["presets"].append(new_preset)
    _save(data)
    return new_preset


def delete_preset(preset_id: str, user: str) -> dict[str, Any]:
    data = _load()
    preset = _find_preset(data, preset_id)
    _require_owner(preset, user)
    data["presets"] = [p for p in data["presets"] if p["id"] != preset_id]
    _save(data)
    return {"deleted": preset_id}


# ---------------------------------------------------------------------------
# 커스텀 EDS 아이템
# ---------------------------------------------------------------------------


def list_custom_eds_items() -> list[dict[str, Any]]:
    return _load()["custom_eds_items"]


def create_custom_eds_item(payload: CustomEdsItemCreate, user: str) -> dict[str, Any]:
    data = _load()
    items = mock_metadata()["eds_items"]
    known_names = set(items["BIN"]) | set(items["MSR"]) | {item["name"] for item in data["custom_eds_items"]}
    if payload.name in known_names:
        raise HTTPException(status_code=409, detail="이미 사용 중인 이름입니다")
    category_items = set(items[payload.category])
    for term in payload.terms:
        if term.item not in category_items:
            raise HTTPException(status_code=400, detail=f"알 수 없는 EDS 아이템: {term.item}")
    item = {
        "name": payload.name,
        "category": payload.category,
        "terms": [{"item": term.item, "sign": term.sign} for term in payload.terms],
        "owner": user,
        "created_at": _now(),
    }
    data["custom_eds_items"].append(item)
    _save(data)
    return item


def delete_custom_eds_item(name: str, user: str) -> dict[str, Any]:
    data = _load()
    for item in data["custom_eds_items"]:
        if item["name"] == name:
            if item["owner"] != user:
                raise HTTPException(status_code=403, detail="생성자만 삭제할 수 있습니다")
            data["custom_eds_items"] = [i for i in data["custom_eds_items"] if i["name"] != name]
            _save(data)
            return {"deleted": name}
    raise HTTPException(status_code=404, detail="커스텀 아이템을 찾을 수 없습니다")


def expand_custom_item(name: str) -> list[tuple[str, int]]:
    """커스텀 아이템 이름을 (기본 아이템, 부호) 목록으로 전개한다. Phase 3 selection_service가 사용."""
    data = _load()
    for item in data["custom_eds_items"]:
        if item["name"] == name:
            return [(term["item"], term["sign"]) for term in item["terms"]]
    raise HTTPException(status_code=404, detail=f"삭제된 커스텀 아이템: {name}")
