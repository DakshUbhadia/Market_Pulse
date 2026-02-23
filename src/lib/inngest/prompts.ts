export const PERSONALIZED_WELCOME_EMAIL_PROMPT = `Generate highly personalized HTML content that will be inserted into an email template at the {{intro}} placeholder.

User profile data:
{{userProfile}}

PERSONALIZATION REQUIREMENTS:
You MUST create content that is obviously tailored to THIS specific user by:

IMPORTANT: Do NOT start the personalized content with "Welcome" since the email header already says "Welcome aboard {{name}}". Use alternative openings like "Thanks for joining", "Great to have you", "You're all set", "Perfect timing", etc.

1. **Direct Reference to User Details**: Extract and use specific information from their profile:
   - Their exact investment goals or objectives
   - Their stated risk tolerance level
   - Their preferred sectors/industries mentioned
   - Their experience level or background
   - Any specific stocks/companies they're interested in
   - Their investment timeline (short-term, long-term, retirement)

2. **Contextual Messaging**: Create content that shows you understand their situation:
   - New investors → Reference learning/starting their journey
   - Experienced traders → Reference advanced tools/strategy enhancement  
   - Retirement planning → Reference building wealth over time
   - Specific sectors → Reference those exact industries by name
   - Conservative approach → Reference safety and informed decisions
   - Aggressive approach → Reference opportunities and growth potential

3. **Personal Touch**: Make it feel like it was written specifically for them:
   - Use their goals in your messaging
   - Reference their interests directly
   - Connect features to their specific needs
   - Make them feel understood and seen

CRITICAL FORMATTING REQUIREMENTS:
- Return ONLY clean HTML content with NO markdown, NO code blocks, NO backticks
- Use SINGLE paragraph only: <p class="mobile-text" style="margin: 0 0 30px 0; font-size: 16px; line-height: 1.6; color: #CCDADC;">content</p>
- Write exactly TWO sentences (add one more sentence than current single sentence)
- Keep total content between 35-50 words for readability
- Use <strong> for key personalized elements (their goals, sectors, etc.)
- DO NOT include "Here's what you can do right now:" as this is already in the template
- Make every word count toward personalization
- Second sentence should add helpful context or reinforce the personalization

Example personalized outputs (showing obvious customization with TWO sentences):
<p class="mobile-text" style="margin: 0 0 30px 0; font-size: 16px; line-height: 1.6; color: #CCDADC;">Thanks for joining Market Pulse! As someone focused on <strong>technology growth stocks</strong>, you'll love our real-time alerts for companies like the ones you're tracking. We'll help you spot opportunities before they become mainstream news.</p>

<p class="mobile-text" style="margin: 0 0 30px 0; font-size: 16px; line-height: 1.6; color: #CCDADC;">Great to have you aboard! Perfect for your <strong>conservative retirement strategy</strong> — we'll help you monitor dividend stocks without overwhelming you with noise. You can finally track your portfolio progress with confidence and clarity.</p>

<p class="mobile-text" style="margin: 0 0 30px 0; font-size: 16px; line-height: 1.6; color: #CCDADC;">You're all set! Since you're new to investing, we've designed simple tools to help you build confidence while learning the <strong>healthcare sector</strong> you're interested in. Our beginner-friendly alerts will guide you without the confusing jargon.</p>`

