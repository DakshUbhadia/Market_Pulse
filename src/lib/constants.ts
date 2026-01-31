export type MarketType = 'US' | 'IN';

export type NavItem = {
  href: string
  label: string
  variant?: "command"
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/market-scope", label: "Market Scope" },
  { href: "/simulator", label: "Simulator" },
  { href: "/search", label: "Search", variant: "command" },
  { href: "/watchlist", label: "Watchlist" },
]

export type StockListItem = {
  symbol: string
  name: string
  exchange: string
}

export const US_DEFAULT_STOCKS: StockListItem[] = [
{ symbol: "AAPL", name: "Apple", exchange: "NASDAQ" },
{ symbol: "MSFT", name: "Microsoft", exchange: "NASDAQ" },
{ symbol: "GOOGL", name: "Alphabet Class A", exchange: "NASDAQ" },
{ symbol: "GOOG", name: "Alphabet Class C", exchange: "NASDAQ" },
{ symbol: "AMZN", name: "Amazon", exchange: "NASDAQ" },
{ symbol: "NVDA", name: "NVIDIA", exchange: "NASDAQ" },
{ symbol: "META", name: "Meta Platforms", exchange: "NASDAQ" },
{ symbol: "TSLA", name: "Tesla", exchange: "NASDAQ" },
{ symbol: "BRK.B", name: "Berkshire Hathaway", exchange: "NYSE" },
{ symbol: "JPM", name: "JPMorgan Chase", exchange: "NYSE" },
{ symbol: "V", name: "Visa", exchange: "NYSE" },
{ symbol: "MA", name: "Mastercard", exchange: "NYSE" },
{ symbol: "UNH", name: "UnitedHealth Group", exchange: "NYSE" },
{ symbol: "XOM", name: "Exxon Mobil", exchange: "NYSE" },
{ symbol: "LLY", name: "Eli Lilly", exchange: "NYSE" },
{ symbol: "AVGO", name: "Broadcom", exchange: "NASDAQ" },
{ symbol: "JNJ", name: "Johnson & Johnson", exchange: "NYSE" },
{ symbol: "WMT", name: "Walmart", exchange: "NYSE" },
{ symbol: "PG", name: "Procter & Gamble", exchange: "NYSE" },
{ symbol: "HD", name: "Home Depot", exchange: "NYSE" },
{ symbol: "ORCL", name: "Oracle", exchange: "NYSE" },
{ symbol: "COST", name: "Costco", exchange: "NASDAQ" },
{ symbol: "MRK", name: "Merck & Co.", exchange: "NYSE" },
{ symbol: "KO", name: "Coca-Cola", exchange: "NYSE" },
{ symbol: "PEP", name: "PepsiCo", exchange: "NASDAQ" },
{ symbol: "ABBV", name: "AbbVie", exchange: "NYSE" },
{ symbol: "BAC", name: "Bank of America", exchange: "NYSE" },
{ symbol: "NFLX", name: "Netflix", exchange: "NASDAQ" },
{ symbol: "TMO", name: "Thermo Fisher Scientific", exchange: "NYSE" },
{ symbol: "CSCO", name: "Cisco Systems", exchange: "NASDAQ" },
{ symbol: "ACN", name: "Accenture", exchange: "NYSE" },
{ symbol: "MCD", name: "McDonald's", exchange: "NYSE" },
{ symbol: "ADBE", name: "Adobe", exchange: "NASDAQ" },
{ symbol: "AMD", name: "Advanced Micro Devices", exchange: "NASDAQ" },
{ symbol: "INTC", name: "Intel", exchange: "NASDAQ" },
{ symbol: "CRM", name: "Salesforce", exchange: "NYSE" },
{ symbol: "QCOM", name: "Qualcomm", exchange: "NASDAQ" },
{ symbol: "IBM", name: "IBM", exchange: "NYSE" },
{ symbol: "TXN", name: "Texas Instruments", exchange: "NASDAQ" },
{ symbol: "AMAT", name: "Applied Materials", exchange: "NASDAQ" },
{ symbol: "NOW", name: "ServiceNow", exchange: "NYSE" },
{ symbol: "GE", name: "General Electric", exchange: "NYSE" },
{ symbol: "DIS", name: "Walt Disney", exchange: "NYSE" },
{ symbol: "BA", name: "Boeing", exchange: "NYSE" },
{ symbol: "CAT", name: "Caterpillar", exchange: "NYSE" },
{ symbol: "LOW", name: "Lowe's", exchange: "NYSE" },
{ symbol: "GS", name: "Goldman Sachs", exchange: "NYSE" },
{ symbol: "MS", name: "Morgan Stanley", exchange: "NYSE" },
{ symbol: "BLK", name: "BlackRock", exchange: "NYSE" },
{ symbol: "SPGI", name: "S&P Global", exchange: "NYSE" },
{ symbol: "UBER", name: "Uber Technologies", exchange: "NYSE" },
{ symbol: "PYPL", name: "PayPal", exchange: "NASDAQ" },
{ symbol: "SHOP", name: "Shopify", exchange: "NYSE" },
{ symbol: "SONY", name: "Sony Group", exchange: "NYSE" },
{ symbol: "TM", name: "Toyota Motor", exchange: "NYSE" },
{ symbol: "TSM", name: "Taiwan Semiconductor", exchange: "NYSE" },
{ symbol: "BABA", name: "Alibaba Group", exchange: "NYSE" },
{ symbol: "TCEHY", name: "Tencent Holdings", exchange: "OTC" },
{ symbol: "NVO", name: "Novo Nordisk", exchange: "NYSE" },
{ symbol: "ASML", name: "ASML Holding", exchange: "NASDAQ" },
{ symbol: "SAP", name: "SAP", exchange: "NYSE" },
{ symbol: "RDS.A", name: "Shell", exchange: "NYSE" },
{ symbol: "HSBC", name: "HSBC Holdings", exchange: "NYSE" },
{ symbol: "BP", name: "BP", exchange: "NYSE" },
{ symbol: "RIO", name: "Rio Tinto", exchange: "NYSE" },
{ symbol: "BHP", name: "BHP Group", exchange: "NYSE" },
{ symbol: "UL", name: "Unilever", exchange: "NYSE" },
{ symbol: "TTE", name: "TotalEnergies", exchange: "NYSE" },
{ symbol: "PFE", name: "Pfizer", exchange: "NYSE" },
{ symbol: "AZN", name: "AstraZeneca", exchange: "NASDAQ" },
{ symbol: "SNY", name: "Sanofi", exchange: "NASDAQ" },
{ symbol: "VOD", name: "Vodafone Group", exchange: "NASDAQ" },
{ symbol: "INFY", name: "Infosys", exchange: "NYSE" },
{ symbol: "SHEL", name: "Shell plc", exchange: "NYSE" },
{ symbol: "ZM", name: "Zoom Video Communications", exchange: "NASDAQ" },
{ symbol: "SNOW", name: "Snowflake", exchange: "NYSE" },
{ symbol: "PLTR", name: "Palantir Technologies", exchange: "NYSE" },
{ symbol: "COIN", name: "Coinbase Global", exchange: "NASDAQ" },
{ symbol: "ARM", name: "Arm Holdings", exchange: "NASDAQ" },

{ symbol: "INTU", name: "Intuit Inc.", exchange: "NASDAQ" },
  { symbol: "ADP", name: "Automatic Data Processing", exchange: "NASDAQ" },
  { symbol: "PANW", name: "Palo Alto Networks", exchange: "NASDAQ" },
  { symbol: "SNPS", name: "Synopsys Inc.", exchange: "NASDAQ" },
  { symbol: "CDNS", name: "Cadence Design Systems", exchange: "NASDAQ" },
  { symbol: "WDAY", name: "Workday Inc.", exchange: "NASDAQ" },
  { symbol: "ADSK", name: "Autodesk Inc.", exchange: "NASDAQ" },
  { symbol: "FTNT", name: "Fortinet Inc.", exchange: "NASDAQ" },
  { symbol: "CRWD", name: "CrowdStrike Holdings", exchange: "NASDAQ" },
  { symbol: "ZS", name: "Zscaler Inc.", exchange: "NASDAQ" },
  { symbol: "NET", name: "Cloudflare Inc.", exchange: "NYSE" },
  { symbol: "DDOG", name: "Datadog Inc.", exchange: "NASDAQ" },
  { symbol: "MDB", name: "MongoDB Inc.", exchange: "NASDAQ" },
  { symbol: "TEAM", name: "Atlassian", exchange: "NASDAQ" },
  { symbol: "HUBS", name: "HubSpot Inc.", exchange: "NYSE" },
  { symbol: "SQ", name: "Block Inc.", exchange: "NYSE" },
  { symbol: "FICO", name: "Fair Isaac Corp", exchange: "NYSE" },
  { symbol: "ANET", name: "Arista Networks", exchange: "NYSE" },
  { symbol: "APH", name: "Amphenol Corp", exchange: "NYSE" },
  { symbol: "TEL", name: "TE Connectivity", exchange: "NYSE" },
  { symbol: "GLW", name: "Corning Inc.", exchange: "NYSE" },
  { symbol: "HPQ", name: "HP Inc.", exchange: "NYSE" },
  { symbol: "DELL", name: "Dell Technologies", exchange: "NYSE" },
  { symbol: "SMCI", name: "Super Micro Computer", exchange: "NASDAQ" },
  { symbol: "HPE", name: "Hewlett Packard Enterprise", exchange: "NYSE" },
  { symbol: "NTAP", name: "NetApp Inc.", exchange: "NASDAQ" },
  { symbol: "STX", name: "Seagate Technology", exchange: "NASDAQ" },
  { symbol: "WDC", name: "Western Digital", exchange: "NASDAQ" },
  { symbol: "GIB", name: "CGI Inc.", exchange: "NYSE" },
  { symbol: "PTC", name: "PTC Inc.", exchange: "NASDAQ" },
  { symbol: "TYL", name: "Tyler Technologies", exchange: "NYSE" },
  { symbol: "AKAM", name: "Akamai Technologies", exchange: "NASDAQ" },
  { symbol: "GEN", name: "Gen Digital (Norton)", exchange: "NASDAQ" },
  { symbol: "DOCU", name: "DocuSign Inc.", exchange: "NASDAQ" },
  { symbol: "OKTA", name: "Okta Inc.", exchange: "NASDAQ" },

  // --- SEMICONDUCTORS (BEYOND NVDA/AMD/INTC) ---
  { symbol: "MU", name: "Micron Technology", exchange: "NASDAQ" },
  { symbol: "LRCX", name: "Lam Research", exchange: "NASDAQ" },
  { symbol: "ADI", name: "Analog Devices", exchange: "NASDAQ" },
  { symbol: "KLAC", name: "KLA Corporation", exchange: "NASDAQ" },
  { symbol: "MRVL", name: "Marvell Technology", exchange: "NASDAQ" },
  { symbol: "MCHP", name: "Microchip Technology", exchange: "NASDAQ" },
  { symbol: "ON", name: "ON Semiconductor", exchange: "NASDAQ" },
  { symbol: "NXPI", name: "NXP Semiconductors", exchange: "NASDAQ" },
  { symbol: "STM", name: "STMicroelectronics", exchange: "NYSE" },
  { symbol: "MPWR", name: "Monolithic Power Systems", exchange: "NASDAQ" },
  { symbol: "TER", name: "Teradyne Inc.", exchange: "NASDAQ" },
  { symbol: "ENTG", name: "Entegris Inc.", exchange: "NASDAQ" },
  { symbol: "SWKS", name: "Skyworks Solutions", exchange: "NASDAQ" },
  { symbol: "QRVO", name: "Qorvo Inc.", exchange: "NASDAQ" },
  { symbol: "WOLF", name: "Wolfspeed Inc.", exchange: "NYSE" },

  // --- FINANCIALS (BANKS, INSURANCE, ASSET MGMT) ---
  { symbol: "WFC", name: "Wells Fargo & Co", exchange: "NYSE" },
  { symbol: "C", name: "Citigroup Inc.", exchange: "NYSE" },
  { symbol: "AXP", name: "American Express", exchange: "NYSE" },
  { symbol: "USB", name: "U.S. Bancorp", exchange: "NYSE" },
  { symbol: "PNC", name: "PNC Financial Services", exchange: "NYSE" },
  { symbol: "TFC", name: "Truist Financial", exchange: "NYSE" },
  { symbol: "BK", name: "BNY Mellon", exchange: "NYSE" },
  { symbol: "STT", name: "State Street Corp", exchange: "NYSE" },
  { symbol: "COF", name: "Capital One Financial", exchange: "NYSE" },
  { symbol: "DFS", name: "Discover Financial", exchange: "NYSE" },
  { symbol: "SCHW", name: "Charles Schwab", exchange: "NYSE" },
  { symbol: "IBKR", name: "Interactive Brokers", exchange: "NASDAQ" },
  { symbol: "ICE", name: "Intercontinental Exchange", exchange: "NYSE" },
  { symbol: "CME", name: "CME Group", exchange: "NASDAQ" },
  { symbol: "MMC", name: "Marsh & McLennan", exchange: "NYSE" },
  { symbol: "AON", name: "Aon plc", exchange: "NYSE" },
  { symbol: "PGR", name: "Progressive Corp", exchange: "NYSE" },
  { symbol: "CB", name: "Chubb Limited", exchange: "NYSE" },
  { symbol: "TRV", name: "Travelers Companies", exchange: "NYSE" },
  { symbol: "ALL", name: "Allstate Corp", exchange: "NYSE" },
  { symbol: "AFL", name: "Aflac Inc.", exchange: "NYSE" },
  { symbol: "MET", name: "MetLife Inc.", exchange: "NYSE" },
  { symbol: "PRU", name: "Prudential Financial", exchange: "NYSE" },
  { symbol: "AIG", name: "American International Group", exchange: "NYSE" },
  { symbol: "HIG", name: "Hartford Financial", exchange: "NYSE" },
  { symbol: "KKR", name: "KKR & Co.", exchange: "NYSE" },
  { symbol: "BX", name: "Blackstone Inc.", exchange: "NYSE" },
  { symbol: "APO", name: "Apollo Global Management", exchange: "NYSE" },
  { symbol: "TROW", name: "T. Rowe Price", exchange: "NASDAQ" },
  { symbol: "AMP", name: "Ameriprise Financial", exchange: "NYSE" },

  // --- HEALTHCARE, BIOTECH & PHARMA ---
  { symbol: "CVS", name: "CVS Health", exchange: "NYSE" },
  { symbol: "CI", name: "The Cigna Group", exchange: "NYSE" },
  { symbol: "ELV", name: "Elevance Health", exchange: "NYSE" },
  { symbol: "HUM", name: "Humana Inc.", exchange: "NYSE" },
  { symbol: "CNC", name: "Centene Corp", exchange: "NYSE" },
  { symbol: "AMGN", name: "Amgen Inc.", exchange: "NASDAQ" },
  { symbol: "GILD", name: "Gilead Sciences", exchange: "NASDAQ" },
  { symbol: "VRTX", name: "Vertex Pharmaceuticals", exchange: "NASDAQ" },
  { symbol: "REGN", name: "Regeneron Pharmaceuticals", exchange: "NASDAQ" },
  { symbol: "BIIB", name: "Biogen Inc.", exchange: "NASDAQ" },
  { symbol: "MRNA", name: "Moderna Inc.", exchange: "NASDAQ" },
  { symbol: "BMY", name: "Bristol Myers Squibb", exchange: "NYSE" },
  { symbol: "ISRG", name: "Intuitive Surgical", exchange: "NASDAQ" },
  { symbol: "SYK", name: "Stryker Corp", exchange: "NYSE" },
  { symbol: "BSX", name: "Boston Scientific", exchange: "NYSE" },
  { symbol: "MDT", name: "Medtronic plc", exchange: "NYSE" },
  { symbol: "EW", name: "Edwards Lifesciences", exchange: "NYSE" },
  { symbol: "ZTS", name: "Zoetis Inc.", exchange: "NYSE" },
  { symbol: "BDX", name: "Becton, Dickinson", exchange: "NYSE" },
  { symbol: "DXCM", name: "DexCom Inc.", exchange: "NASDAQ" },
  { symbol: "IDXX", name: "IDEXX Laboratories", exchange: "NASDAQ" },
  { symbol: "RMD", name: "ResMed Inc.", exchange: "NYSE" },
  { symbol: "HCA", name: "HCA Healthcare", exchange: "NYSE" },
  { symbol: "UHS", name: "Universal Health Services", exchange: "NYSE" },
  { symbol: "DHR", name: "Danaher Corp", exchange: "NYSE" },
  { symbol: "GEHC", name: "GE HealthCare", exchange: "NASDAQ" },
  { symbol: "A", name: "Agilent Technologies", exchange: "NYSE" },
  { symbol: "IQV", name: "IQVIA Holdings", exchange: "NYSE" },
  { symbol: "MTD", name: "Mettler-Toledo", exchange: "NYSE" },

  // --- CONSUMER DISCRETIONARY (RETAIL, AUTO, TRAVEL) ---
  { symbol: "SBUX", name: "Starbucks Corp", exchange: "NASDAQ" },
  { symbol: "NKE", name: "Nike Inc.", exchange: "NYSE" },
  { symbol: "BKNG", name: "Booking Holdings", exchange: "NASDAQ" },
  { symbol: "ABNB", name: "Airbnb Inc.", exchange: "NASDAQ" },
  { symbol: "MAR", name: "Marriott International", exchange: "NASDAQ" },
  { symbol: "HLT", name: "Hilton Worldwide", exchange: "NYSE" },
  { symbol: "GM", name: "General Motors", exchange: "NYSE" },
  { symbol: "F", name: "Ford Motor Company", exchange: "NYSE" },
  { symbol: "LULU", name: "Lululemon Athletica", exchange: "NASDAQ" },
  { symbol: "TGT", name: "Target Corp", exchange: "NYSE" },
  { symbol: "TJX", name: "TJX Companies", exchange: "NYSE" },
  { symbol: "ROST", name: "Ross Stores", exchange: "NASDAQ" },
  { symbol: "ORLY", name: "O'Reilly Automotive", exchange: "NASDAQ" },
  { symbol: "AZO", name: "AutoZone Inc.", exchange: "NYSE" },
  { symbol: "CMG", name: "Chipotle Mexican Grill", exchange: "NYSE" },
  { symbol: "YUM", name: "Yum! Brands", exchange: "NYSE" },
  { symbol: "DRI", name: "Darden Restaurants", exchange: "NYSE" },
  { symbol: "DPZ", name: "Domino's Pizza", exchange: "NYSE" },
  { symbol: "DG", name: "Dollar General", exchange: "NYSE" },
  { symbol: "DLTR", name: "Dollar Tree", exchange: "NASDAQ" },
  { symbol: "LEN", name: "Lennar Corp", exchange: "NYSE" },
  { symbol: "DHI", name: "D.R. Horton", exchange: "NYSE" },
  { symbol: "RCL", name: "Royal Caribbean", exchange: "NYSE" },
  { symbol: "CCL", name: "Carnival Corp", exchange: "NYSE" },
  { symbol: "LVS", name: "Las Vegas Sands", exchange: "NYSE" },
  { symbol: "EBAY", name: "eBay Inc.", exchange: "NASDAQ" },
  { symbol: "ETSY", name: "Etsy Inc.", exchange: "NASDAQ" },

  // --- CONSUMER STAPLES ---
  { symbol: "PM", name: "Philip Morris International", exchange: "NYSE" },
  { symbol: "MO", name: "Altria Group", exchange: "NYSE" },
  { symbol: "MDLZ", name: "Mondelez International", exchange: "NASDAQ" },
  { symbol: "KHC", name: "Kraft Heinz", exchange: "NASDAQ" },
  { symbol: "GIS", name: "General Mills", exchange: "NYSE" },
  { symbol: "K", name: "Kellogg Company (Kellanova)", exchange: "NYSE" },
  { symbol: "HSY", name: "The Hershey Company", exchange: "NYSE" },
  { symbol: "CL", name: "Colgate-Palmolive", exchange: "NYSE" },
  { symbol: "EL", name: "Estee Lauder", exchange: "NYSE" },
  { symbol: "KVUE", name: "Kenvue Inc.", exchange: "NYSE" },
  { symbol: "KMB", name: "Kimberly-Clark", exchange: "NYSE" },
  { symbol: "SYY", name: "Sysco Corp", exchange: "NYSE" },
  { symbol: "ADM", name: "Archer-Daniels-Midland", exchange: "NYSE" },
  { symbol: "STZ", name: "Constellation Brands", exchange: "NYSE" },
  { symbol: "MNST", name: "Monster Beverage", exchange: "NASDAQ" },
  { symbol: "KR", name: "Kroger Co.", exchange: "NYSE" },
  { symbol: "TSN", name: "Tyson Foods", exchange: "NYSE" },
  { symbol: "CAG", name: "Conagra Brands", exchange: "NYSE" },

  // --- INDUSTRIALS & AEROSPACE ---
  { symbol: "UPS", name: "United Parcel Service", exchange: "NYSE" },
  { symbol: "FDX", name: "FedEx Corp", exchange: "NYSE" },
  { symbol: "UNP", name: "Union Pacific", exchange: "NYSE" },
  { symbol: "CSX", name: "CSX Corp", exchange: "NASDAQ" },
  { symbol: "NSC", name: "Norfolk Southern", exchange: "NYSE" },
  { symbol: "DE", name: "John Deere", exchange: "NYSE" },
  { symbol: "CMI", name: "Cummins Inc.", exchange: "NYSE" },
  { symbol: "ETN", name: "Eaton Corp", exchange: "NYSE" },
  { symbol: "ITW", name: "Illinois Tool Works", exchange: "NYSE" },
  { symbol: "EMR", name: "Emerson Electric", exchange: "NYSE" },
  { symbol: "PH", name: "Parker-Hannifin", exchange: "NYSE" },
  { symbol: "HON", name: "Honeywell International", exchange: "NASDAQ" },
  { symbol: "MMM", name: "3M Company", exchange: "NYSE" },
  { symbol: "RTX", name: "RTX Corp (Raytheon)", exchange: "NYSE" },
  { symbol: "LMT", name: "Lockheed Martin", exchange: "NYSE" },
  { symbol: "NOC", name: "Northrop Grumman", exchange: "NYSE" },
  { symbol: "GD", name: "General Dynamics", exchange: "NYSE" },
  { symbol: "LHX", name: "L3Harris Technologies", exchange: "NYSE" },
  { symbol: "TDG", name: "TransDigm Group", exchange: "NYSE" },
  { symbol: "HII", name: "Huntington Ingalls", exchange: "NYSE" },
  { symbol: "AME", name: "AMETEK Inc.", exchange: "NYSE" },
  { symbol: "ROP", name: "Roper Technologies", exchange: "NASDAQ" },
  { symbol: "TT", name: "Trane Technologies", exchange: "NYSE" },
  { symbol: "CARR", name: "Carrier Global", exchange: "NYSE" },
  { symbol: "OTIS", name: "Otis Worldwide", exchange: "NYSE" },
  { symbol: "WM", name: "Waste Management", exchange: "NYSE" },
  { symbol: "RSG", name: "Republic Services", exchange: "NYSE" },
  { symbol: "URI", name: "United Rentals", exchange: "NYSE" },

  // --- ENERGY (OIL & GAS) ---
  { symbol: "CVX", name: "Chevron Corp", exchange: "NYSE" },
  { symbol: "COP", name: "ConocoPhillips", exchange: "NYSE" },
  { symbol: "EOG", name: "EOG Resources", exchange: "NYSE" },
  { symbol: "SLB", name: "Schlumberger", exchange: "NYSE" },
  { symbol: "HAL", name: "Halliburton", exchange: "NYSE" },
  { symbol: "BKR", name: "Baker Hughes", exchange: "NASDAQ" },
  { symbol: "PSX", name: "Phillips 66", exchange: "NYSE" },
  { symbol: "VLO", name: "Valero Energy", exchange: "NYSE" },
  { symbol: "MPC", name: "Marathon Petroleum", exchange: "NYSE" },
  { symbol: "HES", name: "Hess Corp", exchange: "NYSE" },
  { symbol: "OXY", name: "Occidental Petroleum", exchange: "NYSE" },
  { symbol: "DVN", name: "Devon Energy", exchange: "NYSE" },
  { symbol: "KMI", name: "Kinder Morgan", exchange: "NYSE" },
  { symbol: "WMB", name: "Williams Companies", exchange: "NYSE" },
  { symbol: "OKE", name: "ONEOK Inc.", exchange: "NYSE" },
  { symbol: "TRP", name: "TC Energy", exchange: "NYSE" },
  { symbol: "ENB", name: "Enbridge Inc.", exchange: "NYSE" },
  { symbol: "FANG", name: "Diamondback Energy", exchange: "NASDAQ" },

  // --- MATERIALS & CHEMICALS ---
  { symbol: "LIN", name: "Linde plc", exchange: "NYSE" },
  { symbol: "SHW", name: "Sherwin-Williams", exchange: "NYSE" },
  { symbol: "APD", name: "Air Products", exchange: "NYSE" },
  { symbol: "ECL", name: "Ecolab Inc.", exchange: "NYSE" },
  { symbol: "DD", name: "DuPont", exchange: "NYSE" },
  { symbol: "DOW", name: "Dow Inc.", exchange: "NYSE" },
  { symbol: "CTVA", name: "Corteva Inc.", exchange: "NYSE" },
  { symbol: "NEM", name: "Newmont Corp", exchange: "NYSE" },
  { symbol: "FCX", name: "Freeport-McMoRan", exchange: "NYSE" },
  { symbol: "NUE", name: "Nucor Corp", exchange: "NYSE" },
  { symbol: "STLD", name: "Steel Dynamics", exchange: "NASDAQ" },
  { symbol: "VMC", name: "Vulcan Materials", exchange: "NYSE" },
  { symbol: "MLM", name: "Martin Marietta", exchange: "NYSE" },
  { symbol: "ALB", name: "Albemarle Corp", exchange: "NYSE" },
  { symbol: "PPG", name: "PPG Industries", exchange: "NYSE" },

  // --- UTILITIES ---
  { symbol: "NEE", name: "NextEra Energy", exchange: "NYSE" },
  { symbol: "DUK", name: "Duke Energy", exchange: "NYSE" },
  { symbol: "SO", name: "Southern Company", exchange: "NYSE" },
  { symbol: "AEP", name: "American Electric Power", exchange: "NASDAQ" },
  { symbol: "SRE", name: "Sempra", exchange: "NYSE" },
  { symbol: "D", name: "Dominion Energy", exchange: "NYSE" },
  { symbol: "EXC", name: "Exelon Corp", exchange: "NASDAQ" },
  { symbol: "PEG", name: "Public Service Enterprise", exchange: "NYSE" },
  { symbol: "ED", name: "Consolidated Edison", exchange: "NYSE" },
  { symbol: "XEL", name: "Xcel Energy", exchange: "NASDAQ" },
  { symbol: "WEC", name: "WEC Energy Group", exchange: "NYSE" },
  { symbol: "ES", name: "Eversource Energy", exchange: "NYSE" },
  { symbol: "ETR", name: "Entergy Corp", exchange: "NYSE" },
  { symbol: "FE", name: "FirstEnergy", exchange: "NYSE" },
  { symbol: "PPL", name: "PPL Corp", exchange: "NYSE" },
  { symbol: "AWK", name: "American Water Works", exchange: "NYSE" },

  // --- REAL ESTATE (REITS) ---
  { symbol: "PLD", name: "Prologis Inc.", exchange: "NYSE" },
  { symbol: "AMT", name: "American Tower", exchange: "NYSE" },
  { symbol: "CCI", name: "Crown Castle", exchange: "NYSE" },
  { symbol: "SBAC", name: "SBA Communications", exchange: "NASDAQ" },
  { symbol: "EQIX", name: "Equinix Inc.", exchange: "NASDAQ" },
  { symbol: "DLR", name: "Digital Realty", exchange: "NYSE" },
  { symbol: "PSA", name: "Public Storage", exchange: "NYSE" },
  { symbol: "O", name: "Realty Income", exchange: "NYSE" },
  { symbol: "SPG", name: "Simon Property Group", exchange: "NYSE" },
  { symbol: "WELL", name: "Welltower Inc.", exchange: "NYSE" },
  { symbol: "VTR", name: "Ventas Inc.", exchange: "NYSE" },
  { symbol: "VICI", name: "VICI Properties", exchange: "NYSE" },
  { symbol: "CBRE", name: "CBRE Group", exchange: "NYSE" },
  { symbol: "CSGP", name: "CoStar Group", exchange: "NASDAQ" },
  { symbol: "EXR", name: "Extra Space Storage", exchange: "NYSE" },
  { symbol: "IRM", name: "Iron Mountain", exchange: "NYSE" },

  // --- TELECOM & MEDIA ---
  { symbol: "VZ", name: "Verizon Communications", exchange: "NYSE" },
  { symbol: "T", name: "AT&T Inc.", exchange: "NYSE" },
  { symbol: "TMUS", name: "T-Mobile US", exchange: "NASDAQ" },
  { symbol: "CMCSA", name: "Comcast Corp", exchange: "NASDAQ" },
  { symbol: "CHTR", name: "Charter Communications", exchange: "NASDAQ" },
  { symbol: "LBRDA", name: "Liberty Broadband", exchange: "NASDAQ" },
  { symbol: "SIRI", name: "Sirius XM", exchange: "NASDAQ" },
  { symbol: "LYV", name: "Live Nation Entertainment", exchange: "NYSE" },
  { symbol: "OMC", name: "Omnicom Group", exchange: "NYSE" },
  { symbol: "IPG", name: "Interpublic Group", exchange: "NYSE" }
]

