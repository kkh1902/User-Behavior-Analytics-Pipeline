from __future__ import annotations

import pytest

pytestmark = [pytest.mark.resilience, pytest.mark.skip(reason="TODO: resilience tests are documented only for now.")]


def test_idempotency_rerun_todo() -> None:
    # TODO:
    # 1) Run the pipeline twice with the same month input
    # 2) Verify no duplicate rows are loaded
    # 3) Verify result consistency after failure and re-run
    assert True
