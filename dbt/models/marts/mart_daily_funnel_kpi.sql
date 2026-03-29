-- Daily funnel KPI based on consistent population
-- Numerator and denominator use the same cohort so conversion rates stay in the 0-100% range

with base as (
    select
        event_date,
        event_month,
        event_month_date,
        category_main,
        brand,
        has_view,
        has_cart,
        has_purchase
    from {{ ref('fct_funnel_events') }}
)

select
    cast(event_date as date) as event_date,
    cast(event_month as string) as event_month,
    cast(event_month_date as date) as event_month_date,
    cast(category_main as string) as category_main,
    cast(brand as string) as brand,

    -- Consistent-population counts
    cast(countif(has_view = 1) as int64) as view_sessions,
    cast(countif(has_view = 1 and has_cart = 1) as int64) as view_to_cart_sessions,
    cast(countif(has_cart = 1) as int64) as cart_sessions,
    cast(countif(has_cart = 1 and has_purchase = 1) as int64) as cart_to_purchase_sessions,
    cast(countif(has_view = 1 and has_purchase = 1) as int64) as view_to_purchase_sessions,

    -- Conversion rates based on consistent population (0-100%)
    cast(round(safe_divide(countif(has_view = 1 and has_cart = 1), countif(has_view = 1)) * 100, 2) as float64) as view_to_cart_rate,
    cast(round(safe_divide(countif(has_cart = 1 and has_purchase = 1), countif(has_cart = 1)) * 100, 2) as float64) as cart_to_purchase_rate,
    cast(round(safe_divide(countif(has_view = 1 and has_purchase = 1), countif(has_view = 1)) * 100, 2) as float64) as overall_conversion_rate

from base
group by event_date, event_month, event_month_date, category_main, brand
order by event_date, overall_conversion_rate desc