// Default stocks shown when the search box is empty.
export const DEFAULT_SEARCH_STOCKS: StockListItem[] = [
  { symbol: "AAPL", name: "Apple", exchange: "NASDAQ" },
  { symbol: "RELIANCE", name: "Reliance Industries", exchange: "BSE" },
  { symbol: "NVDA", name: "NVIDIA", exchange: "NASDAQ" },
  { symbol: "TSLA", name: "Tesla", exchange: "NASDAQ" },
  { symbol: "HDFCBANK", name: "HDFC Bank", exchange: "BSE" },
  { symbol: "TATASTEEL", name: "Tata Steel", exchange: "BSE" },
  { symbol: "GOOGL", name: "Alphabet (Google)", exchange: "NASDAQ" },
  { symbol: "AMZN", name: "Amazon", exchange: "NASDAQ" },
  { symbol: "META", name: "Meta", exchange: "NASDAQ" },
]
/*
export const NSE_STOCKS: StockListItem[] = [
  // --- BANKING & FINANCE (50+ Stocks) ---
  { symbol: "HDFCBANK.NS", name: "HDFC Bank Ltd.", exchange: "NSE" },
  { symbol: "ICICIBANK.NS", name: "ICICI Bank Ltd.", exchange: "NSE" },
  { symbol: "SBIN.NS", name: "State Bank of India", exchange: "NSE" },
  { symbol: "KOTAKBANK.NS", name: "Kotak Mahindra Bank Ltd.", exchange: "NSE" },
  { symbol: "AXISBANK.NS", name: "Axis Bank Ltd.", exchange: "NSE" },
  { symbol: "INDUSINDBK.NS", name: "IndusInd Bank Ltd.", exchange: "NSE" },
  { symbol: "BAJFINANCE.NS", name: "Bajaj Finance Ltd.", exchange: "NSE" },
  { symbol: "BAJAJFINSV.NS", name: "Bajaj Finserv Ltd.", exchange: "NSE" },
  { symbol: "BANKBARODA.NS", name: "Bank of Baroda", exchange: "NSE" },
  { symbol: "PNB.NS", name: "Punjab National Bank", exchange: "NSE" },
  { symbol: "CANBK.NS", name: "Canara Bank", exchange: "NSE" },
  { symbol: "UNIONBANK.NS", name: "Union Bank of India", exchange: "NSE" },
  { symbol: "IDBI.NS", name: "IDBI Bank Ltd.", exchange: "NSE" },
  { symbol: "IOB.NS", name: "Indian Overseas Bank", exchange: "NSE" },
  { symbol: "UCOBANK.NS", name: "UCO Bank", exchange: "NSE" },
  { symbol: "CENTRALBK.NS", name: "Central Bank of India", exchange: "NSE" },
  { symbol: "BANKINDIA.NS", name: "Bank of India", exchange: "NSE" },
  { symbol: "INDIANB.NS", name: "Indian Bank", exchange: "NSE" },
  { symbol: "MAHABANK.NS", name: "Bank of Maharashtra", exchange: "NSE" },
  { symbol: "J&KBANK.NS", name: "Jammu & Kashmir Bank Ltd.", exchange: "NSE" },
  { symbol: "IDFCFIRSTB.NS", name: "IDFC First Bank Ltd.", exchange: "NSE" },
  { symbol: "AUBANK.NS", name: "AU Small Finance Bank Ltd.", exchange: "NSE" },
  { symbol: "BANDHANBNK.NS", name: "Bandhan Bank Ltd.", exchange: "NSE" },
  { symbol: "FEDERALBNK.NS", name: "The Federal Bank Ltd.", exchange: "NSE" },
  { symbol: "KARURVYSYA.NS", name: "Karur Vysya Bank Ltd.", exchange: "NSE" },
  { symbol: "CITYUNIONB.NS", name: "City Union Bank Ltd.", exchange: "NSE" },
  { symbol: "RBLBANK.NS", name: "RBL Bank Ltd.", exchange: "NSE" },
  { symbol: "YESBANK.NS", name: "Yes Bank Ltd.", exchange: "NSE" },
  { symbol: "SOUTHBANK.NS", name: "The South Indian Bank Ltd.", exchange: "NSE" },
  { symbol: "JIOFIN.NS", name: "Jio Financial Services Ltd.", exchange: "NSE" },
  { symbol: "PFC.NS", name: "Power Finance Corporation Ltd.", exchange: "NSE" },
  { symbol: "RECLTD.NS", name: "REC Ltd.", exchange: "NSE" },
  { symbol: "SHRIRAMFIN.NS", name: "Shriram Finance Ltd.", exchange: "NSE" },
  { symbol: "CHOLAFIN.NS", name: "Cholamandalam Inv. & Fin. Co.", exchange: "NSE" },
  { symbol: "MUTHOOTFIN.NS", name: "Muthoot Finance Ltd.", exchange: "NSE" },
  { symbol: "HDFCAMC.NS", name: "HDFC Asset Management Co. Ltd.", exchange: "NSE" },
  { symbol: "SBICARD.NS", name: "SBI Cards and Payment Services", exchange: "NSE" },
  { symbol: "LICHSGFIN.NS", name: "LIC Housing Finance Ltd.", exchange: "NSE" },
  { symbol: "M&MFIN.NS", name: "Mahindra & Mahindra Fin. Serv.", exchange: "NSE" },
  { symbol: "SUNDARMFIN.NS", name: "Sundaram Finance Ltd.", exchange: "NSE" },
  { symbol: "L&TFH.NS", name: "L&T Finance Holdings Ltd.", exchange: "NSE" },
  { symbol: "MANAPPURAM.NS", name: "Manappuram Finance Ltd.", exchange: "NSE" },
  { symbol: "POONAWALLA.NS", name: "Poonawalla Fincorp Ltd.", exchange: "NSE" },
  { symbol: "ABCAPITAL.NS", name: "Aditya Birla Capital Ltd.", exchange: "NSE" },
  { symbol: "MOTILALOFS.NS", name: "Motilal Oswal Financial Services", exchange: "NSE" },
  { symbol: "ISEC.NS", name: "ICICI Securities Ltd.", exchange: "NSE" },
  { symbol: "ANGELONE.NS", name: "Angel One Ltd.", exchange: "NSE" },
  { symbol: "CDSL.NS", name: "Central Depository Services", exchange: "NSE" },
  { symbol: "BSE.NS", name: "BSE Ltd.", exchange: "NSE" },
  { symbol: "MCX.NS", name: "Multi Commodity Exchange", exchange: "NSE" },

  // --- IT & TECHNOLOGY (40 Stocks) ---
  { symbol: "TCS.NS", name: "Tata Consultancy Services Ltd.", exchange: "NSE" },
  { symbol: "INFY.NS", name: "Infosys Ltd.", exchange: "NSE" },
  { symbol: "HCLTECH.NS", name: "HCL Technologies Ltd.", exchange: "NSE" },
  { symbol: "WIPRO.NS", name: "Wipro Ltd.", exchange: "NSE" },
  { symbol: "TECHM.NS", name: "Tech Mahindra Ltd.", exchange: "NSE" },
  { symbol: "LTIM.NS", name: "LTIMindtree Ltd.", exchange: "NSE" },
  { symbol: "OFSS.NS", name: "Oracle Financial Services", exchange: "NSE" },
  { symbol: "PERSISTENT.NS", name: "Persistent Systems Ltd.", exchange: "NSE" },
  { symbol: "MPHASIS.NS", name: "Mphasis Ltd.", exchange: "NSE" },
  { symbol: "KPITTECH.NS", name: "KPIT Technologies Ltd.", exchange: "NSE" },
  { symbol: "TATAELXSI.NS", name: "Tata Elxsi Ltd.", exchange: "NSE" },
  { symbol: "COFORGE.NS", name: "Coforge Ltd.", exchange: "NSE" },
  { symbol: "LTTS.NS", name: "L&T Technology Services Ltd.", exchange: "NSE" },
  { symbol: "CYIENT.NS", name: "Cyient Ltd.", exchange: "NSE" },
  { symbol: "ZENSARTECH.NS", name: "Zensar Technologies Ltd.", exchange: "NSE" },
  { symbol: "BSOFT.NS", name: "Birlasoft Ltd.", exchange: "NSE" },
  { symbol: "SONATSOFTW.NS", name: "Sonata Software Ltd.", exchange: "NSE" },
  { symbol: "INTELLECT.NS", name: "Intellect Design Arena Ltd.", exchange: "NSE" },
  { symbol: "REDINGTON.NS", name: "Redington Ltd.", exchange: "NSE" },
  { symbol: "LATENTVIEW.NS", name: "Latent View Analytics Ltd.", exchange: "NSE" },
  { symbol: "HAPPSTMNDS.NS", name: "Happiest Minds Technologies", exchange: "NSE" },
  { symbol: "MASTEK.NS", name: "Mastek Ltd.", exchange: "NSE" },
  { symbol: "TANLA.NS", name: "Tanla Platforms Ltd.", exchange: "NSE" },
  { symbol: "ROUTE.NS", name: "Route Mobile Ltd.", exchange: "NSE" },
  { symbol: "AFFLE.NS", name: "Affle (India) Ltd.", exchange: "NSE" },
  { symbol: "NAUKRI.NS", name: "Info Edge (India) Ltd.", exchange: "NSE" },
  { symbol: "PAYTM.NS", name: "One 97 Communications Ltd.", exchange: "NSE" },
  { symbol: "ZOMATO.NS", name: "Zomato Ltd.", exchange: "NSE" },
  { symbol: "PBFINTECH.NS", name: "PB Fintech Ltd. (PolicyBazaar)", exchange: "NSE" },
  { symbol: "NYKAA.NS", name: "FSN E-Commerce Ventures Ltd.", exchange: "NSE" },
  { symbol: "DELHIVERY.NS", name: "Delhivery Ltd.", exchange: "NSE" },
  { symbol: "MAPMYINDIA.NS", name: "C.E. Info Systems Ltd.", exchange: "NSE" },
  { symbol: "RATEGAIN.NS", name: "RateGain Travel Technologies", exchange: "NSE" },
  { symbol: "NAZARA.NS", name: "Nazara Technologies Ltd.", exchange: "NSE" },
  { symbol: "FSL.NS", name: "Firstsource Solutions Ltd.", exchange: "NSE" },
  { symbol: "ECLERX.NS", name: "eClerx Services Ltd.", exchange: "NSE" },
  { symbol: "DATAMATICS.NS", name: "Datamatics Global Services", exchange: "NSE" },
  { symbol: "NETWEB.NS", name: "Netweb Technologies India", exchange: "NSE" },

  // --- AUTOMOBILE & ANCILLARIES (30 Stocks) ---
  { symbol: "MARUTI.NS", name: "Maruti Suzuki India Ltd.", exchange: "NSE" },
  { symbol: "TATAMOTORS.NS", name: "Tata Motors Ltd.", exchange: "NSE" },
  { symbol: "M&M.NS", name: "Mahindra & Mahindra Ltd.", exchange: "NSE" },
  { symbol: "HEROMOTOCO.NS", name: "Hero MotoCorp Ltd.", exchange: "NSE" },
  { symbol: "BAJAJ-AUTO.NS", name: "Bajaj Auto Ltd.", exchange: "NSE" },
  { symbol: "EICHERMOT.NS", name: "Eicher Motors Ltd.", exchange: "NSE" },
  { symbol: "TVSMOTOR.NS", name: "TVS Motor Company Ltd.", exchange: "NSE" },
  { symbol: "ASHOKLEY.NS", name: "Ashok Leyland Ltd.", exchange: "NSE" },
  { symbol: "BHARATFORG.NS", name: "Bharat Forge Ltd.", exchange: "NSE" },
  { symbol: "MOTHERSON.NS", name: "Samvardhana Motherson Intl.", exchange: "NSE" },
  { symbol: "BOSCHLTD.NS", name: "Bosch Ltd.", exchange: "NSE" },
  { symbol: "MRF.NS", name: "MRF Ltd.", exchange: "NSE" },
  { symbol: "APOLLOTYRE.NS", name: "Apollo Tyres Ltd.", exchange: "NSE" },
  { symbol: "BALKRISIND.NS", name: "Balkrishna Industries Ltd.", exchange: "NSE" },
  { symbol: "JKTYRE.NS", name: "JK Tyre & Industries Ltd.", exchange: "NSE" },
  { symbol: "CEATLTD.NS", name: "CEAT Ltd.", exchange: "NSE" },
  { symbol: "EXIDEIND.NS", name: "Exide Industries Ltd.", exchange: "NSE" },
  { symbol: "AMARAJABAT.NS", name: "Amara Raja Energy & Mobility", exchange: "NSE" },
  { symbol: "SONACOMS.NS", name: "Sona BLW Precision Forgings", exchange: "NSE" },
  { symbol: "TIINDIA.NS", name: "Tube Investments of India", exchange: "NSE" },
  { symbol: "TUBERC.NS", name: "Tube Investments", exchange: "NSE" },
  { symbol: "UNO-MINDA.NS", name: "Uno Minda Ltd.", exchange: "NSE" },
  { symbol: "ENDURANCE.NS", name: "Endurance Technologies Ltd.", exchange: "NSE" },
  { symbol: "CRAFTSMAN.NS", name: "Craftsman Automation Ltd.", exchange: "NSE" },
  { symbol: "VARROC.NS", name: "Varroc Engineering Ltd.", exchange: "NSE" },
  { symbol: "GABRIEL.NS", name: "Gabriel India Ltd.", exchange: "NSE" },
  { symbol: "FORCE.NS", name: "Force Motors Ltd.", exchange: "NSE" },
  { symbol: "ESCORTS.NS", name: "Escorts Kubota Ltd.", exchange: "NSE" },
  { symbol: "SMLISUZU.NS", name: "SML Isuzu Ltd.", exchange: "NSE" },
  { symbol: "OLAELEC.NS", name: "Ola Electric Mobility", exchange: "NSE" },

  // --- HEALTHCARE & PHARMA (35 Stocks) ---
  { symbol: "SUNPHARMA.NS", name: "Sun Pharmaceutical Industries", exchange: "NSE" },
  { symbol: "DRREDDY.NS", name: "Dr. Reddy's Laboratories", exchange: "NSE" },
  { symbol: "CIPLA.NS", name: "Cipla Ltd.", exchange: "NSE" },
  { symbol: "DIVISLAB.NS", name: "Divi's Laboratories Ltd.", exchange: "NSE" },
  { symbol: "LUPIN.NS", name: "Lupin Ltd.", exchange: "NSE" },
  { symbol: "AUROPHARMA.NS", name: "Aurobindo Pharma Ltd.", exchange: "NSE" },
  { symbol: "TORNTPHARM.NS", name: "Torrent Pharmaceuticals", exchange: "NSE" },
  { symbol: "ALKEM.NS", name: "Alkem Laboratories Ltd.", exchange: "NSE" },
  { symbol: "ZYDUSLIFE.NS", name: "Zydus Lifesciences Ltd.", exchange: "NSE" },
  { symbol: "MANKIND.NS", name: "Mankind Pharma Ltd.", exchange: "NSE" },
  { symbol: "BIOCON.NS", name: "Biocon Ltd.", exchange: "NSE" },
  { symbol: "GLAND.NS", name: "Gland Pharma Ltd.", exchange: "NSE" },
  { symbol: "LAURUSLAB.NS", name: "Laurus Labs Ltd.", exchange: "NSE" },
  { symbol: "ABBOTINDIA.NS", name: "Abbott India Ltd.", exchange: "NSE" },
  { symbol: "GLAXO.NS", name: "GlaxoSmithKline Pharma", exchange: "NSE" },
  { symbol: "PFIZER.NS", name: "Pfizer Ltd.", exchange: "NSE" },
  { symbol: "SANOFI.NS", name: "Sanofi India Ltd.", exchange: "NSE" },
  { symbol: "JBCHEPHARM.NS", name: "J.B. Chemicals & Pharm", exchange: "NSE" },
  { symbol: "NATCOPHARM.NS", name: "Natco Pharma Ltd.", exchange: "NSE" },
  { symbol: "GRANULES.NS", name: "Granules India Ltd.", exchange: "NSE" },
  { symbol: "ALEMBICLTD.NS", name: "Alembic Pharmaceuticals", exchange: "NSE" },
  { symbol: "APOLLOHOSP.NS", name: "Apollo Hospitals Enterprise", exchange: "NSE" },
  { symbol: "MAXHEALTH.NS", name: "Max Healthcare Institute", exchange: "NSE" },
  { symbol: "FORTIS.NS", name: "Fortis Healthcare Ltd.", exchange: "NSE" },
  { symbol: "MEDANTA.NS", name: "Global Health Ltd.", exchange: "NSE" },
  { symbol: "NH.NS", name: "Narayana Hrudayalaya Ltd.", exchange: "NSE" },
  { symbol: "ASTERDM.NS", name: "Aster DM Healthcare Ltd.", exchange: "NSE" },
  { symbol: "KIMS.NS", name: "Krishna Inst. of Med. Sci.", exchange: "NSE" },
  { symbol: "METROPOLIS.NS", name: "Metropolis Healthcare Ltd.", exchange: "NSE" },
  { symbol: "LALPATHLAB.NS", name: "Dr. Lal PathLabs Ltd.", exchange: "NSE" },
  { symbol: "SYNGENE.NS", name: "Syngene International Ltd.", exchange: "NSE" },
  { symbol: "POLYMED.NS", name: "Poly Medicure Ltd.", exchange: "NSE" },

  // --- FMCG & CONSUMER GOODS (30 Stocks) ---
  { symbol: "HINDUNILVR.NS", name: "Hindustan Unilever Ltd.", exchange: "NSE" },
  { symbol: "ITC.NS", name: "ITC Ltd.", exchange: "NSE" },
  { symbol: "NESTLEIND.NS", name: "Nestle India Ltd.", exchange: "NSE" },
  { symbol: "BRITANNIA.NS", name: "Britannia Industries Ltd.", exchange: "NSE" },
  { symbol: "TATACONSUM.NS", name: "Tata Consumer Products", exchange: "NSE" },
  { symbol: "GODREJCP.NS", name: "Godrej Consumer Products", exchange: "NSE" },
  { symbol: "DABUR.NS", name: "Dabur India Ltd.", exchange: "NSE" },
  { symbol: "MARICO.NS", name: "Marico Ltd.", exchange: "NSE" },
  { symbol: "VBL.NS", name: "Varun Beverages Ltd.", exchange: "NSE" },
  { symbol: "COLPAL.NS", name: "Colgate-Palmolive (India)", exchange: "NSE" },
  { symbol: "BERGEPAINT.NS", name: "Berger Paints India Ltd.", exchange: "NSE" },
  { symbol: "ASIANPAINT.NS", name: "Asian Paints Ltd.", exchange: "NSE" },
  { symbol: "PIDILITE.NS", name: "Pidilite Industries Ltd.", exchange: "NSE" },
  { symbol: "PGHH.NS", name: "P&G Hygiene and Health Care", exchange: "NSE" },
  { symbol: "GILLETTE.NS", name: "Gillette India Ltd.", exchange: "NSE" },
  { symbol: "EMAMILTD.NS", name: "Emami Ltd.", exchange: "NSE" },
  { symbol: "JYOTHYLAB.NS", name: "Jyothy Labs Ltd.", exchange: "NSE" },
  { symbol: "RADICO.NS", name: "Radico Khaitan Ltd.", exchange: "NSE" },
  { symbol: "UBL.NS", name: "United Breweries Ltd.", exchange: "NSE" },
  { symbol: "MCDOWELL-N.NS", name: "United Spirits Ltd.", exchange: "NSE" },
  { symbol: "HATSUN.NS", name: "Hatsun Agro Product Ltd.", exchange: "NSE" },
  { symbol: "BIKAJI.NS", name: "Bikaji Foods International", exchange: "NSE" },
  { symbol: "PATANJALI.NS", name: "Patanjali Foods Ltd.", exchange: "NSE" },
  { symbol: "AWL.NS", name: "Adani Wilmar Ltd.", exchange: "NSE" },
  { symbol: "KRBL.NS", name: "KRBL Ltd.", exchange: "NSE" },
  { symbol: "LTFOODS.NS", name: "LT Foods Ltd.", exchange: "NSE" },
  { symbol: "CCL.NS", name: "CCL Products (India) Ltd.", exchange: "NSE" },
  { symbol: "TITAN.NS", name: "Titan Company Ltd.", exchange: "NSE" },
  { symbol: "BATAINDIA.NS", name: "Bata India Ltd.", exchange: "NSE" },
  { symbol: "RELAXO.NS", name: "Relaxo Footwears Ltd.", exchange: "NSE" },

  // --- ENERGY, OIL & GAS (30 Stocks) ---
  { symbol: "RELIANCE.NS", name: "Reliance Industries Ltd.", exchange: "NSE" },
  { symbol: "ONGC.NS", name: "Oil & Natural Gas Corp.", exchange: "NSE" },
  { symbol: "OIL.NS", name: "Oil India Ltd.", exchange: "NSE" },
  { symbol: "IOC.NS", name: "Indian Oil Corporation", exchange: "NSE" },
  { symbol: "BPCL.NS", name: "Bharat Petroleum Corp.", exchange: "NSE" },
  { symbol: "HPCL.NS", name: "Hindustan Petroleum Corp.", exchange: "NSE" },
  { symbol: "GAIL.NS", name: "GAIL (India) Ltd.", exchange: "NSE" },
  { symbol: "PETRONET.NS", name: "Petronet LNG Ltd.", exchange: "NSE" },
  { symbol: "IGL.NS", name: "Indraprastha Gas Ltd.", exchange: "NSE" },
  { symbol: "MGL.NS", name: "Mahanagar Gas Ltd.", exchange: "NSE" },
  { symbol: "GUJGASLTD.NS", name: "Gujarat Gas Ltd.", exchange: "NSE" },
  { symbol: "ATGL.NS", name: "Adani Total Gas Ltd.", exchange: "NSE" },
  { symbol: "NTPC.NS", name: "NTPC Ltd.", exchange: "NSE" },
  { symbol: "POWERGRID.NS", name: "Power Grid Corp. of India", exchange: "NSE" },
  { symbol: "TATAPOWER.NS", name: "Tata Power Company Ltd.", exchange: "NSE" },
  { symbol: "ADANIGREEN.NS", name: "Adani Green Energy Ltd.", exchange: "NSE" },
  { symbol: "ADANIPOWER.NS", name: "Adani Power Ltd.", exchange: "NSE" },
  { symbol: "JSWENERGY.NS", name: "JSW Energy Ltd.", exchange: "NSE" },
  { symbol: "TORNTPOWER.NS", name: "Torrent Power Ltd.", exchange: "NSE" },
  { symbol: "NHPC.NS", name: "NHPC Ltd.", exchange: "NSE" },
  { symbol: "SJVN.NS", name: "SJVN Ltd.", exchange: "NSE" },
  { symbol: "COALINDIA.NS", name: "Coal India Ltd.", exchange: "NSE" },
  { symbol: "SUZLON.NS", name: "Suzlon Energy Ltd.", exchange: "NSE" },
  { symbol: "WAAREEENER.NS", name: "Waaree Energies Ltd.", exchange: "NSE" },
  { symbol: "IREDA.NS", name: "Indian Renewable Energy Dev", exchange: "NSE" },
  { symbol: "BORORENEW.NS", name: "Borosil Renewables Ltd.", exchange: "NSE" },
  { symbol: "KPIGREEN.NS", name: "KPI Green Energy Ltd.", exchange: "NSE" },
  { symbol: "INOXWIND.NS", name: "Inox Wind Ltd.", exchange: "NSE" },
  { symbol: "CESC.NS", name: "CESC Ltd.", exchange: "NSE" },
  { symbol: "IEX.NS", name: "Indian Energy Exchange", exchange: "NSE" },

  // --- INFRASTRUCTURE, CONSTRUCTION & REALTY (25 Stocks) ---
  { symbol: "LT.NS", name: "Larsen & Toubro Ltd.", exchange: "NSE" },
  { symbol: "DLF.NS", name: "DLF Ltd.", exchange: "NSE" },
  { symbol: "MACROTECH.NS", name: "Macrotech Developers (Lodha)", exchange: "NSE" },
  { symbol: "GODREJPROP.NS", name: "Godrej Properties Ltd.", exchange: "NSE" },
  { symbol: "OBEROIRLTY.NS", name: "Oberoi Realty Ltd.", exchange: "NSE" },
  { symbol: "PHOENIXLTD.NS", name: "The Phoenix Mills Ltd.", exchange: "NSE" },
  { symbol: "PRESTIGE.NS", name: "Prestige Estates Projects", exchange: "NSE" },
  { symbol: "BRIGADE.NS", name: "Brigade Enterprises Ltd.", exchange: "NSE" },
  { symbol: "SOBHA.NS", name: "Sobha Ltd.", exchange: "NSE" },
  { symbol: "ULTRACEMCO.NS", name: "UltraTech Cement Ltd.", exchange: "NSE" },
  { symbol: "GRASIM.NS", name: "Grasim Industries Ltd.", exchange: "NSE" },
  { symbol: "AMBUJACEM.NS", name: "Ambuja Cements Ltd.", exchange: "NSE" },
  { symbol: "ACC.NS", name: "ACC Ltd.", exchange: "NSE" },
  { symbol: "SHREECEM.NS", name: "Shree Cement Ltd.", exchange: "NSE" },
  { symbol: "DALBHARAT.NS", name: "Dalmia Bharat Ltd.", exchange: "NSE" },
  { symbol: "JKCEMENT.NS", name: "JK Cement Ltd.", exchange: "NSE" },
  { symbol: "RAMCOCEM.NS", name: "The Ramco Cements Ltd.", exchange: "NSE" },
  { symbol: "ADANIENT.NS", name: "Adani Enterprises Ltd.", exchange: "NSE" },
  { symbol: "GMRINFRA.NS", name: "GMR Airports Infra Ltd.", exchange: "NSE" },
  { symbol: "IRB.NS", name: "IRB Infrastructure Dev.", exchange: "NSE" },
  { symbol: "RVNL.NS", name: "Rail Vikas Nigam Ltd.", exchange: "NSE" },
  { symbol: "IRCON.NS", name: "Ircon International Ltd.", exchange: "NSE" },
  { symbol: "NBCC.NS", name: "NBCC (India) Ltd.", exchange: "NSE" },
  { symbol: "KNRCON.NS", name: "KNR Constructions Ltd.", exchange: "NSE" },
  { symbol: "PNCINFRA.NS", name: "PNC Infratech Ltd.", exchange: "NSE" },

  // --- METALS & MINING (20 Stocks) ---
  { symbol: "TATASTEEL.NS", name: "Tata Steel Ltd.", exchange: "NSE" },
  { symbol: "JSWSTEEL.NS", name: "JSW Steel Ltd.", exchange: "NSE" },
  { symbol: "HINDALCO.NS", name: "Hindalco Industries Ltd.", exchange: "NSE" },
  { symbol: "VEDL.NS", name: "Vedanta Ltd.", exchange: "NSE" },
  { symbol: "JINDALSTEL.NS", name: "Jindal Steel & Power Ltd.", exchange: "NSE" },
  { symbol: "SAIL.NS", name: "Steel Authority of India", exchange: "NSE" },
  { symbol: "NMDC.NS", name: "NMDC Ltd.", exchange: "NSE" },
  { symbol: "HINDZINC.NS", name: "Hindustan Zinc Ltd.", exchange: "NSE" },
  { symbol: "NATIONALUM.NS", name: "National Aluminium Co.", exchange: "NSE" },
  { symbol: "HINDCOPPER.NS", name: "Hindustan Copper Ltd.", exchange: "NSE" },
  { symbol: "APLAPOLLO.NS", name: "APL Apollo Tubes Ltd.", exchange: "NSE" },
  { symbol: "RATNAMANI.NS", name: "Ratnamani Metals & Tubes", exchange: "NSE" },
  { symbol: "JSL.NS", name: "Jindal Stainless Ltd.", exchange: "NSE" },
  { symbol: "WELCORP.NS", name: "Welspun Corp Ltd.", exchange: "NSE" },
  { symbol: "MOIL.NS", name: "MOIL Ltd.", exchange: "NSE" },
  { symbol: "GMDC.NS", name: "Gujarat Mineral Dev. Corp", exchange: "NSE" },
  { symbol: "KIOCL.NS", name: "KIOCL Ltd.", exchange: "NSE" },
  { symbol: "GPIL.NS", name: "Godawari Power & Ispat", exchange: "NSE" },
  { symbol: "ELECTROSL.NS", name: "Electrosteel Castings", exchange: "NSE" },
  { symbol: "GRAVITA.NS", name: "Gravita India Ltd.", exchange: "NSE" },

  // --- TELECOM & MEDIA (10 Stocks) ---
  { symbol: "BHARTIARTL.NS", name: "Bharti Airtel Ltd.", exchange: "NSE" },
  { symbol: "IDEA.NS", name: "Vodafone Idea Ltd.", exchange: "NSE" },
  { symbol: "INDUSTOWER.NS", name: "Indus Towers Ltd.", exchange: "NSE" },
  { symbol: "TATACOMM.NS", name: "Tata Communications Ltd.", exchange: "NSE" },
  { symbol: "HFCL.NS", name: "HFCL Ltd.", exchange: "NSE" },
  { symbol: "ITI.NS", name: "ITI Ltd.", exchange: "NSE" },
  { symbol: "TEJASNET.NS", name: "Tejas Networks Ltd.", exchange: "NSE" },
  { symbol: "SUNTV.NS", name: "Sun TV Network Ltd.", exchange: "NSE" },
  { symbol: "ZEEL.NS", name: "Zee Entertainment Ent.", exchange: "NSE" },
  { symbol: "PVRINOX.NS", name: "PVR INOX Ltd.", exchange: "NSE" },
  { symbol: "NETWORK18.NS", name: "Network18 Media & Inv.", exchange: "NSE" },
  { symbol: "TV18BRDCST.NS", name: "TV18 Broadcast Ltd.", exchange: "NSE" },

  // --- OTHERS / SERVICES / DEFENCE (20 Stocks) ---
  { symbol: "HAL.NS", name: "Hindustan Aeronautics Ltd.", exchange: "NSE" },
  { symbol: "BEL.NS", name: "Bharat Electronics Ltd.", exchange: "NSE" },
  { symbol: "BDL.NS", name: "Bharat Dynamics Ltd.", exchange: "NSE" },
  { symbol: "MAZDOCK.NS", name: "Mazagon Dock Shipbuilders", exchange: "NSE" },
  { symbol: "COCHINSHIP.NS", name: "Cochin Shipyard Ltd.", exchange: "NSE" },
  { symbol: "GRSE.NS", name: "Garden Reach Shipbuilders", exchange: "NSE" },
  { symbol: "SOLARINDS.NS", name: "Solar Industries India", exchange: "NSE" },
  { symbol: "ASTRAL.NS", name: "Astral Ltd.", exchange: "NSE" },
  { symbol: "POLYCAB.NS", name: "Polycab India Ltd.", exchange: "NSE" },
  { symbol: "HAVELLS.NS", name: "Havells India Ltd.", exchange: "NSE" },
  { symbol: "CROMPTON.NS", name: "Crompton Greaves Cons.", exchange: "NSE" },
  { symbol: "VOLTAS.NS", name: "Voltas Ltd.", exchange: "NSE" },
  { symbol: "BLUESTARACO.NS", name: "Blue Star Ltd.", exchange: "NSE" },
  { symbol: "KAJARIACER.NS", name: "Kajaria Ceramics Ltd.", exchange: "NSE" },
  { symbol: "IRCTC.NS", name: "IRCTC Ltd.", exchange: "NSE" },
  { symbol: "INDHOTEL.NS", name: "The Indian Hotels Co.", exchange: "NSE" },
  { symbol: "CHALET.NS", name: "Chalet Hotels Ltd.", exchange: "NSE" },
  { symbol: "EIHOTEL.NS", name: "EIH Ltd. (Oberoi Group)", exchange: "NSE" },
  { symbol: "TRENT.NS", name: "Trent Ltd.", exchange: "NSE" },
  { symbol: "ABFRL.NS", name: "Aditya Birla Fashion & Retail", exchange: "NSE" },

  // --- CHEMICALS & FERTILIZERS ---
  { symbol: "UPL.NS", name: "UPL Ltd.", exchange: "NSE" },
  { symbol: "SRF.NS", name: "SRF Ltd.", exchange: "NSE" },
  { symbol: "AARTIIND.NS", name: "Aarti Industries Ltd.", exchange: "NSE" },
  { symbol: "ATUL.NS", name: "Atul Ltd.", exchange: "NSE" },
  { symbol: "DEEPAKNTR.NS", name: "Deepak Nitrite Ltd.", exchange: "NSE" },
  { symbol: "TATACHEM.NS", name: "Tata Chemicals Ltd.", exchange: "NSE" },
  { symbol: "NAVINFLUOR.NS", name: "Navin Fluorine International", exchange: "NSE" },
  { symbol: "VINATIORGA.NS", name: "Vinati Organics Ltd.", exchange: "NSE" },
  { symbol: "PIIND.NS", name: "PI Industries Ltd.", exchange: "NSE" },
  { symbol: "COROMANDEL.NS", name: "Coromandel International", exchange: "NSE" },
  { symbol: "CHAMBLFERT.NS", name: "Chambal Fertilisers", exchange: "NSE" },
  { symbol: "GNFC.NS", name: "Gujarat Narmada Valley", exchange: "NSE" },
  { symbol: "GSFC.NS", name: "Gujarat State Fertilizers", exchange: "NSE" },
  { symbol: "RCF.NS", name: "Rashtriya Chemicals & Fert", exchange: "NSE" },
  { symbol: "FACT.NS", name: "Fertilisers & Chem Travancore", exchange: "NSE" },
  { symbol: "LINDEINDIA.NS", name: "Linde India Ltd.", exchange: "NSE" },
  { symbol: "FLUOROCHEM.NS", name: "Gujarat Fluorochemicals", exchange: "NSE" },
  { symbol: "CLEAN.NS", name: "Clean Science & Tech", exchange: "NSE" },
  { symbol: "FINEORG.NS", name: "Fine Organic Industries", exchange: "NSE" },
  { symbol: "ALKYLAMINE.NS", name: "Alkyl Amines Chemicals", exchange: "NSE" },
  { symbol: "BALAMINES.NS", name: "Balaji Amines Ltd.", exchange: "NSE" },
  { symbol: "SUMICHEM.NS", name: "Sumitomo Chemical India", exchange: "NSE" },
  { symbol: "JUBLINGREA.NS", name: "Jubilant Ingrevia Ltd.", exchange: "NSE" },
  { symbol: "SUDARSCHEM.NS", name: "Sudarshan Chemical Inds", exchange: "NSE" },
  { symbol: "ROSSARI.NS", name: "Rossari Biotech Ltd.", exchange: "NSE" },
  { symbol: "NOCIL.NS", name: "NOCIL Ltd.", exchange: "NSE" },
  { symbol: "LAXMISACH.NS", name: "Laxmi Organic Industries", exchange: "NSE" },
  { symbol: "ANUPAM.NS", name: "Anupam Rasayan India", exchange: "NSE" },
  { symbol: "PRIVISCL.NS", name: "Privi Speciality Chemicals", exchange: "NSE" },
  { symbol: "NEOGEN.NS", name: "Neogen Chemicals Ltd.", exchange: "NSE" },

  // --- CAPITAL GOODS, ENGINEERING & POWER ---
  { symbol: "SIEMENS.NS", name: "Siemens Ltd.", exchange: "NSE" },
  { symbol: "ABB.NS", name: "ABB India Ltd.", exchange: "NSE" },
  { symbol: "BHEL.NS", name: "Bharat Heavy Electricals", exchange: "NSE" },
  { symbol: "THERMAX.NS", name: "Thermax Ltd.", exchange: "NSE" },
  { symbol: "CUMMINSIND.NS", name: "Cummins India Ltd.", exchange: "NSE" },
  { symbol: "CGPOWER.NS", name: "CG Power & Industrial Sol", exchange: "NSE" },
  { symbol: "TRITURBINE.NS", name: "Triveni Turbine Ltd.", exchange: "NSE" },
  { symbol: "CARBORUNIV.NS", name: "Carborundum Universal", exchange: "NSE" },
  { symbol: "GRINDWELL.NS", name: "Grindwell Norton Ltd.", exchange: "NSE" },
  { symbol: "AIAENG.NS", name: "AIA Engineering Ltd.", exchange: "NSE" },
  { symbol: "TIMKEN.NS", name: "Timken India Ltd.", exchange: "NSE" },
  { symbol: "SCHAEFFLER.NS", name: "Schaeffler India Ltd.", exchange: "NSE" },
  { symbol: "ELGIEQUIP.NS", name: "Elgi Equipments Ltd.", exchange: "NSE" },
  { symbol: "KEC.NS", name: "KEC International Ltd.", exchange: "NSE" },
  { symbol: "KALPATPOWR.NS", name: "Kalpataru Projects Intl", exchange: "NSE" },
  { symbol: "TECHNOE.NS", name: "Techno Electric & Eng", exchange: "NSE" },
  { symbol: "BEML.NS", name: "BEML Ltd.", exchange: "NSE" },
  { symbol: "ENGINERSIN.NS", name: "Engineers India Ltd.", exchange: "NSE" },
  { symbol: "ISGEC.NS", name: "Isgec Heavy Engineering", exchange: "NSE" },
  { symbol: "PRAJIND.NS", name: "Praj Industries Ltd.", exchange: "NSE" },
  { symbol: "ADANIENSOL.NS", name: "Adani Energy Solutions", exchange: "NSE" },
  { symbol: "NLCINDIA.NS", name: "NLC India Ltd.", exchange: "NSE" },
  { symbol: "JPPOWER.NS", name: "Jaiprakash Power Ventures", exchange: "NSE" },
  { symbol: "RTNPOWER.NS", name: "RattanIndia Power Ltd.", exchange: "NSE" },
  { symbol: "PTC.NS", name: "PTC India Ltd.", exchange: "NSE" },

  // --- FINANCIAL SERVICES (INSURANCE, AMC, NBFC) ---
  { symbol: "HDFCLIFE.NS", name: "HDFC Life Insurance", exchange: "NSE" },
  { symbol: "SBILIFE.NS", name: "SBI Life Insurance", exchange: "NSE" },
  { symbol: "ICICIPRULI.NS", name: "ICICI Pru Life Insurance", exchange: "NSE" },
  { symbol: "ICICIGI.NS", name: "ICICI Lombard Gen Ins", exchange: "NSE" },
  { symbol: "STARHEALTH.NS", name: "Star Health & Allied Ins", exchange: "NSE" },
  { symbol: "GICRE.NS", name: "General Insurance Corp", exchange: "NSE" },
  { symbol: "NIACL.NS", name: "New India Assurance", exchange: "NSE" },
  { symbol: "UTIAMC.NS", name: "UTI Asset Management", exchange: "NSE" },
  { symbol: "NAM-INDIA.NS", name: "Nippon Life India AMC", exchange: "NSE" },
  { symbol: "CAMS.NS", name: "Computer Age Mgmt Svcs", exchange: "NSE" },
  { symbol: "KFINTECH.NS", name: "KFin Technologies Ltd.", exchange: "NSE" },
  { symbol: "CRISIL.NS", name: "CRISIL Ltd.", exchange: "NSE" },
  { symbol: "ICRA.NS", name: "ICRA Ltd.", exchange: "NSE" },
  { symbol: "CREDITACC.NS", name: "CreditAccess Grameen", exchange: "NSE" },
  { symbol: "FIVESTAR.NS", name: "Five-Star Business Finance", exchange: "NSE" },
  { symbol: "AAVAS.NS", name: "Aavas Financiers Ltd.", exchange: "NSE" },
  { symbol: "HUDCO.NS", name: "HUDCO Ltd.", exchange: "NSE" },
  { symbol: "IRFC.NS", name: "Indian Railway Finance", exchange: "NSE" },
  { symbol: "PNBHOUSING.NS", name: "PNB Housing Finance", exchange: "NSE" },
  { symbol: "CANFINHOME.NS", name: "Can Fin Homes Ltd.", exchange: "NSE" },
  { symbol: "HOMEFIRST.NS", name: "Home First Finance Co", exchange: "NSE" },
  { symbol: "INDIASHELT.NS", name: "India Shelter Finance", exchange: "NSE" },
  { symbol: "JMFINANCIL.NS", name: "JM Financial Ltd.", exchange: "NSE" },
  { symbol: "EDELWEISS.NS", name: "Edelweiss Financial", exchange: "NSE" },
  { symbol: "UJJIVANSFB.NS", name: "Ujjivan Small Finance Bank", exchange: "NSE" },
  { symbol: "EQUITASBNK.NS", name: "Equitas Small Finance Bank", exchange: "NSE" },

  // --- CONSUMER DURABLES, CABLES & PLASTICS ---
  { symbol: "KEI.NS", name: "KEI Industries Ltd.", exchange: "NSE" },
  { symbol: "RRKABEL.NS", name: "R R Kabel Ltd.", exchange: "NSE" },
  { symbol: "FINCABLES.NS", name: "Finolex Cables Ltd.", exchange: "NSE" },
  { symbol: "VGUARD.NS", name: "V-Guard Industries Ltd.", exchange: "NSE" },
  { symbol: "ORIENTELEC.NS", name: "Orient Electric Ltd.", exchange: "NSE" },
  { symbol: "SYMPHONY.NS", name: "Symphony Ltd.", exchange: "NSE" },
  { symbol: "WHIRLPOOL.NS", name: "Whirlpool of India Ltd.", exchange: "NSE" },
  { symbol: "TTKPRESTIGE.NS", name: "TTK Prestige Ltd.", exchange: "NSE" },
  { symbol: "HAWKINCOOK.NS", name: "Hawkins Cookers Ltd.", exchange: "NSE" },
  { symbol: "VIPIND.NS", name: "VIP Industries Ltd.", exchange: "NSE" },
  { symbol: "SAFARI.NS", name: "Safari Industries Ltd.", exchange: "NSE" },
  { symbol: "SUPREMEIND.NS", name: "Supreme Industries Ltd.", exchange: "NSE" },
  { symbol: "FINPIPE.NS", name: "Finolex Industries Ltd.", exchange: "NSE" },
  { symbol: "PRINCEPIPE.NS", name: "Prince Pipes & Fittings", exchange: "NSE" },
  { symbol: "CERA.NS", name: "Cera Sanitaryware Ltd.", exchange: "NSE" },
  { symbol: "SOMANYCERA.NS", name: "Somany Ceramics Ltd.", exchange: "NSE" },
  { symbol: "GREENPANEL.NS", name: "Greenpanel Industries", exchange: "NSE" },
  { symbol: "CENTURYPLY.NS", name: "Century Plyboards", exchange: "NSE" },

  // --- HEALTHCARE & DIAGNOSTICS (MIDCAP) ---
  { symbol: "THYROCARE.NS", name: "Thyrocare Technologies", exchange: "NSE" },
  { symbol: "VIJAYA.NS", name: "Vijaya Diagnostic Centre", exchange: "NSE" },
  { symbol: "RAINBOW.NS", name: "Rainbow Childrens Medicare", exchange: "NSE" },
  { symbol: "MEDPLUS.NS", name: "Medplus Health Services", exchange: "NSE" },
  { symbol: "YATHARTH.NS", name: "Yatharth Hospital", exchange: "NSE" },
  { symbol: "JUPITERIN.NS", name: "Jupiter Life Line Hospitals", exchange: "NSE" },
  { symbol: "ERIS.NS", name: "Eris Lifesciences Ltd.", exchange: "NSE" },
  { symbol: "FDC.NS", name: "FDC Ltd.", exchange: "NSE" },
  { symbol: "CAPLIPOINT.NS", name: "Caplin Point Labs", exchange: "NSE" },
  { symbol: "GLENMARK.NS", name: "Glenmark Pharmaceuticals", exchange: "NSE" },
  { symbol: "STAR.NS", name: "Strides Pharma Science", exchange: "NSE" },
  { symbol: "WOCKPHARMA.NS", name: "Wockhardt Ltd.", exchange: "NSE" },
  { symbol: "IOLCP.NS", name: "IOL Chemicals & Pharma", exchange: "NSE" },
  { symbol: "MARKSANS.NS", name: "Marksans Pharma Ltd.", exchange: "NSE" },
  { symbol: "SUPRIYA.NS", name: "Supriya Lifescience Ltd.", exchange: "NSE" },
  { symbol: "HCG.NS", name: "HealthCare Global Ent", exchange: "NSE" },

  // --- TEXTILES & APPAREL ---
  { symbol: "PAGEIND.NS", name: "Page Industries Ltd.", exchange: "NSE" },
  { symbol: "KPRMILL.NS", name: "K.P.R. Mill Ltd.", exchange: "NSE" },
  { symbol: "TRIDENT.NS", name: "Trident Ltd.", exchange: "NSE" },
  { symbol: "RAYMOND.NS", name: "Raymond Ltd.", exchange: "NSE" },
  { symbol: "WELSPUNLIV.NS", name: "Welspun Living Ltd.", exchange: "NSE" },
  { symbol: "VTL.NS", name: "Vardhman Textiles Ltd.", exchange: "NSE" },
  { symbol: "LUXIND.NS", name: "Lux Industries Ltd.", exchange: "NSE" },
  { symbol: "RUPA.NS", name: "Rupa & Company Ltd.", exchange: "NSE" },
  { symbol: "GOKEX.NS", name: "Gokaldas Exports Ltd.", exchange: "NSE" },
  { symbol: "GARFIBRES.NS", name: "Garware Technical Fibres", exchange: "NSE" },
  { symbol: "SWANENERGY.NS", name: "Swan Energy Ltd.", exchange: "NSE" },
  { symbol: "ALOKINDS.NS", name: "Alok Industries Ltd.", exchange: "NSE" },

  // --- LOGISTICS & SHIPPING ---
  { symbol: "CONCOR.NS", name: "Container Corp of India", exchange: "NSE" },
  { symbol: "BLUEDART.NS", name: "Blue Dart Express Ltd.", exchange: "NSE" },
  { symbol: "TCIEXP.NS", name: "TCI Express Ltd.", exchange: "NSE" },
  { symbol: "TCI.NS", name: "Transport Corp of India", exchange: "NSE" },
  { symbol: "MAHLOG.NS", name: "Mahindra Logistics Ltd.", exchange: "NSE" },
  { symbol: "VRLLOG.NS", name: "VRL Logistics Ltd.", exchange: "NSE" },
  { symbol: "GATEWAY.NS", name: "Gateway Distriparks Ltd.", exchange: "NSE" },
  { symbol: "GPPL.NS", name: "Gujarat Pipavav Port", exchange: "NSE" },
  { symbol: "SCI.NS", name: "Shipping Corp of India", exchange: "NSE" },
  { symbol: "DREDGECORP.NS", name: "Dredging Corp of India", exchange: "NSE" },

  // --- MEDIA & ENTERTAINMENT ---
  { symbol: "SAREGAMA.NS", name: "Saregama India Ltd.", exchange: "NSE" },
  { symbol: "TVTODAY.NS", name: "TV Today Network Ltd.", exchange: "NSE" },
  { symbol: "DBCORP.NS", name: "D.B. Corp Ltd.", exchange: "NSE" },
  { symbol: "JAGRAN.NS", name: "Jagran Prakashan Ltd.", exchange: "NSE" },
  { symbol: "DISHTV.NS", name: "Dish TV India Ltd.", exchange: "NSE" },
  { symbol: "HATHWAY.NS", name: "Hathway Cable & Datacom", exchange: "NSE" },
  { symbol: "DEN.NS", name: "DEN Networks Ltd.", exchange: "NSE" },
  { symbol: "INOXGREEN.NS", name: "Inox Green Energy Svcs", exchange: "NSE" },

  // --- AUTO ANCILLARIES (ADDITIONAL) ---
  { symbol: "SKFINDIA.NS", name: "SKF India Ltd.", exchange: "NSE" },
  { symbol: "CIEINDIA.NS", name: "CIE Automotive India", exchange: "NSE" },
  { symbol: "SUPRAJIT.NS", name: "Suprajit Engineering", exchange: "NSE" },
  { symbol: "JAMNAAUTO.NS", name: "Jamna Auto Industries", exchange: "NSE" },
  { symbol: "GNA.NS", name: "GNA Axles Ltd.", exchange: "NSE" },
  { symbol: "RAMKRISNA.NS", name: "Ramkrishna Forgings", exchange: "NSE" },
  { symbol: "PRICOLLTD.NS", name: "Pricol Ltd.", exchange: "NSE" },
  { symbol: "MINDACORP.NS", name: "Minda Corporation Ltd.", exchange: "NSE" },
  { symbol: "SUBROS.NS", name: "Subros Ltd.", exchange: "NSE" },
  { symbol: "LUMAXIND.NS", name: "Lumax Industries Ltd.", exchange: "NSE" },
  { symbol: "FIEMIND.NS", name: "Fiem Industries Ltd.", exchange: "NSE" },

  // --- CONSTRUCTION & REALTY (ADDITIONAL) ---
  { symbol: "HGINFRA.NS", name: "H.G. Infra Engineering", exchange: "NSE" },
  { symbol: "JKIL.NS", name: "J.Kumar Infraprojects", exchange: "NSE" },
  { symbol: "ASHOKA.NS", name: "Ashoka Buildcon Ltd.", exchange: "NSE" },
  { symbol: "SUNTECK.NS", name: "Sunteck Realty Ltd.", exchange: "NSE" },
  { symbol: "MAHSEAMLES.NS", name: "Maharashtra Seamless", exchange: "NSE" },
  { symbol: "IBREALEST.NS", name: "Indiabulls Real Estate", exchange: "NSE" },
  { symbol: "PURVA.NS", name: "Puravankara Ltd.", exchange: "NSE" },
  { symbol: "KOLTEPATIL.NS", name: "Kolte-Patil Developers", exchange: "NSE" },
  { symbol: "ASHIANA.NS", name: "Ashiana Housing Ltd.", exchange: "NSE" },

  // --- RETAIL & JEWELRY ---
  { symbol: "KALYANKJIL.NS", name: "Kalyan Jewellers India", exchange: "NSE" },
  { symbol: "RAJESHEXPO.NS", name: "Rajesh Exports Ltd.", exchange: "NSE" },
  { symbol: "VAIBHAVGBL.NS", name: "Vaibhav Global Ltd.", exchange: "NSE" },
  { symbol: "THANGAMAYL.NS", name: "Thangamayil Jewellery", exchange: "NSE" },
  { symbol: "SENCO.NS", name: "Senco Gold Ltd.", exchange: "NSE" },
  { symbol: "SHOPPERS.NS", name: "Shoppers Stop Ltd.", exchange: "NSE" },
  { symbol: "V-MART.NS", name: "V-Mart Retail Ltd.", exchange: "NSE" },

  // --- AGRI, SUGAR & PAPER ---
  { symbol: "BALRAMCHIN.NS", name: "Balrampur Chini Mills", exchange: "NSE" },
  { symbol: "TRIVENI.NS", name: "Triveni Engineering", exchange: "NSE" },
  { symbol: "EIDPARRY.NS", name: "EID Parry (India) Ltd.", exchange: "NSE" },
  { symbol: "SHREEREN.NS", name: "Shree Renuka Sugars", exchange: "NSE" },
  { symbol: "DALMIASUG.NS", name: "Dalmia Bharat Sugar", exchange: "NSE" },
  { symbol: "JKPAPER.NS", name: "JK Paper Ltd.", exchange: "NSE" },
  { symbol: "WESTCOAST.NS", name: "West Coast Paper Mills", exchange: "NSE" },
  { symbol: "ANDHRAPAP.NS", name: "Andhra Paper Ltd.", exchange: "NSE" },
  { symbol: "KAVERI.NS", name: "Kaveri Seed Company", exchange: "NSE" },
  { symbol: "AVANTIFEED.NS", name: "Avanti Feeds Ltd.", exchange: "NSE" },
  { symbol: "VENKYS.NS", name: "Venky's (India) Ltd.", exchange: "NSE" },
  { symbol: "GODREJAGRO.NS", name: "Godrej Agrovet Ltd.", exchange: "NSE" },

  // --- MISC & SERVICES ---
  { symbol: "TEAMLEASE.NS", name: "TeamLease Services", exchange: "NSE" },
  { symbol: "QUESS.NS", name: "Quess Corp Ltd.", exchange: "NSE" },
  { symbol: "SIS.NS", name: "SIS Ltd.", exchange: "NSE" },
  { symbol: "MMTC.NS", name: "MMTC Ltd.", exchange: "NSE" },
  { symbol: "STCINDIA.NS", name: "State Trading Corp", exchange: "NSE" },
  { symbol: "MIDHANI.NS", name: "Mishra Dhatu Nigam", exchange: "NSE" },
  { symbol: "NESCO.NS", name: "Nesco Ltd.", exchange: "NSE" },
  { symbol: "DELTACORP.NS", name: "Delta Corp Ltd.", exchange: "NSE" },
]
*/

