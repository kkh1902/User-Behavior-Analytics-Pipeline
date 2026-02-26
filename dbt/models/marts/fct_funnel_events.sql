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
        -- 각 단계 도달 여부
        max(case when event_type = 'view'     then 1 else 0 end) as has_view,
        max(case when event_type = 'cart'     then 1 else 0 end) as has_cart,
        max(case when event_type = 'purchase' then 1 else 0 end) as has_purchase
    from {{ ref('stg_clickstream') }}
    group by
        user_id, user_session, product_id,
        category_main, brand, price,
        event_date, event_month
)

select
    user_id,
    user_session,
    product_id,
    category_main,
    brand,
    price,
    event_date,
    event_month,
    has_view,
    has_cart,
    has_purchase,
    -- 퍼널 단계 레이블
    case
        when has_purchase = 1 then 'purchase'
        when has_cart     = 1 then 'cart'
        when has_view     = 1 then 'view'
    end as funnel_stage
from base
