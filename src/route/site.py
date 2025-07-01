from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from database.models import CrawlType, DomainBlacklist, Site, SiteCategory
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
        return Response.success(site.id)
    except Exception as e:
        return Response.fail(f"添加站点失败: {e}")


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