export const BSE_STOCKS: StockListItem[] = [
// --- SENSEX HEAVYWEIGHTS (BSE) ---
  { symbol: "RELIANCE.BO", name: "Reliance Industries Ltd", exchange: "BSE" },
  { symbol: "TCS.BO", name: "Tata Consultancy Services", exchange: "BSE" },
  { symbol: "HDFCBANK.BO", name: "HDFC Bank Ltd", exchange: "BSE" },
  { symbol: "ICICIBANK.BO", name: "ICICI Bank Ltd", exchange: "BSE" },
  { symbol: "BHARTIARTL.BO", name: "Bharti Airtel Ltd", exchange: "BSE" },
  { symbol: "SBIN.BO", name: "State Bank of India", exchange: "BSE" },
  { symbol: "INFY.BO", name: "Infosys Ltd", exchange: "BSE" },
  { symbol: "HINDUNILVR.BO", name: "Hindustan Unilever Ltd", exchange: "BSE" },
  { symbol: "ITC.BO", name: "ITC Ltd", exchange: "BSE" },
  { symbol: "LT.BO", name: "Larsen & Toubro Ltd", exchange: "BSE" },

  // --- BANKING & FINANCE (BSE) ---
  { symbol: "BAJFINANCE.BO", name: "Bajaj Finance Ltd", exchange: "BSE" },
  { symbol: "AXISBANK.BO", name: "Axis Bank Ltd", exchange: "BSE" },
  { symbol: "KOTAKBANK.BO", name: "Kotak Mahindra Bank", exchange: "BSE" },
  { symbol: "INDUSINDBK.BO", name: "IndusInd Bank Ltd", exchange: "BSE" },
  { symbol: "BAJAJFINSV.BO", name: "Bajaj Finserv Ltd", exchange: "BSE" },
  { symbol: "BANKBARODA.BO", name: "Bank of Baroda", exchange: "BSE" },
  { symbol: "PNB.BO", name: "Punjab National Bank", exchange: "BSE" },
  { symbol: "JIOFIN.BO", name: "Jio Financial Services", exchange: "BSE" },
  { symbol: "CHOLAFIN.BO", name: "Cholamandalam Inv & Fin", exchange: "BSE" },
  { symbol: "MUTHOOTFIN.BO", name: "Muthoot Finance", exchange: "BSE" },
  { symbol: "SBICARD.BO", name: "SBI Cards & Payments", exchange: "BSE" },
  { symbol: "IDBI.BO", name: "IDBI Bank Ltd", exchange: "BSE" },
  { symbol: "YESBANK.BO", name: "Yes Bank Ltd", exchange: "BSE" },
  { symbol: "IDFCFIRSTB.BO", name: "IDFC First Bank", exchange: "BSE" },
  { symbol: "AUBANK.BO", name: "AU Small Finance Bank", exchange: "BSE" },
  { symbol: "CANBK.BO", name: "Canara Bank", exchange: "BSE" },
  { symbol: "UNIONBANK.BO", name: "Union Bank of India", exchange: "BSE" },
  { symbol: "ABCAPITAL.BO", name: "Aditya Birla Capital", exchange: "BSE" },
  { symbol: "L&TFH.BO", name: "L&T Finance Holdings", exchange: "BSE" },
  { symbol: "POONAWALLA.BO", name: "Poonawalla Fincorp", exchange: "BSE" },
  { symbol: "M&MFIN.BO", name: "Mahindra & Mahindra Fin", exchange: "BSE" },

  // --- IT & TECH (BSE) ---
  { symbol: "HCLTECH.BO", name: "HCL Technologies", exchange: "BSE" },
  { symbol: "WIPRO.BO", name: "Wipro Ltd", exchange: "BSE" },
  { symbol: "TECHM.BO", name: "Tech Mahindra Ltd", exchange: "BSE" },
  { symbol: "LTIM.BO", name: "LTIMindtree Ltd", exchange: "BSE" },
  { symbol: "OFSS.BO", name: "Oracle Fin Services", exchange: "BSE" },
  { symbol: "PERSISTENT.BO", name: "Persistent Systems", exchange: "BSE" },
  { symbol: "MPHASIS.BO", name: "Mphasis Ltd", exchange: "BSE" },
  { symbol: "KPITTECH.BO", name: "KPIT Technologies", exchange: "BSE" },
  { symbol: "TATAELXSI.BO", name: "Tata Elxsi Ltd", exchange: "BSE" },
  { symbol: "COFORGE.BO", name: "Coforge Ltd", exchange: "BSE" },
  { symbol: "ZOMATO.BO", name: "Zomato Ltd", exchange: "BSE" },
  { symbol: "PAYTM.BO", name: "One 97 Communications", exchange: "BSE" },
  { symbol: "NAUKRI.BO", name: "Info Edge (India) Ltd", exchange: "BSE" },
  { symbol: "PBFINTECH.BO", name: "PB Fintech (PolicyBazaar)", exchange: "BSE" },
  { symbol: "NYKAA.BO", name: "FSN E-Commerce (Nykaa)", exchange: "BSE" },

  // --- AUTOMOBILE (BSE) ---
  { symbol: "TATAMOTORS.BO", name: "Tata Motors Ltd", exchange: "BSE" },
  { symbol: "MARUTI.BO", name: "Maruti Suzuki India", exchange: "BSE" },
  { symbol: "M&M.BO", name: "Mahindra & Mahindra", exchange: "BSE" },
  { symbol: "BAJAJ-AUTO.BO", name: "Bajaj Auto Ltd", exchange: "BSE" },
  { symbol: "EICHERMOT.BO", name: "Eicher Motors Ltd", exchange: "BSE" },
  { symbol: "HEROMOTOCO.BO", name: "Hero MotoCorp Ltd", exchange: "BSE" },
  { symbol: "TVSMOTOR.BO", name: "TVS Motor Company", exchange: "BSE" },
  { symbol: "ASHOKLEY.BO", name: "Ashok Leyland Ltd", exchange: "BSE" },
  { symbol: "BHARATFORG.BO", name: "Bharat Forge Ltd", exchange: "BSE" },
  { symbol: "MRF.BO", name: "MRF Ltd", exchange: "BSE" },
  { symbol: "BOSCHLTD.BO", name: "Bosch Ltd", exchange: "BSE" },
  { symbol: "BALKRISIND.BO", name: "Balkrishna Industries", exchange: "BSE" },
  { symbol: "MOTHERSON.BO", name: "Samvardhana Motherson", exchange: "BSE" },
  { symbol: "UNO-MINDA.BO", name: "Uno Minda Ltd", exchange: "BSE" },
  { symbol: "TIINDIA.BO", name: "Tube Investments", exchange: "BSE" },

  // --- CONSUMER & FMCG (BSE) ---
  { symbol: "TITAN.BO", name: "Titan Company Ltd", exchange: "BSE" },
  { symbol: "ASIANPAINT.BO", name: "Asian Paints Ltd", exchange: "BSE" },
  { symbol: "NESTLEIND.BO", name: "Nestle India Ltd", exchange: "BSE" },
  { symbol: "BRITANNIA.BO", name: "Britannia Industries", exchange: "BSE" },
  { symbol: "GODREJCP.BO", name: "Godrej Consumer Products", exchange: "BSE" },
  { symbol: "TATACONSUM.BO", name: "Tata Consumer Products", exchange: "BSE" },
  { symbol: "VBL.BO", name: "Varun Beverages Ltd", exchange: "BSE" },
  { symbol: "DABUR.BO", name: "Dabur India Ltd", exchange: "BSE" },
  { symbol: "MARICO.BO", name: "Marico Ltd", exchange: "BSE" },
  { symbol: "PIDILITE.BO", name: "Pidilite Industries", exchange: "BSE" },
  { symbol: "BERGEPAINT.BO", name: "Berger Paints India", exchange: "BSE" },
  { symbol: "HAVELLS.BO", name: "Havells India Ltd", exchange: "BSE" },
  { symbol: "COLPAL.BO", name: "Colgate-Palmolive", exchange: "BSE" },
  { symbol: "PGHH.BO", name: "P&G Hygiene & Health", exchange: "BSE" },
  { symbol: "TRENT.BO", name: "Trent Ltd", exchange: "BSE" },
  { symbol: "ABFRL.BO", name: "Aditya Birla Fashion", exchange: "BSE" },
  { symbol: "BATAINDIA.BO", name: "Bata India Ltd", exchange: "BSE" },
  { symbol: "PAGEIND.BO", name: "Page Industries Ltd", exchange: "BSE" },

  // --- PHARMA & HEALTHCARE (BSE) ---
  { symbol: "SUNPHARMA.BO", name: "Sun Pharma Inds", exchange: "BSE" },
  { symbol: "DRREDDY.BO", name: "Dr. Reddy's Labs", exchange: "BSE" },
  { symbol: "CIPLA.BO", name: "Cipla Ltd", exchange: "BSE" },
  { symbol: "DIVISLAB.BO", name: "Divi's Laboratories", exchange: "BSE" },
  { symbol: "APOLLOHOSP.BO", name: "Apollo Hospitals", exchange: "BSE" },
  { symbol: "LUPIN.BO", name: "Lupin Ltd", exchange: "BSE" },
  { symbol: "AUROPHARMA.BO", name: "Aurobindo Pharma", exchange: "BSE" },
  { symbol: "MANKIND.BO", name: "Mankind Pharma", exchange: "BSE" },
  { symbol: "MAXHEALTH.BO", name: "Max Healthcare Inst", exchange: "BSE" },
  { symbol: "TORNTPHARM.BO", name: "Torrent Pharmaceuticals", exchange: "BSE" },
  { symbol: "ZYDUSLIFE.BO", name: "Zydus Lifesciences", exchange: "BSE" },
  { symbol: "ALKEM.BO", name: "Alkem Laboratories", exchange: "BSE" },
  { symbol: "ABBOTINDIA.BO", name: "Abbott India Ltd", exchange: "BSE" },
  { symbol: "BIOCON.BO", name: "Biocon Ltd", exchange: "BSE" },
  { symbol: "LALPATHLAB.BO", name: "Dr. Lal PathLabs", exchange: "BSE" },

  // --- ENERGY, POWER & OIL (BSE) ---
  { symbol: "NTPC.BO", name: "NTPC Ltd", exchange: "BSE" },
  { symbol: "POWERGRID.BO", name: "Power Grid Corp", exchange: "BSE" },
  { symbol: "ONGC.BO", name: "ONGC Ltd", exchange: "BSE" },
  { symbol: "COALINDIA.BO", name: "Coal India Ltd", exchange: "BSE" },
  { symbol: "ADANIGREEN.BO", name: "Adani Green Energy", exchange: "BSE" },
  { symbol: "ADANIPOWER.BO", name: "Adani Power Ltd", exchange: "BSE" },
  { symbol: "TATAPOWER.BO", name: "Tata Power Co Ltd", exchange: "BSE" },
  { symbol: "BPCL.BO", name: "Bharat Petroleum", exchange: "BSE" },
  { symbol: "IOC.BO", name: "Indian Oil Corp", exchange: "BSE" },
  { symbol: "GAIL.BO", name: "GAIL (India) Ltd", exchange: "BSE" },
  { symbol: "JSWENERGY.BO", name: "JSW Energy Ltd", exchange: "BSE" },
  { symbol: "NHPC.BO", name: "NHPC Ltd", exchange: "BSE" },
  { symbol: "SUZLON.BO", name: "Suzlon Energy Ltd", exchange: "BSE" },
  { symbol: "IREDA.BO", name: "IREDA Ltd", exchange: "BSE" },
  { symbol: "TORNTPOWER.BO", name: "Torrent Power Ltd", exchange: "BSE" },

  // --- INFRA, CEMENT & REALTY (BSE) ---
  { symbol: "ULTRACEMCO.BO", name: "UltraTech Cement", exchange: "BSE" },
  { symbol: "GRASIM.BO", name: "Grasim Industries", exchange: "BSE" },
  { symbol: "ADANIENT.BO", name: "Adani Enterprises", exchange: "BSE" },
  { symbol: "AMBUJACEM.BO", name: "Ambuja Cements", exchange: "BSE" },
  { symbol: "SHREECEM.BO", name: "Shree Cement Ltd", exchange: "BSE" },
  { symbol: "DLF.BO", name: "DLF Ltd", exchange: "BSE" },
  { symbol: "MACROTECH.BO", name: "Macrotech Developers", exchange: "BSE" },
  { symbol: "GODREJPROP.BO", name: "Godrej Properties", exchange: "BSE" },
  { symbol: "OBEROIRLTY.BO", name: "Oberoi Realty Ltd", exchange: "BSE" },
  { symbol: "ACC.BO", name: "ACC Ltd", exchange: "BSE" },
  { symbol: "GMRINFRA.BO", name: "GMR Airports Infra", exchange: "BSE" },
  { symbol: "HAL.BO", name: "Hindustan Aeronautics", exchange: "BSE" },
  { symbol: "BEL.BO", name: "Bharat Electronics", exchange: "BSE" },
  { symbol: "MAZDOCK.BO", name: "Mazagon Dock", exchange: "BSE" },
  { symbol: "COCHINSHIP.BO", name: "Cochin Shipyard", exchange: "BSE" },
  { symbol: "POLYCAB.BO", name: "Polycab India Ltd", exchange: "BSE" },

  // --- METALS (BSE) ---
  { symbol: "TATASTEEL.BO", name: "Tata Steel Ltd", exchange: "BSE" },
  { symbol: "JSWSTEEL.BO", name: "JSW Steel Ltd", exchange: "BSE" },
  { symbol: "HINDALCO.BO", name: "Hindalco Industries", exchange: "BSE" },
  { symbol: "VEDL.BO", name: "Vedanta Ltd", exchange: "BSE" },
  { symbol: "JINDALSTEL.BO", name: "Jindal Steel & Power", exchange: "BSE" },
  { symbol: "SAIL.BO", name: "Steel Authority", exchange: "BSE" },
  { symbol: "NMDC.BO", name: "NMDC Ltd", exchange: "BSE" },
  { symbol: "HINDZINC.BO", name: "Hindustan Zinc", exchange: "BSE" },

  // --- CHEMICALS & FERTILIZERS (HIGH GROWTH SECTOR) ---
  { symbol: "UPL.BO", name: "UPL Ltd", exchange: "BSE" },
  { symbol: "SRF.BO", name: "SRF Ltd", exchange: "BSE" },
  { symbol: "AARTIIND.BO", name: "Aarti Industries", exchange: "BSE" },
  { symbol: "ATUL.BO", name: "Atul Ltd", exchange: "BSE" },
  { symbol: "DEEPAKNTR.BO", name: "Deepak Nitrite", exchange: "BSE" },
  { symbol: "TATACHEM.BO", name: "Tata Chemicals", exchange: "BSE" },
  { symbol: "PIIND.BO", name: "PI Industries", exchange: "BSE" },
  { symbol: "NAVINFLUOR.BO", name: "Navin Fluorine Intl", exchange: "BSE" },
  { symbol: "VINATIORGA.BO", name: "Vinati Organics", exchange: "BSE" },
  { symbol: "COROMANDEL.BO", name: "Coromandel Intl", exchange: "BSE" },
  { symbol: "CHAMBLFERT.BO", name: "Chambal Fertilisers", exchange: "BSE" },
  { symbol: "GNFC.BO", name: "Gujarat Narmada Valley", exchange: "BSE" },
  { symbol: "GSFC.BO", name: "Gujarat State Fertilizers", exchange: "BSE" },
  { symbol: "RCF.BO", name: "Rashtriya Chem & Fert", exchange: "BSE" },
  { symbol: "FACT.BO", name: "Fert & Chem Travancore", exchange: "BSE" },
  { symbol: "LINDEINDIA.BO", name: "Linde India Ltd", exchange: "BSE" },
  { symbol: "FLUOROCHEM.BO", name: "Gujarat Fluorochemicals", exchange: "BSE" },
  { symbol: "CLEAN.BO", name: "Clean Science & Tech", exchange: "BSE" },
  { symbol: "FINEORG.BO", name: "Fine Organic Inds", exchange: "BSE" },
  { symbol: "ALKYLAMINE.BO", name: "Alkyl Amines Chem", exchange: "BSE" },
  { symbol: "BALAMINES.BO", name: "Balaji Amines", exchange: "BSE" },
  { symbol: "SUMICHEM.BO", name: "Sumitomo Chemical", exchange: "BSE" },
  { symbol: "ROSSARI.BO", name: "Rossari Biotech", exchange: "BSE" },
  { symbol: "NOCIL.BO", name: "NOCIL Ltd", exchange: "BSE" },
  { symbol: "SUDARSCHEM.BO", name: "Sudarshan Chemical", exchange: "BSE" },
  { symbol: "LAXMISACH.BO", name: "Laxmi Organic Inds", exchange: "BSE" },
  { symbol: "ANUPAM.BO", name: "Anupam Rasayan", exchange: "BSE" },
  { symbol: "PRIVISCL.BO", name: "Privi Speciality Chem", exchange: "BSE" },
  { symbol: "NEOGEN.BO", name: "Neogen Chemicals", exchange: "BSE" },
  { symbol: "JUBLINGREA.BO", name: "Jubilant Ingrevia", exchange: "BSE" },

  // --- CAPITAL GOODS & ENGINEERING ---
  { symbol: "SIEMENS.BO", name: "Siemens Ltd", exchange: "BSE" },
  { symbol: "ABB.BO", name: "ABB India Ltd", exchange: "BSE" },
  { symbol: "CUMMINSIND.BO", name: "Cummins India", exchange: "BSE" },
  { symbol: "THERMAX.BO", name: "Thermax Ltd", exchange: "BSE" },
  { symbol: "BHEL.BO", name: "Bharat Heavy Electricals", exchange: "BSE" },
  { symbol: "CGPOWER.BO", name: "CG Power & Ind Sol", exchange: "BSE" },
  { symbol: "TRITURBINE.BO", name: "Triveni Turbine", exchange: "BSE" },
  { symbol: "TIMKEN.BO", name: "Timken India", exchange: "BSE" },
  { symbol: "SCHAEFFLER.BO", name: "Schaeffler India", exchange: "BSE" },
  { symbol: "SKFINDIA.BO", name: "SKF India Ltd", exchange: "BSE" },
  { symbol: "AIAENG.BO", name: "AIA Engineering", exchange: "BSE" },
  { symbol: "ELGIEQUIP.BO", name: "Elgi Equipments", exchange: "BSE" },
  { symbol: "KEC.BO", name: "KEC International", exchange: "BSE" },
  { symbol: "KALPATPOWR.BO", name: "Kalpataru Projects", exchange: "BSE" },
  { symbol: "TECHNOE.BO", name: "Techno Electric", exchange: "BSE" },
  { symbol: "BEML.BO", name: "BEML Ltd", exchange: "BSE" },
  { symbol: "ENGINERSIN.BO", name: "Engineers India", exchange: "BSE" },
  { symbol: "ISGEC.BO", name: "Isgec Heavy Eng", exchange: "BSE" },
  { symbol: "PRAJIND.BO", name: "Praj Industries", exchange: "BSE" },
  { symbol: "RITES.BO", name: "RITES Ltd", exchange: "BSE" },

  // --- FINANCIAL SERVICES (INSURANCE, AMC, BROKING) ---
  { symbol: "HDFCLIFE.BO", name: "HDFC Life Insurance", exchange: "BSE" },
  { symbol: "SBILIFE.BO", name: "SBI Life Insurance", exchange: "BSE" },
  { symbol: "ICICIPRULI.BO", name: "ICICI Pru Life", exchange: "BSE" },
  { symbol: "ICICIGI.BO", name: "ICICI Lombard Gen Ins", exchange: "BSE" },
  { symbol: "STARHEALTH.BO", name: "Star Health & Allied", exchange: "BSE" },
  { symbol: "GICRE.BO", name: "General Insurance Corp", exchange: "BSE" },
  { symbol: "NIACL.BO", name: "New India Assurance", exchange: "BSE" },
  { symbol: "UTIAMC.BO", name: "UTI Asset Mgmt", exchange: "BSE" },
  { symbol: "NAM-INDIA.BO", name: "Nippon Life India AMC", exchange: "BSE" },
  { symbol: "HDFCAMC.BO", name: "HDFC Asset Mgmt", exchange: "BSE" },
  { symbol: "CAMS.BO", name: "Computer Age Mgmt", exchange: "BSE" },
  { symbol: "KFINTECH.BO", name: "KFin Technologies", exchange: "BSE" },
  { symbol: "CRISIL.BO", name: "CRISIL Ltd", exchange: "BSE" },
  { symbol: "ICRA.BO", name: "ICRA Ltd", exchange: "BSE" },
  { symbol: "ANGELONE.BO", name: "Angel One Ltd", exchange: "BSE" },
  { symbol: "CDSL.BO", name: "Central Depository Svc", exchange: "BSE" },
  { symbol: "BSE.BO", name: "BSE Ltd", exchange: "BSE" },
  { symbol: "MCX.BO", name: "Multi Commodity Exch", exchange: "BSE" },
  { symbol: "CREDITACC.BO", name: "CreditAccess Grameen", exchange: "BSE" },
  { symbol: "FIVESTAR.BO", name: "Five-Star Business Fin", exchange: "BSE" },
  { symbol: "AAVAS.BO", name: "Aavas Financiers", exchange: "BSE" },
  { symbol: "HUDCO.BO", name: "HUDCO", exchange: "BSE" },
  { symbol: "IRFC.BO", name: "Indian Railway Fin", exchange: "BSE" },
  { symbol: "PFC.BO", name: "Power Finance Corp", exchange: "BSE" },
  { symbol: "RECLTD.BO", name: "REC Ltd", exchange: "BSE" },
  { symbol: "SHRIRAMFIN.BO", name: "Shriram Finance", exchange: "BSE" },
  { symbol: "SUNDARMFIN.BO", name: "Sundaram Finance", exchange: "BSE" },
  { symbol: "MAHABANK.BO", name: "Bank of Maharashtra", exchange: "BSE" },
  { symbol: "IOB.BO", name: "Indian Overseas Bank", exchange: "BSE" },
  { symbol: "UCOBANK.BO", name: "UCO Bank", exchange: "BSE" },
  { symbol: "CENTRALBK.BO", name: "Central Bank of India", exchange: "BSE" },
  { symbol: "INDIANB.BO", name: "Indian Bank", exchange: "BSE" },
  { symbol: "J&KBANK.BO", name: "Jammu & Kashmir Bank", exchange: "BSE" },
  { symbol: "KARURVYSYA.BO", name: "Karur Vysya Bank", exchange: "BSE" },
  { symbol: "FEDERALBNK.BO", name: "Federal Bank", exchange: "BSE" },
  { symbol: "CITYUNIONB.BO", name: "City Union Bank", exchange: "BSE" },
  { symbol: "EQUITASBNK.BO", name: "Equitas Small Fin Bank", exchange: "BSE" },
  { symbol: "UJJIVANSFB.BO", name: "Ujjivan Small Fin Bank", exchange: "BSE" },

  // --- CONSUMER DURABLES, CABLES & PLASTICS ---
  { symbol: "HAVELLS.BO", name: "Havells India", exchange: "BSE" },
  { symbol: "POLYCAB.BO", name: "Polycab India", exchange: "BSE" },
  { symbol: "KEI.BO", name: "KEI Industries", exchange: "BSE" },
  { symbol: "RRKABEL.BO", name: "RR Kabel Ltd", exchange: "BSE" },
  { symbol: "FINCABLES.BO", name: "Finolex Cables", exchange: "BSE" },
  { symbol: "VGUARD.BO", name: "V-Guard Industries", exchange: "BSE" },
  { symbol: "CROMPTON.BO", name: "Crompton Greaves Cons", exchange: "BSE" },
  { symbol: "VOLTAS.BO", name: "Voltas Ltd", exchange: "BSE" },
  { symbol: "BLUESTARCO.BO", name: "Blue Star Ltd", exchange: "BSE" },
  { symbol: "WHIRLPOOL.BO", name: "Whirlpool of India", exchange: "BSE" },
  { symbol: "SYMPHONY.BO", name: "Symphony Ltd", exchange: "BSE" },
  { symbol: "DIXON.BO", name: "Dixon Technologies", exchange: "BSE" },
  { symbol: "AMBER.BO", name: "Amber Enterprises", exchange: "BSE" },
  { symbol: "TTKPRESTIGE.BO", name: "TTK Prestige", exchange: "BSE" },
  { symbol: "VIPIND.BO", name: "VIP Industries", exchange: "BSE" },
  { symbol: "SAFARI.BO", name: "Safari Industries", exchange: "BSE" },
  { symbol: "SUPREMEIND.BO", name: "Supreme Industries", exchange: "BSE" },
  { symbol: "ASTRAL.BO", name: "Astral Ltd", exchange: "BSE" },
  { symbol: "FINPIPE.BO", name: "Finolex Industries", exchange: "BSE" },
  { symbol: "PRINCEPIPE.BO", name: "Prince Pipes", exchange: "BSE" },
  { symbol: "CERA.BO", name: "Cera Sanitaryware", exchange: "BSE" },
  { symbol: "KAJARIACER.BO", name: "Kajaria Ceramics", exchange: "BSE" },
  { symbol: "SOMANYCERA.BO", name: "Somany Ceramics", exchange: "BSE" },
  { symbol: "CENTURYPLY.BO", name: "Century Plyboards", exchange: "BSE" },
  { symbol: "GREENPANEL.BO", name: "Greenpanel Inds", exchange: "BSE" },

  // --- IT MIDCAP & SERVICES ---
  { symbol: "LTTS.BO", name: "L&T Technology Svcs", exchange: "BSE" },
  { symbol: "CYIENT.BO", name: "Cyient Ltd", exchange: "BSE" },
  { symbol: "ZENSARTECH.BO", name: "Zensar Technologies", exchange: "BSE" },
  { symbol: "BSOFT.BO", name: "Birlasoft Ltd", exchange: "BSE" },
  { symbol: "SONATSOFTW.BO", name: "Sonata Software", exchange: "BSE" },
  { symbol: "INTELLECT.BO", name: "Intellect Design", exchange: "BSE" },
  { symbol: "REDINGTON.BO", name: "Redington Ltd", exchange: "BSE" },
  { symbol: "HAPPSTMNDS.BO", name: "Happiest Minds", exchange: "BSE" },
  { symbol: "MASTEK.BO", name: "Mastek Ltd", exchange: "BSE" },
  { symbol: "TANLA.BO", name: "Tanla Platforms", exchange: "BSE" },
  { symbol: "ROUTE.BO", name: "Route Mobile", exchange: "BSE" },
  { symbol: "AFFLE.BO", name: "Affle (India) Ltd", exchange: "BSE" },
  { symbol: "MAPMYINDIA.BO", name: "CE Info Systems", exchange: "BSE" },
  { symbol: "RATEGAIN.BO", name: "RateGain Travel Tech", exchange: "BSE" },
  { symbol: "NAZARA.BO", name: "Nazara Technologies", exchange: "BSE" },
  { symbol: "DELHIVERY.BO", name: "Delhivery Ltd", exchange: "BSE" },
  { symbol: "FSL.BO", name: "Firstsource Solutions", exchange: "BSE" },
  { symbol: "ECLERX.BO", name: "eClerx Services", exchange: "BSE" },
  { symbol: "NETWEB.BO", name: "Netweb Technologies", exchange: "BSE" },

  // --- PHARMA & HEALTHCARE (ADDITIONAL) ---
  { symbol: "SYNGENE.BO", name: "Syngene International", exchange: "BSE" },
  { symbol: "GLENMARK.BO", name: "Glenmark Pharma", exchange: "BSE" },
  { symbol: "JBCHEPHARM.BO", name: "J.B. Chemicals", exchange: "BSE" },
  { symbol: "NATCOPHARM.BO", name: "Natco Pharma", exchange: "BSE" },
  { symbol: "PFIZER.BO", name: "Pfizer Ltd", exchange: "BSE" },
  { symbol: "SANOFI.BO", name: "Sanofi India", exchange: "BSE" },
  { symbol: "GLAXO.BO", name: "GlaxoSmithKline Pharma", exchange: "BSE" },
  { symbol: "STAR.BO", name: "Strides Pharma Science", exchange: "BSE" },
  { symbol: "GRANULES.BO", name: "Granules India", exchange: "BSE" },
  { symbol: "LAURUSLAB.BO", name: "Laurus Labs", exchange: "BSE" },
  { symbol: "ALEMBICLTD.BO", name: "Alembic Pharma", exchange: "BSE" },
  { symbol: "ERIS.BO", name: "Eris Lifesciences", exchange: "BSE" },
  { symbol: "CAPLIPOINT.BO", name: "Caplin Point Labs", exchange: "BSE" },
  { symbol: "FDC.BO", name: "FDC Ltd", exchange: "BSE" },
  { symbol: "MARKSANS.BO", name: "Marksans Pharma", exchange: "BSE" },
  { symbol: "METROPOLIS.BO", name: "Metropolis Healthcare", exchange: "BSE" },
  { symbol: "VIJAYA.BO", name: "Vijaya Diagnostic", exchange: "BSE" },
  { symbol: "RAINBOW.BO", name: "Rainbow Childrens", exchange: "BSE" },
  { symbol: "MEDPLUS.BO", name: "Medplus Health Svcs", exchange: "BSE" },
  { symbol: "FORTIS.BO", name: "Fortis Healthcare", exchange: "BSE" },
  { symbol: "NH.BO", name: "Narayana Hrudayalaya", exchange: "BSE" },
  { symbol: "ASTERDM.BO", name: "Aster DM Healthcare", exchange: "BSE" },
  { symbol: "KIMS.BO", name: "Krishna Inst Med Sci", exchange: "BSE" },

  // --- AUTO ANCILLARIES (ADDITIONAL) ---
  { symbol: "APOLLOTYRE.BO", name: "Apollo Tyres", exchange: "BSE" },
  { symbol: "JKTYRE.BO", name: "JK Tyre & Ind", exchange: "BSE" },
  { symbol: "CEATLTD.BO", name: "CEAT Ltd", exchange: "BSE" },
  { symbol: "EXIDEIND.BO", name: "Exide Industries", exchange: "BSE" },
  { symbol: "AMARAJABAT.BO", name: "Amara Raja Energy", exchange: "BSE" },
  { symbol: "ENDURANCE.BO", name: "Endurance Technologies", exchange: "BSE" },
  { symbol: "CRAFTSMAN.BO", name: "Craftsman Automation", exchange: "BSE" },
  { symbol: "SONACOMS.BO", name: "Sona BLW Precision", exchange: "BSE" },
  { symbol: "VARROC.BO", name: "Varroc Engineering", exchange: "BSE" },
  { symbol: "SUPRAJIT.BO", name: "Suprajit Engineering", exchange: "BSE" },
  { symbol: "JAMNAAUTO.BO", name: "Jamna Auto Inds", exchange: "BSE" },
  { symbol: "GABRIEL.BO", name: "Gabriel India", exchange: "BSE" },
  { symbol: "MINDACORP.BO", name: "Minda Corporation", exchange: "BSE" },
  { symbol: "CIEINDIA.BO", name: "CIE Automotive India", exchange: "BSE" },
  { symbol: "MAHSEAMLES.BO", name: "Maharashtra Seamless", exchange: "BSE" },
  { symbol: "RATNAMANI.BO", name: "Ratnamani Metals", exchange: "BSE" },
  { symbol: "APLAPOLLO.BO", name: "APL Apollo Tubes", exchange: "BSE" },
  { symbol: "WELCORP.BO", name: "Welspun Corp", exchange: "BSE" },

  // --- TEXTILES & APPAREL ---
  { symbol: "KPRMILL.BO", name: "K.P.R. Mill Ltd", exchange: "BSE" },
  { symbol: "TRIDENT.BO", name: "Trident Ltd", exchange: "BSE" },
  { symbol: "WELSPUNLIV.BO", name: "Welspun Living", exchange: "BSE" },
  { symbol: "RAYMOND.BO", name: "Raymond Ltd", exchange: "BSE" },
  { symbol: "VTL.BO", name: "Vardhman Textiles", exchange: "BSE" },
  { symbol: "LUXIND.BO", name: "Lux Industries", exchange: "BSE" },
  { symbol: "RUPA.BO", name: "Rupa & Company", exchange: "BSE" },
  { symbol: "GOKEX.BO", name: "Gokaldas Exports", exchange: "BSE" },
  { symbol: "GARFIBRES.BO", name: "Garware Tech Fibres", exchange: "BSE" },
  { symbol: "SWANENERGY.BO", name: "Swan Energy Ltd", exchange: "BSE" },
  { symbol: "ALOKINDS.BO", name: "Alok Industries", exchange: "BSE" },
  { symbol: "KALYANKJIL.BO", name: "Kalyan Jewellers", exchange: "BSE" },
  { symbol: "RAJESHEXPO.BO", name: "Rajesh Exports", exchange: "BSE" },
  { symbol: "VAIBHAVGBL.BO", name: "Vaibhav Global", exchange: "BSE" },
  { symbol: "SENCO.BO", name: "Senco Gold Ltd", exchange: "BSE" },
  { symbol: "SHOPPERS.BO", name: "Shoppers Stop", exchange: "BSE" },

  // --- LOGISTICS, SHIPPING & MISC SERVICES ---
  { symbol: "CONCOR.BO", name: "Container Corp", exchange: "BSE" },
  { symbol: "BLUEDART.BO", name: "Blue Dart Express", exchange: "BSE" },
  { symbol: "TCIEXP.BO", name: "TCI Express", exchange: "BSE" },
  { symbol: "TCI.BO", name: "Transport Corp", exchange: "BSE" },
  { symbol: "MAHLOG.BO", name: "Mahindra Logistics", exchange: "BSE" },
  { symbol: "VRLLOG.BO", name: "VRL Logistics", exchange: "BSE" },
  { symbol: "GATEWAY.BO", name: "Gateway Distriparks", exchange: "BSE" },
  { symbol: "SCI.BO", name: "Shipping Corp", exchange: "BSE" },
  { symbol: "GPPL.BO", name: "Gujarat Pipavav Port", exchange: "BSE" },
  { symbol: "DREDGECORP.BO", name: "Dredging Corp", exchange: "BSE" },
  { symbol: "TEAMLEASE.BO", name: "TeamLease Services", exchange: "BSE" },
  { symbol: "QUESS.BO", name: "Quess Corp", exchange: "BSE" },
  { symbol: "SIS.BO", name: "SIS Ltd", exchange: "BSE" },
  { symbol: "MMTC.BO", name: "MMTC Ltd", exchange: "BSE" },
  { symbol: "DELTACORP.BO", name: "Delta Corp", exchange: "BSE" },

  // --- INFRASTRUCTURE, REALTY & CONSTRUCTION ---
  { symbol: "PHOENIXLTD.BO", name: "Phoenix Mills", exchange: "BSE" },
  { symbol: "PRESTIGE.BO", name: "Prestige Estates", exchange: "BSE" },
  { symbol: "BRIGADE.BO", name: "Brigade Enterprises", exchange: "BSE" },
  { symbol: "SOBHA.BO", name: "Sobha Ltd", exchange: "BSE" },
  { symbol: "RVNL.BO", name: "Rail Vikas Nigam", exchange: "BSE" },
  { symbol: "IRCON.BO", name: "Ircon International", exchange: "BSE" },
  { symbol: "NBCC.BO", name: "NBCC (India) Ltd", exchange: "BSE" },
  { symbol: "RITES.BO", name: "RITES Ltd", exchange: "BSE" },
  { symbol: "KNRCON.BO", name: "KNR Constructions", exchange: "BSE" },
  { symbol: "PNCINFRA.BO", name: "PNC Infratech", exchange: "BSE" },
  { symbol: "IRB.BO", name: "IRB Infrastructure", exchange: "BSE" },
  { symbol: "HGINFRA.BO", name: "HG Infra Engineering", exchange: "BSE" },
  { symbol: "JKIL.BO", name: "J.Kumar Infraprojects", exchange: "BSE" },
  { symbol: "ASHOKA.BO", name: "Ashoka Buildcon", exchange: "BSE" },
  { symbol: "SUNTECK.BO", name: "Sunteck Realty", exchange: "BSE" },
  { symbol: "IBREALEST.BO", name: "Indiabulls Real Est", exchange: "BSE" },
  { symbol: "PURVA.BO", name: "Puravankara Ltd", exchange: "BSE" },

  // --- OIL, GAS & ENERGY (EXPANDED) ---
  { symbol: "PETRONET.BO", name: "Petronet LNG", exchange: "BSE" },
  { symbol: "IGL.BO", name: "Indraprastha Gas", exchange: "BSE" },
  { symbol: "MGL.BO", name: "Mahanagar Gas", exchange: "BSE" },
  { symbol: "GUJGASLTD.BO", name: "Gujarat Gas", exchange: "BSE" },
  { symbol: "ATGL.BO", name: "Adani Total Gas", exchange: "BSE" },
  { symbol: "OIL.BO", name: "Oil India Ltd", exchange: "BSE" },
  { symbol: "HPCL.BO", name: "Hindustan Petroleum", exchange: "BSE" },
  { symbol: "MRPL.BO", name: "Mangalore Refinery", exchange: "BSE" },
  { symbol: "CHENNPETRO.BO", name: "Chennai Petroleum", exchange: "BSE" },
  { symbol: "SJVN.BO", name: "SJVN Ltd", exchange: "BSE" },
  { symbol: "NLCINDIA.BO", name: "NLC India", exchange: "BSE" },
  { symbol: "CESC.BO", name: "CESC Ltd", exchange: "BSE" },
  { symbol: "IEX.BO", name: "Indian Energy Exch", exchange: "BSE" },

  // --- MEDIA & HOSPITALITY ---
  { symbol: "SUNTV.BO", name: "Sun TV Network", exchange: "BSE" },
  { symbol: "ZEEL.BO", name: "Zee Entertainment", exchange: "BSE" },
  { symbol: "PVRINOX.BO", name: "PVR INOX Ltd", exchange: "BSE" },
  { symbol: "TVTODAY.BO", name: "TV Today Network", exchange: "BSE" },
  { symbol: "DBCORP.BO", name: "D.B. Corp Ltd", exchange: "BSE" },
  { symbol: "SAREGAMA.BO", name: "Saregama India", exchange: "BSE" },
  { symbol: "INDHOTEL.BO", name: "Indian Hotels Co", exchange: "BSE" },
  { symbol: "EIHOTEL.BO", name: "EIH Ltd (Oberoi)", exchange: "BSE" },
  { symbol: "CHALET.BO", name: "Chalet Hotels", exchange: "BSE" },
  { symbol: "LEMONTREE.BO", name: "Lemon Tree Hotels", exchange: "BSE" },
  { symbol: "IRCTC.BO", name: "IRCTC Ltd", exchange: "BSE" },

  // --- SUGAR, PAPER & AGRI ---
  { symbol: "BALRAMCHIN.BO", name: "Balrampur Chini", exchange: "BSE" },
  { symbol: "TRIVENI.BO", name: "Triveni Engineering", exchange: "BSE" },
  { symbol: "EIDPARRY.BO", name: "EID Parry (India)", exchange: "BSE" },
  { symbol: "SHREEREN.BO", name: "Shree Renuka Sugars", exchange: "BSE" },
  { symbol: "JKPAPER.BO", name: "JK Paper Ltd", exchange: "BSE" },
  { symbol: "WESTCOAST.BO", name: "West Coast Paper", exchange: "BSE" },
  { symbol: "AVANTIFEED.BO", name: "Avanti Feeds", exchange: "BSE" },
  { symbol: "GODREJAGRO.BO", name: "Godrej Agrovet", exchange: "BSE" },
  { symbol: "VENKYS.BO", name: "Venky's India", exchange: "BSE" },
  { symbol: "KRBL.BO", name: "KRBL Ltd", exchange: "BSE" },
  { symbol: "LTFOODS.BO", name: "LT Foods Ltd", exchange: "BSE" },
  { symbol: "CCL.BO", name: "CCL Products", exchange: "BSE" },
]

