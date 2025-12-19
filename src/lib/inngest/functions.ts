import {inngest} from "@/lib/inngest/client";
import {PERSONALIZED_WELCOME_EMAIL_PROMPT} from "@/lib/inngest/prompts";
import { NEWS_SUMMARY_WITH_WATCHLIST_EMAIL_PROMPT } from "@/lib/inngest/prompts";
import { sendNewsSummaryEmail, sendWelcomeEmail } from "@/lib/nodemailer";
import { getAllUsersForNewsEmail } from "@/lib/actions/user.action";
import { getWatchlistSymbolsByEmail } from "@/lib/actions/watchlist.actions";
import { getNews, type MarketNewsArticle } from "@/lib/actions/finnhub.actions";

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

            for (const user of users as UserForNewsEmail[]) {
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
        }): string | null => {
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
        const userNewsSummaries: Array<{ user: UserForNewsEmail; newsContent: string | null}> = [];

        for (const { user, market, watchlist } of results) {
            try {
                const prompt = NEWS_SUMMARY_WITH_WATCHLIST_EMAIL_PROMPT
                    .replace('{{userName}}', user.name)
                    .replace('{{marketNewsData}}', JSON.stringify(market ?? [], null, 2))
                    .replace('{{watchlistSymbols}}', JSON.stringify(watchlist?.symbols ?? [], null, 2))
                    .replace('{{watchlistNewsData}}', JSON.stringify(watchlist?.articles ?? [], null, 2));

                const response = await step.ai.infer(`summarize-news-${user.email}`, {
                    model: step.ai.models.gemini({ model: 'gemini-2.5-flash-lite' }),
                    body: {
                        contents: [{ role: 'user', parts: [{ text:prompt }]}]
                    }
                });

                const part = response.candidates?.[0]?.content?.parts?.[0];
                const aiHtml = (part && 'text' in part ? part.text : null);
                const newsContent = aiHtml || buildFallbackHtml({
                    userName: user.name,
                    market: market ?? [],
                    watchlistSymbols: watchlist?.symbols ?? [],
                    watchlist: watchlist?.articles ?? [],
                });

                userNewsSummaries.push({ user, newsContent });
            } catch (err) {
                console.error('Failed to summarize news for:', user.email, err);
                userNewsSummaries.push({
                    user,
                    newsContent: buildFallbackHtml({
                        userName: user.name,
                        market: market ?? [],
                        watchlistSymbols: watchlist?.symbols ?? [],
                        watchlist: watchlist?.articles ?? [],
                    }),
                });
            }
        }

        // Step #4: Send the emails
        await step.run('send-news-emails', async () => {
            const date = formatDateTodayUtc();

            await Promise.all(
                userNewsSummaries.map(async ({ user, newsContent}) => {
                    if(!newsContent) return;
                    try {
                        await sendNewsSummaryEmail({ email: user.email, date, newsContent });
                    } catch (err) {
                        console.error('Failed to send news email for:', user.email, err);
                    }
                })
            );
        });

        return { success: true };
    }
)