from fastapi import APIRouter, HTTPException, Query
import hashlib
from database.models import PageSignature, Site
from pubsub.connection import MsgQueue, QUEUE_CRAWL_LISTPAGE
from pubsub.msg import CrawlListPageMsg
from route.response import Response

crawl_router = APIRouter(prefix="/crawl", tags=["爬取"])

SCHEDULE_AUTH_TOKEN = "6iOJKHyQu8Byg4lm"

@crawl_router.get("/schedule", description="触发爬取任务,将所有站点列表页加入爬取队列")
async def schedule(token: str = Query(..., description="授权令牌")) -> Response[bool]:
    if token != SCHEDULE_AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    sites = await Site.all()
    for site in sites:
        await MsgQueue.publish(
            subject=QUEUE_CRAWL_LISTPAGE,
            msg=CrawlListPageMsg(
                site_id=site.id,
                site_name=site.name,
                url=site.listpage_url,
                crawl_list_type=site.listpage_crawl_type,
                crawl_detail_type=site.detailpage_crawl_type,
                rule=site.listpage_parse_rule,
                paywall=site.paywall,
            )
        )

    return Response.success(True)

@crawl_router.post("/deduplicate", description="爬取页面去重")
async def deduplicate(urls: list[str]) -> Response[list[str]]:
    if not urls:
        return Response.success([])

    signature_url_map: dict[str, str] = {}
    for url in urls:
        signature = hashlib.md5(url.encode()).hexdigest()
        signature_url_map[signature] = url

    signatures = signature_url_map.keys()
    exist_signatures = await PageSignature.filter(signature__in=signatures).values_list("signature", flat=True)

    # 返回signature不存在的url的列表
    return Response.success([signature_url_map[signature] for signature in signatures if signature not in exist_signatures])