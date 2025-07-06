from datetime import datetime
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, JsonCssExtractionStrategy, CrawlerRunConfig, LXMLWebScrapingStrategy
from playwright.async_api import BrowserContext, Page, Route
from crawl.util import DetailResult, browser_blacklist_url_keys, filter_links, generate_extraction_schema
from log.logger import crawl_logger
from trafilatura import extract, extract_metadata

browser_config = BrowserConfig(
    headless=True,
    viewport_width=1920,
    viewport_height=1080,
    verbose=True,
)

PAGE_TIMEOUT = 20000

run_config = CrawlerRunConfig(
    scraping_strategy=LXMLWebScrapingStrategy(),
    cache_mode=CacheMode.DISABLED,
    page_timeout=PAGE_TIMEOUT,
    delay_before_return_html=4,
    # magic=True,
)

# 爬取列表页
async def crawl_list_using_browser(url: str, rule: list[str]) -> dict[str, str]:
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # 设置过滤无用资源请求
        crawler.crawler_strategy.set_hook("on_page_context_created", on_page_context_created)

        # 设置提取规则
        schema = generate_extraction_schema(rule)
        run_config.extraction_strategy = JsonCssExtractionStrategy(schema=schema)

        result = await crawler.arun(url, config=run_config)
        if result.success:
            try:
                page_urls = json.loads(result.extracted_content)
                return filter_links(url, page_urls)
            except Exception as e:
                crawl_logger.error(f"CrawlList extract failed: {url} {e}")
        else:
            crawl_logger.error(f"CrawlList failed: {url} {result.error_message}")
        return {}


# 爬取详情页
async def crawl_detail_using_browser(url: str) -> DetailResult:
    async with AsyncWebCrawler(config=browser_config) as crawler:
        crawler.crawler_strategy.set_hook("on_page_context_created", on_page_context_created)
        result = await crawler.arun(url, config=run_config)
        if result.success:
            content = extract(result.html)
            metadata = extract_metadata(result.html)
            return DetailResult(content=str(content), date=metadata.date or datetime.now().strftime("%Y-%m-%d"))
        else:
            crawl_logger.error(f"CrawlDetail failed: {url} {result.error_message}")
            return DetailResult(content="", date="")


# 过滤无用资源请求
async def on_page_context_created(page: Page, context: BrowserContext, **kwargs):
    async def route_filter(route: Route):
        if route.request.resource_type in ["image", "stylesheet", "font", "media"] \
            or any(url_key in route.request.url for url_key in browser_blacklist_url_keys): # 过滤无用资源请求
            crawl_logger.debug(f"Blocking request: {route.request.url}")
            await route.abort()
        else:
            crawl_logger.debug(f"Allowing request: {route.request.url}")
            await route.continue_()

    await context.route("**", route_filter)