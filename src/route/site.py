from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from database.models import CrawlRequest, CrawlType, DomainBlacklist, PushSubscription, Site, SiteCategory
from dingtalk.client import DingTalkClient
from route.response import Response
from settings import get_settings, Settings

site_router = APIRouter(prefix="/site", tags=["site"])

class SiteListRequest(BaseModel):
    page: int = Field(1, description="页码")
    page_size: int = Field(20, description="每页数量")

class SiteItem(BaseModel):
    id: int = Field(..., description="站点ID")
    name: str = Field(..., description="站点名称")
    category: SiteCategory = Field(..., description="站点分类")
    listpage_url: str = Field(..., description="列表页url")
    listpage_crawl_type: CrawlType = Field(..., description="列表页爬取类型")
    detailpage_crawl_type: CrawlType = Field(..., description="详情页爬取类型")
    listpage_parse_rule: list[str] = Field(..., description="列表页解析规则")
    content_filter_keywords: str = Field(..., description="内容过滤关键词")
    paywall: bool = Field(..., description="是否付费阅读")


@site_router.get("/list", description="获取站点列表")
async def list_sites(request: SiteListRequest = Query(..., description="请求参数")) -> Response[list[SiteItem]]:
    sites = await Site.all().order_by("-id").offset((request.page - 1) * request.page_size).limit(request.page_size)
    return Response.success([SiteItem(
        id=site.id,
        name=site.name,
        category=site.category,
        listpage_url=site.listpage_url,
        listpage_crawl_type=site.listpage_crawl_type,
        detailpage_crawl_type=site.detailpage_crawl_type,
        listpage_parse_rule=site.listpage_parse_rule,
        content_filter_keywords=site.content_filter_keywords,
        paywall=site.paywall,
    ) for site in sites])


class SiteAddRequest(BaseModel):
    name: str = Field(..., description="站点名称")
    listpage_url: str = Field(..., description="列表页url")
    category: SiteCategory = Field(SiteCategory.NEWS, description="站点分类")
    listpage_crawl_type: CrawlType = Field(..., description="列表页爬取类型")
    detailpage_crawl_type: CrawlType = Field(..., description="详情页爬取类型")
    listpage_parse_rule: list[str] = Field(..., description="列表页解析规则")
    content_filter_keywords: str = Field(..., description="内容过滤关键词")
    paywall: bool = Field(False, description="是否付费阅读")
    subscribe_staff_numbers: list[str] = Field([], description="订阅用户工号列表")
    subscribe_filter_keywords: str = Field("", description="订阅过滤关键词")

@site_router.post("/add", description="添加站点")
async def add_site(request: SiteAddRequest, token: str = Query(..., description="授权令牌"), settings: Settings = Depends(get_settings)) -> Response[int]:
    if token != settings.admin_auth_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        exist_site = await Site.filter(listpage_url=request.listpage_url).first()
        if exist_site:
            return Response.fail("站点已存在")

        site = await Site.create(
            name=request.name,
            category=request.category,
            listpage_url=request.listpage_url,
            listpage_crawl_type=request.listpage_crawl_type,
            detailpage_crawl_type=request.detailpage_crawl_type,
            listpage_parse_rule=request.listpage_parse_rule,
            content_filter_keywords=request.content_filter_keywords,
            paywall=request.paywall,
        )

        for staff_number in request.subscribe_staff_numbers:
            await PushSubscription.create(
                site_id=site.id,
                staff_number=staff_number,
                filter_keywords=request.subscribe_filter_keywords,
            )

        return Response.success(site.id)
    except Exception as e:
        return Response.fail(f"添加站点失败: {e}")


class SubscribeAddRequest(BaseModel):
    site_ids: list[int] = Field(..., description="站点ID列表")
    user_id: str = Field(..., description="用户ID")
    filter_keywords: str = Field("", description="过滤关键词")

@site_router.post("/subscribe/add", description="添加订阅")
async def subscribe_site(request: SubscribeAddRequest, token: str = Query(..., description="授权令牌"), settings: Settings = Depends(get_settings)) -> Response[bool]:
    if token != settings.admin_auth_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if request.site_ids[0] == -1:
        site_ids = await Site.all().values_list("id", flat=True)
    else:
        site_ids = request.site_ids

    for site_id in site_ids:
        exist = await PushSubscription.filter(site_id=site_id, staff_number=request.user_id).exists()
        if exist:
            continue
    
        try:
            await PushSubscription.create(
                site_id=site_id,
                staff_number=request.user_id,
                filter_keywords=request.filter_keywords,
            )
        except Exception as e:
            return Response.fail(f"添加订阅失败: {e}")
    return Response.success(True)


class DomainBlacklistAddRequest(BaseModel):
    domain: str = Field(..., description="域名")

@site_router.post("/domain_blacklist/add", description="添加域名黑名单")
async def add_domain_blacklist(request: DomainBlacklistAddRequest, token: str = Query(..., description="授权令牌"), settings: Settings = Depends(get_settings)) -> Response[int]:
    if token != settings.admin_auth_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        exist = await DomainBlacklist.filter(domain=request.domain).exists()
        if exist:
            return Response.fail("域名已存在")

        domain_blacklist = await DomainBlacklist.create(domain=request.domain)
        return Response.success(domain_blacklist.id)
    except Exception as e:
        return Response.fail(f"添加域名黑名单失败: {e}")


@site_router.post("/conversation", description="通过对话添加站点")
async def add_site_by_conversation(request: Request, settings: Settings = Depends(get_settings)):
    try:
        req = await request.json()
        stuff_number = req.get("senderStaffId")
        sender_name = req.get("senderNick")
        content = req.get("text").get("content")

        await CrawlRequest.create(
            stuff_name=sender_name,
            stuff_number=stuff_number,
            content=content,
        )

        # 发送消息给管理员
        await DingTalkClient.send_message(
            user_id="362037",
            title=f"收到{sender_name}的采集请求",
            summary=f"工号: {stuff_number}\n\n  内容: {content}",
            url="",
            source="采集请求",
        )

        # 发送示例消息
        await DingTalkClient.send_message(
            user_id=stuff_number,
            title="【示例】关于实施鼓励外商投资企业境内再投资若干措施的通知(发改外资〔2025〕928号)",
            summary="【示例】为贯彻落实党中央和国务院决策部署，更大力度吸引和利用外资，鼓励外商投资企业境内再投资，国家发展改革委等部门发布通知，明确多项政策措施。包括建立再投资项目库、允许外汇资金境内划转、简化再投资登记手续、推动信息报告试点以及优化外商投资评价方式等。",
            url="https://www.ndrc.gov.cn/xxgk/zcfb/tz/202507/t20250718_1399285.html",
            source="【示例】国家发改委",
        )

        return {
           "msgtype": "text",
            "text": {
                "content": "您的信息采集请求已提交，未来新内容消息格式参考示例消息"
            }
        }
    except Exception:
        return {
           "msgtype": "text",
            "text": {
                "content": "对话内容解析失败"
            }
        }