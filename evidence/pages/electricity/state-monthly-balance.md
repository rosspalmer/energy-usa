---
title: State Monthly Electricity Balance
---

This report breaks down the supply and demand balance for a single state
using monthly data from EIA. Use the dropdown to pick a state; every chart
and headline number updates in place.

<Dropdown
  name=state
  data={states}
  value=state
  label=state
  title="State"
  defaultValue="CA"
/>

<DateRange
  name=range
  title="Date range"
  defaultValue="Last 5 Years"
/>

```sql states
select distinct state
from electricity.state_monthly_balance
order by state
```

```sql latest
select *
from electricity.state_monthly_balance
where state = '${inputs.state.value}'
order by period desc
limit 1
```

In **{inputs.state.value}**, the most recent month on record is
**{latest[0].period}**. The state generated
**{latest[0].gen_total_mwh}** MWh of electricity that month. Fossil sources
contributed **{latest[0].gen_fossil_mwh}** MWh, renewables
**{latest[0].gen_renewable_mwh}** MWh, and nuclear
**{latest[0].gen_nuclear_mwh}** MWh. Retail customers consumed
**{latest[0].consumption_total_mwh}** MWh.

<BigValue
  data={latest}
  value=gen_total_mwh
  title="Total generation (MWh)"
  fmt="#,##0"
/>

<BigValue
  data={latest}
  value=net_interstate_trade_mwh
  title="Net interstate trade (MWh)"
  fmt="#,##0"
/>

<BigValue
  data={latest}
  value=consumption_total_mwh
  title="Total consumption (MWh)"
  fmt="#,##0"
/>

<BigValue
  data={latest}
  value=estimated_losses_mwh
  title="Estimated losses (MWh)"
  fmt="#,##0"
/>

## Generation mix over time

Stacked area chart of monthly generation (MWh) by fuel type.

```sql gen_mix
select
  period,
  gen_coal_mwh          as coal,
  gen_natural_gas_mwh   as natural_gas,
  gen_nuclear_mwh       as nuclear,
  gen_hydro_mwh         as hydro,
  gen_solar_mwh         as solar,
  gen_wind_mwh          as wind,
  gen_geothermal_mwh    as geothermal,
  gen_biomass_mwh       as biomass,
  gen_petroleum_mwh     as petroleum
from electricity.state_monthly_balance
where state = '${inputs.state.value}'
  and period between '${inputs.range.start}' and '${inputs.range.end}'
order by period
```

<AreaChart
  data={gen_mix}
  x=period
  y={["coal","natural_gas","nuclear","hydro","solar","wind","geothermal","biomass","petroleum"]}
  type=stacked
  yFmt="#,##0"
  title="Generation by fuel type"
/>

```sql gen_mix_summary
with ranked as (
  select
    case
      when gen_coal_mwh        = gen_total_mwh then 'coal'
      when gen_natural_gas_mwh = gen_total_mwh then 'natural gas'
      when gen_nuclear_mwh     = gen_total_mwh then 'nuclear'
      when gen_hydro_mwh       = gen_total_mwh then 'hydro'
      when gen_solar_mwh       = gen_total_mwh then 'solar'
      when gen_wind_mwh        = gen_total_mwh then 'wind'
      else (
        select fuel from (values
          ('coal',        gen_coal_mwh),
          ('natural gas', gen_natural_gas_mwh),
          ('nuclear',     gen_nuclear_mwh),
          ('hydro',       gen_hydro_mwh),
          ('solar',       gen_solar_mwh),
          ('wind',        gen_wind_mwh),
          ('geothermal',  gen_geothermal_mwh),
          ('biomass',     gen_biomass_mwh),
          ('petroleum',   gen_petroleum_mwh)
        ) as f(fuel, amt)
        order by amt desc nulls last
        limit 1
      )
    end as top_fuel,
    round(100.0 * gen_renewable_mwh / nullif(gen_total_mwh, 0), 1) as renewable_share,
    period
  from electricity.state_monthly_balance
  where state = '${inputs.state.value}'
  order by period desc
  limit 1
)
select * from ranked
```

In the most recent month, the largest single fuel source in
**{inputs.state.value}** was **{gen_mix_summary[0].top_fuel}**. Renewables
supplied **{gen_mix_summary[0].renewable_share}%** of generation.

## Fossil vs renewable vs nuclear

A simpler view of the same data grouped into three derived rollups.

```sql gen_rollup
select
  period,
  gen_fossil_mwh    as fossil,
  gen_renewable_mwh as renewable,
  gen_nuclear_mwh   as nuclear
from electricity.state_monthly_balance
where state = '${inputs.state.value}'
  and period between '${inputs.range.start}' and '${inputs.range.end}'
order by period
```

<AreaChart
  data={gen_rollup}
  x=period
  y={["fossil","renewable","nuclear"]}
  type=stacked
  yFmt="#,##0"
  title="Generation rollup"
/>

```sql rollup_summary
with latest as (
  select *
  from electricity.state_monthly_balance
  where state = '${inputs.state.value}'
  order by period desc
  limit 1
),
yoy as (
  select gen_renewable_mwh
  from electricity.state_monthly_balance
  where state = '${inputs.state.value}'
    and period = (select period - interval '1 year' from latest)
)
select
  round(100.0 * latest.gen_fossil_mwh    / nullif(latest.gen_total_mwh,0), 1) as fossil_share,
  round(100.0 * latest.gen_renewable_mwh / nullif(latest.gen_total_mwh,0), 1) as renewable_share,
  round(100.0 * latest.gen_nuclear_mwh   / nullif(latest.gen_total_mwh,0), 1) as nuclear_share,
  round(100.0 * (latest.gen_renewable_mwh - yoy.gen_renewable_mwh) / nullif(yoy.gen_renewable_mwh, 0), 1) as renewable_yoy_pct
from latest, yoy
```

