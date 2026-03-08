# 클릭스트림 파이프라인 PPT 슬라이드 상세 구성안 (발표용 본문 확장)

## 슬라이드 1. 프로젝트 소개
- 제목: 클릭스트림 전환 퍼널 분석 파이프라인 구축
- 한 줄 요약: "유입은 많은데 구매가 안 되는 문제를 데이터 파이프라인으로 해결"
- 문제: 데이터가 흩어져 있어 전환 병목을 일관되게 측정하기 어려움
- 해결: 수집 -> 변환 -> 적재 -> 모델링 -> 시각화를 하나의 운영 흐름으로 구현
- 성과: 퍼널 KPI를 주기적으로 확인하고 개선 우선순위를 정할 수 있는 기반 확보
- 시각 요소: 파이프라인 아이콘 타임라인
- 발표 포인트: 비즈니스 문제를 기술 구현으로 연결한 프로젝트임을 먼저 강조

## 슬라이드 2. 문제 정의(상세)
- 현상 1: view 트래픽은 충분한데 purchase 전환은 기대 대비 낮음
- 현상 2: 유입 증가 구간에서도 구매가 비례 증가하지 않는 케이스 존재
- 현상 3: 카테고리/브랜드별 편차는 큰데 원인 분석 기준 부재
- 원인 가설 A: 상품 정보/가격/리뷰 부족 -> `view -> cart` 이탈
- 원인 가설 B: 배송비/결제 복잡도/신뢰 이슈 -> `cart -> purchase` 이탈
- 데이터 과제: 원본 로그 품질 편차로 지표 신뢰성 위험
- 해결 목표: 단계별 손실 구간과 개선 대상을 데이터로 명확화
- 시각 요소: 퍼널 + 원인 가설 매핑 다이어그램
- 발표 포인트: "전환이 낮다"가 아니라 "어디서 왜 낮은지"를 찾는 문제로 재정의

## 슬라이드 3. 목표와 KPI 정의
- 목표 1: 수작업 없는 배치 파이프라인 자동화
- 목표 2: 전환 KPI 정의 표준화(팀 내 지표 해석 일치)
- 목표 3: 분석 결과를 실행 액션으로 연결
- KPI 1: `view_to_cart_rate` = cart/view
- KPI 2: `cart_to_purchase_rate` = purchase/cart
- KPI 3: `overall_conversion_rate` = purchase/view
- 분석 축: 월/일, 카테고리, 브랜드, 세션+상품
- 시각 요소: KPI 정의 테이블
- 발표 포인트: KPI를 먼저 고정해 추후 논쟁 비용을 줄인 점 강조

## 슬라이드 4. 전체 아키텍처
- 입력: Kaggle E-commerce Behavior Data (2019 Oct/Nov)
- 저장 계층: GCS `raw/kaggle/` -> GCS `processed/clickstream/`
- 처리 계층: Spark(Dataproc)로 타입 정제/파티션 생성
- 웨어하우스: BigQuery 외부테이블 + 파티션/클러스터 테이블
- 모델 계층: dbt(staging -> marts)
- 소비 계층: Looker Studio 대시보드
- 오케스트레이션: Airflow 3개 DAG 분리 운영
- 시각 요소: End-to-End 아키텍처 다이어그램
- 발표 포인트: 계층 분리로 운영/장애 대응/확장성 확보

## 슬라이드 5. Terraform 인프라 구현
- 문제: 수동 리소스 생성 시 환경별 불일치와 누락 발생
- 해결: Terraform으로 리소스 선언적 관리
- 구현 1: GCS bucket 생성(버저닝, lifecycle rule, uniform access)
- 구현 2: BigQuery dataset 생성
- 운영 효과: 재현 가능한 환경 구축, 재배포 시간 단축
- 리스크/주의: `force_destroy` 설정 사용 시 운영 정책 분리 필요
- 시각 요소: Terraform 리소스 관계도
- 발표 포인트: IaC로 "개발환경만 되는" 상태를 방지

