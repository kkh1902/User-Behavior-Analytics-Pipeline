# Data Directory

## 개요
본 디렉토리는 e-commerce 플랫폼의 클릭스트림 원시 데이터(raw data)를 저장합니다. 사용자의 상품 조회, 장바구니 추가, 구매 등의 행동 이벤트를 시계열로 기록한 데이터셋입니다.

## 데이터 출처
- **데이터셋**: E-commerce Behavior Data from Multi-Category Store
- **기간**: 2019년 10월 ~ 2019년 11월
- **원본**: Kaggle / REES46 eCommerce Events History
- **라이선스**: CC0: Public Domain

## 파일 구조
```
data/
├── 2019-Oct.csv              # 2019년 10월 이벤트 데이터 (~42M rows, ~5.4GB)
├── 2019-Nov.csv              # 2019년 11월 이벤트 데이터 (~67M rows)
├── data_exploration.ipynb    # 데이터 탐색 및 EDA 노트북
└── README.md
```

## 데이터 통계
| 파일 | 레코드 수 | 파일 크기 | 기간 |
|------|----------|----------|------|
| 2019-Oct.csv | 42,448,764 | ~5.4GB | 2019-10-01 ~ 2019-10-31 |
| 2019-Nov.csv | 67,501,979 | ~6.7GB | 2019-11-01 ~ 2019-11-30 |
| **합계** | **109,950,743** | **~12GB** | 2개월 |

### 이벤트 타입 분포 (100k 샘플 기준)
| Event Type | Count | Percentage |
|------------|-------|------------|
| view | 97,130 | 97.1% |
| cart | 1,555 | 1.6% |
| purchase | 1,315 | 1.3% |

> **Note**: view 이벤트가 압도적으로 많으며, cart → purchase 전환율 분석이 중요합니다.

## 스키마

### 컬럼 정의
| 컬럼명 | 데이터 타입 | 설명 | 예시 | Nullable |
|--------|------------|------|------|----------|
| `event_time` | STRING | 이벤트 발생 시각 (UTC) | `2019-10-01 00:00:00 UTC` | NO |
| `event_type` | STRING | 이벤트 유형 (`view`, `cart`, `purchase`) | `view` | NO |
| `product_id` | INTEGER | 상품 고유 ID | `44600062` | NO |
| `category_id` | LONG | 카테고리 고유 ID (계층 구조 포함) | `2103807459595387724` | NO |
| `category_code` | STRING | 카테고리 경로 (점으로 구분) | `appliances.environment.water_heater` | YES |
| `brand` | STRING | 브랜드명 | `shiseido` | YES |
| `price` | FLOAT | 상품 가격 (USD) | `35.79` | NO |
| `user_id` | INTEGER | 사용자 고유 ID (영구 식별자) | `541312140` | NO |
| `user_session` | STRING | 세션 UUID (브라우저 세션 단위) | `72d76fde-8bb3-4e00-8c23-a032dfed738c` | NO |

### Event Type 설명
- **view**: 사용자가 상품 상세 페이지를 조회한 이벤트
- **cart**: 사용자가 상품을 장바구니에 추가한 이벤트
- **purchase**: 사용자가 상품을 실제로 구매 완료한 이벤트

### Category Code 구조
카테고리는 계층 구조로 구성되며, 점(`.`)으로 구분됩니다:
```
[대분류].[중분류].[소분류]

예시:
- electronics.smartphone
- appliances.environment.water_heater
- furniture.living_room.sofa
- computers.notebook
```

## 데이터 품질 분석 (EDA 기반)

### Missing Values (100k 샘플 기준)
| 컬럼 | 결측치 수 | 결측율 | 비고 |
|------|----------|--------|------|
| `category_code` | 32,587 | 32.6% | 일부 상품은 카테고리 정보 없음 (비즈니스 특성) |
| `brand` | 14,393 | 14.4% | 노브랜드 또는 브랜드 미분류 상품 존재 |
| 기타 컬럼 | 0 | 0% | 필수 필드는 모두 채워짐 |

### 중복 데이터
- **중복 레코드 수**: 17건 (100k 샘플 기준, 0.017%)
- 중복률이 매우 낮아 데이터 품질은 양호함
- 필요시 `user_id`, `product_id`, `event_time` 기준으로 중복 제거 고려

### 데이터 분포 및 특성

