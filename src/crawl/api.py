

import hashlib
from pydantic import BaseModel
from log.logger import crawl_logger
from util.http import HttpClient


class ApiNews(BaseModel):
    title: str
    url: str
    website: str
    signature: str
    date: str

async def search_web_news(keywords: str) -> list[ApiNews]:
    url = "https://qianfan.baidubce.com/v2/ai_search/web_search"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer bce-v3/ALTAK-kswGLojd61ZfSwf862R9V/fe9415d5e9fe2d63c9155842a4e6bfa8f7049b51'
    }

    payload = {
        "messages": [{"role": "user", "content": keywords}],
        "edition": "standard",
        "search_source": "baidu_search_v2",
        "block_websites": [
            "baidu.com",
            "huawei.com",
            "cloud.tencent.com",
            "volcengine.com",
            "weibo.com",
            "douyin.com"
        ],
        "search_recency_filter": "week"
    }

    try:
        data = await HttpClient.post(url, data=payload, headers=headers)
        return [ApiNews(
            title=ref["title"],
            url=ref["url"],
            website=ref["website"],
            signature=hashlib.md5(ref["url"].encode()).hexdigest(),
            date=ref["date"]
        ) for ref in data["references"]]

    except Exception as e:
        crawl_logger.error(f"Search web news failed: {url} {e}")
        return []