Fossil fuels currently supply **{rollup_summary[0].fossil_share}%** of
generation, renewables **{rollup_summary[0].renewable_share}%**, and nuclear
**{rollup_summary[0].nuclear_share}%**. Renewable output is
**{rollup_summary[0].renewable_yoy_pct}%** year-over-year.

## Supply & trade

Where the state's electricity comes from when generation alone doesn't
balance demand. International imports and exports are typically small;
interstate trade is usually the bigger lever.

```sql supply_trade
select
  period,
  total_supply_mwh              as total_supply,
  international_imports_mwh     as intl_imports,
  international_exports_mwh     as intl_exports,
  net_interstate_trade_mwh      as net_interstate
from electricity.state_monthly_balance
where state = '${inputs.state.value}'
  and period between '${inputs.range.start}' and '${inputs.range.end}'
order by period
```

<LineChart
  data={supply_trade}
  x=period
  y={["total_supply","intl_imports","intl_exports","net_interstate"]}
  yFmt="#,##0"
  title="Supply and trade (MWh)"
/>

```sql trade_summary
with latest as (
  select *
  from electricity.state_monthly_balance
  where state = '${inputs.state.value}'
  order by period desc
  limit 1
)
select
  case when net_interstate_trade_mwh < 0 then 'importer' else 'exporter' end as direction,
  abs(net_interstate_trade_mwh) as net_interstate_abs,
  international_imports_mwh      as intl_imports,
  international_exports_mwh      as intl_exports
from latest
```

In the most recent month, **{inputs.state.value}** was a net
**{trade_summary[0].direction}** of
**{trade_summary[0].net_interstate_abs}** MWh across state lines.
International trade totaled **{trade_summary[0].intl_imports}** MWh of
imports and **{trade_summary[0].intl_exports}** MWh of exports.

## Consumption by sector

Retail sales broken out by customer class. Residential and commercial
demand swap the top spot seasonally; industrial demand is typically flatter
year-round.

```sql consumption
select
  period,
  consumption_residential_mwh    as residential,
  consumption_commercial_mwh     as commercial,
  consumption_industrial_mwh     as industrial,
  consumption_transportation_mwh as transportation,
  consumption_other_mwh          as other
from electricity.state_monthly_balance
where state = '${inputs.state.value}'
  and period between '${inputs.range.start}' and '${inputs.range.end}'
order by period
```

<AreaChart
  data={consumption}
  x=period
  y={["residential","commercial","industrial","transportation","other"]}
  type=stacked
  yFmt="#,##0"
  title="Retail consumption by sector"
/>

```sql consumption_summary
with latest as (
  select *
  from electricity.state_monthly_balance
  where state = '${inputs.state.value}'
  order by period desc
  limit 1
),
top_sector as (
  select sector, amt
  from (
    select 'residential'    as sector, consumption_residential_mwh    as amt from latest
    union all select 'commercial',     consumption_commercial_mwh     from latest
    union all select 'industrial',     consumption_industrial_mwh     from latest
    union all select 'transportation', consumption_transportation_mwh from latest
    union all select 'other',          consumption_other_mwh          from latest
  ) s
  order by amt desc nulls last
  limit 1
)
select
  latest.consumption_total_mwh as total_mwh,
  top_sector.sector             as top_sector,
  round(100.0 * top_sector.amt / nullif(latest.consumption_total_mwh, 0), 1) as top_sector_share
from latest, top_sector
```

Of the **{consumption_summary[0].total_mwh}** MWh consumed in the most
recent month, the largest sector was **{consumption_summary[0].top_sector}**
at **{consumption_summary[0].top_sector_share}%** of the total.

## Balance check

A sanity check on the underlying EIA data. Supply side is generation plus
net imports; demand side is retail consumption plus estimated losses. They
should roughly match.

```sql balance
select
  period,
  (gen_total_mwh
    + coalesce(net_interstate_trade_mwh, 0)
    + coalesce(international_imports_mwh, 0)
    - coalesce(international_exports_mwh, 0)) as supply_side,
  (coalesce(consumption_total_mwh, 0)
    + coalesce(estimated_losses_mwh, 0))       as demand_side
from electricity.state_monthly_balance
where state = '${inputs.state.value}'
  and period between '${inputs.range.start}' and '${inputs.range.end}'
order by period
```

<LineChart
  data={balance}
  x=period
  y={["supply_side","demand_side"]}
  yFmt="#,##0"
  title="Supply vs demand side (MWh)"
/>

```sql balance_summary
select
  round(
    avg(
      100.0 * abs(supply_side - demand_side) / nullif((supply_side + demand_side) / 2.0, 0)
    ),
    2
  ) as residual_pct
from (
  select
    (gen_total_mwh
      + coalesce(net_interstate_trade_mwh, 0)
      + coalesce(international_imports_mwh, 0)
      - coalesce(international_exports_mwh, 0)) as supply_side,
    (coalesce(consumption_total_mwh, 0)
      + coalesce(estimated_losses_mwh, 0))       as demand_side
  from electricity.state_monthly_balance
  where state = '${inputs.state.value}'
    and period between '${inputs.range.start}' and '${inputs.range.end}'
) b
```

Supply and demand match to within **{balance_summary[0].residual_pct}%** on
average across the selected date range. Residuals come from rounding,
reporting lag, and consumption categories not captured in retail sales
(e.g. behind-the-meter generation for own-use).
