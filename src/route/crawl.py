import asyncio
import datetime as dt
from datetime import datetime
import urllib.parse
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
import hashlib

from pydantic import BaseModel, Field
from crawl.api import search_web_news
from database.models import DomainBlacklist, Page, PageSignature, Site, WebSearchNews
from llm.bailian import Bailian
from log.logger import server_logger
from oss.store import OSS
from pubsub.connection import MsgQueue, QUEUE_CRAWL_LISTPAGE
from pubsub.msg import CrawlListPageMsg
from route.response import Response
from settings import get_settings, Settings
from crawl.util import duplicate_search_web_news

crawl_router = APIRouter(prefix="/crawl", tags=["爬取"])

@crawl_router.get("/search_web_news", description="网络搜索新闻")
async def web_news_by_search(token: str = Query(..., description="授权令牌"), settings: Settings = Depends(get_settings)) -> Response[bool]:
    if token != settings.admin_auth_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    keywords_map = {
        "华为": ["华为在芯片、GPU、昇腾、CUDA、大模型等方面的新闻资讯", "华为在各地参与的活动、项目资讯"],
        "字节跳动": ["字节跳动、火山引擎在芯片、GPU、CUDA、大模型、豆包等方面的新闻资讯", "字节跳动、火山引擎在各地参与的活动、项目资讯"],
        "百度云": ["百度云在芯片、GPU、CUDA、大模型、文心一言等方面的新闻资讯", "百度云在各地参与的活动、项目资讯"],
        "其他": [
            "腾讯云在芯片、GPU、CUDA、大模型、混元等方面的新闻资讯", 
            "腾讯云在各地参与的活动、项目资讯",
            "列举deepseek、openai、gemini、AWS、谷歌、meta、微软、英伟达、XAI、claude等厂商动态",
        ],
    }
    for company, keywords in keywords_map.items():
        for keyword in keywords:
            news = await search_web_news(keyword)
            news = await duplicate_search_web_news(news)
            for news_item in news:
                await WebSearchNews.create(
                    company=company,
                    title=news_item.title,
                    url=news_item.url,
                    website=news_item.website,
                    date=news_item.date,
                    signature=news_item.signature
                )
        await asyncio.sleep(1)
        
    return Response.success(True)

@crawl_router.get("/schedule", description="触发爬取任务,将所有站点列表页加入爬取队列")
async def schedule(token: str = Query(..., description="授权令牌"), settings: Settings = Depends(get_settings)) -> Response[bool]:
    if token != settings.admin_auth_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    pub_conn = None
    try:
        pub_conn = await MsgQueue.connect(settings)

        sites = await Site.all().order_by("-id")
        for site in sites:
            await pub_conn.publish(
                subject=QUEUE_CRAWL_LISTPAGE,
                payload=CrawlListPageMsg(
                    site_id=site.id,
                    site_name=site.name,
                    url=site.listpage_url,
                    crawl_list_type=site.listpage_crawl_type,
                    crawl_detail_type=site.detailpage_crawl_type,
                    rule=site.listpage_parse_rule,
                    paywall=site.paywall,
                    first_crawl=site.crawled_at is None, # 首次爬取标记, 用于判断是否需要发送推送
                ).model_dump_json().encode("utf-8")
            )

            # 更新站点最近爬取时间
            site.crawled_at = datetime.now()
            await site.save()

    except Exception as e:
        server_logger.error(f"Schedule crawl error: {e}")
        return Response.fail("触发爬取任务失败")
    finally:
        if pub_conn and not pub_conn.is_closed:
            await pub_conn.close()

    return Response.success(True)


@crawl_router.post("/sync_articles_to_oss", description="同步文章到OSS")
async def sync_articles_to_oss(token: str = Query(..., description="授权令牌"), settings: Settings = Depends(get_settings)) -> Response[bool]:
    if token != settings.admin_auth_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    site_ids = await Site.filter(send_to_aiagent=True).values_list("id", flat=True)
    today = datetime.now().date()
    pages = await Page.filter(
        site_id__in=site_ids, 
        visible=True,
        date__gte=datetime.combine(today, datetime.min.time()),
        date__lte=datetime.combine(today, datetime.max.time())
    ).all().select_related("site")

    today_str = today.strftime("%Y-%m-%d")
    for page in pages:
        summary_url = f"https://pre-assistant-voice-ga.alibaba-inc.com/weekly?source_link={urllib.parse.quote_plus(page.display_url)}"
        content = f"标题: {page.title}\n\n日期: {page.date.strftime("%Y-%m-%d")}\n\n来源: {page.site.name}\n\n网址: {page.display_url}\n\n摘要: {page.summary}\n\n详细摘要地址: {summary_url}"
        await OSS.upload(f"articles/{today_str}_{page.id}.txt", content)

    return Response.success(True)


