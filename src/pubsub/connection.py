from nats.aio.client import Client
import nats
from settings import Settings

QUEUE_CRAWL_LISTPAGE = "crawl.listpage" # 列表页队列
QUEUE_CRAWL_DETAILPAGE = "crawl.detailpage" # 详情页队列
QUEUE_CRAWL_PAGECONTENT = "crawl.pagecontent" # 页面内容队列(爬取完成)

class MsgQueue:
    @classmethod
    async def connect(cls, settings: Settings) -> Client:
        return await nats.connect(
            f'nats://{settings.nats_host}:{settings.nats_port}',
            token=settings.nats_auth_token
        )