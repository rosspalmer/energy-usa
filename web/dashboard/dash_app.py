"""
State electricity Dash app: price, generation, consumption by state over time.
Data from Postgres ingest database (eia_retail_sales, eia_electric_power_operational, eia_state_summary).
"""
from django.db import connections
from django.db.utils import OperationalError
from django_plotly_dash import DjangoDash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd

# Gas-station brand palette — teal primary, red accent
BRAND_COLORS = ["#008b8b", "#c41e3a", "#20b2aa", "#e85a6b", "#005f5f", "#8b1224"]
CHART_TEMPLATE = "plotly_white"


def _get_ingest_status():
    """Return {"ok": True} or {"ok": False, "error": "..."} for ingest DB availability."""
    try:
        conn = connections["ingest"]
    except KeyError:
        return {
            "ok": False,
            "error": "Ingest database not configured. Check INGEST_DATABASE_URL.",
        }
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
    except OperationalError as e:
        return {
            "ok": False,
            "error": "Cannot connect to ingest database or tables missing. Check INGEST_DATABASE_URL and that migrations/ingest have been run.",
        }
    return {"ok": True}


# Table name -> Prefect flow name for empty-table messages
_TABLE_FLOWS = {
    "eia_retail_sales": "ingest_eia_retail_sales",
    "eia_electric_power_operational": "ingest_eia_electric_power_operational",
    "eia_state_summary": "ingest_eia_state_summary",
}


def _get_data_status():
    """Return {"ingest_error": None|str, "tables": {table: count}}. Uses _get_ingest_status()."""
    status = _get_ingest_status()
    if not status.get("ok"):
        return {"ingest_error": status.get("error", "Unknown error"), "tables": {}}
    tables = {}
    try:
        with connections["ingest"].cursor() as cur:
            for table in _TABLE_FLOWS:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                tables[table] = cur.fetchone()[0]
    except (KeyError, OperationalError) as e:
        return {"ingest_error": "Cannot read ingest tables.", "tables": {}}
    return {"ingest_error": None, "tables": tables}


app = DjangoDash("StateElectricity")

