# Open Energy Data Sources in the United States

This document provides detailed information on open data sources for energy within the United States. These datasets should provide information on one of the following categories:

- Production: Ability to produce energy whether direct electrical or resources which can be converted to energy like gas
- Consumption: Expenditure of energy source whether direct electrical or resource
- Transmission: Ability to transmit energy across districts and regions
- Expansion: Forecasted ability to expand production of energy sources
- Consumption Price: Market price of energy sources for consumer 
- Production Cost: Different components of costs 
    - Fuel: The price of raw materials (e.g., coal, natural gas, oil, uranium) needed for energy production.
    - Capital: Investments in infrastructure, such as power plants, renewable energy installations, and transmission lines. This includes costs for construction, equipment, and financing.
    - Operation and Maintenance: Ongoing expenses associated with running and maintaining energy facilities, including labor, repairs, and routine maintenance.
    - Environmental Compliance: Expenses related to meeting environmental regulations, such as emissions controls and pollution mitigation.
    - Transmission and Distribution: Costs incurred in transporting electricity from power plants to end-users, including infrastructure, maintenance, and energy losses.
    - Insurance and Risk Management: Premiums paid for insuring the facilities against potential risks (e.g., natural disasters, accidents).
    - Decommissioning: Costs anticipated for dismantling facilities and restoring sites once they are no longer in operation.
    - Financing: Interest on loans and financing for the initial capital outlay required for construction and development.
    - Government Fees and Taxes: Costs related to licenses, permits, and taxes imposed by federal, state, or local authorities.

---

## 1. U.S. Energy Information Administration (EIA)

### Summary
The U.S. Energy Information Administration (EIA) is the statistical and analytical agency within the U.S. Department of Energy. It provides the most comprehensive collection of independent energy statistics and analysis for the U.S., covering all energy sources and sectors.

### Categories Provided
*   **Consumption:** Detailed breakdowns by residential, commercial, industrial, and transportation sectors.
*   **Production:** Generation data for fossil fuels, nuclear, and renewables (wind, solar, hydro).
*   **Transmission:** Hourly electric grid monitor provides data on interchange (power flow) between balancing authorities.
*   **Expansion:** Planned generator additions and retirements (Form 860).
*   **Consumption Price:** Retail electricity prices by sector and state.
*   **Production Cost:** Fuel costs and receipts (Form 923).
*   **Maintenance:** Operational status and capacity availability (implied through operating data).

