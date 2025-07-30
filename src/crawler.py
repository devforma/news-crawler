import asyncio
import time

from nats.aio.client import Client
from nats.aio.subscription import Subscription
from crawl.util import duplicate_url, is_same_domain
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
        finally:
            # return # 测试用,只抓取第一个列表页
            await asyncio.sleep(2)

# 爬取正文页
async def crawl_detail_page_loop(detail_sub: Subscription, pub_conn: Client):
    async for msg in detail_sub.messages:
        try:
            msg = CrawlDetailPageMsg.model_validate_json(msg.data.decode("utf-8"))
            content_msg = await crawl_detail(msg)
            if content_msg is not None:
                await pub_conn.publish(QUEUE_CRAWL_PAGECONTENT, content_msg.model_dump_json().encode("utf-8"))
        except Exception as e:
            crawl_logger.error(f"CrawlDetail loop error: {e}")
        finally:
            await asyncio.sleep(2)

# 爬取列表页
async def crawl_list(msg: CrawlListPageMsg) -> list[CrawlDetailPageMsg]:
    start_time = time.time()
    display_url_map = {}
    match msg.crawl_list_type:
        case CrawlType.HTML_DYNAMIC:
            pages = await crawl_list_using_browser(msg.url, msg.rule)
        case CrawlType.HTML_STATIC:
            pages = await crawl_list_using_http(msg.url, msg.rule)
        case CrawlType.JSON:
            pages, display_url_map = await crawl_list_using_json(msg.url, msg.rule)
    end_time = time.time()
    crawl_logger.info(f"CrawlList time: {end_time - start_time:.3f}s, {msg.site_name}, {msg.url}, pages: {len(pages)}")
    if len(pages) == 0:
        return []

    deduplicated_pages = await duplicate_url(settings.url_deduplicate_api, pages)
    crawl_logger.info(f"CrawlList deduplicated: {msg.site_name}, {msg.url}, pages: {len(deduplicated_pages)}")
    if len(deduplicated_pages) == 0:
        return []

    detail_msgs = []
    for url, title in deduplicated_pages.items():
        # 当列表页爬取类型是网页时, 对于非当前域名的url(外链), 正文页爬取类型设置为html_dynamic
        if msg.crawl_list_type != CrawlType.JSON and not is_same_domain(url, msg.url): 
            crawl_detail_type = CrawlType.HTML_DYNAMIC
        else:
            crawl_detail_type = msg.crawl_detail_type
        
        detail_msgs.append(CrawlDetailPageMsg(
                site_id=msg.site_id,
                site_name=msg.site_name,
                url=url,
                display_url=display_url_map.get(url, url),
                title=title,
                crawl_detail_type=crawl_detail_type,
                first_crawl=msg.first_crawl,
                paywall=msg.paywall,
            ))

    return detail_msgs


# 爬取正文页
async def crawl_detail(msg: CrawlDetailPageMsg) -> CrawlPageContentMsg | None:
    start_time = time.time()
    match msg.crawl_detail_type:
        case CrawlType.HTML_DYNAMIC:
            detail = await crawl_detail_using_browser(msg.url)
        case CrawlType.HTML_STATIC:
            detail = await crawl_detail_using_http(msg.url)
    end_time = time.time()
    crawl_logger.info(f"CrawlDetail time: {end_time - start_time:.3f}s, {msg.site_name}, {msg.url}")

    if detail is None:
        return None

    return CrawlPageContentMsg(
        site_id=msg.site_id,
        site_name=msg.site_name,
        url=msg.url,
        display_url=msg.display_url,
        title=msg.title,
        date=detail.date,
        content=detail.content,
        first_crawl=msg.first_crawl,
        paywall=msg.paywall,
    )


if __name__ == "__main__":
    asyncio.run(main())
