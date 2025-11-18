from dataclasses import dataclass
import hashlib
from typing import Any
from urllib.parse import urljoin, urlparse

from crawl.api import ApiNews
from database.models import DomainBlacklist, WebSearchNews
from util.http import HttpClient
from log.logger import crawl_logger

@dataclass
class DetailResult:
    content: str
    date: str


# 浏览器黑名单域名列表
browser_blacklist_url_keys = [
    "google-analytics.com",
    "doubleclick.net",
    "ads.google.com",
    "hm.baidu.com",
    "fwl.mot.gov.cn/jubac/sync/detailcollect.do", # 交通运输部信息收集, 请求会超时
]

def generate_extraction_schema(anchor_selectors: list[str]) -> dict[str, Any]:
    schema = {
        "baseSelector": "body",
        "fields": []
    }
    
    for i, anchor_selector in enumerate(anchor_selectors):
        if "|" in anchor_selector:
            new_anchor_selector = anchor_selector.split("|")[0].strip()
            title_selector = anchor_selector.split("|")[1].strip()

            schema["fields"].append({
                "name": f"list-{i}",
                "type": "list",
                "selector": new_anchor_selector,
                "fields": [
                    {
                        "name": "title",
                        "type": "text",
                        "selector": title_selector,
                    },
                    {
                        "name": "url",
                        "type": "attribute",
                        "attribute": "href",
                    }
                ]
            })
        else:
            schema["fields"].append({
                "name": f"list-{i}",
                "type": "list",
                "selector": anchor_selector,
                "fields": [
                    {
                        "name": "title",
                        "type": "text",
                    },
                    {
                        "name": "url",
                        "type": "attribute",
                        "attribute": "href",
                    }
                ]
            })

    return schema

# 过滤列表页的链接
def filter_links(base_url: str, links_groups: list[dict]) -> dict[str, str]:
    filtered_links = {}
    for links_group in links_groups:
        for links in links_group.values():
            for link in links:
                if "title" not in link or link["title"] == "": # 没有标题
                    continue
                if "url" not in link or link["url"] == "" or link["url"].startswith("javascript:"): # 没有链接或者链接是javascript
                    continue
                
                # 字典结构保证了链接是唯一的
                filtered_links[compose_url(base_url, link["url"])] = link["title"].strip()

    return filtered_links

# 拼接链接
def compose_url(entry_url: str, url: str) -> str:
    if url.startswith("http"):
        return url
    if url.startswith("//"):
        return f"https:{url}" if entry_url.startswith("https") else f"http:{url}"
    return urljoin(entry_url, url)

# 当前url列表与已爬取的url进行去重
async def duplicate_url(deduplicate_api: str, urls: dict[str, str]) -> dict[str, str]:
    try:
        results = await HttpClient.post(deduplicate_api, list(urls.keys()))
        return {url: title for url, title in urls.items() if url in results.get("data", [])}
    except Exception as e:
        crawl_logger.error(f"Duplicate url error: {e}")
        return {}

# 判断两个url是否是同一个域名
def is_same_domain(url1: str, url2: str) -> bool:
    url1_parsed = urlparse(url1)
    url2_parsed = urlparse(url2)
    return url1_parsed.netloc == url2_parsed.netloc

# 滤重
async def duplicate_search_web_news(news: list[ApiNews]) -> list[ApiNews]:
    filtered_news = []

    domin_blacklist = await DomainBlacklist.all().values_list("domain", flat=True)

    titles = []
    for news_item in news:
        if any(domain in news_item.url for domain in domin_blacklist):
            continue
        
        # 标题先滤重
        if news_item.title in titles:
            continue
        titles.append(news_item.title)

        # url滤重
        if await WebSearchNews.filter(signature=news_item.signature).exists():
            continue
        filtered_news.append(news_item)
    

    return filtered_news