# **The Architecture of American Energy Data: A Comprehensive Assessment of Regional Pricing Systems and API-Driven Access**

The landscape of energy pricing data in the United States represents a complex, multi-tiered architecture that reflects the nation’s fragmented regulatory and operational history. For the energy market participant, researcher, or software developer, navigating this ecosystem requires a sophisticated understanding of how federal oversight, regional market operation, and retail utility governance intersect to produce high-frequency and historical data streams. In the modern era, the shift toward algorithmic trading, decentralized energy resources, and grid modernization has necessitated a transition from static reports to dynamic, machine-readable data accessible via Application Programming Interfaces (APIs). This evolution allows for the automation of complex economic models, real-time grid monitoring, and long-term forecasting, provided that the user can reconcile the varying temporal, geographical, and technical standards employed by different data providers.1

At the apex of this hierarchy sit federal agencies like the Energy Information Administration (EIA) and the Federal Energy Regulatory Commission (FERC), which serve as the primary repositories for historical, statistical, and transactional data across the entire country. Complementing these are the Independent System Operators (ISOs) and Regional Transmission Organizations (RTOs), which manage the day-to-day and sub-hourly fluctuations of wholesale electricity markets in deregulated regions. Finally, at the retail level, organizations like the National Renewable Energy Laboratory (NREL) and private aggregators provide the granular utility-specific rate structures that govern the costs seen by end-use consumers. Understanding the mechanisms of these sources is essential for anyone seeking to build a comprehensive picture of the American energy economy.5

## **The Federal Foundation: The Energy Information Administration API Ecosystem**

The U.S. Energy Information Administration (EIA) serves as the primary statistical authority for the nation’s energy sector. Its mission is to collect, analyze, and disseminate independent energy information to promote sound policymaking, efficient markets, and public understanding.1 For developers and data scientists, the EIA’s most critical offering is its Open Data platform, which provides a gateway to millions of data points covering petroleum, natural gas, electricity, coal, and renewable energy.5 The launch of the EIA API v2 in November 2022, internally referred to as the "Clementia" release, represented a significant modernization of this infrastructure, moving toward a fully RESTful implementation with a logical dataset hierarchy.2

### **Technical Architecture and Data Hierarchy of API v2**

The API v2 is organized into a hierarchical structure where child datasets can be discovered by querying their parent nodes. This programmatic discovery feature is essential for navigating the vast volume of data held by the agency. The system utilizes "facets," which are essentially customizable filters that allow users to specify exactly which dimensions of the data they wish to retrieve.2 For instance, a query for electricity pricing can be narrowed down by state, sector (residential, commercial, industrial), and frequency (monthly, annual).2

| API Parent Node | Sub-Datasets Available | Data Scope and Origins |
| :---- | :---- | :---- |
| /electricity | Retail sales, state profiles, RTO data, operational stats | Forms EIA-861, 861M, 923 |
| /natural-gas | Prices by sector, storage, consumption, imports/exports | Surveys of distributors and storage operators |
| /petroleum | Spot prices, retail gasoline, diesel, stocks, refinery output | Weekly Petroleum Status Reports |
| /coal | Prices, production, reserves, distribution | Quarterly Coal Reports |
| /total-energy | Integrated summaries across all sources | Monthly Energy Review |

The technical specifications of the API v2 allow for highly efficient data retrieval. The system supports JSON as the primary output format, with XML available for smaller requests. Users can specify up to 5,000 rows in a single JSON return, and the system includes advanced sorting and pagination features via the sort, length, and offset parameters.2 For historical analysis, the EIA is unparalleled; it provides annual state-level data for various energy sources dating back to 1960, and price data in dollars per million Btu from 1970 forward.5

### **Electricity Retail Sales and Pricing Granularity**

Within the /electricity route, the retail-sales endpoint is the most frequently accessed for pricing information. This dataset aggregates information from Form EIA-861 (Annual Electric Power Industry Report) and Form EIA-861M (Monthly Electric Power Industry Report).2 These forms collect data from every electric utility in the country, including investor-owned, municipal, and cooperative entities. The data provided includes total revenue, sales in megawatthours, customer counts, and the average price (calculated as revenue divided by sales).2

