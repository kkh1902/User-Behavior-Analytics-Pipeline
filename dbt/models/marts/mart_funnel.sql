-- Final funnel conversion rate aggregation for Looker Studio
-- Compute view→cart→purchase conversion rates per category / brand / month using a consistent population

with funnel_base as (
    select
        event_month,
        event_month_date,
        category_main,
        brand,
        -- Define per-stage counts using a consistent population so conversion rates stay in 0-100%
        countif(has_view = 1) as view_count,
        countif(has_view = 1 and has_cart = 1) as cart_count,
        countif(has_view = 1 and has_cart = 1 and has_purchase = 1) as purchase_count
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

    -- view → cart conversion rate
    cast(round(safe_divide(cart_count, view_count) * 100, 2) as float64) as view_to_cart_rate,
    -- cart → purchase conversion rate
    cast(round(safe_divide(purchase_count, cart_count) * 100, 2) as float64) as cart_to_purchase_rate,
    -- view → purchase overall conversion rate
    cast(round(safe_divide(purchase_count, view_count) * 100, 2) as float64) as overall_conversion_rate

from funnel_base
where view_count > 0
order by event_month_date, overall_conversion_rate desc