### API Access
The EIA provides a robust, free Open Data API (v2) that uses a RESTful architecture.
*   **Endpoint:** `https://api.eia.gov/v2/`
*   **Documentation:** [EIA Open Data API](https://www.eia.gov/opendata/)
*   **Key Requirement:** Requires a free API key registration.

### Date Ranges
*   **Historical:** Extensive archives dating back to the 1970s/1980s for many datasets.
*   **Current:** Monthly and Annual updates for most aggregate reports.
*   **Real-Time:** Hourly data available for the electric grid.

### Accessibility Analysis
*   **Real-Time:** **High.** The Hourly Electric Grid Monitor is one of the few official sources for near real-time grid demand and generation mix.
*   **Current:** **High.** Monthly data is released with a consistent lag (usually 1-2 months).
*   **Historical:** **Excellent.** Deep archives available for long-term trend analysis.

### Datasets
1.  **Hourly Electric Grid Monitor**
    *   *Description:* Hourly electricity demand, generation by energy source, and interchange for the Lower 48 states.
    *   *Link:* [Hourly Grid Data](https://www.eia.gov/electricity/gridmonitor/)
    *   *Categories:* Consumption, Production
2.  **State Energy Data System (SEDS)**
    *   *Description:* Comprehensive annual time-series estimates of state-level energy production, consumption, prices, and expenditures.
    *   *Link:* [SEDS](https://www.eia.gov/state/seds/)
    *   *Categories:* Consumption, Production
3.  **Form EIA-860**
    *   *Description:* Annual generator-level data about existing and planned generators and associated environmental equipment.
    *   *Link:* [Form EIA-860](https://www.eia.gov/electricity/data/eia860/)
    *   *Categories:* Expansion, Production
4.  **Electric Power Monthly**
    *   *Description:* Monthly statistics on electricity production and consumption prices (retail).
    *   *Link:* [Electric Power Monthly](https://www.eia.gov/electricity/monthly/)
    *   *Categories:* Consumption Price, Production

---

## 2. National Renewable Energy Laboratory (NREL)

### Summary
NREL focuses on renewable energy efficiency and sustainable transportation. Their Developer Network offers APIs specifically useful for solar, wind, and transportation analysis.

### Categories Provided
*   **Production:** Solar and wind resource data, potential capacity.
*   **Consumption:** Alternative fuel vehicle data, building efficiency models.
*   **Production Cost:** Technology cost projections (Annual Technology Baseline) covering Capital and O&M.
*   **Expansion:** Projected capacity additions based on cost models.

### API Access
NREL offers a suite of APIs via their Developer Network.
*   **Endpoint:** `https://developer.nrel.gov/api/`
*   **Documentation:** [NREL Developer Network](https://developer.nrel.gov/)
*   **Key Requirement:** Requires a free API key.

### Date Ranges
*   **Historical:** Weather and solar irradiance data (multi-year averages).
*   **Projected:** Focuses heavily on modeled and projected performance data rather than real-time grid status.

### Accessibility Analysis
*   **Real-Time:** **Low.** Mostly static or modeled datasets.
*   **Current:** **Medium.** Regularly updated reference databases (e.g., station locations).
*   **Historical:** **Good.** Excellent for resource potential (e.g., "typical meteorological year").

### Example Datasets
1.  **PVWatts V8 API**
    *   *Description:* Estimates the energy production of grid-connected photovoltaic (PV) energy systems based on location and system specs.
    *   *Link:* [PVWatts API](https://developer.nrel.gov/docs/solar/pvwatts/v8/)
2.  **Annual Technology Baseline (ATB)**
    *   *Description:* Cost and performance data for renewable and conventional energy technologies, including CapEx and O&M.
    *   *Link:* [NREL ATB](https://atb.nrel.gov/)
    *   *Categories:* Production Cost (Capital, O&M), Expansion

---

## 3. Lawrence Berkeley National Laboratory (LBNL)

### Summary
LBNL provides critical reports and datasets on the status of U.S. energy markets, specifically focusing on renewables, cost trends, and interconnection.

### Categories Provided
*   **Production Cost:** Detailed installed price trends for solar (Tracking the Sun).
*   **Expansion:** Interconnection queue data showing the pipeline of energy projects.

### API Access
Data is primarily provided via downloadable files (CSV, Excel) and interactive visualizations.
*   **Portal:** [Electricity Markets & Policy](https://emp.lbl.gov/data)

### Date Ranges
*   **Historical:** Annual reports tracking trends over the last decade+.
*   **Current:** Annual releases.

### Accessibility Analysis
*   **Real-Time:** **None.**
*   **Historical:** **Excellent.** High-quality, cleaned datasets on project costs and queues.

### Example Datasets
1.  **Tracking the Sun**
    *   *Description:* Installed price trends for distributed photovoltaic systems in the United States.
    *   *Link:* [Tracking the Sun](https://emp.lbl.gov/tracking-the-sun)
    *   *Categories:* Production Cost (Capital)
2.  **Queued Up**
    *   *Description:* Data on power plants seeking interconnection to the transmission grid (active, withdrawn, and energized).
    *   *Link:* [Queued Up](https://emp.lbl.gov/queues)
    *   *Categories:* Expansion

---

## 4. EPA Emissions & Generation Resource Integrated Database (eGRID)

### Summary
eGRID is a comprehensive source of environmental characteristics of all electric power generated in the United States. It links air emissions data with electric generation data.

### Categories Provided
*   **Production:** Generation by fuel type at the plant level.
*   **Maintenance/Efficiency:** Heat rates and capacity factors imply plant efficiency and operational status.
*   **Production Cost:** Environmental compliance metrics (emissions rates).

### API Access
While eGRID is primarily distributed as Excel/CSV files, related data is accessible via the **Clean Air Markets Program Data (CAMD)** API.
*   **Source:** [EPA CAMD](https://www.epa.gov/airmarkets/cam-api-portal)
*   **Primary Access:** [eGRID Data Files](https://www.epa.gov/egrid/download-data)

### Date Ranges
*   **Historical:** 1996 – 2023 (Annual releases).
*   **Lag:** Significant reporting lag (usually 1-2 years behind current date).

### Accessibility Analysis
*   **Real-Time:** **None.**
*   **Current:** **Low.** Data is rigorous but not timely.
*   **Historical:** **Excellent.** The gold standard for analyzing the environmental impact of historical energy production.

### Example Datasets
1.  **eGRID2023**
    *   *Description:* The latest release containing 2023 data on plant-level emissions rates, net generation, and resource mix.
    *   *Link:* [eGRID2023 Summary Tables](https://www.epa.gov/egrid/summary-data)

---

## 5. Federal Energy Regulatory Commission (FERC)

### Summary
FERC regulates the transmission and wholesale sale of electricity and natural gas. Their data is critical for understanding the *legal and economic* structure of energy transmission and markets.

### Categories Provided
*   **Transmission:** Detailed filings on transmission planning and loads (Form 714).
*   **Production Cost:** Financial reports from major electric utilities (Form 1) covering O&M and Capital costs.
*   **Maintenance/Operations:** Reliability and service quality reports.

### API Access
FERC generally provides data via file downloads (eLibrary) rather than a modern JSON API. However, **eLibrary** allows searching and downloading filings.
*   **Access Point:** [FERC Online eLibrary](https://elibrary.ferc.gov/eLibrary/search)

### Date Ranges
*   **Historical:** Decades of regulatory filings.
*   **Current:** Filings are available shortly after submission deadlines.

### Accessibility Analysis
*   **Real-Time:** **Low.**
*   **Current:** **Medium.** Good for quarterly/annual regulatory checkups.
*   **Historical:** **High.** Deep legal and operational history.

### Example Datasets
1.  **Form 1**
    *   *Description:* Annual Report of Major Electric Utilities, Licensees and Others. Contains detailed financial and operational data (Balance Sheets, Income Statements, O&M expenses).
    *   *Link:* [Form 1 Data](https://www.ferc.gov/industries-data/electric/general-information/electric-industry-forms/form-1-annual-report-major)
    *   *Categories:* Production Cost (Capital, O&M, Financing)
2.  **Form 714**
    *   *Description:* Annual Electric Balancing Authority Area and Planning Area Report. Contains hourly system lambda (market price proxy) and load data.
    *   *Link:* [Form 714 Data](https://www.ferc.gov/industries-data/electric/general-information/electric-industry-forms/form-no-714-annual-electric/data)

---

## 6. ISO/RTO Public Data (PJM, CAISO, ERCOT, etc.)

### Summary
Independent System Operators (ISOs) and Regional Transmission Organizations (RTOs) manage the grid for roughly 2/3 of the US population. They publish granular data on market operations.

### Categories Provided
*   **Consumption Price:** Real-time and Day-Ahead Locational Marginal Pricing (LMP).
*   **Expansion:** Detailed interconnection queues.
*   **Transmission:** Outage data and constraints.

### API Access
Most ISOs have their own APIs or data portals (e.g., PJM Data Miner, CAISO OASIS).
*   **PJM:** [Data Miner 2](https://dataminer2.pjm.com/)
*   **CAISO:** [OASIS](http://oasis.caiso.com/mrioasis/logon.do)
*   **ERCOT:** [Grid Information](https://www.ercot.com/gridinfo)

### Accessibility Analysis
*   **Real-Time:** **Excellent.** Primary source for market prices.
*   **Historical:** **Good.** Archives usually available via CSV/API.

### Example Datasets
1.  **Locational Marginal Pricing (LMP)**
    *   *Description:* Wholesale electricity prices at specific nodes on the grid, reflecting the cost of energy, congestion, and losses.
    *   *Link:* Varies by ISO (e.g., [PJM LMP](https://dataminer2.pjm.com/feed/rt_hrl_lmps))
    *   *Categories:* Consumption Price

---

## 7. Open Energy Information (OpenEI)

### Summary
An open-source knowledge-sharing platform linked to the DOE. It aggregates data on utility rates, incentives, and other decentralized energy topics.

### Categories Provided
*   **Consumption Price:** Utility rates (tariffs) which drive consumption patterns.
*   **Expansion:** Database of incentives (DSIRE) for renewable adoption.

### API Access
OpenEI provides wiki-based APIs and specific dataset APIs.
*   **Endpoint:** `https://api.openei.org/`
*   **Documentation:** [OpenEI API](https://openei.org/wiki/Service:APIs)

### Date Ranges
*   **Current:** Rates and incentives are generally kept up to date by the community and contributors.

### Accessibility Analysis
*   **Real-Time:** **Low.**
*   **Current:** **High.** Best source for current utility pricing structures.
*   **Historical:** **Medium.**

### Example Datasets
1.  **U.S. Utility Rate Database**
    *   *Description:* Detailed structure of electricity rates for residential, commercial, and industrial customers across US utilities.
    *   *Link:* [URDB](https://openei.org/wiki/Utility_Rate_Database)

---

## 8. Electricity Maps (Open Source / Commercial Hybrid)

### Summary
While offering a commercial product, Electricity Maps provides free access for non-commercial use and open-sourced their visualization frontend. They aggregate real-time grid data from official sources (like EIA) into a unified format.

### Categories Provided
*   **Production:** Real-time generation mix.
*   **Transmission:** Cross-border exchange (imports/exports).
*   **Consumption:** Carbon intensity of consumed electricity.

### API Access
*   **Portal:** [Electricity Maps API](https://www.electricitymaps.com/data-portal)
*   **Note:** Free tier available for non-commercial/academic use.

### Date Ranges
*   **Real-Time:** Live data.
*   **Historical:** Available (often paid for granular history, but free recent history via UI/API tier).

### Accessibility Analysis
*   **Real-Time:** **Excellent.** Best-in-class visualization of live grid status.
*   **Historical:** **Good.**
*   **Current:** **Excellent.**

### Example Datasets
1.  **US Carbon Intensity**
    *   *Description:* Live CO2 emissions intensity (gCO2eq/kWh) for US regional grids (PJM, CAISO, ERCOT, etc.).
    *   *Link:* [Electricity Maps App](https://app.electricitymaps.com/map)
