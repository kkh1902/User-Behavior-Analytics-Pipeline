-- 원본 이벤트 데이터 정제
-- - NULL 제거
-- - event_type을 view / cart / purchase 3가지로 필터
-- - category_code에서 대분류 추출

with source as (
    select * from {{ source('clickstream_raw', 'clickstream_partitioned_clustered') }}
),

cleaned as (
    select
        event_time,
        event_type,
        product_id,
        category_id,
        category_code,
        -- 카테고리 대분류 추출 (예: 'electronics.smartphone' → 'electronics')
        split(category_code, '.')[safe_offset(0)] as category_main,
        brand,
        price,
        user_id,
        user_session,
        event_date,
        event_month
    from source
    where
        event_type in ('view', 'cart', 'purchase')
        and user_id is not null
        and user_session is not null
        and product_id is not null
)

select * from cleaned
