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
