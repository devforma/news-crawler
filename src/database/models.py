from tortoise import fields, models

from enum import Enum

class SiteCategory(str, Enum):
    NEWS = "news"
    ARTICLE = "article"
    TALENT_POLICY = "talent_policy"

class CrawlType(str, Enum):
    HTML_STATIC = "html_static"
    HTML_DYNAMIC = "html_dynamic"
    JSON = "json"

class Site(models.Model):
    id = fields.IntField(primary_key=True, generated=True)
    name = fields.TextField(description="站点名称")
    category = fields.CharEnumField(enum_type=SiteCategory, default=SiteCategory.NEWS, description="站点分类", index=True)
    listpage_url = fields.TextField(description="列表页URL")
    listpage_crawl_type = fields.CharEnumField(enum_type=CrawlType, default=CrawlType.HTML_STATIC, description="列表页爬取类型")
    listpage_parse_rule = fields.JSONField(default=[], description="列表页解析规则")
    detailpage_crawl_type = fields.CharEnumField(enum_type=CrawlType, default=CrawlType.HTML_STATIC, description="详情页爬取类型")
    content_filter_keywords = fields.TextField(default="", description="内容过滤关键词")
    paywall = fields.BooleanField(default=False, description="是否付费阅读")
    send_to_aiagent = fields.BooleanField(default=False, description="是否用于AI agent")
    created_at = fields.DatetimeField(auto_now_add=True)
    crawled_at = fields.DatetimeField(null=True, description="最近爬取时间")

    class Meta:
        table = "sites"
        table_description = "站点列表"

class Page(models.Model):
    id = fields.BigIntField(primary_key=True, generated=True)
    site: fields.ForeignKeyRelation[Site] = fields.ForeignKeyField("models.Site", related_name="pages", description="站点ID", db_index=True)
    title = fields.TextField(description="标题")
    url = fields.TextField(description="URL")
    display_url = fields.TextField(description="显示URL")
    summary = fields.TextField(description="摘要")
    date = fields.DatetimeField(description="日期")
    signature_id = fields.BigIntField(description="签名ID", index=True)
    visible = fields.BooleanField(default=True, description="是否可见")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")

    class Meta:
        table = "pages"
        table_description = "已爬取页面列表"

class PageContent(models.Model):
    page_id = fields.BigIntField(primary_key=True)
    content = fields.TextField(description="内容")

    class Meta:
        table = "page_contents"
        table_description = "已爬取页面内容"

class PageSignature(models.Model):
    id = fields.BigIntField(primary_key=True, generated=True)
    signature = fields.CharField(max_length=32, description="页面url的md5值", unique=True)

    class Meta:
        table = "page_signatures"
        table_description = "已爬取页面签名"

class PushSubscription(models.Model):
    id = fields.IntField(primary_key=True, generated=True)
    site_id = fields.IntField(description="站点ID", index=True)
    staff_number = fields.CharField(max_length=10, description="工号")
    filter_keywords = fields.TextField(description="过滤关键词")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")

    class Meta:
        table = "push_subscriptions"
        table_description = "站点新内容推送订阅列表"

class DomainBlacklist(models.Model):
    id = fields.IntField(primary_key=True, generated=True)
    domain = fields.CharField(max_length=255, description="域名", unique=True)
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")

    class Meta:
        table = "domain_blacklist"
        table_description = "域名黑名单"

class CrawlRequest(models.Model):
    id = fields.IntField(primary_key=True, generated=True)
    stuff_name = fields.TextField(description="工号")
    stuff_number = fields.CharField(max_length=16, description="工号")
    content = fields.TextField(description="内容")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")

    class Meta:
        table = "crawl_requests"
        table_description = "采集请求"

class WebSearchNews(models.Model):
    id = fields.IntField(primary_key=True, generated=True)
    company = fields.CharField(max_length=24, description="公司", index=True)
    title = fields.TextField(description="标题")
    url = fields.TextField(description="URL")
    signature = fields.CharField(max_length=32, description="签名", index=True)
    website = fields.TextField(description="网站")
    date = fields.DatetimeField(description="日期")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")

    class Meta:
        table = "web_search_news"
        table_description = "网络搜索新闻"