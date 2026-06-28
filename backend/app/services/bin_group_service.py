from __future__ import annotations

from typing import Any

import pandas as pd

from app.data.mock_store import store
from app.models.schemas import BinGroupCreate
from app.services.mock_data_service import ensure_mock_data


def create_bin_group(payload: BinGroupCreate) -> dict[str, Any]:
    ensure_mock_data()
    group_id = store.next_id("bin_group", "BG")
    item = {"id": group_id, **payload.model_dump()}
    store.bin_groups[group_id] = item
    return item


def list_bin_groups() -> list[dict[str, Any]]:
    ensure_mock_data()
    return list(store.bin_groups.values())


def get_bin_group(group_id: str) -> dict[str, Any]:
    ensure_mock_data()
    return store.bin_groups[group_id]


def metric_name(group: dict[str, Any]) -> str:
    return f"metric_{group['id']}"


def attach_group_metric(frame: pd.DataFrame, group: dict[str, Any]) -> pd.Series:
    bin_ids = [bin_id for bin_id in group["bin_ids"] if bin_id in frame.columns]
    if not bin_ids:
        return pd.Series(0.0, index=frame.index)
    values = frame[bin_ids].sum(axis=1)
    if group.get("zone"):
        values = values.where(frame["zone"] == group["zone"], other=0.0)
    return values.clip(0, 1)
