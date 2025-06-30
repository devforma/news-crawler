import asyncio

from nats.aio.client import Client
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
    pub_conn = None
    sub_listpage_conn = None
    sub_detailpage_conn = None
    try:
        # 初始化http连接器
        await HttpClient.init(conn_limit=10, conn_limit_per_host=10, timeout=10)
        crawl_logger.info("HttpClient initialized")

        # 初始化消息队列
        pub_conn = await MsgQueue.connect(settings)
        sub_listpage_conn = await MsgQueue.connect(settings)
        sub_detailpage_conn = await MsgQueue.connect(settings)

        # 订阅列表页
        list_sub = await sub_listpage_conn.subscribe(subject=QUEUE_CRAWL_LISTPAGE, queue="workers")
        crawl_logger.info("List page subscription initialized")

        # 订阅正文页
        detail_sub = await sub_detailpage_conn.subscribe(subject=QUEUE_CRAWL_DETAILPAGE, queue="workers")
        crawl_logger.info("Detail page subscription initialized")

        # 启动消费任务
        await asyncio.gather(
            crawl_list_page_loop(list_sub, pub_conn),
            crawl_detail_page_loop(detail_sub, pub_conn),
        )
    except Exception as e:
        crawl_logger.error(f"Main loop error: {e}")
    finally:
        if pub_conn and not pub_conn.is_closed:
            await pub_conn.close()
        if sub_listpage_conn and not sub_listpage_conn.is_closed:
            await sub_listpage_conn.close()
        if sub_detailpage_conn and not sub_detailpage_conn.is_closed:
            await sub_detailpage_conn.close()

# 爬取列表页
async def crawl_list_page_loop(list_sub: Subscription, pub_conn: Client):
    async for msg in list_sub.messages:
        try:
            msg = CrawlListPageMsg.model_validate_json(msg.data.decode("utf-8"))
            detail_msgs = await crawl_list(msg)
            for detail_msg in detail_msgs:
                await pub_conn.publish(QUEUE_CRAWL_DETAILPAGE, detail_msg.model_dump_json().encode("utf-8"))
        except Exception as e:
            crawl_logger.error(f"CrawlList loop error: {e}")

# 爬取正文页
async def crawl_detail_page_loop(detail_sub: Subscription, pub_conn: Client):
    async for msg in detail_sub.messages:
        try:
            msg = CrawlDetailPageMsg.model_validate_json(msg.data.decode("utf-8"))
            content_msg = await crawl_detail(msg)
            await pub_conn.publish(QUEUE_CRAWL_PAGECONTENT, content_msg.model_dump_json().encode("utf-8"))
        except Exception as e:
            crawl_logger.error(f"CrawlDetail loop error: {e}")
        finally:
            await asyncio.sleep(1)

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