## 슬라이드 6. Airflow DAG 분리 전략
- DAG 1: `clickstream_ingest_raw` (수집)
- DAG 2: `clickstream_spark_transform` (변환)
- DAG 3: `clickstream_pipeline` (적재+모델링+검증)
- 문제: 단일 DAG에 모든 단계를 넣으면 장애 구간 추적이 어려움
- 해결: 역할별 DAG 분리 + 태스크 책임 명확화
- 운영 장점: 실패 범위 축소, 재실행 단위 최소화
- 공통 운영: 실패 시 Slack webhook 알림
- 시각 요소: DAG 분리 구조도
- 발표 포인트: 기술 구현보다 운영가능성(operability)을 우선한 설계

## 슬라이드 7. Ingest DAG 상세 구현
- 태스크 1: Kaggle CLI로 원본 zip 다운로드
- 태스크 2: PythonOperator로 zip 압축 해제
- 태스크 3: CSV 파일을 GCS `raw/kaggle/` 업로드
- 데이터 보장: 파일 존재 여부 검증 후 실패 처리(FileNotFoundError)
- 문제 해결: 수작업 다운로드/업로드 제거
- 성과: 원천 수집 표준화, 월별 입력 재현 가능
- 시각 요소: ingest task sequence
- 발표 포인트: "데이터 유입" 단계 자동화가 파이프라인 신뢰성 시작점

## 슬라이드 8. Spark Transform DAG 상세
- 태스크 1: `csv_parquet_job.py`를 GCS `code/` 경로 업로드
- 태스크 2: Dataproc job 실행(10월)
- 태스크 3: Dataproc job 실행(11월)
- 설정: executor instances/cores/memory, shuffle partition 등 성능 파라미터 명시
- 운영 제어: `max_active_runs=1`로 중복 실행 제한
- 문제 해결: 대용량 CSV 직접 쿼리 비효율 해소
- 성과: 분석 친화 포맷(Parquet) 전환
- 시각 요소: Dataproc 실행 플로우
- 발표 포인트: 데이터량 증가를 고려한 분산 처리 선택 근거

## 슬라이드 9. Spark 변환 로직 핵심
- Bronze: 모든 컬럼 string으로 읽어 원본 손실 최소화
- Typed: 주요 컬럼 타입 캐스팅(`event_time`, `product_id`, `price`, `user_id` 등)
- 품질: 캐스팅 실패 탐지 후 `failure_reason` 컬럼으로 원인 라벨링
- Processed: 핵심 식별값 유효한 행만 채택(event_time/user_id/product_id)
- 스키마 안정화: Processed schema 재강제(enforce)
- 시계열 컬럼: `event_date`, `event_month`, `event_month_date` 파생
- 시각 요소: Bronze -> Typed -> Processed 데이터 흐름
- 발표 포인트: 변환 로직이 단순 포맷 변경이 아니라 데이터 품질 게이트 역할 수행

## 슬라이드 10. 저장 전략과 재실행 안정성
- 출력 포맷: Parquet + Snappy compression
- 파티션: `event_month`, `event_date`
- 문제: 재실행 시 중복 적재/불일치 위험
- 해결: 대상 월 파티션 경로 삭제 후 append 적재
- 결과: 월 단위 idempotent 재처리 가능
- 확장성: 월 추가 시 동일 패턴 재사용 가능
- 시각 요소: 파티션 overwrite 전략 도식
- 발표 포인트: 운영 환경에서 재실행 전략은 필수 설계 요소

## 슬라이드 11. BigQuery DDL/적재 구조
- SQL 1: `create_external_table.sql` (GCS 원본 참조)
- SQL 2: `create_partitioned_table.sql`
- SQL 3: `create_partitioned_clustered_table.sql`
- 문제: 원본 접근성과 쿼리 성능/비용을 동시에 만족해야 함
- 해결: 외부테이블 + 최적화 테이블 2계층 운영
- 성과: 분석용 소스 안정화 및 비용 관리 기반 확보
- 시각 요소: BigQuery 테이블 계층 구조
- 발표 포인트: "일단 적재"가 아니라 "분석 운영 관점" DDL 설계