const toCuratedSymbolKey = (raw: string): string => String(raw ?? "").toUpperCase().trim()

const toIndiaBaseSymbolKey = (raw: string): string => {
  const normalized = toCuratedSymbolKey(raw)
  if (normalized.endsWith(".BO")) return normalized.slice(0, -3)
  if (normalized.endsWith(".NS")) return normalized.slice(0, -3)
  return normalized
}

const CURATED_STOCKS: StockListItem[] = [...US_DEFAULT_STOCKS, ...BSE_STOCKS]
const CURATED_STOCK_MAP = new Map<string, StockListItem>()
for (const stock of CURATED_STOCKS) {
  const fullKey = toCuratedSymbolKey(stock.symbol)
  if (fullKey) CURATED_STOCK_MAP.set(fullKey, stock)

  const baseKey = toIndiaBaseSymbolKey(stock.symbol)
  if (baseKey && baseKey !== fullKey && !CURATED_STOCK_MAP.has(baseKey)) {
    CURATED_STOCK_MAP.set(baseKey, stock)
  }
}

export const getCuratedStockBySymbol = (symbol: string): StockListItem | undefined => {
  const normalized = String(symbol ?? "").toUpperCase().trim()
  if (!normalized) return undefined
  return CURATED_STOCK_MAP.get(normalized)
}

