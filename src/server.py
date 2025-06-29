import asyncio
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from tortoise.contrib.fastapi import RegisterTortoise
from database.connection import generate_tortoise_config
from database.models import Page, PageSignature, PushSubscription, Site
from dingtalk.client import DingTalkClient
from llm.bailian import Bailian
from log.logger import server_logger
from pubsub.msg import CrawlPageContentMsg
from route.crawl import crawl_router
from route.site import site_router
from settings import Settings
from middleware.log import AccessLogMiddleware
from pubsub.connection import QUEUE_CRAWL_PAGECONTENT, MsgQueue
from util.page import get_signature, is_hit_keywords

app_settings = Settings()

async def subscribe_and_save_crawl_page_content_and_push():
    sub = await MsgQueue.subscribe(QUEUE_CRAWL_PAGECONTENT, worker_mode=True)

    sites = await Site.all()
    content_filter_keywords = {site.id: site.content_filter_keywords for site in sites}

    push_subscriptions = await PushSubscription.all()
    push_filter_keywords = {f"{push_subscription.site_id}__{push_subscription.staff_number}": push_subscription.filter_keywords for push_subscription in push_subscriptions}
    push_user_ids = {str(push_subscription.site_id): [push_subscription.staff_number] for push_subscription in push_subscriptions}

    async for msg in sub.messages:
        try:
            page_content = CrawlPageContentMsg.model_validate_json(msg.data.decode("utf-8"))

            # 无条件记录页面签名，用于去重
            page_signature = await PageSignature.create(signature=get_signature(page_content.url))

            # 根据站点id获取过滤关键词
            site_id = page_content.site_id
            content_filter_keyword = content_filter_keywords.get(site_id, "")

            # 如果命中过滤关键词才进行保存
            if is_hit_keywords(page_content.title, page_content.content, content_filter_keyword):
                summary = await Bailian.text_summary(page_content.title, page_content.content)
                await Page.create(
                    site_id=site_id,
                    url=page_content.url,
                    summary=summary,
                    date=page_content.date,
                    signature_id=page_signature.id
                )

                # 对订阅用户推送
                for user_id in push_user_ids.get(str(site_id), []):
                    # 命中推送过滤关键词才进行推送
                    push_filter_keyword = push_filter_keywords.get(f"{site_id}__{user_id}", "")
                    if is_hit_keywords(page_content.title, page_content.content, push_filter_keyword):
                        await DingTalkClient.send_message(
                            user_id=user_id,
                            title=page_content.title,
                            summary=summary,
                            url=page_content.url,
                            source=page_content.site_name,
                        )
        except Exception as e:
            server_logger.error(f"Subscribe crawl page content error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化百炼
    Bailian.init(app_settings.dashscope_api_key)

    # 初始化消息队列
    await MsgQueue.init(settings=app_settings)

    # 初始化钉钉
    await DingTalkClient.init(
        accesskey_id=app_settings.dingtalk_accesskey_id,
        accesskey_secret=app_settings.dingtalk_accesskey_secret,
        robot_code=app_settings.dingtalk_robot_code
    )

    # 订阅爬取页面内容并保存和推送
    asyncio.create_task(subscribe_and_save_crawl_page_content_and_push())

    # 初始化数据库
    async with RegisterTortoise(
        app=app,
        config=generate_tortoise_config(settings=app_settings),
        generate_schemas=True
    ):
        yield

    # 关闭消息队列连接
    await MsgQueue.close()

app = FastAPI(lifespan=lifespan, title="资讯政策数据采集", description="资讯政策数据采集")

app.add_middleware(AccessLogMiddleware)
app.include_router(crawl_router)
app.include_router(site_router)

if __name__ == "__main__":
    uvicorn.run(app, host=app_settings.api_server_host, port=app_settings.api_server_port, access_log=False)