export const NEWS_SUMMARY_EMAIL_PROMPT = `Generate HTML content for a market news summary email that will be inserted into the NEWS_SUMMARY_EMAIL_TEMPLATE at the {{newsContent}} placeholder.

News data to summarize:
{{newsData}}

CRITICAL FORMATTING REQUIREMENTS:
- Return ONLY clean HTML content with NO markdown, NO code blocks, NO backticks
- Structure content with clear sections using proper HTML headings and paragraphs
- Use these specific CSS classes and styles to match the email template:

SECTION HEADINGS (for categories like "Market Highlights", "Top Movers", etc.):
<h3 class="mobile-news-title dark-text" style="margin: 30px 0 15px 0; font-size: 18px; font-weight: 600; color: #f8f9fa; line-height: 1.3;">Section Title</h3>

PARAGRAPHS (for news content):
<p class="mobile-text dark-text-secondary" style="margin: 0 0 20px 0; font-size: 16px; line-height: 1.6; color: #CCDADC;">Content goes here</p>

STOCK/COMPANY MENTIONS:
<strong style="color: #FDD458;">Stock Symbol</strong> for ticker symbols
<strong style="color: #CCDADC;">Company Name</strong> for company names

PERFORMANCE INDICATORS:
Use 📈 for gains, 📉 for losses, 📊 for neutral/mixed

NEWS ARTICLE STRUCTURE:
For each individual news item within a section, use this structure:
1. Article container with visual styling and icon
2. Article title as a subheading
3. Key takeaways in bullet points (2-3 actionable insights)
4. "What this means" section for context
5. "Read more" link to the original article
6. Visual divider between articles

ARTICLE CONTAINER:
Wrap each article in a clean, simple container:
<div class="dark-info-box" style="background-color: #212328; padding: 24px; margin: 20px 0; border-radius: 8px;">

ARTICLE TITLES:
<h4 class="dark-text" style="margin: 0 0 16px 0; font-size: 18px; font-weight: 600; color: #FFFFFF; line-height: 1.4;">
Article Title Here
</h4>

BULLET POINTS (minimum 3 concise insights):
Use this format with clear, concise explanations (no label needed):
<ul style="margin: 16px 0 20px 0; padding-left: 0; margin-left: 0; list-style: none;">
  <li class="dark-text-secondary" style="margin: 0 0 16px 0; padding: 0; margin-left: 0; font-size: 16px; line-height: 1.6; color: #CCDADC;">
    <span style="color: #FDD458; font-weight: bold; font-size: 20px; margin-right: 8px;">•</span>Clear, concise explanation in simple terms that's easy to understand quickly.
  </li>
  <li class="dark-text-secondary" style="margin: 0 0 16px 0; padding: 0; margin-left: 0; font-size: 16px; line-height: 1.6; color: #CCDADC;">
    <span style="color: #FDD458; font-weight: bold; font-size: 20px; margin-right: 8px;">•</span>Brief explanation with key numbers and what they mean in everyday language.
  </li>
  <li class="dark-text-secondary" style="margin: 0 0 16px 0; padding: 0; margin-left: 0; font-size: 16px; line-height: 1.6; color: #CCDADC;">
    <span style="color: #FDD458; font-weight: bold; font-size: 20px; margin-right: 8px;">•</span>Simple takeaway about what this means for regular people's money.
  </li>
</ul>

INSIGHT SECTION:
Add simple context explanation:
<div style="background-color: #141414; border: 1px solid #374151; padding: 15px; border-radius: 6px; margin: 16px 0;">
<p class="dark-text-secondary" style="margin: 0; font-size: 14px; color: #CCDADC; line-height: 1.4;">💡 <strong style="color: #FDD458;">Bottom Line:</strong> Simple explanation of why this news matters to your money in everyday language.</p>
</div>

READ MORE BUTTON:
<div style="margin: 20px 0 0 0;">
<a href="ARTICLE_URL" style="color: #FDD458; text-decoration: none; font-weight: 500; font-size: 14px;" target="_blank" rel="noopener noreferrer">Read Full Story →</a>
</div>

ARTICLE DIVIDER:
Close each article container:
</div>

SECTION DIVIDERS:
Between major sections, use:
<div style="border-top: 1px solid #374151; margin: 32px 0 24px 0;"></div>

Content guidelines:
- Organize news into logical sections with icons (📊 Market Overview, 📈 Top Gainers, 📉 Top Losers, 🔥 Breaking News, 💼 Earnings Reports, 🏛️ Economic Data, etc.)
- NEVER repeat section headings - use each section type only once per email
- For each news article, include its actual headline/title from the news data
- Provide MINIMUM 3 CONCISE bullet points (NO "Key Takeaways" label - start directly with bullets)
- Each bullet should be SHORT and EASY TO UNDERSTAND - one clear sentence preferred
- Use PLAIN ENGLISH - avoid jargon, complex financial terms, or insider language
- Explain concepts as if talking to someone new to investing
- Include specific numbers but explain what they mean in simple terms
- Add "Bottom Line" context in everyday language anyone can understand
- Use clean, light design with yellow bullets for better readability
- Make each article easy to scan with clear spacing and structure
- Always include simple "Read Full Story" buttons with actual URLs
- Focus on PRACTICAL insights regular people can understand and use
- Explain what the news means for regular investors' money
- Keep language conversational and accessible to everyone
- Prioritize BREVITY and CLARITY over detailed explanations

Example structure:
<h3 class="mobile-news-title dark-text" style="margin: 30px 0 15px 0; font-size: 20px; font-weight: 600; color: #f8f9fa; line-height: 1.3;">📊 Market Overview</h3>

<div class="dark-info-box" style="background-color: #212328; padding: 24px; margin: 20px 0; border-radius: 8px;">
<h4 class="dark-text" style="margin: 0 0 16px 0; font-size: 18px; font-weight: 600; color: #FDD458; line-height: 1.4;">
Stock Market Had Mixed Results Today
</h4>

<ul style="margin: 16px 0 20px 0; padding-left: 0; margin-left: 0; list-style: none;">
  <li class="dark-text-secondary" style="margin: 0 0 16px 0; padding: 0; margin-left: 0; font-size: 16px; line-height: 1.6; color: #CCDADC;">
    <span style="color: #FDD458; font-weight: bold; font-size: 20px; margin-right: 8px;">•</span>Tech stocks like Apple went up 1.2% today, which is good news for tech investors.
  </li>
  <li class="dark-text-secondary" style="margin: 0 0 16px 0; padding: 0; margin-left: 0; font-size: 16px; line-height: 1.6; color: #CCDADC;">
    <span style="color: #FDD458; font-weight: bold; font-size: 20px; margin-right: 8px;">•</span>Traditional companies went down 0.3%, showing investors prefer tech right now.
  </li>
  <li class="dark-text-secondary" style="margin: 0 0 16px 0; padding: 0; margin-left: 0; font-size: 16px; line-height: 1.6; color: #CCDADC;">
    <span style="color: #FDD458; font-weight: bold; font-size: 20px; margin-right: 8px;">•</span>High trading volume (12.4 billion shares) shows investors are confident and active.
  </li>
</ul>

<div style="background-color: #141414; border: 1px solid #374151; padding: 15px; border-radius: 6px; margin: 16px 0;">
<p class="dark-text-secondary" style="margin: 0; font-size: 14px; color: #CCDADC; line-height: 1.4;">💡 <strong style="color: #FDD458;">Bottom Line:</strong> If you own tech stocks, today was good for you. If you're thinking about investing, tech companies might be a smart choice right now.</p>
</div>

<div style="margin: 20px 0 0 0;">
<a href="https://example.com/article1" style="color: #FDD458; text-decoration: none; font-weight: 500; font-size: 14px;" target="_blank" rel="noopener noreferrer">Read Full Story →</a>
</div>
</div>

<div style="border-top: 1px solid #374151; margin: 32px 0 24px 0;"></div>

<h3 class="mobile-news-title dark-text" style="margin: 30px 0 15px 0; font-size: 20px; font-weight: 600; color: #f8f9fa; line-height: 1.3;">📈 Top Gainers</h3>

<div class="dark-info-box" style="background-color: #212328; padding: 24px; margin: 20px 0; border-radius: 8px;">
<h4 class="dark-text" style="margin: 0 0 16px 0; font-size: 18px; font-weight: 600; color: #FDD458; line-height: 1.4;">
Apple Stock Jumped After Great Earnings Report
</h4>

<ul style="margin: 16px 0 20px 0; padding-left: 0; margin-left: 0; list-style: none;">
  <li class="dark-text-secondary" style="margin: 0 0 16px 0; padding: 0; margin-left: 0; font-size: 16px; line-height: 1.6; color: #CCDADC;">
    <span style="color: #FDD458; font-weight: bold; font-size: 20px; margin-right: 8px;">•</span>Apple stock jumped 5.2% after beating earnings expectations.
  </li>
  <li class="dark-text-secondary" style="margin: 0 0 16px 0; padding: 0; margin-left: 0; font-size: 16px; line-height: 1.6; color: #CCDADC;">
    <span style="color: #FDD458; font-weight: bold; font-size: 20px; margin-right: 8px;">•</span>iPhone sales expected to grow 8% next quarter despite economic uncertainty.
  </li>
  <li class="dark-text-secondary" style="margin: 0 0 16px 0; padding: 0; margin-left: 0; font-size: 16px; line-height: 1.6; color: #CCDADC;">
    <span style="color: #FDD458; font-weight: bold; font-size: 20px; margin-right: 8px;">•</span>App store and services revenue hit $22.3 billion (up 14%), providing steady income.
  </li>
</ul>

<div style="background-color: #141414; border: 1px solid #374151; padding: 15px; border-radius: 6px; margin: 16px 0;">
<p class="dark-text-secondary" style="margin: 0; font-size: 14px; color: #CCDADC; line-height: 1.4;">💡 <strong style="color: #FDD458;">Bottom Line:</strong> Apple is making money in different ways (phones AND services), so it's a pretty safe stock to own even when the economy gets shaky.</p>
</div>

<div style="margin: 20px 0 0 0;">
<a href="https://example.com/article2" style="color: #FDD458; text-decoration: none; font-weight: 500; font-size: 14px;" target="_blank" rel="noopener noreferrer">Read Full Story →</a>
</div>
</div>`

