import { useEffect, useRef } from 'react';

const useTradingViewWidgets = (scriptURL:string, config:Record<string, unknown>, height = 600) => {
    const containerRef = useRef<HTMLDivElement |null>(null);
      useEffect(() => {
            const element = containerRef.current;
            if(!element) return;
            if(element.dataset.loaded) return;

            element.innerHTML = `<div class="tradingview-widget-container__widget" style="height: ${height}px;"></div>`;

            const script = document.createElement("script");
            script.src = scriptURL;
            script.async = true;
            script.innerHTML = JSON.stringify(config);

            script.onerror = () => {
                // Network blocks/adblockers can prevent TradingView scripts from loading.
                // Keep the rest of the page functional and allow retries.
                element.innerHTML = `
                  <div style="height:${height}px;display:flex;align-items:center;justify-content:center;padding:16px;text-align:center;" class="text-muted-foreground">
                    <div>
                      <div style="font-weight:600;">Widget failed to load</div>
                      <div style="font-size:12px;margin-top:6px;">Your network may be blocking TradingView embeds (net::ERR_CONNECTION_RESET).</div>
                    </div>
                  </div>
                `;
                delete element.dataset.loaded;
            };

            element.appendChild(script);
            element.dataset.loaded = "true";

            return () => {
                element.innerHTML = "";
                delete element.dataset.loaded;
            }
        }, [scriptURL, config, height]
      );
    return containerRef;
}

export default useTradingViewWidgets;