Analysts using this API must understand the distinction between the "price" reported by the EIA and a "tariff" found in a utility bill. The EIA price is an ex-post average reflecting what was actually paid across an entire sector, whereas a tariff is the ex-ante rate structure that determines those costs.9 This makes the EIA data excellent for longitudinal studies of economic trends, but less suitable for real-time cost-of-service calculations at the individual meter level. To facilitate regional analysis, the EIA provides state-level IDs (e.g., facets\[stateid\]=NY) and sector IDs (e.g., facets\[sectorid\]=RES for residential).2

## **Regulatory Transparency: FERC and the Electric Quarterly Report System**

While the EIA focuses on statistical aggregation, the Federal Energy Regulatory Commission (FERC) provides transparency into the actual wholesale transactions that occur between market participants. The primary mechanism for this is the Electric Quarterly Report (EQR), a reporting requirement established under Section 205(c) of the Federal Power Act.10 Any entity that makes jurisdictional sales of electricity—meaning sales for resale in interstate commerce—must file an EQR summarizing their contractual terms and transaction details.10

### **The Granularity of EQR Transactional Data**

The EQR database is unique in its depth, tracking physical contracts and transactions in wholesale power markets with extreme precision. Each filing includes information about the buyer, the seller, the price, the quantity, and the specific location of the sale, often mapped to individual power plants or pricing nodes.11 This allows for a level of competitive intelligence that is not possible with aggregate statistics. Market participants use EQR data to understand how their competitors are monetizing their assets, what types of ancillary services are being traded, and the terms of long-term power purchase agreements (PPAs).11

Historically, the sheer volume of EQR data—often exceeding 130 GB when decompressed—made it difficult to access without specialized IT infrastructure.12 Legacy data was provided in Visual FoxPro format, which required sophisticated database applications to query.12 However, FERC has moved toward a more accessible "eForms" ecosystem, utilizing XBRL (eXtensible Business Reporting Language) for many of its regulatory filings, which facilitates machine-to-machine communication.13

### **Modernization and Programmatic Access at FERC**

Under the "eForms Refresh" initiative, FERC has modernized the submission and retrieval of forms such as Form 1 (Annual Report of Major Electric Utilities) and Form 714 (Annual Electric Balancing Authority Area and Planning Area Report).13 A Submission API now exists to facilitate the filing process, and while the retrieval of EQR data is still largely handled through a dedicated web portal and bulk downloads, the move toward structured XML and JSON formats indicates a commitment to data accessibility.13 For historical EQR data, users can access filings from Q3-2013 to the present through the EQR Online portal, while older data requires specific requests to FERC Online Support.10

| FERC Data Asset | Primary Utility | Format / Access |
| :---- | :---- | :---- |
| Electric Quarterly Report (EQR) | Transactional wholesale prices, contracts | CSV, XML, Visual FoxPro (legacy) |
| Form 1 / 3-Q | Financial and operational data for utilities | XBRL, eForms Portal |
| Form 714 | Hourly demand and balancing area stats | XBRL, eForms Portal |
| eLibrary | Official orders, filings, and rate cases | Document search system |

The strategic value of FERC data lies in its role as a legal record. Unlike voluntary surveys, EQRs are mandated filings subject to federal oversight, making them a highly reliable source for verifying wholesale market activity.10 For researchers, the ability to link EQR transactions to specific grid locations (nodes) provides the necessary bridge between financial activity and the physical reality of the power grid.11

## **Regional Transmission Organizations: The Real-Time Wholesale Markets**

In deregulated regions covering approximately two-thirds of the United States, wholesale electricity prices are determined by Independent System Operators (ISOs) and Regional Transmission Organizations (RTOs). These entities operate competitive markets where the price of electricity is calculated at thousands of individual locations, known as Pricing Nodes (PNodes), through a process called Locational Marginal Pricing (LMP).6 LMPs reflect the cost of supplying the next megawatt of power at a specific location, accounting for the cost of generation, transmission congestion, and line losses.16

### **PJM Interconnection: Data Miner 2 and Indefinite Archives**

