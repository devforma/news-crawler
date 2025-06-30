import asyncio

from nats.aio.subscription import Subscription
from crawl.util import duplicate_url
from database.models import CrawlType
from pubsub.connection import QUEUE_CRAWL_DETAILPAGE, QUEUE_CRAWL_LISTPAGE, QUEUE_CRAWL_PAGECONTENT, MsgQueue
from pubsub.msg import CrawlDetailPageMsg, CrawlListPageMsg, CrawlPageContentMsg
from settings import Settings
from crawl.browser import crawl_detail_using_browser, crawl_list_using_browser
from crawl.http import crawl_detail_using_http, crawl_list_using_http
from crawl.json import crawl_list_using_json
from log.logger import crawl_logger
from util.http import HttpClient

settings = Settings()

async def main():
    try:
        # 初始化http连接器
        await HttpClient.init(conn_limit=10, conn_limit_per_host=10, timeout=10)

        # 初始化消息队列
        await MsgQueue.init(settings)

        # 订阅列表页
        list_sub = await MsgQueue.subscribe(subject=QUEUE_CRAWL_LISTPAGE, worker_mode=True)

        # 订阅正文页
        detail_sub = await MsgQueue.subscribe(subject=QUEUE_CRAWL_DETAILPAGE, worker_mode=True)

        # 启动消费任务
        await asyncio.gather(
            crawl_list_page_loop(list_sub),
            crawl_detail_page_loop(detail_sub),
        )
    except Exception as e:
        crawl_logger.error(f"Main loop error: {e}")
    finally:
        await MsgQueue.close()

# 爬取列表页
async def crawl_list_page_loop(list_sub: Subscription):
    async for msg in list_sub.messages:
        try:
            msg = CrawlListPageMsg.model_validate_json(msg.data.decode("utf-8"))
            detail_msgs = await crawl_list(msg)
            for detail_msg in detail_msgs:
                await MsgQueue.publish(subject=QUEUE_CRAWL_DETAILPAGE, msg=detail_msg)
        except Exception as e:
            crawl_logger.error(f"CrawlList loop error: {e}")

# 爬取正文页
async def crawl_detail_page_loop(detail_sub: Subscription):
    async for msg in detail_sub.messages:
        try:
            msg = CrawlDetailPageMsg.model_validate_json(msg.data.decode("utf-8"))
            content_msg = await crawl_detail(msg)
            await MsgQueue.publish(subject=QUEUE_CRAWL_PAGECONTENT, msg=content_msg)
        except Exception as e:
            crawl_logger.error(f"CrawlDetail loop error: {e}")

# 爬取列表页
async def crawl_list(msg: CrawlListPageMsg) -> list[CrawlDetailPageMsg]:
    match msg.crawl_list_type:
        case CrawlType.HTML_DYNAMIC:
            pages = await crawl_list_using_browser(msg.url, msg.rule)
        case CrawlType.HTML_STATIC:
            pages = await crawl_list_using_http(msg.url, msg.rule)
        case CrawlType.JSON:
            pages = await crawl_list_using_json(msg.url, msg.rule)

    if len(pages) == 0:
        return []

    deduplicated_pages = await duplicate_url(settings.url_deduplicate_api, pages)
    if len(deduplicated_pages) == 0:
        return []

    return [
        CrawlDetailPageMsg(site_id=msg.site_id, site_name=msg.site_name, url=url, title=title, crawl_detail_type=msg.crawl_detail_type)
        for url, title in deduplicated_pages.items()
    ]


# 爬取正文页
async def crawl_detail(msg: CrawlDetailPageMsg) -> CrawlPageContentMsg:
    match msg.crawl_detail_type:
        case CrawlType.HTML_DYNAMIC:
            detail = await crawl_detail_using_browser(msg.url)
        case CrawlType.HTML_STATIC:
            detail = await crawl_detail_using_http(msg.url)

    return CrawlPageContentMsg(
        site_id=msg.site_id,
        site_name=msg.site_name,
        url=msg.url,
        title=msg.title,
        date=detail.date,
        content=detail.content,
    )


if __name__ == "__main__":
    asyncio.run(main())
