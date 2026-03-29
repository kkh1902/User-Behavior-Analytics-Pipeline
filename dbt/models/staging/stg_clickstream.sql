-- Clean raw event data
-- - Remove NULLs
-- - Filter event_type to view / cart / purchase only
-- - Extract top-level category from category_code

with source as (
    select * from {{ source('clickstream_raw', 'clickstream_partitioned_clustered') }}
),

cleaned as (
    select
        cast(event_time as timestamp) as event_time,
        cast(event_type as string) as event_type,
        cast(product_id as int64) as product_id,
        cast(category_id as int64) as category_id,
        cast(category_code as string) as category_code,
        -- Extract top-level category (e.g. 'electronics.smartphone' → 'electronics')
        cast(split(category_code, '.')[safe_offset(0)] as string) as category_main,
        cast(brand as string) as brand,
        cast(price as float64) as price,
        cast(user_id as int64) as user_id,
        cast(user_session as string) as user_session,
        cast(event_date as date) as event_date,
        cast(event_month as string) as event_month,
        cast(event_month_date as date) as event_month_date
    from source
    where
        event_type in ('view', 'cart', 'purchase')
        and user_id is not null
        and user_session is not null
        and product_id is not null
)

select * from cleaned