PJM Interconnection, the RTO serving the Mid-Atlantic and parts of the Midwest, operates what is arguably the most transparent data portal in the industry: Data Miner 2\.18 This platform provides public access to hundreds of "feeds" through both a web interface and a robust API.18 The PJM API requires a Tools Account and an API key, but it offers a level of historical depth that is rare in the ISO world; for example, Day-Ahead Hourly LMP data is available back to June 1, 2000, and is retained indefinitely.16

| PJM Data Feed | Description | Temporal Resolution |
| :---- | :---- | :---- |
| Day-Ahead Hourly LMPs | Cleared prices for the next day's market | Hourly, Indefinite archive |
| Real-Time LMPs | Prices based on actual system conditions | 5-minute intervals, 30-day retention |
| Regulation Prices | Clearing prices for frequency control services | 5-minute intervals |
| Historical Load Forecasts | Predicted vs. actual demand levels | Hourly |
| Generation Offers | Unit-specific bids (anonymized) | Monthly update, 4-month delay |

A critical insight for PJM data users is the distinction between "unverified" and "final" prices. Real-time prices are posted every five minutes but are subject to a verification process that may change the values after the operating day.19 Furthermore, for competitive reasons, generation offer data—the prices at which power plants bid into the market—is released with a four-month delay.20 This balance between transparency and market protection is a hallmark of deregulated power markets.20

### **California ISO (CAISO): OASIS and the Western Expansion**

The California Independent System Operator (CAISO) manages the grid for most of California and provides market data through its Open Access Same-Time Information System (OASIS).21 OASIS is the primary hub for real-time data, including LMPs, demand forecasts, and transmission outage status.22 As CAISO has expanded its footprint through the Western Energy Imbalance Market (WEIM), the OASIS API has become the central source of pricing data for a significant portion of the Western United States.23

CAISO's pricing data includes unique components that reflect California’s environmental policies. For example, the OASIS API provides Greenhouse Gas (GHG) shadow prices, which reflect the cost of carbon allowances for electricity imported into California.22 Developers accessing CAISO data through the OASIS web services can retrieve results in XML or CSV formats, while more sensitive applications, such as the Market Participant Portal, require digital certificates and formal registration.23

### **New York ISO (NYISO): The Transition to Finance APIs**

The New York Independent System Operator (NYISO) has historically provided data through its Decision Support System (DSS), which allowed market participants to create Custom Automated Data Delivery (CADD) reports.25 However, NYISO is currently undergoing a major technological shift. The legacy SDX application, which many participants used for settlement data, is being retired in September 2025 in favor of a new suite of Finance APIs.27

| NYISO API / Tool | Purpose | Access Requirement |
| :---- | :---- | :---- |
| Finance APIs | Settlements and financial reporting | Digital Certificate, Stakeholder account |
| BUD API | Bidding Upload Download for market activity | Marketplace credentials, Certificate |
| DSS / CADD | Custom historical and operational reports | DSS account, Web Intelligence setup |
| Real-Time Dashboard | Live grid conditions and price snapshots | Public access |

The NYISO BUD API (Bidding Upload Download) is a critical tool for market participants, providing a RESTful framework for managing load details and bidding functions.28 Setting up these APIs typically requires the use of digital certificates (often in.pfx format) and authentication via tools like Postman.28 This high barrier to entry—requiring both technical skill and formal regulatory standing—is common in the more "mature" ISO markets like New York and New England.28

### **ERCOT, MISO, and ISO-NE: Regional Variations in Access**

The Electric Reliability Council of Texas (ERCOT) provides a modern API Explorer based on OpenAPI standards.8 This framework allows developers to build applications using ERCOT reports, which include real-time and day-ahead Settlement Point Prices (SPPs) for hubs and load zones.8 While ERCOT's current API is highly accessible, historical data from the 2001-2009 period often requires a manual data request via the EMIL (ERCOT Market Information List).8

ISO New England (ISO-NE) provides a robust suite of web services, organized via WSDL (Web Services Definition Language) and WADL (Web Application Description Language) files.31 Their API (v1.1) provides preliminary and final LMPs, system demand, and transmission constraints in both XML and JSON formats.31 Similarly, the Midcontinent Independent System Operator (MISO) offers a Data Exchange portal with APIs for load, generation, and pricing data, specifically focusing on its five ancillary service products: Regulation, Spinning, Supplemental, Short-term reserves, and Ramp.33

