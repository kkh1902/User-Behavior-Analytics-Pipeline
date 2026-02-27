from __future__ import annotations

import pytest

pytestmark = [pytest.mark.resilience, pytest.mark.skip(reason="TODO: resilience tests are documented only for now.")]


def test_idempotency_rerun_todo() -> None:
    # TODO:
    # 1) 동일 월 입력으로 파이프라인 2회 실행
    # 2) 결과 중복 적재가 없는지 검증
    # 3) 실패 후 재실행 시 최종 결과 일관성 검증
    assert True
