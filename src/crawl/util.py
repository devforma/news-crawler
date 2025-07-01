from typing import Any
from urllib.parse import urljoin

from util.http import HttpClient
from log.logger import crawl_logger

# 浏览器黑名单域名列表
browser_blacklist_url_keys = [
    "google-analytics.com",
    "doubleclick.net",
    "ads.google.com",
    "hm.baidu.com",
]

def generate_extraction_schema(anchor_selectors: list[str]) -> dict[str, Any]:
    schema = {
        "baseSelector": "body",
        "fields": []
    }
    
    for i, anchor_selector in enumerate(anchor_selectors):
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
        results = await HttpClient.post(deduplicate_api, urls)
        return {url: title for url, title in urls.items() if url in results.get("data", [])}
    except Exception as e:
        crawl_logger.error(f"Duplicate url error: {e}")
        return {}