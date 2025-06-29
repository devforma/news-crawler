from nats.aio.client import Client
import nats
from nats.aio.subscription import Subscription
from pubsub.msg import Msg
from settings import Settings

QUEUE_CRAWL_LISTPAGE = "crawl.listpage" # 列表页队列
QUEUE_CRAWL_DETAILPAGE = "crawl.detailpage" # 详情页队列
QUEUE_CRAWL_PAGECONTENT = "crawl.pagecontent" # 页面内容队列(爬取完成)

class MsgQueue:
    nats_client: Client

    @classmethod
    async def init(cls, settings: Settings):
        if not hasattr(cls, 'nats_client') or cls.nats_client.is_closed:
            cls.nats_client = await nats.connect(
                f'nats://{settings.nats_host}:{settings.nats_port}',
                token=settings.nats_auth_token
            )

    @classmethod
    async def publish(cls, subject: str, msg: Msg):
        if not hasattr(cls, 'nats_client') or cls.nats_client.is_closed:
            raise ConnectionError("MsgQueue is not initialized or closed.")
        await cls.nats_client.publish(subject, msg.model_dump_json().encode('utf-8'))

    @classmethod
    async def subscribe(cls, subject: str, worker_mode: bool = True) -> Subscription:
        if not hasattr(cls, 'nats_client') or cls.nats_client.is_closed:
            raise ConnectionError("MsgQueue is not initialized or closed.")
        
        if worker_mode:
            return await cls.nats_client.subscribe(subject, queue="workers")
        return await cls.nats_client.subscribe(subject)
    
    @classmethod
    async def close(cls):
        if hasattr(cls, 'nats_client') and not cls.nats_client.is_closed:
            await cls.nats_client.close()