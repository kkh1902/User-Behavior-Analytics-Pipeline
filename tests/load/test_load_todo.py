from __future__ import annotations

import pytest

pytestmark = [pytest.mark.load, pytest.mark.skip(reason="TODO: load tests are documented only for now.")]


def test_medium_volume_load_todo() -> None:
    # TODO:
    # 1) Prepare a medium-scale sample (e.g. 100k–1M rows)
    # 2) Measure throughput (rows/sec) and failure rate
    # 3) Warn/fail if below threshold
    assert True