export const NEWS_SUMMARY_WITH_WATCHLIST_EMAIL_PROMPT = `Generate HTML content for a daily Market Pulse news email that will be inserted into the NEWS_SUMMARY_EMAIL_TEMPLATE at the {{newsContent}} placeholder.

You MUST include BOTH sections in this order:
1) A general market section using the Market News data
2) A watchlist section using the Watchlist News data

INPUT DATA:
- User: {{userName}} (use their name once in a friendly opening line)
- Market News: {{marketNewsData}}
- Watchlist Symbols: {{watchlistSymbols}}
- Watchlist News: {{watchlistNewsData}}

CRITICAL FORMATTING REQUIREMENTS:
- Return ONLY clean HTML content with NO markdown, NO code blocks, NO backticks
- Use the same HTML structures/classes/styles as in NEWS_SUMMARY_EMAIL_PROMPT (headings, containers, bullets, bottom line, read more link)
- Use EXACT section headings (same styles) like:
  <h3 class="mobile-news-title dark-text" style="margin: 30px 0 15px 0; font-size: 18px; font-weight: 600; color: #f8f9fa; line-height: 1.3;">📊 Market Highlights</h3>
  <h3 class="mobile-news-title dark-text" style="margin: 30px 0 15px 0; font-size: 18px; font-weight: 600; color: #f8f9fa; line-height: 1.3;">⭐ Your Watchlist News</h3>
- Between the two major sections, include this divider:
  <div style="border-top: 1px solid #374151; margin: 32px 0 24px 0;"></div>

CONTENT RULES:
- Market section: summarize up to 4 items (pick the most relevant)
- Watchlist section: prioritize news that includes a relatedSymbol; if multiple symbols exist, cover as many distinct symbols as possible
- If Watchlist Symbols is empty or Watchlist News is empty, say so briefly in the watchlist section (still include the section header)
- Keep language simple and actionable; include at least 3 bullets per article container
`;

