# Electricity Overview Dashboard

## Audience
State energy policy analysts and industry professionals who need to compare
their state's electricity profile against regional and national benchmarks.
Should be usable by someone with no SQL or programming experience.

## Key questions this dashboard answers
1. How has my state's electricity generation mix changed over time?
2. How does my state's retail electricity price compare to neighboring states?
3. What is the relationship between generation volume and carbon intensity?
4. Which states have the highest/lowest retail electricity sales?

## Data sources
- electricity.generation_mix (transform DB) — state + month grain, has total_generation_mwh, co2_tons, carbon_intensity
- electricity.retail_by_state (transform DB) — state + month grain, has total_revenue, total_sales, avg_price, total_customers

## Suggested visualizations

### Chart 1: Retail Price by State (Bar Chart)
- **Type**: Horizontal bar chart
- **X-axis**: avg_price
- **Y-axis**: state
- **Filter**: Most recent period (auto)
- **Sort**: Descending by price
- **Purpose**: Quick comparison of current electricity prices across states

### Chart 2: Price Trend Over Time (Line Chart)
- **Type**: Multi-line time series
- **X-axis**: period
- **Y-axis**: avg_price
- **Color**: state (filtered to a selectable subset)
- **Filter**: State picker (default: top 10 by sales volume)
- **Purpose**: How has pricing changed? Spot trends and seasonal patterns

### Chart 3: Generation vs Carbon Intensity (Scatter)
- **Type**: Scatter plot
- **X-axis**: total_generation_mwh
- **Y-axis**: carbon_intensity
- **Size**: total_sales (bubble)
- **Color**: state
- **Filter**: Most recent year
- **Purpose**: Identify which high-generation states are also high-emission

### Chart 4: Sales Volume by State (Choropleth or Treemap)
- **Type**: US state map or treemap
- **Value**: total_sales
- **Filter**: Period selector
- **Purpose**: Spatial view of electricity consumption

### Chart 5: Data Quality Summary (Table)
- **Type**: Table
- **Source**: quality.audit_results (ingest DB)
- **Columns**: dataset, pass count, fail count, last_run
- **Filter**: source = 'eia'
- **Purpose**: At-a-glance data freshness and quality status

## Dashboard layout
- **Row 1**: Chart 1 (price bar, 60%) + Chart 5 (quality table, 40%)
- **Row 2**: Chart 2 (price trend, 100%)
- **Row 3**: Chart 3 (scatter, 50%) + Chart 4 (sales map, 50%)
- **Global filters**: State picker, date range

## Notes for interactive build session
- Start with the simplest chart (Chart 1) to verify data connectivity
- Use Superset's "Explore" view to iterate on each chart before adding to dashboard
- The quality table (Chart 5) uses the ingest DB connection, not transform
- For the state filter, use Superset's native dashboard filter component