const BSE_SYMBOL_SET = new Set(BSE_STOCKS.map((s) => s.symbol.toUpperCase()))
const BSE_BASE_SYMBOL_SET = new Set(BSE_STOCKS.map((s) => toIndiaBaseSymbolKey(s.symbol)))

const toTradingViewExchangePrefix = (exchange: string): string => {
  const ex = String(exchange ?? "").toUpperCase().trim()
  if (ex === "BSE") return "BSE"
  if (ex === "NYSE") return "NYSE"
  if (ex === "NASDAQ") return "NASDAQ"
  if (ex === "OTC") return "OTC"
  return "NASDAQ"
}

export const toTradingViewSymbol = (raw: string) => {
  const normalized = String(raw ?? "").trim().toUpperCase()
  if (!normalized) return ""
  if (normalized.includes(":")) return normalized

  // Handle common Indian ticker suffixes from data providers.
  if (normalized.endsWith(".BO")) return `BSE:${normalized.replace(/\.BO$/, "")}`
  // NSE is intentionally not supported; treat .NS as a plain symbol.
  const maybeBase = normalized.endsWith(".NS") ? normalized.replace(/\.NS$/, "") : normalized

  if (BSE_SYMBOL_SET.has(maybeBase) || BSE_BASE_SYMBOL_SET.has(maybeBase)) return `BSE:${maybeBase}`

  // Prefer curated metadata to pick the correct US exchange (NYSE/NASDAQ/OTC).
  const curated = getCuratedStockBySymbol(maybeBase)
  if (curated) {
    const prefix = toTradingViewExchangePrefix(curated.exchange)
    return `${prefix}:${maybeBase}`
  }

  return `NASDAQ:${maybeBase}`
}