export const TRADINGVIEW_SYMBOL_MAPPING_PROMPT = `You are an expert in financial markets and trading platforms. Your task is to find the correct TradingView symbol that corresponds to a given Finnhub stock symbol.

Stock information from Finnhub:
Symbol: {{symbol}}
Company: {{company}}
Exchange: {{exchange}}
Currency: {{currency}}
Country: {{country}}

IMPORTANT RULES:
1. TradingView uses specific symbol formats that may differ from Finnhub
2. For US stocks: Usually just the symbol (e.g., AAPL for Apple)
3. For international stocks: Often includes exchange prefix (e.g., NASDAQ:AAPL, NYSE:MSFT, LSE:BARC)
4. Some symbols may have suffixes for different share classes
5. ADRs and foreign stocks may have different symbol formats

RESPONSE FORMAT:
Return ONLY a valid JSON object with this exact structure:
{
  "tradingViewSymbol": "EXCHANGE:SYMBOL",
  "confidence": "high|medium|low",
  "reasoning": "Brief explanation of why this mapping is correct"
}

EXAMPLES:
- Apple Inc. (AAPL) from Finnhub → {"tradingViewSymbol": "NASDAQ:AAPL", "confidence": "high", "reasoning": "Apple trades on NASDAQ as AAPL"}
- Microsoft Corp (MSFT) from Finnhub → {"tradingViewSymbol": "NASDAQ:MSFT", "confidence": "high", "reasoning": "Microsoft trades on NASDAQ as MSFT"}
- Barclays PLC (BARC.L) from Finnhub → {"tradingViewSymbol": "LSE:BARC", "confidence": "high", "reasoning": "Barclays trades on London Stock Exchange as BARC"}

Your response must be valid JSON only. Do not include any other text.`

