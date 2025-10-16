import asyncio
from datetime import datetime
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from nats.aio.client import Client
from tortoise.contrib.fastapi import RegisterTortoise
from database.connection import generate_tortoise_config
from database.models import Page, PageContent, PageSignature, PushSubscription, Site
from dingtalk.client import DingTalkClient
from llm.bailian import Bailian
from log.logger import server_logger
from oss.store import OSS
from pubsub.msg import CrawlPageContentMsg
from route.crawl import crawl_router
from route.post import post_router
from route.site import site_router
from settings import get_settings
from middleware.log import AccessLogMiddleware
from pubsub.connection import QUEUE_CRAWL_PAGECONTENT, MsgQueue
from util.page import get_signature, is_hit_keywords

app_settings = get_settings()

async def subscribe_and_save_crawl_page_content_and_push(sub_conn: Client):
    sub = await sub_conn.subscribe(QUEUE_CRAWL_PAGECONTENT, queue="workers")
    async for msg in sub.messages:
        try:
            page_content = CrawlPageContentMsg.model_validate_json(msg.data.decode("utf-8"))

            # 无条件记录页面签名，用于去重
            page_signature = await PageSignature.create(signature=get_signature(page_content.url))

            # 根据站点id获取过滤关键词
            site_id = page_content.site_id
            site = await Site.get(id=site_id).only("content_filter_keywords")

            # 如果命中过滤关键词才进行保存
            if is_hit_keywords(page_content.title, page_content.content, site.content_filter_keywords):
                if page_content.paywall:
                    summary = "网站包含付费订阅内容，请查看原文"
                else:
                    summary = await Bailian.text_summary(page_content.title, page_content.content)
                page = await Page.create(
                    site_id=site_id,
                    title=page_content.title,
                    url=page_content.url,
                    display_url=page_content.display_url if page_content.display_url != "" else page_content.url,
                    summary=summary,
                    date=page_content.date,
                    signature_id=page_signature.id,
                    visible=True
                )

                await PageContent.create(
                    page_id=page.id,
                    content=page_content.content
                )

                # 首次爬取数据量大, 不进行推送
                if page_content.first_crawl:
                    continue

                # 非首次爬取, 根据推送过滤关键词进行推送
                sub_users = await PushSubscription.filter(site_id=site_id).all()

                weekday = datetime.now().weekday()
                hour = datetime.now().hour
                exclude_sub_users = ["348170", "355211", "112293", "163986"]
                for sub_user in sub_users:
                    # 对特定用户周六、周日不推送，周一至周五9-18时推送
                    if (weekday in [5, 6] or (weekday in [0, 1, 2, 3, 4] and (hour < 9 or hour > 18))) and sub_user.staff_number in exclude_sub_users:
                        continue

                    # 命中推送过滤关键词才进行推送
                    if is_hit_keywords(page_content.title, page_content.content, sub_user.filter_keywords):
                        await DingTalkClient.send_message(
                            user_id=sub_user.staff_number,
                            title=page_content.title,
                            summary=summary,
                            url=page_content.display_url if page_content.display_url != "" else page_content.url,
                            source=page_content.site_name,
                        )
                        server_logger.info(f"Push message to {sub_user.staff_number}: {page_content.title}")
        except Exception as e:
            server_logger.error(f"Subscribe crawl page content error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化百炼
    Bailian.init(app_settings.dashscope_api_key, app_settings.dashscope_interpretation_app_id)

    # 初始化OSS
    OSS.init(
        endpoint=app_settings.push_oss_endpoint,
        region=app_settings.push_oss_region,
        bucket=app_settings.push_oss_bucket,
        accesskey_id=app_settings.push_oss_accesskey_id,
        accesskey_secret=app_settings.push_oss_accesskey_secret
    )

    # 初始化钉钉
    await DingTalkClient.init(
        accesskey_id=app_settings.dingtalk_accesskey_id,
        accesskey_secret=app_settings.dingtalk_accesskey_secret,
        robot_code=app_settings.dingtalk_robot_code
    )

    # 订阅爬取页面内容并保存和推送
    sub_conn = await MsgQueue.connect(settings=app_settings)
    asyncio.create_task(subscribe_and_save_crawl_page_content_and_push(sub_conn))

    # 初始化数据库
    async with RegisterTortoise(
        app=app,
        config=generate_tortoise_config(settings=app_settings),
        generate_schemas=True
    ):
        yield

    # 关闭消息队列连接
    await sub_conn.close()

app = FastAPI(lifespan=lifespan, title="资讯政策数据采集", description="资讯政策数据采集")

app.add_middleware(AccessLogMiddleware)
app.include_router(crawl_router)
app.include_router(site_router)
app.include_router(post_router)

if __name__ == "__main__":
    uvicorn.run(app, host=app_settings.api_server_host, port=app_settings.api_server_port, access_log=False)