export const STOCK_SYMBOL = (symbol:string) => ({
          "symbol": toTradingViewSymbol(symbol),
          "colorTheme": "dark",
          "isTransparent": true,
          "locale": "en",
          "width": "100%"
});

export const TECHNICAL_ANALYSIS = (symbol:string) => ({
          "colorTheme": "dark",
          "displayMode": "single",
          "isTransparent": true,
          "locale": "en",
          "interval": "15m",
          "disableInterval": false,
          "width": "100%",
          "height": 395,
          "symbol": toTradingViewSymbol(symbol),
          "showIntervalTabs": true
});

export const FUNDAMENTAL_DATA = (symbol:string) => ({
          "symbol": toTradingViewSymbol(symbol),
          "colorTheme": "dark",
          "displayMode": "regular",
          "isTransparent": true,
          "locale": "en",
          "width": "100%",
          "height": 520
});

export const COMPANY_PROFILE = (symbol:string) => ({
          "symbol": toTradingViewSymbol(symbol),
          "colorTheme": "dark",
          "isTransparent": true,
          "locale": "en",
          "width": "100%",
          "height": 520
});

export const ADVANCED_CHART_1 = (symbol:string) => ({
          "allow_symbol_change": true,
          "calendar": false,
          "details": true,
          "hide_side_toolbar": true,
          "hide_top_toolbar": false,
          "hide_legend": false,
          "hide_volume": false,
          "hotlist": false,
          "interval": "D",
          "locale": "en",
          "save_image": true,
          "style": "1",
          "symbol": toTradingViewSymbol(symbol),
          "theme": "dark",
          "timezone": "Asia/Kolkata",
          "backgroundColor": "#0F0F0F",
          "gridColor": "rgba(242, 242, 242, 0.06)",
          "watchlist": [],
          "withdateranges": false,
          "compareSymbols": [],
          "studies": [
            "STD;Supertrend"
          ],
          "width": "100%",
          "height": 720
});

