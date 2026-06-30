from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class MockStore:
    wafer_data: pd.DataFrame = field(default_factory=pd.DataFrame)
    metadata: dict[str, Any] = field(default_factory=dict)
    analysis_sets: dict[str, dict[str, Any]] = field(default_factory=dict)
    bin_groups: dict[str, dict[str, Any]] = field(default_factory=dict)
    condition_rules: dict[str, dict[str, Any]] = field(default_factory=dict)
    analysis_conditions: dict[str, dict[str, Any]] = field(default_factory=dict)
    exclusion_rules: dict[str, dict[str, Any]] = field(default_factory=dict)
    analysis_runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    counters: dict[str, int] = field(
        default_factory=lambda: {
            "analysis_set": 0,
            "bin_group": 0,
            "condition_rule": 0,
            "analysis_condition": 0,
            "exclusion_rule": 0,
            "analysis_run": 0,
        }
    )

    def next_id(self, kind: str, prefix: str) -> str:
        self.counters[kind] += 1
        return f"{prefix}{self.counters[kind]:03d}"


store = MockStore()