#### 카테고리 및 브랜드
| 항목 | 고유값 수 | 가장 많은 값 | 빈도 |
|------|----------|-------------|------|
| `event_type` | 3 | view | 97.1% |
| `category_code` | 123 | electronics.smartphone | 26,738 |
| `brand` | 1,506 | samsung | 11,683 |
| `category_id` | 509 | - | - |
| `product_id` | 20,621 | - | - |
| `user_id` | 20,384 | - | - |
| `user_session` | 24,382 | - | 최대 113회 반복 |

#### 가격 분석
| 통계량 | 값 (USD) |
|--------|----------|
| 최소값 | 0.00 |
| 25% | 61.01 |
| 중간값 | 154.38 |
| 평균값 | 286.83 |
| 75% | 357.11 |
| 최대값 | 2,574.07 |

> **처리 필요 사항**: price = 0인 레코드에 대한 정책 정의 필요 (무료 상품 vs 오류 데이터)

### 주의사항
1. **데이터 타입 변환 필요**
   - `event_time`: string → datetime 변환 필요
   - `category_id`: int64 (매우 큰 숫자, 계층 구조 인코딩)

2. **결측치 처리 정책**
   - `category_code`: NULL 값은 "unknown" 또는 "uncategorized" 처리
   - `brand`: NULL 값은 "no_brand" 또는 "unbranded" 처리

3. **세션 특성**
   - 한 세션에서 최대 113개의 이벤트 발생 (동일 `user_session`)
   - 동일 사용자(`user_id`)가 여러 세션(`user_session`)을 가질 수 있음

4. **타임존**: 모든 시간은 UTC 기준

5. **가격 변동**: 동일 상품이라도 시간에 따라 가격이 변동될 수 있음

## 사용 방법

### 데이터 탐색 시작하기
처음 데이터를 다루는 경우, 먼저 **`data_exploration.ipynb`** 노트북을 참조하세요:

```bash
cd data
jupyter notebook data_exploration.ipynb
```

노트북에는 다음 내용이 포함되어 있습니다:
- 데이터 로드 및 기본 구조 파악
- 결측치 및 중복 데이터 확인
- 컬럼별 통계 분석
- 이벤트 타입 분포 확인
- 다음 단계(Transform) 준비

### 로컬에서 데이터 샘플 확인
```bash
# 첫 10줄 확인
head -n 10 data/2019-Oct.csv

# 특정 이벤트 타입 필터링
grep ",purchase," data/2019-Oct.csv | head -n 5

# 레코드 수 확인
wc -l data/*.csv

# 파일 크기 확인
ls -lh data/*.csv
```

### Apache Spark로 로드
```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("Clickstream Analysis") \
    .getOrCreate()

df = spark.read \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .csv("data/2019-Oct.csv")

df.printSchema()
df.show(5)
```

### Pandas로 로드 (샘플링 권장)
```python
import pandas as pd
import numpy as np

# 표시 옵션 설정
pd.set_option("display.max_columns", None)
pd.set_option("display.float_format", "{:.2f}".format)

# 샘플링 로드 (권장: 100k rows)
df = pd.read_csv('2019-Oct.csv', nrows=100_000)

# 데이터 확인
print(df.shape)           # (100000, 9)
print(df.info())          # 타입 및 결측치
print(df.head())          # 상위 5개
print(df.describe())      # 기초 통계
print(df.nunique())       # 고유값 개수

# 전체 로드 (메모리 주의: ~5.4GB → RAM 16GB+ 권장)
# df_full = pd.read_csv('2019-Oct.csv')

# 청크 단위 처리 (대용량 처리 시)
for chunk in pd.read_csv('2019-Oct.csv', chunksize=100_000):
    # 처리 로직
    pass
```

## 데이터 활용 시나리오

### 분석 가능한 비즈니스 질문
1. **전환율 분석**
   - 조회 → 장바구니 → 구매 퍼널 분석
   - 카테고리/브랜드별 전환율 비교

2. **사용자 행동 분석**
   - 세션 길이 및 이벤트 수 분석
   - 구매까지의 평균 조회 횟수
   - 반복 구매 사용자 식별

3. **상품 성과 분석**
   - 인기 상품/카테고리 랭킹
   - 브랜드별 매출 및 조회수
   - 장바구니 추가율 vs 실제 구매율

4. **시간대 분석**
   - 시간대별/요일별 트래픽 패턴
   - 피크 타임 식별
   - 계절성 및 트렌드 분석

## 파이프라인 통합

이 원시 데이터는 다음 단계를 거쳐 처리됩니다:

