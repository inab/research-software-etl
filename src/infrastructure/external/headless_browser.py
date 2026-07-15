from __future__ import annotations

import logging

from playwright.async_api import async_playwright

logger = logging.getLogger("rs-etl-pipeline")


class HeadlessBrowserFetcher:
    """
    Renders a page in headless Chrome and returns its HTML.

    Link enrichment needs the *rendered* page: many tool homepages build their
    content with JavaScript, and several sit behind a Cloudflare interstitial that
    a plain GET never gets past. That makes this a transport concern like any other
    client here -- the service that reads the HTML should not be driving a browser.
    """

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/118.0.5993.90 Safari/537.36"
    )

    def __init__(self, page_timeout: int = 60000, settle_ms: int = 8000) -> None:
        self.page_timeout = page_timeout
        self.settle_ms = settle_ms

    async def fetch(self, url: str) -> str | None:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    channel="chrome",
                    args=[
                        "--proxy-bypass-list=<-loopback>",
                        "--dns-prefetch-disable",
                    ],
                )

                context = await browser.new_context(
                    user_agent=self.USER_AGENT,
                    locale="en-US",
                    viewport={"width": 1366, "height": 768},
                )

                page = await context.new_page()
                response = await page.goto(
                    url, wait_until="networkidle", timeout=self.page_timeout
                )
                await page.wait_for_timeout(self.settle_ms)

                content = await page.content()
                status = response.status if response else None

                logger.debug(f"Fetched {url} -> {status} (final URL: {page.url})")

                await browser.close()

                if (
                    "Just a moment" in content
                    or "Enable JavaScript and cookies to continue" in content
                ):
                    logger.warning(f"Cloudflare challenge not bypassed for {url}")
                    return None

                return content

        except Exception as e:
            logger.warning(f"Headless fetch failed for {url}: {e}")
            return None