@crawl_router.get("/get_articles", description="获取文章")
async def get_articles(start_date: str = Query(..., description="开始日期"), end_date: str = Query(..., description="结束日期")) -> Response[list[dict]]:
    site_ids = await Site.filter(send_to_aiagent=True).values_list("id", flat=True)
    pages = await Page.filter(
        site_id__in=site_ids, 
        visible=True,
        created_at__gte=datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S"),
        created_at__lte=datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
    ).order_by("-id").all().select_related("site")


    china_timezone = dt.timezone(dt.timedelta(hours=8))
    contents = []
    for page in pages:
        contents.append({
            "id": str(page.id),
            "title": page.title,
            "publish_time": page.created_at.astimezone(china_timezone).strftime("%Y-%m-%d %H:%M:%S"),
            "source": page.site.name,
            "url": page.display_url,
            "summary": page.summary,
        })

    return Response.success(contents)


class SummarizeArticleRequest(BaseModel):
    title: str = Field(..., description="标题")
    content: str = Field(..., description="内容")


@crawl_router.post("/summarize_article", description="总结文章")
async def summarize_article(summarize_request: SummarizeArticleRequest = Body(..., description="总结文章请求")) -> Response[str]:
    result = await Bailian.text_summary(summarize_request.title, summarize_request.content)
    return Response.success(result)


@crawl_router.get("/today_articles", description="获取今日文章", response_class=PlainTextResponse)
async def today_articles(chunk: int = Query(1, description="分块")) -> str:
    site_ids = await Site.filter(send_to_aiagent=True).values_list("id", flat=True)
    today = datetime.now().date()
    pages = await Page.filter(
        site_id__in=site_ids, 
        visible=True,
        date__gte=datetime.combine(today, datetime.min.time()),
        date__lte=datetime.combine(today, datetime.max.time())
    ).order_by("-id").all().select_related("site")

    contents = []

    # 对pages分2个chunk
    chunks = [pages[0:len(pages)//2], pages[len(pages)//2:]]
    if chunk == 1:
        pages_chunk = chunks[0]
    else:
        pages_chunk = chunks[1]

    for page in pages_chunk:
        if page.summary.find("大模型生成摘要失败") != -1:
            continue
        
        summary_url = f"https://pre-assistant-voice-ga.alibaba-inc.com/weekly?source_link={urllib.parse.quote_plus(page.display_url)}"
        content = f"标题: {page.title}\n\n日期: {page.date.strftime("%Y-%m-%d")}\n\n来源: {page.site.name}\n\n网址: {page.display_url}\n\n摘要: {page.summary}\n\n详细摘要地址: {summary_url}"
        contents.append(content)

    return "\n\n\n\n".join(contents)


@crawl_router.post("/trigger_agent", description="触发AIAgent")
async def trigger_agent(token: str = Query(..., description="授权令牌"), settings: Settings = Depends(get_settings)):
    if token != settings.admin_auth_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    api_key = "sk-42bca06dcba54a10a3bb4f6c133f449f"
    app_id = "c5fb1a62f20a4df288b076752fc00bd1"
    result = await Bailian.trigger_agent(api_key, app_id)
    return Response.success(result)


@crawl_router.post("/deduplicate", description="爬取页面去重")
async def deduplicate(urls: list[str]) -> Response[list[str]]:
    if not urls:
        return Response.success([])

    # 检查urls中是否包含域名黑名单中的域名
    domain_blacklist = await DomainBlacklist.all().values_list("domain", flat=True)
    urls = list(filter(lambda url: not any(domain in url for domain in domain_blacklist), urls))

    signature_url_map: dict[str, str] = {}
    for url in urls:
        signature = hashlib.md5(url.encode()).hexdigest()
        signature_url_map[signature] = url

    signatures = signature_url_map.keys()
    exist_signatures = await PageSignature.filter(signature__in=signatures).values_list("signature", flat=True)

    # 返回signature不存在的url的列表
    return Response.success([signature_url_map[signature] for signature in signatures if signature not in exist_signatures])