```
data/ (Raw CSV)
  ↓
[Kestra] 데이터 수집 및 GCS 업로드
  ↓
[Spark] 데이터 정제 및 변환 → Parquet 저장
  ↓
[BigQuery] 데이터 웨어하우스 적재
  ↓
[dbt] 데이터 마트 생성
  ↓
[Looker Studio] 대시보드 시각화
```

상세 파이프라인 설명은 프로젝트 루트의 [README.md](../README.md)를 참조하세요.

## 샘플 데이터 (data_exploration.ipynb에서 확인)

```csv
event_time,event_type,product_id,category_id,category_code,brand,price,user_id,user_session
2019-10-01 00:00:00 UTC,view,44600062,2103807459595387724,,shiseido,35.79,541312140,72d76fde-8bb3-4e00-8c23-a032dfed738c
2019-10-01 00:00:00 UTC,view,3900821,2053013552326770905,appliances.environment.water_heater,aqua,33.20,554748717,9333dfbd-b87a-4708-9857-6336556b0fcc
2019-10-01 00:00:01 UTC,view,17200506,2053013559792632471,furniture.living_room.sofa,,543.10,519107250,566511c2-e2e3-422b-b695-cf8e6e792ca8
2019-10-01 00:00:01 UTC,view,1307067,2053013558920217191,computers.notebook,lenovo,251.74,550050854,7c90fc70-0e80-4590-96f3-13c02c18c713
2019-10-01 00:00:04 UTC,view,1004237,2053013555631882655,electronics.smartphone,apple,1081.98,535871217,c6bd7419-2748-4c56-95b4-8cec9ff8b80d
```

## EDA 요약 (Extract Phase)

### 주요 발견사항
다음은 `data_exploration.ipynb`에서 수행한 탐색적 데이터 분석(EDA) 결과입니다:

1. **데이터 크기**
   - 샘플: 100,000 rows × 9 columns
   - 전체 파일: 2019-Oct.csv (5,406 MB)
   - 메모리 사용량: 6.9 MB (100k 샘플 기준)

2. **데이터 타입**
   - String: `event_time`, `event_type`, `category_code`, `brand`, `user_session`
   - Integer: `product_id`, `category_id`, `user_id`
   - Float: `price`

3. **결측치 분석**
   - `category_code`: 32,587개 (32.6%) - 카테고리 미분류 상품
   - `brand`: 14,393개 (14.4%) - 노브랜드 또는 브랜드 미등록 상품
   - 나머지 컬럼: 결측치 없음

4. **이벤트 분포**
   - **view**: 97,130건 (97.1%) - 상품 페이지 조회가 대부분
   - cart: 1,555건 (1.6%)
   - purchase: 1,315건 (1.3%)
   - **전환율**: view → cart (1.6%), cart → purchase (84.6%)

5. **카테고리 & 브랜드**
   - 카테고리: 123개 (electronics.smartphone이 가장 많음)
   - 브랜드: 1,506개 (samsung이 1위, 11,683건)
   - 상품: 20,621개 고유 상품

6. **사용자 & 세션**
   - 사용자: 20,384명
   - 세션: 24,382개 (사용자보다 많음 → 1인 다세션)
   - 한 세션 최대 이벤트: 113개

7. **가격 분포**
   - 평균: $286.83
   - 중간값: $154.38
   - 범위: $0 ~ $2,574.07
   - **이슈**: 가격 0인 상품 존재 → 무료 샘플 or 데이터 오류

8. **중복 데이터**
   - 17건 (0.017%) - 매우 낮은 중복률

### 다음 단계 (Transform Phase)
- `event_time` string → datetime 변환
- 결측치 처리 정책 수립 및 적용
- price = 0 레코드 처리 방침 결정
- Feature engineering (시간대, 요일, 세션 지속 시간 등)
- 이벤트 시퀀스 분석을 위한 데이터 구조 변환

## 참고사항

### 성능 최적화
- 대용량 파일이므로 전체 로드 시 충분한 메모리 필요 (최소 16GB 권장)
- Spark 사용 시 적절한 파티셔닝 및 캐싱 전략 적용
- 분석 전 필요한 컬럼만 선택하여 메모리 사용량 최적화

### 보안 및 개인정보
- `user_id`는 익명화된 ID로 실제 개인정보와 매핑되지 않음
- 본 데이터는 Public Domain으로 교육 및 연구 목적으로 자유롭게 사용 가능

## 문의 및 이슈
데이터 관련 문제나 질문은 프로젝트 관리자에게 문의하거나 이슈를 등록해주세요.