## 슬라이드 12. dbt Staging 모델(`stg_clickstream`)
- 입력 소스: `clickstream_partitioned_clustered`
- 정제 1: 이벤트 타입 `view/cart/purchase`만 필터
- 정제 2: `user_id`, `user_session`, `product_id` null 제거
- 파생: `category_code`에서 `category_main` 추출
- 표준화: 컬럼 타입 cast 통일
- 문제 해결: 원본 로그 품질 편차 완화
- 성과: 하위 mart 모델의 안정된 입력 보장
- 시각 요소: stg 전/후 컬럼 비교표
- 발표 포인트: staging 품질이 전체 KPI 신뢰도의 출발점

## 슬라이드 13. dbt Mart 모델(`fct`/`mart`)
- `fct_funnel_events`: 세션+상품 단위 퍼널 플래그 생성
- 플래그: `has_view`, `has_cart`, `has_purchase`, `funnel_stage`
- `mart_funnel`: 월/카테고리/브랜드 단위 전환율 집계
- `mart_daily_funnel_kpi`: 일 단위 KPI 및 세션 볼륨 집계
- 지표 일관성: 동일 모수 기반 전환율 계산
- 성과: BI에서 재가공 없이 바로 활용 가능
- 시각 요소: dbt lineage + 지표 산식 박스
- 발표 포인트: fact와 mart 분리로 상세 진단과 경영 지표를 동시 지원

## 슬라이드 14. 품질 관리/테스트 현황
- dbt test: `accepted_values`, `not_null` 적용
- unit test 1: DAG import/태스크 구조 검증
- unit test 2: Spark 함수(캐스팅/파티션/스키마) 검증
- integration test: 샘플 데이터로 Spark E2E 흐름 검증
- TODO: load/resilience/performance 테스트는 현재 skip
- 리스크 관리: 구현/미구현 범위를 명시해 과장 방지
- 시각 요소: 테스트 커버리지 매트릭스
- 발표 포인트: "무엇을 검증했고 무엇이 남았는지" 투명하게 제시

## 슬라이드 15. 대시보드 인사이트와 액션
- 데이터소스: `mart_funnel`, `mart_daily_funnel_kpi`, `fct_funnel_events`
- 인사이트 1: `view_to_cart_rate` 저조 카테고리 -> 상세페이지/가격 정책 점검 우선
- 인사이트 2: `cart_to_purchase_rate` 저조 구간 -> 결제 UX/배송비 정책 실험 우선
- 인사이트 3: 특정 일자 급락 -> 캠페인 품질/재고/운영장애 교차 점검
- 액션 1: 상세 콘텐츠 개선 A/B 테스트
- 액션 2: 결제 단계 단순화, 쿠폰/배송비 실험
- 액션 3: 장바구니 이탈 세그먼트 리마케팅
- 우선순위 기준: 영향도 x 실행 난이도 x 리드타임
- 시각 요소: 인사이트 -> 액션 매핑 테이블
- 발표 포인트: 분석이 "발견"에서 끝나지 않고 실행으로 이어진다는 점 강조

## 슬라이드 16. 한계와 개선 로드맵
- 한계 1: 배치 중심이라 near real-time 대응 한계
- 한계 2: 고급 성능/회복탄력성 테스트 미완료
- 단기(1~2개월): 모니터링/알림 강화, 테스트 보강
- 중기(분기): 세그먼트/코호트/리텐션 분석 모델 추가
- 장기(반기+): 스트리밍 수집/처리 아키텍처 전환 검토
- 기대 효과: 운영 리스크 감소 + 인사이트 반영 속도 향상
- 결론: 신뢰 가능한 데이터 제품으로 단계적 고도화
- 시각 요소: 단기-중기-장기 로드맵 타임라인
- 발표 포인트: 현재 수준을 과장하지 않고 확장 계획을 명확히 제시
