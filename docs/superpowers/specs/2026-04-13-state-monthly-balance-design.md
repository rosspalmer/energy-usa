# electricity.state_monthly_balance

Wide table giving a complete picture of each state's electricity supply, trade,
and consumption for every month — production broken out by fuel type,
international trade (gross), interstate trade (net), and consumption by retail
sector.

## Grain

One row per **(state, period)** — state × month.

## Source tables

| Table | Role | Grain |
|-------|------|-------|
| `eia.electric_power_operational` | Production by fuel type | state × month × sector × fueltype |
| `eia.state_source_disposition` | Trade + supply/disposition totals | state × month |
| `eia.retail_sales` | Consumption by retail sector | state × month × sector |

## Ingest spec changes

`eia.state_source_disposition` currently captures only `net_interstate_trade`
and `total_disposition`. The following columns must be added to the ingest spec
(`specs/ingest/eia.md`, section `state_source_disposition`) and to the DDL at
`docker/postgres/init/ingest/eia/state_source_disposition.sql`:

| New column | API field | Type |
|------------|-----------|------|
| total_net_generation | total-net-generation | NUMERIC |
| total_international_imports | total-international-imports | NUMERIC |
| total_international_exports | total-international-exports | NUMERIC |
| total_supply | total-supply | NUMERIC |
| estimated_losses | estimated-losses | NUMERIC |

After updating the spec and DDL, regenerate the ingest artifacts:

```bash
make generate-ingest SOURCE=eia GDATASET=state_source_disposition
```

Then re-backfill the table to pick up the new columns:

```bash
make backfill DATASET=state_source_disposition START=2020-01 END=2026-04
```

## Output columns

### Production (from `eia.electric_power_operational`)

Generation is summed across all `sectorid` values for each fuel type so the
column reflects total state production regardless of producer category (utility,
IPP, CHP, etc.).

| Column | fueltypeid filter | Type |
|--------|-------------------|------|
| gen_coal_mwh | COW | NUMERIC |
| gen_natural_gas_mwh | NG | NUMERIC |
| gen_nuclear_mwh | NUC | NUMERIC |
| gen_hydro_mwh | HYC | NUMERIC |
| gen_solar_mwh | SUN | NUMERIC |
| gen_wind_mwh | WND | NUMERIC |
| gen_geothermal_mwh | GEO | NUMERIC |
| gen_biomass_mwh | BIO | NUMERIC |
| gen_petroleum_mwh | PEL, PC | NUMERIC |
| gen_other_mwh | OOG, AOR | NUMERIC |

### Production rollups (derived)

| Column | Logic | Type |
|--------|-------|------|
| gen_fossil_mwh | coal + natural_gas + petroleum | NUMERIC |
| gen_renewable_mwh | hydro + solar + wind + geothermal + biomass | NUMERIC |
| gen_total_mwh | from `state_source_disposition.total_net_generation` | NUMERIC |

### Trade (from `eia.state_source_disposition`)

| Column | Source field | Notes | Type |
|--------|-------------|-------|------|
| international_imports_mwh | total_international_imports | Gross from Canada/Mexico | NUMERIC |
| international_exports_mwh | total_international_exports | Gross to Canada/Mexico | NUMERIC |
| net_interstate_trade_mwh | net_interstate_trade | Negative = net importer | NUMERIC |
| total_supply_mwh | total_supply | Generation + all imports | NUMERIC |

### Consumption (from `eia.retail_sales`)

Sales are summed per sector. The `ALL` sectorid row from EIA gives the
pre-computed total; if it is absent, fall back to summing the individual sectors.

| Column | sectorid filter | Type |
|--------|-----------------|------|
| consumption_residential_mwh | RES | NUMERIC |
| consumption_commercial_mwh | COM | NUMERIC |
| consumption_industrial_mwh | IND | NUMERIC |
| consumption_transportation_mwh | TRA | NUMERIC |
| consumption_other_mwh | OTH | NUMERIC |
| consumption_total_mwh | ALL (or sum of above) | NUMERIC |

### Losses and metadata

| Column | Source | Type |
|--------|--------|------|
| estimated_losses_mwh | state_source_disposition.estimated_losses | NUMERIC |
| transformed_at | now() | TIMESTAMPTZ |

## Unique key

```sql
PRIMARY KEY (state, period)
```

## Transform join logic

`state_source_disposition` is the anchor table (one row per state × month).
LEFT JOIN the other two sources on `(stateid, period)`:

1. **Generation pivot** — query `electric_power_operational`, GROUP BY
   (stateid, period), pivot `fueltypeid` into columns via conditional
   aggregation (`SUM CASE WHEN fueltypeid = 'COW' THEN generation END`).
2. **Consumption pivot** — query `retail_sales`, GROUP BY (stateid, period),
   pivot `sectorid` into columns the same way.
3. **Join** — LEFT JOIN generation CTE and consumption CTE onto
   `state_source_disposition` on (stateid, period).
4. **Derived columns** — compute `gen_fossil_mwh`, `gen_renewable_mwh` from
   the pivoted fuel columns.

## Files to create / modify

| File | Action |
|------|--------|
| `specs/ingest/eia.md` (state_source_disposition section) | Add 5 new columns |
| `docker/postgres/init/ingest/eia/state_source_disposition.sql` | Add 5 columns to DDL |
| `src/energy_usa/db/ingest/eia/state_source_disposition.py` | Add new columns to upsert |
| `src/energy_usa/flows/ingest/eia/state_source_disposition.py` | Add new data[] fields |
| `specs/transform/electricity.md` | Add state_monthly_balance section |
| `docker/postgres/init/transform/electricity/state_monthly_balance.sql` | CREATE TABLE DDL |
| `src/energy_usa/db/transform/electricity/state_monthly_balance.py` | Query + upsert functions |
| `src/energy_usa/flows/transform/electricity.py` | Add new task + register in flow |
