import {inngest} from "@/lib/inngest/client";
import {PERSONALIZED_WELCOME_EMAIL_PROMPT, NEWS_SUMMARY_WITH_WATCHLIST_EMAIL_PROMPT, DAILY_TRADING_INSIGHTS_EMAIL_PROMPT } from "@/lib/inngest/prompts";
import { sendNewsSummaryEmail, sendWelcomeEmail, sendDailyTradingInsightsEmail } from "@/lib/nodemailer";
import { getAllUsersForNewsEmail } from "@/lib/actions/user.action";
import { getWatchlistSymbolsByEmail } from "@/lib/actions/watchlist.actions";
import { getNews, type MarketNewsArticle } from "@/lib/actions/finnhub.actions";
import { getStrongMoneyScope, type MarketScopeResult, type StockAnalysis, type SectorHeatmapData } from "@/lib/actions/analysis.actions";
import { connectToDatabase } from "@/database/mongoose";
import EmailPreferences from "@/database/models/email-preferences.model";

type UserForNewsEmail = {
    id: string;
    email: string;
    name: string;
};

const formatDateTodayUtc = (): string => {
    const now = new Date();
    const yyyy = now.getUTCFullYear();
    const mm = String(now.getUTCMonth() + 1).padStart(2, '0');
    const dd = String(now.getUTCDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
};

export const sendSignUpEmail = inngest.createFunction(
    { id: 'sign-up-email' },
    { event: 'app/user.created'},
    async ({ event, step }) => {
        const userProfile = `
            - Country: ${event.data.country}
            - Investment goals: ${event.data.investmentGoals}
            - Risk tolerance: ${event.data.riskTolerance}
            - Preferred industry: ${event.data.preferredIndustry}
        `

        const prompt = PERSONALIZED_WELCOME_EMAIL_PROMPT.replace('{{userProfile}}', userProfile)

        const response = await step.ai.infer('generate-welcome-intro', {
            model: step.ai.models.gemini({ model: 'gemini-2.5-flash-lite' }),
            body: {
                contents: [
                    {
                        role: 'user',
                        parts: [
                            { text: prompt }
                        ]
                    }]
            }
        })

        await step.run('send-welcome-email', async () => {
            const part = response.candidates?.[0]?.content?.parts?.[0];
            const introText = (part && 'text' in part ? part.text : null) ||'Thanks for joining Market Pulse. You now have the tools to track markets and make smarter moves.'

            const { data: { email, name } } = event;

            return await sendWelcomeEmail({ email, name, intro: introText });
        })

        return {
            success: true,
            message: 'Welcome email sent successfully'
        }
    }
)

export const sendDailyNewsSummary = inngest.createFunction(
    { id: 'daily-news-summary' },
    [ { event: 'app/send.daily.news' }, { cron: 'TZ=Asia/Kolkata 0 12 * * *' } ],
    async ({ step }) => {
        // Step #1: Get all users for news delivery
        const users = (await step.run('get-all-users', getAllUsersForNewsEmail)) as UserForNewsEmail[];

        if(!users || users.length === 0) return { success: true };

        // Step #1b: Filter to users who have Daily news summary enabled.
        const optedInUsers = await step.run('filter-users-by-email-preferences', async () => {
            await connectToDatabase();

            const userIds = users.map((u) => u.id).filter(Boolean);
            const prefs = await EmailPreferences.find({ userId: { $in: userIds } })
                .select({ userId: 1, receiveDailyNewsSummary: 1 })
                .lean<Array<{ userId?: string; receiveDailyNewsSummary?: boolean }>>();

            const map = new Map<string, boolean>();
            for (const p of prefs || []) {
                if (typeof p.userId === 'string') {
                    map.set(p.userId, p.receiveDailyNewsSummary !== false);
                }
            }

            return users.filter((u) => (map.get(u.id) ?? true) === true);
        }) as UserForNewsEmail[];

        if (!optedInUsers || optedInUsers.length === 0) return { success: true };

        // Step #2: For each user, fetch market news + watchlist news.
        const results = await step.run('fetch-user-news', async () => {
            const perUser: Array<{ user: UserForNewsEmail; market: MarketNewsArticle[]; watchlist: { symbols: string[]; articles: MarketNewsArticle[] } }> = [];

            // Market news is the same for everyone (fetch once per run).
            let marketArticles: MarketNewsArticle[] = [];
            try {
                marketArticles = await getNews(undefined, { maxItems: 6 });
            } catch (e) {
                console.error('daily-news: error fetching market news', e);
                marketArticles = [];
            }

            for (const user of optedInUsers as UserForNewsEmail[]) {
                try {
                    const symbols = await getWatchlistSymbolsByEmail(user.email);
                    const watchlistArticles = symbols.length
                        ? await getNews(symbols, { daysBack: 1, maxRounds: 6 })
                        : [];

                    perUser.push({
                        user,
                        market: marketArticles,
                        watchlist: { symbols, articles: watchlistArticles },
                    });
                } catch (e) {
                    console.error('daily-news: error preparing user watchlist news', user.email, e);
                    perUser.push({ user, market: marketArticles, watchlist: { symbols: [], articles: [] } });
                }
            }

            return perUser;
        }) as Array<{ user: UserForNewsEmail; market: MarketNewsArticle[]; watchlist: { symbols: string[]; articles: MarketNewsArticle[] } }>;

        const buildFallbackHtml = (args: {
            userName: string;
            market: MarketNewsArticle[];
            watchlistSymbols: string[];
            watchlist: MarketNewsArticle[];
        }): string => {
            const { userName, market, watchlistSymbols, watchlist } = args;

            const safe = (s: string) =>
                String(s)
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
                    .replace(/\"/g, "&quot;")
                    .replace(/'/g, "&#39;");

            const intro = `<p class="mobile-text dark-text-secondary" style="margin: 0 0 20px 0; font-size: 16px; line-height: 1.6; color: #CCDADC;">Hi <strong style="color: #CCDADC;">${safe(userName)}</strong>, here are the latest headlines — plus updates related to your watchlist.</p>`;

            const renderArticles = (articles: MarketNewsArticle[], max: number) =>
                articles.slice(0, max).map((a) => {
                    const symbolLine = a.relatedSymbol
                        ? `<p class="mobile-text dark-text-secondary" style="margin: 0 0 12px 0; font-size: 14px; line-height: 1.5; color: #CCDADC;">Related: <strong style="color: #FDD458;">${safe(a.relatedSymbol)}</strong></p>`
                        : "";
                    return `
<div class="dark-info-box" style="background-color: #212328; padding: 24px; margin: 20px 0; border-radius: 8px;">
  <h4 class="dark-text" style="margin: 0 0 16px 0; font-size: 18px; font-weight: 600; color: #FFFFFF; line-height: 1.4;">${safe(a.headline)}</h4>
  ${symbolLine}
  <p class="dark-text-secondary" style="margin: 0 0 20px 0; font-size: 16px; line-height: 1.6; color: #CCDADC;">${safe(a.summary)}</p>
  <div style="background-color: #141414; border: 1px solid #374151; padding: 15px; border-radius: 6px; margin: 16px 0;">
    <p class="dark-text-secondary" style="margin: 0; font-size: 14px; color: #CCDADC; line-height: 1.4;">💡 <strong style="color: #FDD458;">Bottom Line:</strong> Open the story to see the full context and how it could affect investors.</p>
  </div>
  <div style="margin: 20px 0 0 0;">
    <a href="${safe(a.url)}" style="color: #FDD458; text-decoration: none; font-weight: 500; font-size: 14px;" target="_blank" rel="noopener noreferrer">Read Full Story →</a>
  </div>
</div>`;
                }).join("");

            const marketSection = market?.length
                ? `<h3 class="mobile-news-title dark-text" style="margin: 30px 0 15px 0; font-size: 18px; font-weight: 600; color: #f8f9fa; line-height: 1.3;">📊 Market Highlights</h3>${renderArticles(market, 4)}`
                : `<h3 class="mobile-news-title dark-text" style="margin: 30px 0 15px 0; font-size: 18px; font-weight: 600; color: #f8f9fa; line-height: 1.3;">📊 Market Highlights</h3><p class="mobile-text dark-text-secondary" style="margin: 0 0 20px 0; font-size: 16px; line-height: 1.6; color: #CCDADC;">No market headlines available right now.</p>`;

            const watchlistHeader = `<h3 class="mobile-news-title dark-text" style="margin: 30px 0 15px 0; font-size: 18px; font-weight: 600; color: #f8f9fa; line-height: 1.3;">⭐ Your Watchlist News</h3>`;

            const watchlistBody = watchlistSymbols.length === 0
                ? `<p class="mobile-text dark-text-secondary" style="margin: 0 0 20px 0; font-size: 16px; line-height: 1.6; color: #CCDADC;">Your watchlist is empty — add stocks in Market Pulse to get watchlist news here.</p>`
                : watchlist?.length
                    ? renderArticles(watchlist, 6)
                    : `<p class="mobile-text dark-text-secondary" style="margin: 0 0 20px 0; font-size: 16px; line-height: 1.6; color: #CCDADC;">No fresh headlines found for your watchlist in the last 24 hours.</p>`;

            return `${intro}${marketSection}<div style="border-top: 1px solid #374151; margin: 32px 0 24px 0;"></div>${watchlistHeader}${watchlistBody}`;
        };

        // Step #3: Summarize news via AI (single combined email content per user)
        const userNewsSummaries: Array<{ user: UserForNewsEmail; newsContent: string }> = [];

        const withTimeout = async <T,>(promise: Promise<T>, ms: number): Promise<T> => {
            return await Promise.race([
                promise,
                new Promise<T>((_, reject) => {
                    setTimeout(() => reject(new Error(`Timed out after ${ms}ms`)), ms);
                }),
            ]);
        };

        const summarizeOneUser = async (args: { user: UserForNewsEmail; market: MarketNewsArticle[]; watchlist: { symbols: string[]; articles: MarketNewsArticle[] } }) => {
            const { user, market, watchlist } = args;
            try {
                // Avoid pretty JSON (wastes tokens/time). Keep payload compact.
                const prompt = NEWS_SUMMARY_WITH_WATCHLIST_EMAIL_PROMPT
                    .replace('{{userName}}', user.name)
                    .replace('{{marketNewsData}}', JSON.stringify(market ?? []))
                    .replace('{{watchlistSymbols}}', JSON.stringify(watchlist?.symbols ?? []))
                    .replace('{{watchlistNewsData}}', JSON.stringify(watchlist?.articles ?? []));

                const inferPromise = step.ai.infer(`summarize-news-${user.email}`, {
                    model: step.ai.models.gemini({ model: 'gemini-2.5-flash-lite' }),
                    body: {
                        contents: [{ role: 'user', parts: [{ text: prompt }] }]
                    }
                });

                const response = await withTimeout(inferPromise, 25_000);

                const part = response.candidates?.[0]?.content?.parts?.[0];
                const aiHtml = (part && 'text' in part ? part.text : null);
                const newsContent = (typeof aiHtml === 'string' && aiHtml.trim().length > 0)
                    ? aiHtml
                    : buildFallbackHtml({
                    userName: user.name,
                    market: market ?? [],
                    watchlistSymbols: watchlist?.symbols ?? [],
                    watchlist: watchlist?.articles ?? [],
                });

                return { user, newsContent };
            } catch (err) {
                console.error('Failed to summarize news for:', user.email, err);
                return {
                    user,
                    newsContent: buildFallbackHtml({
                        userName: user.name,
                        market: args.market ?? [],
                        watchlistSymbols: args.watchlist?.symbols ?? [],
                        watchlist: args.watchlist?.articles ?? [],
                    }),
                };
            }
        };

        // Concurrency limit: keep the run fast without overwhelming the AI provider.
        const concurrency = 3;
        for (let i = 0; i < results.length; i += concurrency) {
            const chunk = results.slice(i, i + concurrency);
            const summarized = await Promise.all(chunk.map((r) => summarizeOneUser(r)));
            userNewsSummaries.push(...summarized);
        }

        // Step #4: Send the emails
        await step.run('send-news-emails', async () => {
            const date = formatDateTodayUtc();

            const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));
            const sendWithRetries = async (args: { email: string; date: string; newsContent: string }) => {
                const delays = [0, 750, 1500];
                let lastErr: unknown = null;
                for (let i = 0; i < delays.length; i++) {
                    try {
                        if (delays[i] > 0) await delay(delays[i]);
                        await sendNewsSummaryEmail(args);
                        return;
                    } catch (e) {
                        lastErr = e;
                    }
                }
                throw lastErr instanceof Error ? lastErr : new Error('Failed to send news email');
            };

            await Promise.all(
                userNewsSummaries.map(async ({ user, newsContent}) => {
                    const safeContent = (typeof newsContent === 'string' && newsContent.trim().length > 0)
                        ? newsContent
                        : buildFallbackHtml({ userName: user.name, market: [], watchlistSymbols: [], watchlist: [] });
                    try {
                        await sendWithRetries({ email: user.email, date, newsContent: safeContent });
                    } catch (err) {
                        console.error('Failed to send news email for:', user.email, err);
                    }
                })
            );
        });

        return { success: true };
    }
)

// ============================================
// DAILY TRADING INSIGHTS - 10 AM IST (Indian Market)
// ============================================

export const sendDailyTradingInsights = inngest.createFunction(
    { id: 'daily-trading-insights' },
    [{ event: 'app/send.daily.insights' }, { cron: 'TZ=Asia/Kolkata 45 9 * * 1-5' }],
    async ({ step }) => {
        // Step #1: Get all users for insights delivery
        const users = (await step.run('get-all-users', getAllUsersForNewsEmail)) as UserForNewsEmail[];

        if (!users || users.length === 0) return { success: true };

        // Step #1b: Filter to users who have opted in for trading insights
        const optedInUsers = await step.run('filter-users-by-email-preferences', async () => {
            await connectToDatabase();

            const userIds = users.map((u) => u.id).filter(Boolean);
            const prefs = await EmailPreferences.find({ userId: { $in: userIds } })
                .select({ userId: 1, receiveDailyNewsSummary: 1 })
                .lean<Array<{ userId?: string; receiveDailyNewsSummary?: boolean }>>();

            const map = new Map<string, boolean>();
            for (const p of prefs || []) {
                if (typeof p.userId === 'string') {
                    map.set(p.userId, p.receiveDailyNewsSummary !== false);
                }
            }

            return users.filter((u) => (map.get(u.id) ?? true) === true);
        }) as UserForNewsEmail[];

        if (!optedInUsers || optedInUsers.length === 0) return { success: true };

        // Step #2: Fetch Indian market analysis data
        const marketData = await step.run('fetch-indian-market-data', async () => {
            try {
                const scopeData = await getStrongMoneyScope('IN', 20);
                return scopeData;
            } catch (e) {
                console.error('daily-insights: error fetching market data', e);
                return null;
            }
        }) as MarketScopeResult | null;

        if (!marketData) {
            console.error('daily-insights: no market data available');
            return { success: false, error: 'No market data available' };
        }

        // Step #3: Process market data to extract insights
        const insights = await step.run('process-market-insights', () => {
            // Get all stocks from all sectors
            const allStocks: StockAnalysis[] = marketData.sectors.flatMap(s => s.stocks);
            
            // Sort sectors by institutional activity (strongMoneyIntensity)
            const sortedSectorsByBuying = [...marketData.heatmap]
                .filter(s => s.strongMoneyIntensity > 0)
                .sort((a, b) => b.strongMoneyIntensity - a.strongMoneyIntensity)
                .slice(0, 3);
            
            const sortedSectorsBySelling = [...marketData.heatmap]
                .filter(s => s.strongMoneyIntensity < 0)
                .sort((a, b) => a.strongMoneyIntensity - b.strongMoneyIntensity)
                .slice(0, 3);
            
            // Get stocks with highest bullish probability (high R-Factor + Buying signal + Bullish intraday)
            const bullishStocks = allStocks
                .filter(s => s.strongMoneySignal === 'Buying' && s.intradayTrend === 'Bullish')
                .sort((a, b) => {
                    // Score based on R-Factor and strongMoneyScore
                    const scoreA = a.rFactor * 0.6 + a.strongMoneyScore * 10;
                    const scoreB = b.rFactor * 0.6 + b.strongMoneyScore * 10;
                    return scoreB - scoreA;
                })
                .slice(0, 5);
            
            // Get stocks with highest bearish probability (low R-Factor + Selling signal + Bearish intraday)
            const bearishStocks = allStocks
                .filter(s => s.strongMoneySignal === 'Selling' || s.intradayTrend === 'Bearish')
                .sort((a, b) => {
                    // Lower R-Factor = more bearish, lower strongMoneyScore = more selling
                    const scoreA = (100 - a.rFactor) * 0.6 + Math.abs(Math.min(0, a.strongMoneyScore)) * 10;
                    const scoreB = (100 - b.rFactor) * 0.6 + Math.abs(Math.min(0, b.strongMoneyScore)) * 10;
                    return scoreB - scoreA;
                })
                .slice(0, 5);
            
            // Top 3 options trading picks (combine both directions based on market sentiment)
            const optionsPicks: Array<StockAnalysis & { direction: 'BULLISH' | 'BEARISH'; reason: string }> = [];
            
            // If market is bullish, prioritize bullish stocks for CALL options
            // If market is bearish, prioritize bearish stocks for PUT options
            const isBullishMarket = marketData.marketSentiment === 'Bullish' || marketData.marketADRatio > 1;
            
            if (isBullishMarket) {
                // 2 bullish picks + 1 bearish for hedging
                bullishStocks.slice(0, 2).forEach(s => {
                    optionsPicks.push({
                        ...s,
                        direction: 'BULLISH',
                        reason: `Strong R-Factor (${s.rFactor.toFixed(0)}) with institutional buying. Consider CALL options.`
                    });
                });
                if (bearishStocks.length > 0) {
                    optionsPicks.push({
                        ...bearishStocks[0],
                        direction: 'BEARISH',
                        reason: `Weak momentum (R: ${bearishStocks[0].rFactor.toFixed(0)}) with selling pressure. Consider PUT options for hedging.`
                    });
                }
            } else {
                // 2 bearish picks + 1 bullish for recovery plays
                bearishStocks.slice(0, 2).forEach(s => {
                    optionsPicks.push({
                        ...s,
                        direction: 'BEARISH',
                        reason: `Weak R-Factor (${s.rFactor.toFixed(0)}) with institutional selling. Consider PUT options.`
                    });
                });
                if (bullishStocks.length > 0) {
                    optionsPicks.push({
                        ...bullishStocks[0],
                        direction: 'BULLISH',
                        reason: `Strong momentum (R: ${bullishStocks[0].rFactor.toFixed(0)}) despite weak market. Consider CALL options for recovery play.`
                    });
                }
            }
            
            return {
                marketSentiment: marketData.marketSentiment,
                marketADRatio: marketData.marketADRatio,
                topBuyingSectors: sortedSectorsByBuying,
                topSellingSectors: sortedSectorsBySelling,
                bullishStocks,
                bearishStocks,
                optionsPicks: optionsPicks.slice(0, 3),
                isBullishMarket
            };
        });

        // Step #4: Build fallback HTML content
        const buildFallbackInsightsHtml = (args: {
            userName: string;
            insights: typeof insights;
        }): string => {
            const { userName, insights: ins } = args;
            
            // Determine sentiment color
            const getSentimentColor = (sentiment: string): string => {
                if (sentiment === 'Bullish') return '#22c55e';
                if (sentiment === 'Bearish') return '#ef4444';
                return '#f59e0b';
            };
            const sentimentColor = getSentimentColor(ins.marketSentiment);
            const dominantDirection = ins.isBullishMarket ? 'UPWARD' : 'DOWNWARD';
            const dominantColor = ins.isBullishMarket ? '#22c55e' : '#ef4444';
            
            // Market Overview
            const marketOverview = `
<div style="background-color: #212328; padding: 20px; margin: 0 0 24px 0; border-radius: 8px; border-left: 4px solid ${sentimentColor};">
  <h3 style="margin: 0 0 12px 0; font-size: 16px; font-weight: 600; color: #FFFFFF;">📊 Market Pulse</h3>
  <p style="margin: 0; font-size: 15px; color: #CCDADC; line-height: 1.5;">
    Hi <strong style="color: #CCDADC;">${userName}</strong>, the Indian market is showing <strong style="color: ${sentimentColor};">${ins.marketSentiment}</strong> sentiment today with an A/D ratio of ${ins.marketADRatio.toFixed(2)}. 
    ${ins.isBullishMarket ? 'Buyers are in control - look for long opportunities.' : 'Sellers are dominating - consider defensive positions or short plays.'}
  </p>
</div>`;

            // Institutional Activity
            const buyingSectorsHtml = ins.topBuyingSectors.length > 0
                ? ins.topBuyingSectors.map((s: SectorHeatmapData) => `<p style="margin: 0 0 8px 0; font-size: 13px; color: #CCDADC;">• <strong style="color: #22c55e;">${s.sector}</strong> (${s.buyingStocks} stocks)</p>`).join('')
                : '<p style="margin: 0; font-size: 13px; color: #9ca3af;">No significant buying detected</p>';
            
            const sellingSectorsHtml = ins.topSellingSectors.length > 0
                ? ins.topSellingSectors.map((s: SectorHeatmapData) => `<p style="margin: 0 0 8px 0; font-size: 13px; color: #CCDADC;">• <strong style="color: #ef4444;">${s.sector}</strong> (${s.sellingStocks} stocks)</p>`).join('')
                : '<p style="margin: 0; font-size: 13px; color: #9ca3af;">No significant selling detected</p>';

            const institutionalActivity = `
<h3 style="margin: 24px 0 15px 0; font-size: 18px; font-weight: 600; color: #FDD458; line-height: 1.3;">🏛️ Institutional Money Flow</h3>
<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin: 0 0 24px 0;">
  <tr>
    <td style="width: 48%; vertical-align: top; padding-right: 2%;">
      <div style="background-color: #0d2818; border: 1px solid #22c55e; border-radius: 8px; padding: 16px;">
        <h4 style="margin: 0 0 12px 0; font-size: 14px; font-weight: 600; color: #22c55e;">📈 Top Buying Sectors</h4>
        ${buyingSectorsHtml}
      </div>
    </td>
    <td style="width: 48%; vertical-align: top; padding-left: 2%;">
      <div style="background-color: #2d1215; border: 1px solid #ef4444; border-radius: 8px; padding: 16px;">
        <h4 style="margin: 0 0 12px 0; font-size: 14px; font-weight: 600; color: #ef4444;">📉 Top Selling Sectors</h4>
        ${sellingSectorsHtml}
      </div>
    </td>
  </tr>
</table>`;

            // High Probability Stocks
            const bullishStocksHtml = ins.bullishStocks.length > 0
                ? ins.bullishStocks.map((s: StockAnalysis) => `<p style="margin: 0 0 8px 0; font-size: 13px; color: #CCDADC;">• <strong style="color: #22c55e;">${s.symbol}</strong> (R: ${s.rFactor.toFixed(0)}) - ${s.reasons.slice(0, 2).join(', ')}</p>`).join('')
                : '<p style="margin: 0; font-size: 13px; color: #9ca3af;">No strong bullish signals detected</p>';
            
            const bearishStocksHtml = ins.bearishStocks.length > 0
                ? ins.bearishStocks.map((s: StockAnalysis) => `<p style="margin: 0 0 8px 0; font-size: 13px; color: #CCDADC;">• <strong style="color: #ef4444;">${s.symbol}</strong> (R: ${s.rFactor.toFixed(0)}) - ${s.reasons.slice(0, 2).join(', ')}</p>`).join('')
                : '<p style="margin: 0; font-size: 13px; color: #9ca3af;">No strong bearish signals detected</p>';

            const highProbabilityStocks = `
<h3 style="margin: 24px 0 15px 0; font-size: 18px; font-weight: 600; color: #FDD458; line-height: 1.3;">🎯 High Probability Movers</h3>
<p style="margin: 0 0 16px 0; font-size: 14px; color: #9ca3af;">
  Based on current market conditions, <strong style="color: ${dominantColor};">${dominantDirection} moves are more probable today</strong>.
</p>
<div style="background-color: #0d2818; border: 1px solid #22c55e; border-radius: 8px; padding: 16px; margin: 0 0 16px 0;">
  <h4 style="margin: 0 0 12px 0; font-size: 15px; font-weight: 600; color: #22c55e;">🚀 Likely to Go UP</h4>
  ${bullishStocksHtml}
</div>
<div style="background-color: #2d1215; border: 1px solid #ef4444; border-radius: 8px; padding: 16px; margin: 0 0 16px 0;">
  <h4 style="margin: 0 0 12px 0; font-size: 15px; font-weight: 600; color: #ef4444;">⚠️ Likely to Go DOWN</h4>
  ${bearishStocksHtml}
</div>`;

            // Options Trading Picks
            const optionsPicksHtml = ins.optionsPicks.map((s: StockAnalysis & { direction: 'BULLISH' | 'BEARISH'; reason: string }) => {
                const directionBg = s.direction === 'BULLISH' ? '#0d2818' : '#2d1215';
                const directionColor = s.direction === 'BULLISH' ? '#22c55e' : '#ef4444';
                const directionLabel = s.direction === 'BULLISH' ? '📈 BULLISH' : '📉 BEARISH';
                
                return `
<div style="background-color: #212328; padding: 16px; margin: 0 0 12px 0; border-radius: 8px;">
  <div style="margin: 0 0 8px 0;">
    <span style="font-size: 16px; font-weight: 600; color: #FDD458;">${s.symbol}</span>
    <span style="font-size: 12px; padding: 4px 8px; border-radius: 4px; background-color: ${directionBg}; color: ${directionColor}; margin-left: 8px;">${directionLabel}</span>
  </div>
  <p style="margin: 0 0 8px 0; font-size: 14px; color: #CCDADC;">${s.name}</p>
  <p style="margin: 0; font-size: 13px; color: #9ca3af;">${s.reason}</p>
</div>`;
            }).join('');

            const optionsPicks = `
<h3 style="margin: 24px 0 15px 0; font-size: 18px; font-weight: 600; color: #FDD458; line-height: 1.3;">⚡ Today's Options Trading Picks</h3>
<p style="margin: 0 0 16px 0; font-size: 14px; color: #9ca3af;">
  Top 3 stocks combining technical and institutional analysis for potential options plays.
</p>
${optionsPicksHtml || '<p style="margin: 0; font-size: 13px; color: #9ca3af;">No strong options candidates identified today.</p>'}`;

            return `${marketOverview}${institutionalActivity}${highProbabilityStocks}${optionsPicks}`;
        };

        // Step #5: Generate AI-enhanced content for each user (or use fallback)
        const userInsightsSummaries: Array<{ user: UserForNewsEmail; insightsContent: string }> = [];

        const withTimeout = async <T,>(promise: Promise<T>, ms: number): Promise<T> => {
            return await Promise.race([
                promise,
                new Promise<T>((_, reject) => {
                    setTimeout(() => reject(new Error(`Timed out after ${ms}ms`)), ms);
                }),
            ]);
        };

        const formatDateToday = (): string => {
            const now = new Date();
            return now.toLocaleDateString('en-IN', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric',
            });
        };

        const dateStr = formatDateToday();

        const summarizeInsightsForUser = async (user: UserForNewsEmail) => {
            try {
                const prompt = DAILY_TRADING_INSIGHTS_EMAIL_PROMPT
                    .replace('{{userName}}', user.name)
                    .replace('{{date}}', dateStr)
                    .replace('{{marketSentiment}}', insights.marketSentiment)
                    .replace('{{marketADRatio}}', insights.marketADRatio.toFixed(2))
                    .replace('{{topBuyingSectors}}', JSON.stringify(insights.topBuyingSectors.map((s: SectorHeatmapData) => ({ sector: s.sector, buyingStocks: s.buyingStocks, intensity: s.strongMoneyIntensity }))))
                    .replace('{{topSellingSectors}}', JSON.stringify(insights.topSellingSectors.map((s: SectorHeatmapData) => ({ sector: s.sector, sellingStocks: s.sellingStocks, intensity: s.strongMoneyIntensity }))))
                    .replace('{{bullishStocks}}', JSON.stringify(insights.bullishStocks.map((s: StockAnalysis) => ({ symbol: s.symbol, name: s.name, rFactor: s.rFactor, reasons: s.reasons, changePercent: s.changePercent }))))
                    .replace('{{bearishStocks}}', JSON.stringify(insights.bearishStocks.map((s: StockAnalysis) => ({ symbol: s.symbol, name: s.name, rFactor: s.rFactor, reasons: s.reasons, changePercent: s.changePercent }))))
                    .replace('{{optionsPicks}}', JSON.stringify(insights.optionsPicks.map((s: StockAnalysis & { direction: string; reason: string }) => ({ symbol: s.symbol, name: s.name, direction: s.direction, reason: s.reason, rFactor: s.rFactor }))));

                const inferPromise = step.ai.infer(`summarize-insights-${user.email}`, {
                    model: step.ai.models.gemini({ model: 'gemini-2.5-flash-lite' }),
                    body: {
                        contents: [{ role: 'user', parts: [{ text: prompt }] }]
                    }
                });

                const response = await withTimeout(inferPromise, 30_000);

                const part = response.candidates?.[0]?.content?.parts?.[0];
                const aiHtml = (part && 'text' in part ? part.text : null);
                const insightsContent = (typeof aiHtml === 'string' && aiHtml.trim().length > 0)
                    ? aiHtml
                    : buildFallbackInsightsHtml({ userName: user.name, insights });

                return { user, insightsContent };
            } catch (err) {
                console.error('Failed to generate insights for:', user.email, err);
                return {
                    user,
                    insightsContent: buildFallbackInsightsHtml({ userName: user.name, insights }),
                };
            }
        };

        // Process users with concurrency limit
        const concurrency = 3;
        for (let i = 0; i < optedInUsers.length; i += concurrency) {
            const chunk = optedInUsers.slice(i, i + concurrency);
            const summarized = await Promise.all(chunk.map((user) => summarizeInsightsForUser(user)));
            userInsightsSummaries.push(...summarized);
        }

        // Step #6: Send the emails
        await step.run('send-insights-emails', async () => {
            const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));
            const sendWithRetries = async (args: { email: string; date: string; insightsContent: string }) => {
                const delays = [0, 750, 1500];
                let lastErr: unknown = null;
                for (let i = 0; i < delays.length; i++) {
                    try {
                        if (delays[i] > 0) await delay(delays[i]);
                        await sendDailyTradingInsightsEmail(args);
                        return;
                    } catch (e) {
                        lastErr = e;
                    }
                }
                throw lastErr instanceof Error ? lastErr : new Error('Failed to send insights email');
            };

            await Promise.all(
                userInsightsSummaries.map(async ({ user, insightsContent }) => {
                    const safeContent = (typeof insightsContent === 'string' && insightsContent.trim().length > 0)
                        ? insightsContent
                        : buildFallbackInsightsHtml({ userName: user.name, insights });
                    try {
                        await sendWithRetries({ email: user.email, date: dateStr, insightsContent: safeContent });
                    } catch (err) {
                        console.error('Failed to send insights email for:', user.email, err);
                    }
                })
            );
        });

        return { success: true };
    }
)