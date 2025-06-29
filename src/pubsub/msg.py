from pydantic import BaseModel

from database.models import CrawlType

class Msg(BaseModel):
    pass

class CrawlListPageMsg(Msg):
    site_id: int
    site_name: str
    url: str
    crawl_list_type: CrawlType
    crawl_detail_type: CrawlType
    rule: list[str]
    paywall: bool

class CrawlDetailPageMsg(Msg):
    site_id: int
    site_name: str
    title: str
    url: str
    crawl_detail_type: CrawlType

class CrawlPageContentMsg(Msg):
    site_id: int
    site_name: str
    title: str
    url: str
    date: str
    content: str