export const ADVANCED_CHART_2 = (symbol:string) => ({
          "allow_symbol_change": true,
          "calendar": false,
          "details": false,
          "hide_side_toolbar": false,
          "hide_top_toolbar": true,
          "hide_legend": false,
          "hide_volume": false,
          "hotlist": false,
          "interval": "D",
          "locale": "en",
          "save_image": true,
          "style": "3",
          "symbol": toTradingViewSymbol(symbol),
          "theme": "dark",
          "timezone": "Asia/Kolkata",
          "backgroundColor": "#0F0F0F",
          "gridColor": "rgba(242, 242, 242, 0.06)",
          "watchlist": [],
          "withdateranges": false,
          "compareSymbols": [],
          "studies": [],
          "width": "100%",
          "height": 650
});

export const CRYPTO_MARKETS = {
          "defaultColumn": "overview",
          "screener_type": "crypto_mkt",
          "displayCurrency": "USD",
          "colorTheme": "dark",
          "isTransparent": false,
          "locale": "en",
          "width": "100%",
          "height": 550
}

export const MARKET_DATA = {
          "colorTheme": "dark",
          "locale": "en",
          "largeChartUrl": "",
          "isTransparent": false,
          "showSymbolLogo": true,
          "backgroundColor": "#0F0F0F",
          "support_host": "https://www.tradingview.com",
          "width": 550,
          "height": 550,
          "symbolsGroups": [
            {
              "name": "Financial",
              "symbols": [
                {
                  "name": "NYSE:JPM",
                  "displayName": " JP Morgan Chase & Co."
                },
                {
                  "name": "NYSE:V",
                  "displayName": " Visa Inc."
                },
                {
                  "name": "NASDAQ:HOOD",
                  "displayName": " Robinhood Markets, Inc."
                },
                {
                  "name": "BSE:NSDL",
                  "displayName": " National Securities Depository Limited"
                },
                {
                  "name": "BSE:SBIN",
                  "displayName": " State Bank of India"
                },
                {
                  "name": "BSE:HDFCBANK",
                  "displayName": " HDFC Bank Limited"
                },
                {
                  "name": "BSE:ICICIBANK",
                  "displayName": " ICICI Bank Limited"
                },
                {
                  "name": "NASDAQ:COIN",
                  "displayName": " Coinbase Global, Inc."
                },
                {
                  "name": "NYSE:BAC",
                  "displayName": " Bank of America Corporation"
                }
              ]
            },
            {
              "name": "Technology",
              "symbols": [
                {
                  "name": "NASDAQ:META",
                  "displayName": " Meta Platforms, Inc."
                },
                {
                  "name": "NASDAQ:MSFT",
                  "displayName": " Microsoft Corporation"
                },
                {
                  "name": "NASDAQ:GOOGL",
                  "displayName": " Alphabet Inc."
                },
                {
                  "name": "NYSE:ORCL",
                  "displayName": " Oracle Corporation"
                },
                {
                  "name": "NASDAQ:AAPL",
                  "displayName": " Apple Inc."
                },
                {
                  "name": "NASDAQ:NVDA",
                  "displayName": " NVIDIA Corporation"
                },
                {
                  "name": "BSE:TCS",
                  "displayName": " Tata Consultancy Services Limited"
                },
                {
                  "name": "NASDAQ:NFLX",
                  "displayName": " Netflix, Inc."
                }
              ]
            },
            {
              "name": "Services",
              "symbols": [
                {
                  "name": "NASDAQ:PYPL",
                  "displayName": " PayPal Holdings, Inc."
                },
                {
                  "name": "NASDAQ:AMZN",
                  "displayName": " Amazon.com, Inc."
                },
                {
                  "name": "NYSE:BABA",
                  "displayName": " Alibaba Group Holding Limited Sponsored ADR"
                },
                {
                  "name": "NASDAQ:WMT",
                  "displayName": " Walmart Inc."
                },
                {
                  "name": "BSE:MEESHO",
                  "displayName": " Meesho Limited"
                },
                {
                  "name": "BSE:DMART",
                  "displayName": " Avenue Supermarts Ltd."
                }
              ]
            }
          ]
}

