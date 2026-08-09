"""Contract tests for the nightly index workflow.

The `index-daily` workflow is the deployment surface: it builds the index,
publishes it as a Release asset, and redeploys the HF Space. These tests pin
the invariants that keep that pipeline safe — the eval step is report-only and
can never block the publish, and the concurrency group, size check, and
restart steps stay in place.
"""

from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW_PATH = Path(__file__).resolve().parent.parent / ".github/workflows/index-daily.yml"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW_PATH.read_text())


def _steps() -> list[dict]:
    return _workflow()["jobs"]["build"]["steps"]


def _eval_steps() -> list[dict]:
    return [s for s in _steps() if "uv run evals" in s.get("run", "")]


def _position(name: str) -> int:
    names = [s.get("name", "") for s in _steps()]
    return names.index(name)


def test_concurrency_group_is_index_daily_with_no_cancellation():
    assert _workflow()["concurrency"] == {
        "group": "index-daily",
        "cancel-in-progress": False,
    }


def test_eval_step_runs_evals_against_the_built_index():
    eval_steps = _eval_steps()
    assert len(eval_steps) == 1
    assert "~/.cache/xkcd-search/index.sqlite" in eval_steps[0]["run"]


def test_eval_step_is_report_only_and_never_blocks_publish():
    assert _eval_steps()[0]["continue-on-error"] is True


def test_eval_step_sits_between_build_and_publish():
    assert (
        _position("Build index")
        < _position("Run evals (report-only)")
        < _position("Publish release")
    )


def test_size_check_step_remains_before_publish():
    assert _position("Check artifact size") < _position("Publish release")


def test_hf_space_restart_step_remains_after_publish():
    assert _position("Restart HF Space") > _position("Publish release")
