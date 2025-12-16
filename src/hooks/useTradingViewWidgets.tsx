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