"""
State electricity Dash app: price, generation, consumption by state over time.
Data from Postgres ingest database (eia_retail_sales, eia_electric_power_operational, eia_state_summary).
"""
from django.db import connections
from django_plotly_dash import DjangoDash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd


app = DjangoDash("StateElectricity")

# Layout: top-line state selector, graph placeholder
app.layout = html.Div(
    [
        html.H2("State electricity: price, generation, consumption", className="dashboard-title"),
        html.Div(
            [
                html.Label("State (primary):"),
                dcc.Dropdown(id="state-primary", placeholder="Select state", clearable=False),
                html.Label("Compare (optional):"),
                dcc.Dropdown(id="state-compare", placeholder="Select state to compare", clearable=True),
            ],
            className="dashboard-controls",
            style={"display": "flex", "gap": "1rem", "alignItems": "center", "flexWrap": "wrap", "marginBottom": "1rem"},
        ),
        dcc.Graph(id="ts-price", style={"marginBottom": "1rem"}),
        dcc.Graph(id="ts-generation", style={"marginBottom": "1rem"}),
        dcc.Store(id="states-store", data={"primary": None, "compare": None}),
    ],
    className="dashboard-container",
)


def _get_states():
    """Return list of state IDs from eia_retail_sales."""
    with connections["ingest"].cursor() as cur:
        cur.execute("SELECT DISTINCT stateid FROM eia_retail_sales ORDER BY stateid")
        return [row[0] for row in cur.fetchall()]


def _get_retail_price(state_ids):
    """Fetch average price by period for given states from eia_retail_sales (residential)."""
    if not state_ids:
        return pd.DataFrame()
    placeholders = ",".join("%s" for _ in state_ids)
    with connections["ingest"].cursor() as cur:
        cur.execute(
            f"""
            SELECT period, stateid, AVG(price) AS avg_price
            FROM eia_retail_sales
            WHERE stateid IN ({placeholders}) AND sectorid = 'RES' AND price IS NOT NULL
            GROUP BY period, stateid
            ORDER BY period, stateid
            """,
            state_ids,
        )
        rows = cur.fetchall()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows, columns=["period", "stateid", "avg_price"])


def _get_generation(state_ids):
    """Fetch total generation by period and state from eia_electric_power_operational."""
    if not state_ids:
        return pd.DataFrame()
    placeholders = ",".join("%s" for _ in state_ids)
    with connections["ingest"].cursor() as cur:
        cur.execute(
            f"""
            SELECT period, stateid, SUM(generation) AS total_generation
            FROM eia_electric_power_operational
            WHERE stateid IN ({placeholders}) AND generation IS NOT NULL
            GROUP BY period, stateid
            ORDER BY period, stateid
            """,
            state_ids,
        )
        rows = cur.fetchall()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows, columns=["period", "stateid", "total_generation"])


def _get_summary_consumption(state_ids):
    """Fetch total_consumption / average_retail_price by period from eia_state_summary."""
    if not state_ids:
        return pd.DataFrame()
    placeholders = ",".join("%s" for _ in state_ids)
    with connections["ingest"].cursor() as cur:
        cur.execute(
            f"""
            SELECT period, stateid, total_consumption, average_retail_price
            FROM eia_state_summary
            WHERE stateid IN ({placeholders})
            ORDER BY period, stateid
            """,
            state_ids,
        )
        rows = cur.fetchall()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows, columns=["period", "stateid", "total_consumption", "average_retail_price"])


@app.callback(
    Output("state-primary", "options"),
    Output("state-compare", "options"),
    Input("states-store", "data"),
)
def _set_state_options(_):
    states = _get_states()
    opts = [{"label": s, "value": s} for s in states]
    return opts, opts


@app.callback(
    Output("state-primary", "value"),
    Input("state-primary", "options"),
)
def _set_primary_default(options):
    if options and len(options) > 0:
        return options[0]["value"]
    return None


@app.callback(
    Output("ts-price", "figure"),
    Input("state-primary", "value"),
    Input("state-compare", "value"),
)
def _update_price(state_primary, state_compare):
    state_ids = [s for s in (state_primary, state_compare) if s]
    df = _get_retail_price(state_ids)
    if df.empty:
        return px.line(title="Retail price (residential) — no data").update_layout(template="plotly_white")
    fig = px.line(df, x="period", y="avg_price", color="stateid", title="Retail price (residential, $/kWh)")
    fig.update_layout(template="plotly_white", xaxis_title="Period", yaxis_title="Avg price")
    return fig


@app.callback(
    Output("ts-generation", "figure"),
    Input("state-primary", "value"),
    Input("state-compare", "value"),
)
def _update_generation(state_primary, state_compare):
    state_ids = [s for s in (state_primary, state_compare) if s]
    df = _get_generation(state_ids)
    if df.empty:
        return px.line(title="Total generation — no data").update_layout(template="plotly_white")
    fig = px.line(df, x="period", y="total_generation", color="stateid", title="Total generation")
    fig.update_layout(template="plotly_white", xaxis_title="Period", yaxis_title="Generation")
    return fig