## **Retail Pricing and the Challenge of Fragmented Utility Data**

While wholesale markets are highly standardized, the retail energy market is a patchwork of over 3,000 utilities, each with its own tariff structures.3 For users seeking local energy pricing at the residential or commercial level, federal and regional wholesale data is often insufficient because it does not include the delivery charges, taxes, and specialized rate riders that make up the bulk of a consumer's bill.35

### **The NREL Utility Rate Database (URDB)**

The National Utility Rate Database (URDB), maintained by NREL and housed on the OpenEI.org platform, is the most comprehensive source for this information.3 The URDB provides detailed rate structure information for virtually every utility in the U.S..3 Unlike simple average price data, the URDB includes the "logic" of the rate: tiers, time-of-use (TOU) windows, demand charges, and seasonal adjustments.3

The URDB API is a vital tool for the solar and storage industry. It allows developers to programmatically retrieve a specific utility’s rate and apply it to a customer’s hourly load profile to calculate potential savings.3 NREL provides a quality-controlled list of the top 150 utilities, representing 70% of the U.S. load, which are updated annually.3 For the remaining 3,000+ utilities, data is maintained on a "continual basis" through a partnership with Illinois State University.3

### **Geographical Mapping: ZIP Codes and Counties**

A major hurdle in localized pricing is the lack of a direct link between utility territories and ZIP codes. The EIA does not publish data by ZIP code, citing the fact that utility boundaries rarely align with postal or political boundaries.38 To address this, NREL has compiled cross-reference datasets that map utilities to likely ZIP codes based on service territory data from ABB and the Velocity Suite.39 These datasets (e.g., iou\_zipcodes\_2024.csv) allow analysts to identify which utilities are active in a specific ZIP code, which can then be used to query the URDB for the applicable rates.39

| Local Data Resource | Granularity | Data Type | Source Agency |
| :---- | :---- | :---- | :---- |
| Utility Rate Database (URDB) | Individual Utility Tariff | Complex rate logic (TOU, Demand) | NREL / OpenEI |
| ZIP Code Cross-Reference | ZIP to Utility Mapping | Average rates, service area | NREL / EIA-861 |
| Utility Rates v3 API | Lat/Lon Coordinates | Annual average $/kWh (Stale 2012\) | NREL Developer |
| Consumer Price Index (CPI) | U.S. City Average | Monthly index of price changes | BLS / FRED |

Analysts should exercise caution when using the "Utility Rates v3" API found on the NREL developer portal. While it allows for coordinate-based searching, the documentation explicitly states that the data is from 2012 and there are no plans to update it.42 For any current analysis, the URDB or the ZIP code cross-reference files from 2023 or 2024 are the only reliable options.39

## **Standardizers and Aggregators: The Modern Analyst's Toolkit**

The fragmentation of the energy data landscape has given rise to a new generation of tools designed to standardize and aggregate these disparate sources. These range from open-source libraries to commercial-grade data pipelines.

### **Grid Status: The Open-Source Library**

The gridstatus Python library has emerged as the industry standard for programmatic energy data access.4 It provides a consistent API across all major ISOs (CAISO, ERCOT, ISO-NE, MISO, NYISO, PJM, SPP) and the EIA.4 By abstracting the specific API endpoints and scraping logic for each source, gridstatus allows an analyst to retrieve load or pricing data with a single line of code, such as caiso.get\_load(date='2024-01-01').4

| Tool | Focus | Target User |
| :---- | :---- | :---- |
| gridstatus library | Raw supply, demand, and LMP data | Python developers, Data scientists |
| GridStatus.io | Real-time dashboards and nodal maps | Market observers, Traders |
| UtilityAPI | Meter-level bill and interval data | Energy managers, Solar installers |
| Yes Energy (FERC Dataset) | EQR transaction mapping and intelligence | Financial analysts, Asset owners |
| Enverus | Long-term nodal and zonal forecasting | Project developers, Financiers |

The significance of gridstatus lies in its ability to return data in Pandas DataFrames, making it immediately compatible with the broader Python data science ecosystem.4 This standardization is essential for tasks such as cross-ISO nodal analysis, where an analyst might want to compare the frequency of negative prices in ERCOT versus CAISO to identify optimal locations for energy storage.44

