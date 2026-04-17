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
