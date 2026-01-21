# Kestra Workflows

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Kestra (Orchestration - EL)                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  Local Data     │      │   GCS Raw        │      │  GCS Processed  │
│  /app/data/     │─────▶│   gs://bucket/   │─────▶│   gs://bucket/  │
│  *.csv          │      │   raw/*.csv      │      │   processed/    │
└─────────────────┘      └──────────────────┘      │   *.parquet     │
                                                    └─────────────────┘
     Flow 01                                               │
  Data Ingestion                                          │
                                                           │
                                                           ▼
                                              ┌─────────────────────┐
                                              │   Local Spark       │
                                              │   (Docker)          │
                                              │   - Data Cleaning   │
                                              │   - CSV → Parquet   │
                                              └─────────────────────┘
                                                    Flow 02
                                                Spark Processing
                                                           │
                                                           ▼
                                              ┌─────────────────────┐
                                              │  BigQuery Staging   │
                                              │  events_staging     │
                                              │  (Temp Table)       │
                                              └─────────────────────┘
                                                    Flow 03
                                              Load to Staging (LOAD)
┌─────────────────────────────────────────────────────────────────────┐
│                        dbt (Transformation - T)                     │
└─────────────────────────────────────────────────────────────────────┘
                                                           │
                                                           ▼
                                              ┌─────────────────────┐
                                              │ BigQuery Production │
                                              │  events (MERGE)     │
                                              │  - Partitioned      │
                                              │  - Deduplicated     │
                                              └─────────────────────┘
                                                    dbt Models
                                                Incremental MERGE
                                                           │
                                                           ▼
                                              ┌─────────────────────┐
                                              │   Data Marts        │
                                              │ - user_sessions     │
                                              │ - product_perf      │
                                              │ - conversion_funnel │
                                              └─────────────────────┘
                                                    Flow 04
                                                   dbt Run
                                                           │
                                                           ▼
                                              ┌─────────────────────┐
                                              │   Looker Studio     │
                                              │   - Dashboards      │
                                              └─────────────────────┘
```

## ELT 패턴 (Extract, Load, Transform)

이 프로젝트는 **Modern ELT** 패턴을 따릅니다:

| 도구 | 역할 | 책임 |
|---|---|---|
| **Kestra** | Orchestration + EL | 워크플로우 스케줄링, 데이터 이동 |
| **Spark** | Transform (초기) | 데이터 클리닝, CSV → Parquet |
| **dbt** | Transform (SQL) | MERGE, Data Marts, 테스트 |

### 왜 이렇게 분리하는가?

**장점:**
- ✅ 명확한 책임 분리 (Separation of Concerns)
- ✅ Kestra: 데이터 이동에만 집중
- ✅ dbt: 모든 SQL 변환 관리 (버전 관리, 테스트, 문서화)
- ✅ 유지보수 용이 (SQL 수정 시 dbt만 수정)
- ✅ 데이터 lineage 추적 가능

## 워크플로우 흐름

### Kestra의 역할: Extract & Load (EL)

1. **Flow 01: Data Ingestion**
   - 로컬 CSV → GCS Raw 버킷
   - 트리거: 스케줄 또는 수동

2. **Flow 02: Spark Processing**
   - GCS Raw → 로컬 Spark (Docker) 처리 → GCS Processed (Parquet)
   - 데이터 클리닝, 변환, CSV → Parquet 변환
   - 의존성: Flow 01 완료 후

3. **Flow 03: Load to Staging**
   - GCS Processed (Parquet) → BigQuery Staging 테이블 (LOAD)
   - `events_staging` 임시 테이블에 적재
   - Kestra는 여기까지만 담당 (데이터 이동)
   - 의존성: Flow 02 완료 후

4. **Flow 04: dbt Transformation**
   - dbt CLI 실행 (`dbt run`, `dbt test`)
   - dbt가 모든 SQL 변환 담당
   - 의존성: Flow 03 완료 후

### dbt의 역할: Transform (T)

dbt가 `Flow 04`에서 실행하는 작업:

1. **Staging → Production (Incremental MERGE)**
   ```sql
   models/marts/events.sql
   - events_staging → events (중복 제거 MERGE)
   - Partitioned by event_time
   - Unique key: event_id
   ```

2. **Data Marts 생성**
   ```sql
   models/marts/user_sessions.sql
   models/marts/product_performance.sql
   models/marts/conversion_funnel.sql
   ```

3. **데이터 품질 테스트**
   ```yaml
   tests:
     - unique, not_null checks
     - relationship tests
     - custom business logic tests
   ```

### 전체 파이프라인

**Flow 00: Full Pipeline**
- Flow 01 → 02 → 03 → 04 순차 실행
- Kestra: 오케스트레이션 + EL
- dbt: 모든 SQL 변환 (T)

## 현재 진행 상황

### 0. Kestra 설정
- [x] Docker Compose 설정 완료
- [x] Kestra 실행 (`docker-compose up -d`)
- [x] KV Store에 GCP 설정값 등록 완료
  - `GCP_PROJECT_ID`: clickstream-pipeline-484705
  - `GCP_LOCATION`: asia-northeast3
  - `GCP_BUCKET_NAME`: clickstream-pipeline-484705-clickstream-data
  - `GCP_DATASET`: zoomcamp

## 다음 해야할 것들

### 1. GCP 인증 설정
- [ ] GCP 서비스 계정 키 파일 다운로드 (JSON)
- [ ] Kestra Secret에 서비스 계정 등록
  - UI: `http://localhost:8080` → Namespaces → zoomcamp → Secrets
  - Key: `GCP_SERVICE_ACCOUNT`
  - Value: JSON 파일 내용 전체 붙여넣기
- [ ] GCS 버킷 접근 권한 확인

### 2. Flows 작성

#### `flows/01-data-ingestion.yml`
- [ ] 로컬 클릭스트림 데이터를 GCS Raw 버킷으로 업로드
- [ ] 파일 존재 여부 체크
- [ ] 업로드 성공/실패 로깅
- [ ] 스케줄 설정 (일일 1회 또는 수동)

#### `flows/02-spark-processing.yml`
- [ ] GCS Raw 데이터를 읽어서 로컬 Spark 처리
- [ ] Docker Spark 컨테이너 실행
- [ ] 데이터 클리닝 및 변환 (Null 처리, 중복 제거, 타입 변환)
- [ ] CSV → Parquet 변환
- [ ] 처리된 Parquet 파일을 GCS Processed 버킷에 저장
- [ ] 처리 로그 및 통계 확인

#### `flows/03-load-staging.yml`
- [ ] GCS Processed Parquet를 BigQuery Staging 테이블로 로드
- [ ] `events_staging` 테이블 생성/교체 (WRITE_TRUNCATE)
- [ ] 로드 성공 여부 확인
- [ ] Kestra는 여기까지만 (데이터 이동만 담당)

#### `flows/04-dbt-run.yml`
- [ ] dbt CLI 실행 (Docker)
- [ ] `dbt run`: Staging → Production MERGE + Data Marts 생성
- [ ] `dbt test`: 데이터 품질 테스트 실행
- [ ] `dbt docs generate`: 문서 생성 (선택)

#### `flows/00-full-pipeline.yml` (통합 워크플로우)
- [ ] 위 4개 워크플로우를 순차적으로 실행
- [ ] 각 단계별 의존성 관리
- [ ] 실패 시 재시도 로직
- [ ] 완료 후 알림 (선택)

### 3. 실행 및 모니터링
- [ ] Kestra UI에서 워크플로우 테스트
- [ ] 스케줄 트리거 설정
- [ ] 실행 로그 모니터링
- [ ] 에러 핸들링 검증

## 실행 방법

```bash
# Kestra 시작
cd kestra
docker-compose up -d

# UI 접속
http://localhost:8080
```

## 데이터 흐름 요약

```
Raw Data (CSV)
  → Kestra Flow 01: GCS 업로드
  → Kestra Flow 02: Spark 처리 (Parquet)
  → Kestra Flow 03: BigQuery Staging 로드
  → Kestra Flow 04: dbt 실행
    ├─ dbt: Staging → Production (MERGE, 중복 제거)
    └─ dbt: Production → Data Marts (집계, 분석)
  → Looker Studio (시각화)
```

## 다음 단계

1. GCP 인증 설정
2. Kestra flows/ 폴더에 워크플로우 파일 작성 (EL 담당)
3. dbt 프로젝트 설정 (T 담당)
4. 각 워크플로우 개별 테스트
5. 통합 파이프라인 실행