### **Commercial Data Services**

For production-level applications where data reliability and "cleanliness" are paramount, commercial aggregators offer hosted APIs. UtilityAPI provides a secure, authorized pipeline for collecting meter-level data from utilities, which is essential for billing, community solar, and ESG reporting.35 Meanwhile, firms like Enverus use fundamental-based production cost models combined with machine learning to provide price forecasting at the node level, helping developers evaluate the long-term economic viability of new projects.45

## **Technical and Operational Challenges in Data Synthesis**

Successful integration of United States energy pricing data requires overcoming several persistent technical and operational challenges. These hurdles are often the "hidden costs" of building energy-aware applications.

### **Temporal Discrepancies and Timezone Management**

The U.S. power grid operates across multiple timezones, and each ISO has its own convention for reporting time. PJM, for instance, reports data in Eastern Prevailing Time (EPT) and UTC.16 Analysts must be extremely careful when merging price data from one region with demand data from another, as misalignments of even one hour can lead to significant errors in correlation analysis.47 The standard practice among sophisticated users is to convert all timestamps to UTC immediately upon ingestion.19

### **Geographical Complexity and Nodal Mapping**

While a retail consumer lives in a ZIP code, the electricity they consume is priced at a specific electrical bus or node on the transmission grid.18 Mapping a physical address to a specific pricing node—a process known as "nodal mapping"—is a complex task that requires detailed knowledge of the high-voltage network.11 For most users, "zonal" prices (the average price across a load zone) serve as a sufficient proxy, but for large-scale industrial users or renewable developers, the basis risk (the difference between the nodal and zonal price) can be the difference between profit and loss.45

### **Data Latency and the Verification Cycle**

In energy markets, the trade-off between speed and accuracy is constant. Real-time 5-minute LMPs are available almost instantaneously via APIs like PJM’s or CAISO’s, but these are often "unverified" and subject to change.19 Final, settlement-quality data often takes several days or even months to clear the verification process.49 For real-time grid operations, latency is the primary concern; for financial auditing or ESG reporting, the verified historical record from the EIA or FERC is the necessary source of truth.1

## **Strategic Applications of Energy Pricing Data**

The democratization of energy data via APIs is not merely a technical convenience; it is a catalyst for the "energy transition." The ability to programmatically access pricing data enables several high-value strategic initiatives.

### **Optimization of Distributed Energy Resources (DERs)**

Energy storage systems (batteries) are perhaps the most data-dependent assets on the grid. Their business model relies on "arbitrage"—charging when prices are low and discharging when they are high.44 By using APIs from Grid Status or directly from ISOs, storage operators can feed real-time price signals into their dispatch algorithms to maximize returns.44 Similarly, demand response programs use API-delivered "Threshold Prices" to signal to industrial facilities when they should curtail production to support grid stability.49

### **Site Selection and Project Finance**

For developers of new wind, solar, or battery projects, historical nodal pricing data from FERC and ISOs is the foundation of the "bankability" analysis. By examining five to ten years of historical LMPs at a proposed interconnection point, developers can calculate the "capture price"—the actual revenue the project would have earned based on when it was generating.11 High-confidence forecasts from providers like Enverus, which combine these historical records with fundamental models of grid expansion, are essential for securing low-cost financing.45

### **Corporate Sustainability and Carbon Accounting**

As corporations commit to 24/7 carbon-free energy (CFE), the need for hourly emissions and pricing data has surged. By linking hourly load data from UtilityAPI with hourly grid fuel-mix data from the EIA’s Hourly Electric Grid Monitor API, companies can calculate their true carbon footprint with far greater accuracy than annual averages would allow.46 This real-time visibility into the grid’s carbon intensity also allows companies to shift flexible loads, like EV charging or data center processing, to hours when renewable generation is high and prices are low.51

## **Conclusion: Navigating the Multi-Source Ecosystem**

Building a comprehensive view of United States energy pricing requires a synthesis of federal, regional, and local data sources. No single API provides the complete picture; instead, the sophisticated user must weave together the historical depth of the EIA, the transactional transparency of FERC, the real-time granularity of the ISOs, and the retail specificity of the URDB.

