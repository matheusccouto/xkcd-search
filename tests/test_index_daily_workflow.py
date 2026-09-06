"""Contract tests for the nightly index workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

WORKFLOW_PATH = (
    Path(__file__).resolve().parent.parent / ".github" / "workflows" / "index-daily.yml"
)


def _workflow() -> dict[str, Any]:
    """Parse and return workflow YAML document."""
    return yaml.safe_load(WORKFLOW_PATH.read_text())


def _steps() -> list[dict[str, Any]]:
    """Return build job steps list from workflow."""
    return _workflow()["jobs"]["build"]["steps"]


def _position(name: str) -> int:
    """Return step index by name."""
    names = [s.get("name", "") for s in _steps()]
    return names.index(name)


def test_concurrency_group_is_index_daily_with_no_cancellation() -> None:
    """Ensure concurrency group prevents overlapping daily indexers."""
    assert _workflow()["concurrency"] == {
        "group": "index-daily",
        "cancel-in-progress": False,
    }


def test_build_step_runs_ingest_with_hf_dataset_repo() -> None:
    """Ensure workflow executes xkcd-ingest script with HF repo env var."""
    build_step = next(s for s in _steps() if "Ingest and upload" in s.get("name", ""))
    assert "xkcd-ingest" in build_step["run"]
    assert "HF_DATASET_REPO" in build_step["env"]
    assert "HF_TOKEN" in build_step["env"]


def test_hf_space_restart_step_remains_after_build() -> None:
    """Ensure space restart occurs strictly after dataset upload."""
    build_idx = _position("Ingest and upload LanceDB dataset to Hugging Face")
    assert _position("Restart HF Space") > build_idx
