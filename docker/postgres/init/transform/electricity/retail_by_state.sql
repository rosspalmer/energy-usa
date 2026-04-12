-- Retail electricity sales, prices, and customer counts by state and period.
-- Grain: state + month. Source: eia.retail_sales.
CREATE TABLE IF NOT EXISTS electricity.retail_by_state (
    state TEXT NOT NULL,
    period DATE NOT NULL,
    total_revenue NUMERIC,
    total_sales NUMERIC,
    avg_price NUMERIC,
    total_customers NUMERIC,
    transformed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (state, period)
);
