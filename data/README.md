# Data Directory

## Overview
This folder contains the raw clickstream CSVs (2019-10, 2019-11) and the EDA notebook.

## Source
https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store?select=2019-Oct.csv

## Files
- `2019-Oct.csv`: October 2019 event data
- `2019-Nov.csv`: November 2019 event data
- `data_exploration.ipynb`: Sample EDA notebook

## Schema (summary)
`event_time`, `event_type`, `product_id`, `category_id`, `category_code`, `brand`, `price`, `user_id`, `user_session`

## Usage
For EDA, refer to `data_exploration.ipynb`.

## Data usage scenario
Based on the BigQuery analysis, only the following aggregate is used:
- Hourly event type aggregation: `event_type_by_hour` (for donut/line charts)

## Business questions (examples)
1. **Conversion analysis**
   - View → cart → purchase funnel
   - Conversion rate by category/brand

2. **User behavior**
   - Session length and event counts
   - Average views to purchase
   - Repeat purchaser identification

3. **Product performance**
   - Top products/categories
   - Brand-level views and revenue
   - Cart add rate vs purchase rate

4. **Time-based patterns**
   - Hourly/weekday traffic
   - Peak time detection
   - Seasonality and trend checks

## Pipeline integration

Raw data is processed as follows:

```
data/ (Raw CSV)
  ↓
[Kestra] Ingestion to GCS
  ↓
[Spark] Cleaning/transform → Parquet
  ↓
[BigQuery] Warehouse load
  ↓
[Looker Studio] Dashboarding
```

For details, see the root `README.md`.

## Sample data (from data_exploration.ipynb)

```csv
event_time,event_type,product_id,category_id,category_code,brand,price,user_id,user_session
2019-10-01 00:00:00 UTC,view,44600062,2103807459595387724,,shiseido,35.79,541312140,72d76fde-8bb3-4e00-8c23-a032dfed738c
2019-10-01 00:00:00 UTC,view,3900821,2053013552326770905,appliances.environment.water_heater,aqua,33.20,554748717,9333dfbd-b87a-4708-9857-6336556b0fcc
2019-10-01 00:00:01 UTC,view,17200506,2053013559792632471,furniture.living_room.sofa,,543.10,519107250,566511c2-e2e3-422b-b695-cf8e6e792ca8
2019-10-01 00:00:01 UTC,view,1307067,2053013558920217191,computers.notebook,lenovo,251.74,550050854,7c90fc70-0e80-4590-96f3-13c02c18c713
2019-10-01 00:00:04 UTC,view,1004237,2053013555631882655,electronics.smartphone,apple,1081.98,535871217,c6bd7419-2748-4c56-95b4-8cec9ff8b80d
```

## EDA Summary (Extract Phase)

### Key findings
Below is the EDA summary from `data_exploration.ipynb`:

1. **Data size**
   - Sample: 100,000 rows × 9 columns
   - Full file: 2019-Oct.csv (5,406 MB)
   - Memory usage: 6.9 MB (100k sample)

2. **Data types**
   - String: `event_time`, `event_type`, `category_code`, `brand`, `user_session`
   - Integer: `product_id`, `category_id`, `user_id`
   - Float: `price`

3. **Missing values**
   - `category_code`: 32,587 (32.6%) - uncategorized items
   - `brand`: 14,393 (14.4%) - unbranded or missing
   - Other columns: no missing values

4. **Event distribution**
   - **view**: 97,130 (97.1%) - mostly product views
   - cart: 1,555 (1.6%)
   - purchase: 1,315 (1.3%)
   - **Conversion**: view → cart (1.6%), cart → purchase (84.6%)

5. **Categories & brands**
   - Categories: 123 (electronics.smartphone is the largest)
   - Brands: 1,506 (samsung is #1 with 11,683)
   - Products: 20,621 unique products

6. **Users & sessions**
   - Users: 20,384
   - Sessions: 24,382 (users have multiple sessions)
   - Max events per session: 113

7. **Price distribution**
   - Mean: $286.83
   - Median: $154.38
   - Range: $0 ~ $2,574.07
   - **Issue**: price = 0 exists → free items or data error

8. **Duplicates**
   - 17 rows (0.017%) - very low duplication rate
