import asyncio
import json
from crawl.api import search_web_news
from crawl.json import JsonExtractRule, crawl_list_using_json, extract_json_data
from crawl.util import duplicate_url, generate_extraction_schema, is_same_domain
from oss.store import OSS
from settings import get_settings
from util.http import HttpClient


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
    s = [
          {
            "feedPosts": [
          {
            "name": "homepage-story-card",
            "config": {
              "hed": "OpenAI is launching a version of ChatGPT for college students",
              "link": "https://www.technologyreview.com/2025/07/29/1120801/openai-is-launching-a-version-of-chatgpt-for-college-students/",
            }
          }
            ]
          }
    ]
    s, ss = extract_json_data(s, JsonExtractRule(base_path='$.[0].feedPosts[*]', title_path='$.config.hed', url_path='$.config.link', compose_template='', display_url=""))

    return s, ss


async def test_oss_upload():
    settings = get_settings()
    OSS.init(
        endpoint=settings.push_oss_endpoint,
        region=settings.push_oss_region,
        bucket=settings.push_oss_bucket,
        accesskey_id=settings.push_oss_accesskey_id,
        accesskey_secret=settings.push_oss_accesskey_secret
    )
    
    await OSS.upload("articles/2025-07-21/1.txt", "test")

async def test_search_web_news():
    await HttpClient.init(conn_limit=10, conn_limit_per_host=10, timeout=10)
    news = await search_web_news("华为", "gov")
    print(news)
    await HttpClient.shutdown()

if __name__ == "__main__":
    # asyncio.run(test_duplicate_url())
    # asyncio.run(test_oss_upload())


    # test_extract_json_data()

    # print(is_same_domain("http://xa.baidu.com/dawda/adawd", "https://www.baidu.com/s?wd=123"))

    # print(json.dumps(generate_extraction_schema(["div.news--item div.news--item-title a.sdaa | ada"]), indent=4))


    asyncio.run(test_search_web_news())