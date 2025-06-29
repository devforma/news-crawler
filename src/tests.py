import asyncio
from crawl.json import JsonExtractRule, crawl_list_using_json, extract_json_data
from crawl.util import duplicate_url
from core.http import HttpClient


print(12 + (1231 or 300))


async def test_duplicate_url():
    await HttpClient.init(conn_limit=10, conn_limit_per_host=10, timeout=10)
    s = {"da": 1}

    urls = {
      "https://www.baidu.com": "title1",
      "https://www.baidus.com": "title2",
    }
    deduplicated_urls = await duplicate_url("http://localhost:8000/crawl/deduplicate", urls)
    print(deduplicated_urls)


def test_extract_json_data():
    s = {
      "title": "十字路口Crossing",
      "home_page_url": "/feeds/MP_WXS_3010319264.json",
      "description": "AI 正在给各行各业带来改变，我们在「十字路口」关注变革与机会，寻找、访谈和凝聚 AI 时代的「积极行动者」，和他们一起，探索和拥抱，新变化，新的可能性。「十字路口」是乔布斯形容苹果公司站在科技与人文的十字路口，伟大的产品往往诞生在这里。",
      "items": [
        {
          "id": "FoRKhydaa65jYEXcInwQNQ",
          "content_html": "",
          "url": "https://mp.weixin.qq.com/s/FoRKhydaa65jYEXcInwQNQ",
          "title": "谢谢 OpenAI，谢谢 o3，新的「套壳」创业机会来了 | 附 12 个潜力方向",
          "image": "https://mmbiz.qpic.cn/mmbiz_jpg/FFcNSoQ3Kict7PKrLvrIq46DxfrvbzssSGAhmaR2F8zuqpxiabha6jcdInAibAMrRVNBVjY78ABoMmSmZk0icJKWHg/0?wx_fmt=jpeg",
          "date_modified": "2025-04-23T08:43:55.000Z"
        },
        {
          "id": "1vXrC9W9wR-DPh28bT6Zlw",
          "content_html": "",
          "url": "https://mp.weixin.qq.com/s/1vXrC9W9wR-DPh28bT6Zlw",
          "title": "成为一个「接地气」的AI创业者分几步？从Google X研究员到做出6个月100万ARR的产品｜对谈Vozo创始人周昌印",
          "image": "https://mmbiz.qpic.cn/mmbiz_jpg/FFcNSoQ3Kicv5uaQGs8u0BAtaicmaCOS8RPKrPia6hTPG3qXDvD9XXAOC3tREZJ6mEeIMwU3G1mtPeh8MAgCtvKnQ/0?wx_fmt=jpeg",
          "date_modified": "2025-04-12T14:45:47.000Z"
        }
      ]
    }
    s = extract_json_data(s, JsonExtractRule(base_path='$.items', title_path='$[*].title', url_path='$[*].id', compose_template='https://mp.weixin.qq.com/s/$'))
    print(s)


if __name__ == "__main__":
    asyncio.run(test_duplicate_url())