export const DAILY_TRADING_INSIGHTS_EMAIL_PROMPT = `Generate HTML content for a daily trading insights email that will be inserted into the DAILY_TRADING_INSIGHTS_EMAIL_TEMPLATE at the {{insightsContent}} placeholder.

This email is for INDIAN MARKET (NSE/BSE) stocks only, sent at 10 AM IST.

INPUT DATA:
- User: {{userName}}
- Date: {{date}}
- Market Sentiment: {{marketSentiment}} (Bullish/Bearish/Neutral)
- Market A/D Ratio: {{marketADRatio}}
- Top Institutional Buying Sectors: {{topBuyingSectors}}
- Top Institutional Selling Sectors: {{topSellingSectors}}
- Stocks with Highest Upward Probability: {{bullishStocks}}
- Stocks with Highest Downward Probability: {{bearishStocks}}
- Top Options Trading Picks: {{optionsPicks}}

CRITICAL FORMATTING REQUIREMENTS:
- Return ONLY clean HTML content with NO markdown, NO code blocks, NO backticks
- Use the same dark theme styling as news summary emails
- Use gold (#FDD458) for highlights and important elements
- Use green (#22c55e) for bullish/buying indicators
- Use red (#ef4444) for bearish/selling indicators
- Use #CCDADC for regular text and #9ca3af for secondary text

SECTION 1: MARKET OVERVIEW (Brief summary of market condition)
<div class="dark-info-box" style="background-color: #212328; padding: 20px; margin: 0 0 24px 0; border-radius: 8px; border-left: 4px solid {{sentimentColor}};">
  <h3 style="margin: 0 0 12px 0; font-size: 16px; font-weight: 600; color: #FFFFFF;">📊 Market Pulse</h3>
  <p style="margin: 0; font-size: 15px; color: #CCDADC; line-height: 1.5;">Brief 2-3 sentence summary of overall market condition and what direction is more probable today based on sentiment and A/D ratio.</p>
</div>

SECTION 2: INSTITUTIONAL ACTIVITY (Two columns - Buying & Selling sectors)
<h3 class="mobile-news-title dark-text" style="margin: 24px 0 15px 0; font-size: 18px; font-weight: 600; color: #FDD458; line-height: 1.3;">🏛️ Institutional Money Flow</h3>

Use this two-column layout:
<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin: 0 0 24px 0;">
  <tr>
    <td style="width: 48%; vertical-align: top; padding-right: 2%;">
      <div style="background-color: #0d2818; border: 1px solid #22c55e; border-radius: 8px; padding: 16px;">
        <h4 style="margin: 0 0 12px 0; font-size: 14px; font-weight: 600; color: #22c55e;">📈 Top Buying Sectors</h4>
        <!-- List 3 sectors with buying activity -->
      </div>
    </td>
    <td style="width: 48%; vertical-align: top; padding-left: 2%;">
      <div style="background-color: #2d1215; border: 1px solid #ef4444; border-radius: 8px; padding: 16px;">
        <h4 style="margin: 0 0 12px 0; font-size: 14px; font-weight: 600; color: #ef4444;">📉 Top Selling Sectors</h4>
        <!-- List 3 sectors with selling activity -->
      </div>
    </td>
  </tr>
</table>

SECTION 3: HIGH PROBABILITY STOCKS
Based on market sentiment, indicate which direction (up or down) is MORE LIKELY today.

<h3 class="mobile-news-title dark-text" style="margin: 24px 0 15px 0; font-size: 18px; font-weight: 600; color: #FDD458; line-height: 1.3;">🎯 High Probability Movers</h3>

<p style="margin: 0 0 16px 0; font-size: 14px; color: #9ca3af;">
  Based on current market conditions, <strong style="color: {{dominantColor}};">{{dominantDirection}} moves are more probable today</strong>.
</p>

For BULLISH stocks (Top 5):
<div style="background-color: #0d2818; border: 1px solid #22c55e; border-radius: 8px; padding: 16px; margin: 0 0 16px 0;">
  <h4 style="margin: 0 0 12px 0; font-size: 15px; font-weight: 600; color: #22c55e;">🚀 Likely to Go UP</h4>
  <!-- List each stock with: Symbol, Company Name, R-Factor score, Key reason -->
  <!-- Format: Symbol (R: XX) - Brief reason -->
</div>

For BEARISH stocks (Top 5):
<div style="background-color: #2d1215; border: 1px solid #ef4444; border-radius: 8px; padding: 16px; margin: 0 0 16px 0;">
  <h4 style="margin: 0 0 12px 0; font-size: 15px; font-weight: 600; color: #ef4444;">⚠️ Likely to Go DOWN</h4>
  <!-- List each stock with: Symbol, Company Name, R-Factor score, Key reason -->
</div>

SECTION 4: TOP OPTIONS TRADING PICKS
<h3 class="mobile-news-title dark-text" style="margin: 24px 0 15px 0; font-size: 18px; font-weight: 600; color: #FDD458; line-height: 1.3;">⚡ Today's Options Trading Picks</h3>

<p style="margin: 0 0 16px 0; font-size: 14px; color: #9ca3af;">
  Top 3 stocks combining technical and institutional analysis for potential options plays.
</p>

For each of 3 stocks:
<div class="dark-info-box" style="background-color: #212328; padding: 16px; margin: 0 0 12px 0; border-radius: 8px;">
  <div style="display: flex; justify-content: space-between; align-items: center; margin: 0 0 8px 0;">
    <span style="font-size: 16px; font-weight: 600; color: #FDD458;">SYMBOL</span>
    <span style="font-size: 12px; padding: 4px 8px; border-radius: 4px; background-color: {{directionBg}}; color: {{directionColor}};">BULLISH/BEARISH</span>
  </div>
  <p style="margin: 0 0 8px 0; font-size: 14px; color: #CCDADC;">Company Name</p>
  <p style="margin: 0; font-size: 13px; color: #9ca3af;">Brief explanation of why this stock is a good options candidate today.</p>
</div>

CONTENT GUIDELINES:
- Keep language simple and actionable
- Use specific data (R-Factor scores, % changes, sector names)
- Clearly indicate bullish vs bearish bias for each stock
- Explain in simple terms why each stock made the list
- For options picks, suggest whether to look at CALLS (bullish) or PUTS (bearish)
- Make analysis relevant to intraday/short-term traders
- Be specific about which direction is more favorable given market conditions`
