-- Looker Studio용 최종 퍼널 전환율 집계
-- 카테고리 / 브랜드 / 월별로 view→cart→purchase 전환율 계산

with funnel_base as (
    select
        event_month,
        event_month_date,
        category_main,
        brand,
        count(distinct user_session || '-' || cast(product_id as string)) as total_sessions,
        sum(has_view)     as view_count,
        sum(has_cart)     as cart_count,
        sum(has_purchase) as purchase_count
    from {{ ref('fct_funnel_events') }}
    group by event_month, event_month_date, category_main, brand
)

select
    cast(event_month as string) as event_month,
    cast(event_month_date as date) as event_month_date,
    cast(category_main as string) as category_main,
    cast(brand as string) as brand,
    cast(view_count as int64) as view_count,
    cast(cart_count as int64) as cart_count,
    cast(purchase_count as int64) as purchase_count,

    -- view → cart 전환율
    cast(round(safe_divide(cart_count, view_count) * 100, 2) as float64) as view_to_cart_rate,
    -- cart → purchase 전환율
    cast(round(safe_divide(purchase_count, cart_count) * 100, 2) as float64) as cart_to_purchase_rate,
    -- view → purchase 전체 전환율
    cast(round(safe_divide(purchase_count, view_count) * 100, 2) as float64) as overall_conversion_rate

from funnel_base
where view_count > 0
order by event_month_date, overall_conversion_rate desc