export const MARKET_HEATMAP = {
        "dataSource": "SPX500",
        "blockSize": "market_cap_basic",
        "blockColor": "change",
        "grouping": "sector",
        "locale": "en",
        "symbolUrl": "",
        "colorTheme": "dark",
        "exchanges": [],
        "hasTopBar": false,
        "isDataSetEnabled": false,
        "isZoomEnabled": true,
        "hasSymbolTooltip": true,
        "isMonoSize": false,
        "width": "100%",
        "height": "100%"
}

export const TICKER_TAPE = {
        "symbols": [
            {
              "proName": "FOREXCOM:SPXUSD",
              "title": "S&P 500 Index"
            },
            {
              "proName": "FOREXCOM:NSXUSD",
              "title": "US 100 Cash CFD"
            },
            {
              "proName": "FX_IDC:EURUSD",
              "title": "EUR to USD"
            },
            {
              "proName": "BITSTAMP:BTCUSD",
              "title": "Bitcoin"
            },
            {
              "proName": "BITSTAMP:ETHUSD",
              "title": "Ethereum"
            },
            {
              "proName": "FX_IDC:INRUSD",
              "title": "INDIAN RUPEE / U.S. DOLLAR"
            },
            {
              "proName": "TVC:GOLD",
              "title": " GOLD (US$/OZ)"
            },
            {
              "proName": "NASDAQ:NVDA",
              "title": " NVIDIA Corporation"
            },
            {
              "proName": "NASDAQ:AAPL",
              "title": " Apple Inc."
            },
            {
              "proName": "NYSE:ORCL",
              "title": " Oracle Corporation"
            },
            {
              "proName": "NASDAQ:GOOGL",
              "title": " Alphabet Inc."
            }
          ],
          "colorTheme": "dark",
          "locale": "en",
          "largeChartUrl": "",
          "isTransparent": false,
          "showSymbolLogo": true,
          "displayMode": "adaptive"
}

export const MARKET_OVERVIEW_CHART = {
          "colorTheme": "dark",
          "dateRange": "12M",
          "locale": "en",
          "largeChartUrl": "",
          "isTransparent": false,
          "showFloatingTooltip": false,
          "plotLineColorGrowing": "rgba(41, 98, 255, 1)",
          "plotLineColorFalling": "rgba(41, 98, 255, 1)",
          "gridLineColor": "rgba(240, 243, 250, 0)",
          "scaleFontColor": "#DBDBDB",
          "belowLineFillColorGrowing": "rgba(41, 98, 255, 0.12)",
          "belowLineFillColorFalling": "rgba(41, 98, 255, 0.12)",
          "belowLineFillColorGrowingBottom": "rgba(41, 98, 255, 0)",
          "belowLineFillColorFallingBottom": "rgba(41, 98, 255, 0)",
          "symbolActiveColor": "rgba(41, 98, 255, 0.12)",
          "tabs": [
            {
              "title": "Stocks",
              "symbols": [
                {
                  "s": "NASDAQ:TSLA",
                  "d": "Tesla, Inc.",
                  "logoid": "tesla",
                  "currency-logoid": "country/US"
                },
                {
                  "s": "NASDAQ:NVDA",
                  "d": "NVIDIA Corporation",
                  "logoid": "nvidia",
                  "currency-logoid": "country/US"
                },
                {
                  "s": "NASDAQ:AAPL",
                  "d": " Apple Inc.",
                  "logoid": "apple",
                  "currency-logoid": "country/US"
                },
                {
                  "s": "NASDAQ:META",
                  "d": " Meta Platforms, Inc.",
                  "logoid": "meta-platforms",
                  "currency-logoid": "country/US"
                },
                {
                  "s": "NASDAQ:AMZN",
                  "d": " Amazon.com, Inc.",
                  "logoid": "amazon",
                  "currency-logoid": "country/US"
                },
                {
                  "s": "NYSE:ORCL",
                  "d": " Oracle Corporation",
                  "logoid": "oracle",
                  "currency-logoid": "country/US"
                },
                {
                  "s": "NASDAQ:MSFT",
                  "d": " Microsoft Corporation",
                  "logoid": "microsoft",
                  "currency-logoid": "country/US"
                }
              ],
              "originalTitle": "Indices"
            },
            {
              "title": "Futures",
              "symbols": [
                {
                  "s": "BMFBOVESPA:ISP1!",
                  "d": "S&P 500"
                },
                {
                  "s": "BMFBOVESPA:EUR1!",
                  "d": "Euro"
                },
                {
                  "s": "CMCMARKETS:GOLD",
                  "d": "Gold"
                },
                {
                  "s": "BMFBOVESPA:CCM1!",
                  "d": "Corn"
                }
              ],
              "originalTitle": "Futures"
            },
            {
              "title": "Forex",
              "symbols": [
                {
                  "s": "FX:EURUSD",
                  "d": "EUR to USD"
                },
                {
                  "s": "FX:GBPUSD",
                  "d": "GBP to USD"
                },
                {
                  "s": "FX:USDJPY",
                  "d": "USD to JPY"
                },
                {
                  "s": "FX:AUDUSD",
                  "d": "AUD to USD"
                },
                {
                  "s": "FX:USDCAD",
                  "d": "USD to CAD"
                },
                {
                  "s": "FX_IDC:INRUSD",
                  "d": " INDIAN RUPEE / U.S. DOLLAR",
                  "base-currency-logoid": "country/IN",
                  "currency-logoid": "country/US"
                },
                {
                  "s": "FX_IDC:INREUR",
                  "d": " INDIAN RUPEE / EURO",
                  "base-currency-logoid": "country/IN",
                  "currency-logoid": "country/EU"
                }
              ],
              "originalTitle": "Forex"
            },
            {
              "title": "Crypto",
              "symbols": [
                {
                  "s": "BITSTAMP:BTCUSD",
                  "d": " Bitcoin / U.S. dollar",
                  "base-currency-logoid": "crypto/XTVCBTC",
                  "currency-logoid": "country/US"
                },
                {
                  "s": "BINANCE:BTCUSDT",
                  "d": " Bitcoin / TetherUS",
                  "base-currency-logoid": "crypto/XTVCBTC",
                  "currency-logoid": "crypto/XTVCUSDT"
                },
                {
                  "s": "BITSTAMP:ETHUSD",
                  "d": " Ethereum / U.S. dollar",
                  "base-currency-logoid": "crypto/XTVCETH",
                  "currency-logoid": "country/US"
                },
                {
                  "s": "BINANCE:ETHUSDT",
                  "d": " Ethereum / TetherUS",
                  "base-currency-logoid": "crypto/XTVCETH",
                  "currency-logoid": "crypto/XTVCUSDT"
                }
              ]
            }
          ],
          "support_host": "https://www.tradingview.com",
          "backgroundColor": "#0f0f0f",
          "width": "100%",
          "height": "550",
          "showSymbolLogo": true,
          "showChart": true
        }

export const NEWS_WIDGET = {
        "displayMode": "adaptive",
        "feedMode": "all_symbols",
        "colorTheme": "dark",
        "isTransparent": true,
        "locale": "en",
        "width": "100%",
        "height": 550
}

export const BSE_MARKET_DATA = {
          "market": "india",
          "showToolbar": true,
          "defaultColumn": "overview",
          "defaultScreen": "most_capitalized",
          "isTransparent": true,
          "locale": "en",
          "colorTheme": "dark",
          "width": "100%",
          "height": 550
}

export const USA_MARKET_DATA = {
          "market": "america",
          "showToolbar": true,
          "defaultColumn": "overview",
          "defaultScreen": "most_capitalized",
          "isTransparent": true,
          "locale": "en",
          "colorTheme": "dark",
          "width": "100%",
          "height": 550
}

export const getStocksForMarket = (market: MarketType): StockListItem[] => {
  if (market === 'US') {
    return US_DEFAULT_STOCKS ?? [];
  }

  // For Indian market, use BSE stocks (with .BO suffix for Yahoo Finance)
  return (BSE_STOCKS ?? []).map((s) => ({
    ...s,
    symbol: s.symbol.endsWith('.BO') ? s.symbol : `${s.symbol}.BO`,
  }));
};