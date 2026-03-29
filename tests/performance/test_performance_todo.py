from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.performance,
    pytest.mark.skip(reason="TODO: performance benchmarks are documented only for now."),
]


def test_runtime_sla_todo() -> None:
    # TODO:
    # 1) Measure execution time per input size
    # 2) Define SLA threshold (e.g. within N minutes)
    # 3) Treat exceeding the threshold as a regression
    assert True
