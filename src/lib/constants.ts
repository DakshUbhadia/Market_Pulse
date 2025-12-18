export type NavItem = {
  href: string
  label: string
  variant?: "command"
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Dashboard" },
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
{ symbol: "ARM", name: "Arm Holdings", exchange: "NASDAQ" }
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

export const BSE_STOCKS: StockListItem[] = [
{ symbol: "RELIANCE", name: "Reliance Industries Ltd.", exchange: "BSE" },
{ symbol: "HDFCBANK", name: "HDFC Bank Ltd.", exchange: "BSE" },
{ symbol: "BHARTIARTL", name: "Bharti Airtel Ltd.", exchange: "BSE" },
{ symbol: "TCS", name: "Tata Consultancy Services Ltd.", exchange: "BSE" },
{ symbol: "INFY", name: "Infosys Ltd.", exchange: "BSE" },
{ symbol: "HINDUNILVR", name: "Hindustan Unilever Ltd.", exchange: "BSE" },
{ symbol: "ICICIBANK", name: "ICICI Bank Ltd.", exchange: "BSE" },
{ symbol: "LT", name: "Larsen & Toubro Ltd.", exchange: "BSE" },
{ symbol: "SUNPHARMA", name: "Sun Pharmaceutical Industries Ltd.", exchange: "BSE" },
{ symbol: "ITC", name: "ITC Ltd.", exchange: "BSE" },
{ symbol: "SBIN", name: "State Bank of India", exchange: "BSE" },
{ symbol: "TATAMOTORS", name: "Tata Motors Ltd.", exchange: "BSE" },
{ symbol: "MARUTI", name: "Maruti Suzuki India Ltd.", exchange: "BSE" },
{ symbol: "AXISBANK", name: "Axis Bank Ltd.", exchange: "BSE" },
{ symbol: "KOTAKBANK", name: "Kotak Mahindra Bank Ltd.", exchange: "BSE" },
{ symbol: "BAJFINANCE", name: "Bajaj Finance Ltd.", exchange: "BSE" },
{ symbol: "BAJAJFINSV", name: "Bajaj Finserv Ltd.", exchange: "BSE" },
{ symbol: "ULTRACEMCO", name: "UltraTech Cement Ltd.", exchange: "BSE" },
{ symbol: "TITAN", name: "Titan Company Ltd.", exchange: "BSE" },
{ symbol: "WIPRO", name: "Wipro Ltd.", exchange: "BSE" },
{ symbol: "TECHM", name: "Tech Mahindra Ltd.", exchange: "BSE" },
{ symbol: "POWERGRID", name: "Power Grid Corporation of India Ltd.", exchange: "BSE" },
{ symbol: "HCLTECH", name: "HCL Technologies Ltd.", exchange: "BSE" },
{ symbol: "BPCL", name: "Bharat Petroleum Corporation Ltd.", exchange: "BSE" },
{ symbol: "IOC", name: "Indian Oil Corporation Ltd.", exchange: "BSE" },
{ symbol: "COALINDIA", name: "Coal India Ltd.", exchange: "BSE" },
{ symbol: "VEDL", name: "Vedanta Ltd.", exchange: "BSE" },
{ symbol: "NTPC", name: "NTPC Ltd.", exchange: "BSE" },
{ symbol: "INDUSINDBK", name: "IndusInd Bank Ltd.", exchange: "BSE" },
{ symbol: "BRITANNIA", name: "Britannia Industries Ltd.", exchange: "BSE" },
{ symbol: "NESTLEIND", name: "Nestlé India Ltd.", exchange: "BSE" },
{ symbol: "SHREECEM", name: "Shriram Cement Ltd.", exchange: "BSE" },
{ symbol: "GRASIM", name: "Grasim Industries Ltd.", exchange: "BSE" },
{ symbol: "HINDALCO", name: "Hindalco Industries Ltd.", exchange: "BSE" },
{ symbol: "CIPLA", name: "Cipla Ltd.", exchange: "BSE" },
{ symbol: "BPCLS", name: "BPCL Ltd.", exchange: "BSE" },
{ symbol: "MOTHERSON", name: "Samvardhana Motherson International Ltd.", exchange: "BSE" },
{ symbol: "TVSMOTOR", name: "TVS Motor Company Ltd.", exchange: "BSE" },
{ symbol: "ADANIGREEN", name: "Adani Green Energy Ltd.", exchange: "BSE" },
{ symbol: "TORNTPHARM", name: "Torrent Pharmaceuticals Ltd.", exchange: "BSE" },
{ symbol: "AMBUJACEM", name: "Ambuja Cements Ltd.", exchange: "BSE" },
{ symbol: "PNB", name: "Punjab National Bank", exchange: "BSE" },
{ symbol: "CANBK", name: "Canara Bank", exchange: "BSE" },
{ symbol: "IDEA", name: "Vodafone Idea Ltd.", exchange: "BSE" },
{ symbol: "TATAPOWER", name: "Tata Power Company Ltd.", exchange: "BSE" },
{ symbol: "SHRIRAMFIN", name: "Shriram Transport Finance Co. Ltd.", exchange: "BSE" },
{ symbol: "PIDILITIND", name: "Pidilite Industries Ltd.", exchange: "BSE" },
{ symbol: "BOSCHLTD", name: "Bosch Ltd.", exchange: "BSE" },
{ symbol: "SIEMENS", name: "Siemens India Ltd.", exchange: "BSE" },
{ symbol: "ABB", name: "ABB India Ltd.", exchange: "BSE" },
{ symbol: "SOLARINDS", name: "Solar Industries India Ltd.", exchange: "BSE" },
{ symbol: "BSE", name: "BSE Ltd.", exchange: "BSE" },
{ symbol: "GMRAIRPORT", name: "GMR Airports Ltd.", exchange: "BSE" },
{ symbol: "POLYCAB", name: "Polycab India Ltd.", exchange: "BSE" },
{ symbol: "INDUSTOWER", name: "Indus Towers Ltd.", exchange: "BSE" },
{ symbol: "HDFCAMC", name: "HDFC Asset Management Company Ltd.", exchange: "BSE" },
{ symbol: "PFC", name: "Power Finance Corporation Ltd.", exchange: "BSE" },
{ symbol: "GAIL", name: "GAIL (India) Ltd.", exchange: "BSE" },
{ symbol: "IDBI", name: "IDBI Bank Ltd.", exchange: "BSE" },
{ symbol: "LGEINDIA", name: "LG Electronics India Ltd.", exchange: "BSE" },
{ symbol: "INDIANB", name: "Indian Bank", exchange: "BSE" },
{ symbol: "HERO MOTOCORP", name: "Hero MotoCorp Ltd.", exchange: "BSE" },
{ symbol: "GODREJCP", name: "Godrej Consumer Products Ltd.", exchange: "BSE" },
{ symbol: "BANKBARODA", name: "Bank of Baroda", exchange: "BSE" },
{ symbol: "TRENT", name: "Trent Ltd.", exchange: "BSE" },
{ symbol: "JIOFIN", name: "Jio Financial Services Ltd.", exchange: "BSE" },
{ symbol: "EICHERMOT", name: "Eicher Motors Ltd.", exchange: "BSE" },
{ symbol: "LTIM", name: "LTI-Mindtree Ltd.", exchange: "BSE" },
{ symbol: "BAJAJHLDNG", name: "Bajaj Holdings & Investment Ltd.", exchange: "BSE" },
{ symbol: "MUTHOOTFIN", name: "Muthoot Finance Ltd.", exchange: "BSE" },
{ symbol: "VARUNBEV", name: "Varun Beverages Ltd.", exchange: "BSE" },
{ symbol: "TATACONSUM", name: "Tata Consumer Products Ltd.", exchange: "BSE" },
{ symbol: "DRREDDY", name: "Dr. Reddy’s Laboratories Ltd.", exchange: "BSE" },
{ symbol: "APOLLOHOSP", name: "Apollo Hospitals Enterprise Ltd.", exchange: "BSE" },
{ symbol: "COLPAL", name: "Colgate-Palmolive (India) Ltd.", exchange: "BSE" },
{ symbol: "BRITANNIA", name: "Britannia Industries Ltd.", exchange: "BSE" },
{ symbol: "AUROPHARMA", name: "Aurobindo Pharma Ltd.", exchange: "BSE" },
{ symbol: "ACC", name: "ACC Ltd.", exchange: "BSE" },
{ symbol: "CADILAHC", name: "Cadila Healthcare Ltd.", exchange: "BSE" },
{ symbol: "BANDHANBNK", name: "Bandhan Bank Ltd.", exchange: "BSE" },
{ symbol: "CHOLAFIN", name: "Cholamandalam Investment & Finance Co. Ltd.", exchange: "BSE" },
{ symbol: "BERGEPAINT", name: "Berger Paints India Ltd.", exchange: "BSE" },
{ symbol: "AU SMALL FIN", name: "AU Small Finance Bank Ltd.", exchange: "BSE" },
{ symbol: "TORNTPOWER", name: "Torrent Power Ltd.", exchange: "BSE" },
{ symbol: "ADANIPOWER", name: "Adani Power Ltd.", exchange: "BSE" },
{ symbol: "WAAREEENER", name: "Waaree Energies Ltd.", exchange: "BSE" },
{ symbol: "SUZLON", name: "Suzlon Energy Ltd.", exchange: "BSE" },
]

const CURATED_STOCKS: StockListItem[] = [...US_DEFAULT_STOCKS, ...BSE_STOCKS]
const CURATED_STOCK_MAP = new Map(
  CURATED_STOCKS.map((s) => [s.symbol.toUpperCase().trim(), s])
)

export const getCuratedStockBySymbol = (symbol: string): StockListItem | undefined => {
  const normalized = String(symbol ?? "").toUpperCase().trim()
  if (!normalized) return undefined
  return CURATED_STOCK_MAP.get(normalized)
}

const BSE_SYMBOL_SET = new Set(BSE_STOCKS.map((s) => s.symbol.toUpperCase()))

const toTradingViewExchangePrefix = (exchange: string): string => {
  const ex = String(exchange ?? "").toUpperCase().trim()
  if (ex === "BSE") return "BSE"
  if (ex === "NSE") return "NSE"
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
  if (normalized.endsWith(".NS")) return `NSE:${normalized.replace(/\.NS$/, "")}`

  if (BSE_SYMBOL_SET.has(normalized)) return `BSE:${normalized}`

  // Prefer curated metadata to pick the correct US exchange (NYSE/NASDAQ/OTC).
  const curated = getCuratedStockBySymbol(normalized)
  if (curated) {
    const prefix = toTradingViewExchangePrefix(curated.exchange)
    return `${prefix}:${normalized}`
  }

  return `NASDAQ:${normalized}`
}

export const STOCK_SYMBOL = (symbol:string) => ({
          "symbol": toTradingViewSymbol(symbol),
          "colorTheme": "dark",
          "isTransparent": false,
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
          "height": 440,
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
          "height": 700
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
          "height": 640
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
          "width": "100%",
          "height": 550,
          "symbolsGroups": [
            {
              "name": "Indices",
              "symbols": [
                {
                  "name": "FOREXCOM:SPXUSD",
                  "displayName": "S&P 500 Index"
                },
                {
                  "name": "FOREXCOM:NSXUSD",
                  "displayName": "US 100 Cash CFD"
                },
                {
                  "name": "FOREXCOM:DJI",
                  "displayName": "Dow Jones Industrial Average Index"
                },
                {
                  "name": "INDEX:NKY",
                  "displayName": "Japan 225"
                },
                {
                  "name": "INDEX:DEU40",
                  "displayName": "DAX Index"
                },
                {
                  "name": "FOREXCOM:UKXGBP",
                  "displayName": "FTSE 100 Index"
                }
              ]
            },
            {
              "name": "Futures",
              "symbols": [
                {
                  "name": "BMFBOVESPA:ISP1!",
                  "displayName": "S&P 500"
                },
                {
                  "name": "BMFBOVESPA:EUR1!",
                  "displayName": "Euro"
                },
                {
                  "name": "CMCMARKETS:GOLD",
                  "displayName": "Gold"
                },
                {
                  "name": "BMFBOVESPA:CCM1!",
                  "displayName": "Corn"
                }
              ]
            },
            {
              "name": "Bonds",
              "symbols": [
                {
                  "name": "EUREX:FGBL1!",
                  "displayName": "Euro Bund"
                },
                {
                  "name": "EUREX:FBTP1!",
                  "displayName": "Euro BTP"
                },
                {
                  "name": "EUREX:FGBM1!",
                  "displayName": "Euro BOBL"
                }
              ]
            },
            {
              "name": "Forex",
              "symbols": [
                {
                  "name": "FX:EURUSD",
                  "displayName": "EUR to USD"
                },
                {
                  "name": "FX:GBPUSD",
                  "displayName": "GBP to USD"
                },
                {
                  "name": "FX:USDJPY",
                  "displayName": "USD to JPY"
                },
                {
                  "name": "FX:USDCHF",
                  "displayName": "USD to CHF"
                },
                {
                  "name": "FX:AUDUSD",
                  "displayName": "AUD to USD"
                },
                {
                  "name": "FX:USDCAD",
                  "displayName": "USD to CAD"
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
        "isTransparent": false,
        "locale": "en",
        "width": "100%",
        "height": 550
}