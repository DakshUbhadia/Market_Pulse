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

export const STOCK_SYMBOL_APPL = {
          "symbol": "NASDAQ:AAPL",
          "colorTheme": "dark",
          "isTransparent": false,
          "locale": "en",
          "width": 1015
}

export const TECHNICAL_ANALYSIS_APPL = {
          "colorTheme": "dark",
          "displayMode": "single",
          "isTransparent": true,
          "locale": "en",
          "interval": "15m",
          "disableInterval": false,
          "width": 425,
          "height": 440,
          "symbol": "NASDAQ:AAPL",
          "showIntervalTabs": true
}

export const FUNDAMENTAL_DATA_APPL = {
          "symbol": "NASDAQ:AAPL",
          "colorTheme": "dark",
          "displayMode": "regular",
          "isTransparent": true,
          "locale": "en",
          "width": 425,
          "height": 550
}

export const COMPANY_PROFILE_APPL = {
          "symbol": "NASDAQ:AAPL",
          "colorTheme": "dark",
          "isTransparent": true,
          "locale": "en",
          "width": 425,
          "height": 480
}

export const ADVANCED_CHART_1_APPL = {
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
          "symbol": "NASDAQ:AAPL",
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
          "width": 980,
          "height": 700
}

export const ADVANCED_CHART_2_APPL = {
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
          "symbol": "NASDAQ:AAPL",
          "theme": "dark",
          "timezone": "Asia/Kolkata",
          "backgroundColor": "#0F0F0F",
          "gridColor": "rgba(242, 242, 242, 0.06)",
          "watchlist": [],
          "withdateranges": false,
          "compareSymbols": [],
          "studies": [],
          "width": 980,
          "height": 630
}

export const CRYPTO_MARKETS = {
          "defaultColumn": "overview",
          "screener_type": "crypto_mkt",
          "displayCurrency": "USD",
          "colorTheme": "dark",
          "isTransparent": false,
          "locale": "en",
          "width": 450,
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
          "width": "400",
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
        "width": 400,
        "height": 550
}