# Layout: data-status banner, then title, state selector, graphs
app.layout = html.Div(
    [
        html.Div(id="data-status-banner", style={"marginBottom": "1rem"}),
        dcc.Store(id="data-status-store", data=None),
        html.H2("State electricity: price, generation, consumption", className="dashboard-title"),
        html.Div(
            [
                html.Label("State (primary):"),
                dcc.Dropdown(id="state-primary", placeholder="Select state", clearable=False),
                html.Label("Compare (optional):"),
                dcc.Dropdown(id="state-compare", placeholder="Select state to compare", clearable=True),
                html.Div(id="state-empty-msg", style={"width": "100%", "marginTop": "0.5rem"}),
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


def _render_data_status_banner(status):
    """Return Dash children for data-status-banner from _get_data_status() result."""
    if status.get("ingest_error"):
        return html.Div(
            [
                html.Strong("Data status: "),
                status["ingest_error"],
            ],
            className="dashboard-container",
            style={
                "padding": "0.75rem 1rem",
                "borderRadius": "var(--radius-base, 8px)",
                "background": "var(--color-card-bg, #f8fafa)",
                "borderLeft": "4px solid var(--color-accent-red, #c41e3a)",
            },
        )
    tables = status.get("tables") or {}
    empty = [t for t, n in tables.items() if n == 0]
    if not empty:
        return []
    lines = []
    for table in empty:
        flow = _TABLE_FLOWS.get(table, table)
        lines.append(html.Li([f"No data in {table}. Run Prefect flow: ", html.Strong(flow)]))
    return html.Div(
        [
            html.Strong("Data status: "),
            "Some tables are empty. ",
            html.Ul(lines, style={"margin": "0.5rem 0 0 1rem", "paddingLeft": "1rem"}),
        ],
        className="dashboard-container",
        style={
            "padding": "0.75rem 1rem",
            "borderRadius": "var(--radius-base, 8px)",
            "background": "var(--color-card-bg, #f8fafa)",
            "borderLeft": "4px solid var(--color-accent-teal, #008b8b)",
        },
    )


def _get_states():
    """Return list of state IDs from eia_retail_sales. On DB error returns []."""
    try:
        with connections["ingest"].cursor() as cur:
            cur.execute("SELECT DISTINCT stateid FROM eia_retail_sales ORDER BY stateid")
            return [row[0] for row in cur.fetchall()]
    except (KeyError, OperationalError):
        return []


def _get_retail_price(state_ids):
    """Fetch average price by period for given states from eia_retail_sales (residential)."""
    if not state_ids:
        return pd.DataFrame()
    try:
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
    except (KeyError, OperationalError):
        return pd.DataFrame()


def _get_generation(state_ids):
    """Fetch total generation by period and state from eia_electric_power_operational."""
    if not state_ids:
        return pd.DataFrame()
    try:
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
    except (KeyError, OperationalError):
        return pd.DataFrame()


def _get_summary_consumption(state_ids):
    """Fetch total_consumption / average_retail_price by period from eia_state_summary."""
    if not state_ids:
        return pd.DataFrame()
    try:
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
    except (KeyError, OperationalError):
        return pd.DataFrame()


@app.callback(
    Output("data-status-banner", "children"),
    Output("data-status-store", "data"),
    Input("states-store", "data"),
)
def _update_data_status_banner(_):
    """On load, compute data status and show banner if ingest error or empty tables."""
    status = _get_data_status()
    banner = _render_data_status_banner(status)
    return banner, status


@app.callback(
    Output("state-primary", "options"),
    Output("state-compare", "options"),
    Output("state-empty-msg", "children"),
    Input("states-store", "data"),
)
def _set_state_options(_):
    states = _get_states()
    opts = [{"label": s, "value": s} for s in states]
    if not states:
        empty_msg = html.Div(
            [
                "No states available. The state list comes from ",
                html.Strong("eia_retail_sales"),
                ". Run the ",
                html.Strong("ingest_eia_retail_sales"),
                " Prefect flow, then refresh.",
            ],
            style={"color": "var(--color-text)", "fontSize": "0.95rem"},
        )
        return opts, opts, empty_msg
    return opts, opts, []


@app.callback(
    Output("state-primary", "value"),
    Input("state-primary", "options"),
)
def _set_primary_default(options):
    if options and len(options) > 0:
        return options[0]["value"]
    return None


def _apply_brand_style(fig):
    """Apply gas-station colors and consistent layout to a Plotly figure."""
    fig.update_layout(
        template=CHART_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#f8fafa",
        font={"family": "system-ui, sans-serif", "color": "#1a1a1a"},
        title_font={"family": "Georgia, serif", "color": "#008b8b"},
        legend={"bgcolor": "rgba(0,0,0,0)"},
    )
    # Apply brand color sequence to each trace in order
    for i, trace in enumerate(fig.data):
        color = BRAND_COLORS[i % len(BRAND_COLORS)]
        trace.update(line={"color": color, "width": 2})
    return fig


@app.callback(
    Output("ts-price", "figure"),
    Input("state-primary", "value"),
    Input("state-compare", "value"),
)
def _update_price(state_primary, state_compare):
    state_ids = [s for s in (state_primary, state_compare) if s]
    df = _get_retail_price(state_ids)
    if df.empty:
        return px.line(title="Retail price (residential) — no data").update_layout(template=CHART_TEMPLATE)
    fig = px.line(
        df, x="period", y="avg_price", color="stateid",
        title="Retail price (residential, ¢/kWh)",
        color_discrete_sequence=BRAND_COLORS,
    )
    fig.update_layout(xaxis_title="Period", yaxis_title="Avg price (¢/kWh)")
    return _apply_brand_style(fig)


@app.callback(
    Output("ts-generation", "figure"),
    Input("state-primary", "value"),
    Input("state-compare", "value"),
)
def _update_generation(state_primary, state_compare):
    state_ids = [s for s in (state_primary, state_compare) if s]
    df = _get_generation(state_ids)
    if df.empty:
        return px.line(title="Total generation — no data").update_layout(template=CHART_TEMPLATE)
    fig = px.line(
        df, x="period", y="total_generation", color="stateid",
        title="Total electricity generation (MWh)",
        color_discrete_sequence=BRAND_COLORS,
    )
    fig.update_layout(xaxis_title="Period", yaxis_title="Generation (MWh)")
    return _apply_brand_style(fig)
