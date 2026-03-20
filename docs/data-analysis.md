# Analyzing Data

This guide covers three ways to explore and analyze the energy data: **DBeaver** (visual SQL tool), **Jupyter Lab** (Python notebooks with Claude AI), and **Claude.ai** (no-code, upload a CSV and ask questions in plain English).

---

## Option 1: DBeaver (visual SQL tool)

DBeaver is a free desktop app for exploring databases visually — browse tables, write SQL, and see results. No Python required.

### Connect to the database

1. Download [DBeaver Community](https://dbeaver.io/download/) (free)
2. Open DBeaver → New Database Connection
3. Choose **PostgreSQL** → Next
4. Fill in:
   - Host: `localhost`
   - Port: `5432`
   - Database: `ingest`
   - Username: `energy`
   - Password: `energy` (or whatever you set in `.env`)
5. Click **Test Connection** (it may ask to download a driver — say yes)
6. Finish

You should now see the `ingest` database with tables like `eia_retail_sales` in the left panel.

### Example queries to get started

```sql
-- Average electricity price by state, most recent year
SELECT stateid, AVG(price) AS avg_price_cents_per_kwh
FROM eia_retail_sales
WHERE period >= '2023-01-01'
  AND sectorid = 'RES'   -- residential customers
GROUP BY stateid
ORDER BY avg_price_cents_per_kwh DESC;

-- Monthly generation trend for California, all fuel types
SELECT period, fueltypeid, generation
FROM eia_electric_power_operational
WHERE stateid = 'CA'
  AND period >= '2020-01-01'
ORDER BY period, fueltypeid;

-- Which states import the most electricity?
SELECT stateid, AVG(net_interstate_trade) AS avg_net_import_mwh
FROM eia_state_source_disposition
WHERE period >= '2020-01-01'
GROUP BY stateid
ORDER BY avg_net_import_mwh ASC
LIMIT 10;
```

### Export from DBeaver

Right-click any query result → Export → CSV. Or use the command line:

```bash
make export TABLE=eia_retail_sales
make export TABLE=eia_retail_sales FILTER="stateid='TX'" OUT=exports/tx_retail.csv
```

Exported files go to the `exports/` folder at the project root.

---

## Option 2: Jupyter Lab (Python + Claude AI)

Jupyter Lab runs in your browser and lets you write Python code in cells, run them one at a time, and see results (including charts) immediately. The Claude AI assistant in the sidebar can write queries and code for you.

### Start Jupyter

```bash
# Via Docker (recommended — matches production environment)
make up
# Then open http://localhost:8888

# Or locally without Docker
make jupyter
```

### Query the database in a notebook

Create a new notebook (File → New → Notebook → Python 3) and run:

```python
import os
from energy_usa.db.dataframe import query_to_dataframe

url = os.environ["INGEST_DATABASE_URL"]

df = query_to_dataframe(url, """
    SELECT period, stateid, sectorid, price
    FROM eia_retail_sales
    WHERE stateid IN ('CA', 'TX', 'NY')
      AND sectorid = 'RES'
    ORDER BY period, stateid
""")

df.head(20)
```

`query_to_dataframe` runs any SQL and returns a pandas DataFrame — the standard Python table format that works with charts, exports, and calculations.

### Use Claude AI in Jupyter

Make sure `ANTHROPIC_API_KEY` is set in your `.env` file. Then:

1. Look for the **✦** (sparkle) icon in the left sidebar — this opens the Claude chat panel
2. Ask it questions about your notebook or data:

```
The dataframe `df` has columns: period, stateid, sectorid, price.
Write Python code to plot average monthly price for CA vs TX as a line chart.
```

Or use the `%%ai` magic directly in a cell:

```python
%%ai anthropic:claude-sonnet-4-6
I have a dataframe called `df` with columns: period (date), stateid (state code),
sales (MWh). What are the top 5 states by total sales? Show me the pandas code.
```

### Save a chart

```python
import plotly.express as px

fig = px.line(df, x="period", y="price", color="stateid",
              title="Residential Electricity Price: CA vs TX vs NY")
fig.write_html("exports/price_comparison.html")  # interactive
fig.write_image("exports/price_comparison.png")  # static
fig.show()
```

---

## Option 3: Claude.ai with a CSV export (no coding required)

The simplest approach — no Python, no SQL, no setup. Export a slice of data to a CSV file and upload it directly to Claude.ai.

### Step 1: Export the data

```bash
# All California electricity sales
make export TABLE=eia_retail_sales FILTER="stateid='CA'" OUT=exports/ca_retail.csv

# National data for a specific year
make export TABLE=eia_retail_sales FILTER="period >= '2023-01-01' AND period < '2024-01-01'" OUT=exports/2023_retail.csv

# Generation by fuel type for Texas
make export TABLE=eia_electric_power_operational FILTER="stateid='TX'" OUT=exports/tx_generation.csv
```

### Step 2: Upload to Claude.ai

1. Go to [claude.ai](https://claude.ai) and start a new conversation
2. Click the paperclip icon and attach your CSV file
3. Ask questions in plain English:

> "What state has the highest average electricity price? Show me a summary table."

> "Is there a trend in California's solar generation over time? What does the data show?"

> "Which sectors use the most electricity? Compare residential vs commercial vs industrial."

> "Can you suggest what might explain the spike in Texas electricity prices in February 2021?"

Claude can read the data, calculate statistics, identify trends, and suggest explanations — all without any coding on your part.

### Tips for better results

- **Keep exports focused** — filter to the state, date range, or sector you care about. A 10,000-row file is easier for Claude to work with than a 10-million-row full table.
- **Describe the columns** — Claude can figure out most things, but telling it "the `sectorid` column uses codes like RES=residential, COM=commercial" gets better answers faster.
- **Ask follow-up questions** — Claude remembers the context of the conversation, so you can build on previous answers.

---

## Understanding the data columns

### `eia_retail_sales`

| Column | Description | Units |
|--------|-------------|-------|
| `period` | First day of the month | Date |
| `stateid` | Two-letter state code (e.g. `CA`, `TX`) | — |
| `sectorid` | Customer sector: `RES` residential, `COM` commercial, `IND` industrial, `TRA` transport, `ALL` all sectors | — |
| `revenue` | Total revenue from electricity sales | Thousand dollars |
| `sales` | Total electricity sold | Million kWh |
| `price` | Average retail price | Cents per kWh |
| `customers` | Number of customers | Count |

### `eia_electric_power_operational`

| Column | Description | Units |
|--------|-------------|-------|
| `period` | First day of the month | Date |
| `stateid` | State code | — |
| `sectorid` | Generator sector | — |
| `fueltypeid` | Fuel type: `COL` coal, `NG` natural gas, `NUC` nuclear, `WND` wind, `SUN` solar, `HYC` hydro, etc. | — |
| `generation` | Electricity generated | Thousand MWh |

### `eia_state_source_disposition`

| Column | Description | Units |
|--------|-------------|-------|
| `period` | First day of the month | Date |
| `stateid` | State code | — |
| `net_interstate_trade` | Net electricity imported from other states (negative = net exporter) | Thousand MWh |
| `total_disposition` | Total electricity disposed of (sales + losses + exports) | Thousand MWh |

### `eia_state_summary`

| Column | Description | Units |
|--------|-------------|-------|
| `period` | January 1st of the year (annual data) | Date |
| `stateid` | State code | — |
| `average_retail_price` | Annual average retail price | Cents per kWh |
| `total_generation` | Total electricity generated in the state | Thousand MWh |
| `total_consumption` | Total electricity consumed in the state | Thousand MWh |
