from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.performance,
    pytest.mark.skip(reason="TODO: performance benchmarks are documented only for now."),
]


def test_runtime_sla_todo() -> None:
    # TODO:
    # 1) 입력 크기별 실행 시간 측정
    # 2) SLA 임계치(예: N분 이내) 정의
    # 3) 임계치 초과 시 회귀로 판단
    assert True
