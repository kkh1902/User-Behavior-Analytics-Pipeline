-- 세션 + 상품 단위로 퍼널 단계 플래그 생성
-- 각 (user_session, product_id) 조합에서 어디까지 진행했는지 기록

with base as (
    select
        user_id,
        user_session,
        product_id,
        category_main,
        brand,
        price,
        event_date,
        event_month,
        event_month_date,
        -- 각 단계 도달 여부
        max(case when event_type = 'view'     then 1 else 0 end) as has_view,
        max(case when event_type = 'cart'     then 1 else 0 end) as has_cart,
        max(case when event_type = 'purchase' then 1 else 0 end) as has_purchase
    from {{ ref('stg_clickstream') }}
    group by
        user_id, user_session, product_id,
        category_main, brand, price,
        event_date, event_month, event_month_date
)

select
    cast(user_id as int64) as user_id,
    cast(user_session as string) as user_session,
    cast(product_id as int64) as product_id,
    cast(category_main as string) as category_main,
    cast(brand as string) as brand,
    cast(price as float64) as price,
    cast(event_date as date) as event_date,
    cast(event_month as string) as event_month,
    cast(event_month_date as date) as event_month_date,
    cast(has_view as int64) as has_view,
    cast(has_cart as int64) as has_cart,
    cast(has_purchase as int64) as has_purchase,
    -- 퍼널 단계 레이블
    cast(
        case
            when has_purchase = 1 then 'purchase'
            when has_cart     = 1 then 'cart'
            when has_view     = 1 then 'view'
        end as string
    ) as funnel_stage
from base
