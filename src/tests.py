import asyncio
import json
from crawl.api import search_web_news
from crawl.json import JsonExtractRule, crawl_list_using_json, extract_json_data
from crawl.util import duplicate_url, generate_extraction_schema, is_same_domain
from llm import bailian
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
    urls = await duplicate_url("http://8.217.57.144:8081/crawl/deduplicate", {"http://221.228.10.206:8082/article?article_id=3236757533-2247844501_1":"dadwa"})

    urls = await HttpClient.post("http://8.217.57.144:8081/crawl/deduplicate", ["http://221.228.10.206:8082/article?article_id=3236757533-2247844501_1"])
    print(urls)
    await HttpClient.shutdown()

if __name__ == "__main__":
    # asyncio.run(test_duplicate_url())
    # asyncio.run(test_oss_upload())

    # asyncio.run(test_search_web_news())


    # test_extract_json_data()

    # print(is_same_domain("http://xa.baidu.com/dawda/adawd", "https://www.baidu.com/s?wd=123"))

    # print(json.dumps(generate_extraction_schema(["div.news--item div.news--item-title a.sdaa | ada"]), indent=4))


    # asyncio.run(test_search_web_news())
    # bailian.Bailian.init("sk-47a5f6599d304a449b3c79020baab081", "842a1aaa3998431da0127f17e0dd1a20")
    # a = asyncio.run(bailian.Bailian.text_summary("东北地区首座跨省“异地货站”启用[11-18]", "东北地区首座跨省“异地货站”在大连国际机场和鄂州花湖国际机场之间启用，标志着双方合作搭建了“华中—大连—日韩”“大连—华中—全球”的双向航空货运通道，有效缓解东北地区欧美航线运力不足的问题，推动特色产品走向世界，同时助力华中地区货物辐射东北亚。启用当日，一批服装货物从大连经鄂州中转发往纽约，运输时间由4天缩短至2天，效率提升一倍。"))
    # print(a)


    # s = "华为携手伙伴共筑算力基石专场活动成功举办 "
    # print(s.strip())