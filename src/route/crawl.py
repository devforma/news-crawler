from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
import hashlib
from database.models import DomainBlacklist, PageSignature, Site
from log.logger import server_logger
from pubsub.connection import MsgQueue, QUEUE_CRAWL_LISTPAGE
from pubsub.msg import CrawlListPageMsg
from route.response import Response
from settings import get_settings, Settings
crawl_router = APIRouter(prefix="/crawl", tags=["爬取"])

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