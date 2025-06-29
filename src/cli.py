import hashlib
from tortoise import run_async

from database.connection import init_db
from database.models import PageSignature, Site
from settings import Settings



async def main():
    await init_db(settings=Settings())

    # site = Site(
    #     name="dawda",
    #     category="news",
    #     listpage_url="https://www.baidu.com",
    #     listpage_crawl_type="html_static",
    #     listpage_parse_rule=[],
    #     detailpage_crawl_type="html_static",
    #     paywall=False,
    #     content_filter_keywords=""
    # )

    test_urls = [
        "https://www.baidu.com",
        "https://www.google.com",
        "https://www.qq.com",
    ]
    for i, url in enumerate(test_urls):
        sig = PageSignature(page_id=i+1, signature=hashlib.md5(url.encode()).hexdigest())
        await sig.save()

run_async(main())