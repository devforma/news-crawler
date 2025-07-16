import datetime as dt
from datetime import datetime
from typing import Generic, Optional, TypeVar
from fastapi import APIRouter, Path, Query
from pydantic import BaseModel, Field

from database.models import Page, PageContent, Site, SiteCategory
from llm.bailian import Bailian

post_router = APIRouter(prefix="/post", tags=["post"])

class Pagination(BaseModel):
    page: int = Field(..., description="页码")
    page_size: int = Field(..., description="每页大小")
    total: int = Field(..., description="总数")

T = TypeVar("T")
class Response(BaseModel, Generic[T]):
    success: bool = Field(..., description="是否成功")
    error_message: str = Field("", description="错误信息")
    data: T = Field(..., description="数据")
    pagination: Optional[Pagination] = Field(None, description="分页信息")


@post_router.get("/source", response_model=Response[list[str]], summary="获取文章网站源")
async def get_post_website_source(type: SiteCategory = Query(SiteCategory.NEWS, description="类型")) -> Response[list[str]]:
    sites = await Site.filter(category=type).all()
    site_names = [site.name for site in sites]
    return Response(success=True, error_message="", data=site_names, pagination=None)


class Post(BaseModel):
    id: int = Field(..., description="ID")
    title: str = Field(..., description="标题")
    type: SiteCategory = Field(..., description="类型")
    site: str = Field(..., description="网站源")
    url: str = Field(..., description="URL")
    content: str = Field("", description="内容")
    summary: str = Field(..., description="摘要")
    publish_time: str = Field(..., description="发布时间")

@post_router.get("", response_model=Response[list[Post]], summary="获取文章列表")
async def list_posts(
    site: str = Query("", description="网站源，多个用逗号分隔"),
    date_range: str = Query("", description="日期范围，格式：2024-01-01,2024-01-31"),
    type: SiteCategory = Query(SiteCategory.NEWS, description="类型"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页大小"),
) -> Response[list[Post]]:
    query = Page.filter(visible=True)

    if site:
        site_ids = await Site.filter(name__in=site.split(","), category=type).values_list("id", flat=True)
        query = query.filter(site_id__in=site_ids)
    if date_range:
        start_date = datetime.strptime(date_range.split(",")[0], "%Y-%m-%d").date()
        end_date = datetime.strptime(date_range.split(",")[1], "%Y-%m-%d").date()
        # Convert to datetime objects for proper filtering
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(date__gte=start_datetime, date__lte=end_datetime)
    if type:
        query = query.filter(site__category=type)

    total = await query.count()
    results = await query.order_by("-id").offset((page - 1) * page_size).limit(page_size).all().select_related("site")

    # 中国时区
    china_timezone = dt.timezone(dt.timedelta(hours=8))
    posts = [Post(
            id=result.id,
            title=result.title,
            type=result.site.category,
            site=result.site.name,
            content="",
            url=result.url,
            summary=result.summary,
            # 展示日期使用爬取时间, 页面解析得到的日期不准
            publish_time=result.created_at.astimezone(china_timezone).strftime("%Y-%m-%d") if result.created_at else ""
        ) for result in results]

    return Response(success=True, error_message="", data=posts, pagination=Pagination(page=page, page_size=page_size, total=total))
    

class PostInterpretation(BaseModel):
    title: str = Field(description="标题")
    url: str = Field(description="链接")
    content: str = Field(description="内容")

@post_router.get("/{id}/interpretation", response_model=Response[PostInterpretation | None], summary="获取文章解读")
async def get_article_interpretation(id: int = Path(..., description="文章ID")) -> Response[PostInterpretation | None]:

    page = await Page.get(id=id)
    page_content = await PageContent.get(page_id=id)

    interpretation = await Bailian.rag_interpretation(page.title, page_content.content)
    return Response(success=True, error_message="", data=PostInterpretation(title=page.title, url=page.url, content=interpretation), pagination=None)


# 获取所有站点
async def get_sites(names: list[str] = Query(..., description="站点名称")) -> tuple[list[int], dict[int, str]]:
    sites = await Site.filter(name__in=names).all()
    return [site.id for site in sites], {site.id: site.name for site in sites}