The evolution of these systems toward RESTful APIs and standardized data formats is significantly lowering the barrier to entry for energy-aware innovation. While challenges regarding timezone management, nodal mapping, and data latency remain, the tools available today—from open-source libraries like gridstatus to modernized federal platforms like EIA API v2—provide a robust foundation for the next generation of energy management, grid optimization, and economic research. For the professional peer navigating this field, the key is to match the specific dataset’s granularity, update frequency, and historical range to the unique requirements of the analytical task at hand.

#### **Works cited**

1. Homepage \- U.S. Energy Information Administration (EIA), accessed February 21, 2026, [https://www.eia.gov/](https://www.eia.gov/)  
2. EIA's API Technical Documentation \- U.S. Energy Information ..., accessed February 21, 2026, [https://www.eia.gov/opendata/documentation.php](https://www.eia.gov/opendata/documentation.php)  
3. Utility Rate Database \- Open Energy Information, accessed February 21, 2026, [https://openei.org/wiki/Utility\_Rate\_Database](https://openei.org/wiki/Utility_Rate_Database)  
4. What is the gridstatus library? — gridstatus, accessed February 21, 2026, [https://opensource.gridstatus.io/](https://opensource.gridstatus.io/)  
5. Opendata \- U.S. Energy Information Administration (EIA), accessed February 21, 2026, [https://www.eia.gov/opendata/](https://www.eia.gov/opendata/)  
6. Wholesale Electricity Market Portal (U.S. Energy Information Administration), accessed February 21, 2026, [https://dss.princeton.edu/catalog/resource7699](https://dss.princeton.edu/catalog/resource7699)  
7. OpenEI Utility Rates API | NLR: Developer Network, accessed February 21, 2026, [https://developer.nrel.gov/docs/electricity/openei-utility-rates/](https://developer.nrel.gov/docs/electricity/openei-utility-rates/)  
8. ERCOT Public API Applications, accessed February 21, 2026, [https://www.ercot.com/services/mdt/data-portal](https://www.ercot.com/services/mdt/data-portal)  
9. Electricity Data \- U.S. Energy Information Administration (EIA), accessed February 21, 2026, [https://www.eia.gov/electricity/data.php](https://www.eia.gov/electricity/data.php)  
10. Electric Quarterly Reports (EQR) | Federal Energy Regulatory Commission, accessed February 21, 2026, [https://www.ferc.gov/power-sales-and-markets/electric-quarterly-reports-eqr](https://www.ferc.gov/power-sales-and-markets/electric-quarterly-reports-eqr)  
11. Marketplace | FERC EQR Dataset \- Yes Energy, accessed February 21, 2026, [https://www.yesenergy.com/ferc-eqr-dataset](https://www.yesenergy.com/ferc-eqr-dataset)  
12. Download Database \- Federal Energy Regulatory Commission, accessed February 21, 2026, [https://www.ferc.gov/download-database](https://www.ferc.gov/download-database)  
13. eForms Refresh | Federal Energy Regulatory Commission, accessed February 21, 2026, [https://www.ferc.gov/filing-forms/eforms-refresh](https://www.ferc.gov/filing-forms/eforms-refresh)  
14. EQR Online \- Home Page \- Federal Energy Regulatory Commission, accessed February 21, 2026, [https://eqronline.ferc.gov/](https://eqronline.ferc.gov/)  
15. Energy Market & Operational Data \- NYISO, accessed February 21, 2026, [https://www.nyiso.com/energy-market-operational-data](https://www.nyiso.com/energy-market-operational-data)  
16. Day-Ahead Hourly LMPs \- Data Miner 2, accessed February 21, 2026, [https://dataminer2.pjm.com/feed/da\_hrl\_lmps/definition](https://dataminer2.pjm.com/feed/da_hrl_lmps/definition)  
17. Administer Electricity Markets \- NYISO, accessed February 21, 2026, [https://www.nyiso.com/administer-electricity-markets](https://www.nyiso.com/administer-electricity-markets)  
18. Data Miner 2 – Getting Started \- PJM.com, accessed February 21, 2026, [https://www.pjm.com/-/media/DotCom/etools/data-miner-2/data-miner-2-getting-started-guide.pdf](https://www.pjm.com/-/media/DotCom/etools/data-miner-2/data-miner-2-getting-started-guide.pdf)  
19. Regulation Prices \- Data Miner 2, accessed February 21, 2026, [https://dataminer2.pjm.com/feed/reg\_prices/definition](https://dataminer2.pjm.com/feed/reg_prices/definition)  
20. Energy Market Generation Offers \- Data Miner 2, accessed February 21, 2026, [https://dataminer2.pjm.com/feed/energy\_market\_offers/definition](https://dataminer2.pjm.com/feed/energy_market_offers/definition)  
21. Open Access Same-Time Information System (OASIS) \- California ISO, accessed February 21, 2026, [https://www.caiso.com/systems-applications/portals-applications/open-access-same-time-information-system-oasis](https://www.caiso.com/systems-applications/portals-applications/open-access-same-time-information-system-oasis)  
22. caiso oasis \- California ISO, accessed February 21, 2026, [https://oasis.caiso.com/](https://oasis.caiso.com/)  
23. Portals and applications \- California ISO, accessed February 21, 2026, [https://www.caiso.com/systems-applications/portals-applications](https://www.caiso.com/systems-applications/portals-applications)  
24. Developer Portal | California ISO, accessed February 21, 2026, [https://www.caiso.com/systems-applications/developer-portal](https://www.caiso.com/systems-applications/developer-portal)  
25. Is there a DSS API?, accessed February 21, 2026, [https://nyiso.my.site.com/MemberCommunity/s/article/Is-there-a-DSS-API](https://nyiso.my.site.com/MemberCommunity/s/article/Is-there-a-DSS-API)  
26. Using the Decision Support System (DSS) Custom Automated Data Delivery (CADD) \- NYISO, accessed February 21, 2026, [https://www.nyiso.com/documents/20142/2931465/tb\_147.pdf/ea5ea14b-38ab-06de-55a0-c32f91c6446f](https://www.nyiso.com/documents/20142/2931465/tb_147.pdf/ea5ea14b-38ab-06de-55a0-c32f91c6446f)  
27. The NYISO deployed new Finance APIs that replicate the functionality currently offered through the SDX application. A market tri, accessed February 21, 2026, [https://www.nyiso.com/documents/20142/20259596/SDX-Upload-Download-Application-Retirement.pdf/93ebf171-b383-520d-b3af-00cb9f433d3c](https://www.nyiso.com/documents/20142/20259596/SDX-Upload-Download-Application-Retirement.pdf/93ebf171-b383-520d-b3af-00cb9f433d3c)  
28. Market Access Login \- NYISO, accessed February 21, 2026, [https://www.nyiso.com/market-access-login](https://www.nyiso.com/market-access-login)  
29. Market Prices \- ERCOT.com, accessed February 21, 2026, [https://www.ercot.com/mktinfo/prices](https://www.ercot.com/mktinfo/prices)  
30. Historical Price Data · ercot api-specs · Discussion \#51 \- GitHub, accessed February 21, 2026, [https://github.com/ercot/api-specs/discussions/51](https://github.com/ercot/api-specs/discussions/51)  
31. Web Services Data \- ISO New England, accessed February 21, 2026, [https://www.iso-ne.com/participate/support/web-services-data](https://www.iso-ne.com/participate/support/web-services-data)  
32. Upload and Download File Format Protocols \- ISO New England, accessed February 21, 2026, [https://www.iso-ne.com/participate/support/upload-download/?sort=normalized\_document\_title\_s.asc](https://www.iso-ne.com/participate/support/upload-download/?sort=normalized_document_title_s.asc)  
33. APIs: List \- MISO Data Exchange, accessed February 21, 2026, [https://data-exchange.misoenergy.org/apis](https://data-exchange.misoenergy.org/apis)  
34. Access MISO Market and Operations Data \- Help Center, accessed February 21, 2026, [https://help.misoenergy.org/knowledgebase/article/KA-01000/en-us](https://help.misoenergy.org/knowledgebase/article/KA-01000/en-us)  
35. Pricing \- UtilityAPI, accessed February 21, 2026, [https://utilityapi.com/pricing](https://utilityapi.com/pricing)  
36. Utility Rate Database (URDB) \- Open Energy Data Initiative (OEDI), accessed February 21, 2026, [https://data.openei.org/submissions/5](https://data.openei.org/submissions/5)  
37. National Utility Rate Database: Preprint \- Publications, accessed February 21, 2026, [https://docs.nrel.gov/docs/fy12osti/54633.pdf](https://docs.nrel.gov/docs/fy12osti/54633.pdf)  
38. Does EIA publish energy consumption and price data for cities, counties, or by zip code?, accessed February 21, 2026, [https://www.eia.gov/tools/faqs/faq.php?id=448\&t=5](https://www.eia.gov/tools/faqs/faq.php?id=448&t=5)  
39. U.S. Electric Utility Companies and Rates: Look-up by Zip Code (2024), accessed February 21, 2026, [https://data.openei.org/submissions/8563](https://data.openei.org/submissions/8563)  
40. U.S. Electric Utility Companies and Rates: Look-up by Zipcode (2023) \- OEDI, accessed February 21, 2026, [https://data.openei.org/submissions/6225](https://data.openei.org/submissions/6225)  
41. electric-rates \- Dataset \- Catalog \- Data.gov, accessed February 21, 2026, [https://catalog.data.gov/dataset/?tags=electric-rates](https://catalog.data.gov/dataset/?tags=electric-rates)  
42. Utility Rates API | NLR: Developer Network, accessed February 21, 2026, [https://developer.nrel.gov/docs/electricity/utility-rates-v3/](https://developer.nrel.gov/docs/electricity/utility-rates-v3/)  
43. gridstatus/gridstatus: Extract data from ISOs and other energy grid sources \- GitHub, accessed February 21, 2026, [https://github.com/gridstatus/gridstatus](https://github.com/gridstatus/gridstatus)  
44. CAISO Live Dashboard and Price Map \- Grid Status, accessed February 21, 2026, [https://www.gridstatus.io/live/caiso](https://www.gridstatus.io/live/caiso)  
45. Long-Term Power Market Forecasting | Power & Energy Transition \- Enverus, accessed February 21, 2026, [https://www.enverus.com/products/long-term-power-market-forecasting/](https://www.enverus.com/products/long-term-power-market-forecasting/)  
46. Energy management \- UtilityAPI, accessed February 21, 2026, [https://utilityapi.com/use-cases/energy-management](https://utilityapi.com/use-cases/energy-management)  
47. Latest Data for ISOs | Grid Status, accessed February 21, 2026, [https://www.gridstatus.io/datasets/isos\_latest](https://www.gridstatus.io/datasets/isos_latest)  
48. System-Wide Prices \- ERCOT.com, accessed February 21, 2026, [https://www.ercot.com/gridmktinfo/dashboards/systemwideprices](https://www.ercot.com/gridmktinfo/dashboards/systemwideprices)  
49. Pricing Reports \- ISO New England, accessed February 21, 2026, [https://www.iso-ne.com/markets-operations/iso-express/pricing-reports](https://www.iso-ne.com/markets-operations/iso-express/pricing-reports)  
50. Energy \- Pricing Reports, accessed February 21, 2026, [https://www.iso-ne.com/isoexpress/web/reports/pricing/-/tree/ener-mkt-prices](https://www.iso-ne.com/isoexpress/web/reports/pricing/-/tree/ener-mkt-prices)  
51. Utilities reshape rate structures amid data center boom \- Enverus, accessed February 21, 2026, [https://www.enverus.com/newsroom/utilities-reshape-rate-structures-amid-data-center-boom/](https://www.enverus.com/newsroom/utilities-reshape-rate-structures-amid-data-center-boom/)  
52. Demand Resources \- ISO New England, accessed February 21, 2026, [https://www.iso-ne.com/markets-operations/markets/demand-resources](https://www.iso-ne.com/markets-operations/markets/demand-resources)  
53. Wholesale Electricity Markets U.S. Energy Information Administration (EIA), accessed February 21, 2026, [https://www.eia.gov/electricity/wholesalemarkets/](https://www.eia.gov/electricity/wholesalemarkets/)