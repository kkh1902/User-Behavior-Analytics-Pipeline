from __future__ import annotations

import pytest

pytestmark = [pytest.mark.load, pytest.mark.skip(reason="TODO: load tests are documented only for now.")]


def test_medium_volume_load_todo() -> None:
    # TODO:
    # 1) 중간 규모 샘플(예: 100k~1M rows) 준비
    # 2) 처리량(rows/sec)과 실패율 측정
    # 3) 기준치 미달 시 경고/실패 처리
    assert True
