-- Looker Studio용 최종 퍼널 전환율 집계
-- 카테고리 / 브랜드 / 월별로 view→cart→purchase 전환율 계산

with funnel_base as (
    select
        event_month,
        category_main,
        brand,
        count(distinct user_session || '-' || cast(product_id as string)) as total_sessions,
        sum(has_view)     as view_count,
        sum(has_cart)     as cart_count,
        sum(has_purchase) as purchase_count
    from {{ ref('fct_funnel_events') }}
    group by event_month, category_main, brand
)

select
    event_month,
    category_main,
    brand,
    view_count,
    cart_count,
    purchase_count,

    -- view → cart 전환율
    round(safe_divide(cart_count, view_count) * 100, 2)     as view_to_cart_rate,
    -- cart → purchase 전환율
    round(safe_divide(purchase_count, cart_count) * 100, 2) as cart_to_purchase_rate,
    -- view → purchase 전체 전환율
    round(safe_divide(purchase_count, view_count) * 100, 2) as overall_conversion_rate

from funnel_base
where view_count > 0
order by event_month, overall_conversion_rate desc
