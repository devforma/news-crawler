from dataclasses import dataclass
import json
from crawl4ai import (
    AsyncWebCrawler,
    CacheMode,
    HTTPCrawlerConfig,
    JsonCssExtractionStrategy,
    CrawlerRunConfig,
    LXMLWebScrapingStrategy,
)
from crawl4ai.async_crawler_strategy import AsyncHTTPCrawlerStrategy
from crawl.util import filter_links, generate_extraction_schema
from log.logger import crawl_logger
from trafilatura import extract, extract_metadata

http_crawler_config = HTTPCrawlerConfig(
    method="GET",
    headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"},
    follow_redirects=True,
    verify_ssl=False,
)

PAGE_TIMEOUT = 20000

run_config = CrawlerRunConfig(
    scraping_strategy=LXMLWebScrapingStrategy(),
    cache_mode=CacheMode.DISABLED,
    page_timeout=PAGE_TIMEOUT,
    magic=True,
)


# 爬取列表页
async def crawl_list_using_http(url: str, rule: list[str]) -> dict[str, str]:
    async with AsyncWebCrawler(crawler_strategy=AsyncHTTPCrawlerStrategy(browser_config=http_crawler_config)) as crawler:

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


@dataclass
class DetailResult:
    content: str
    date: str


async def crawl_detail_using_http(url: str) -> DetailResult:
    async with AsyncWebCrawler(crawler_strategy=AsyncHTTPCrawlerStrategy(browser_config=http_crawler_config)) as crawler:
        result = await crawler.arun(url, config=run_config)
        if result.success:
            content = extract(result.html)
            metadata = extract_metadata(result.html)
            return DetailResult(content=content, date=metadata.date or "")
        else:
            crawl_logger.error(f"CrawlDetail failed: {url} {result.error_message}")
            return DetailResult(content="", date="")