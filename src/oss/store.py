import asyncio
import oss2
from oss2.credentials import StaticCredentialsProvider
from log.logger import server_logger

class OSS:
    bucket: oss2.Bucket

    @classmethod
    def init(cls, endpoint: str, region:str, bucket: str, accesskey_id: str, accesskey_secret: str):
        auth = oss2.ProviderAuthV4(StaticCredentialsProvider(accesskey_id, accesskey_secret))
        cls.bucket = oss2.Bucket(auth=auth, endpoint=endpoint, bucket_name=bucket, region=region)

    @classmethod
    async def upload(cls, key: str, content: str):
        try:
            await asyncio.to_thread(cls.bucket.put_object, key, content)
        except oss2.exceptions.OssError as e:
            server_logger.error(f"OSS Upload failed, key: {key}, error: {e}")

    @classmethod
    async def delete(cls, key: str):
        try:
            await asyncio.to_thread(cls.bucket.delete_object, key)
        except oss2.exceptions.OssError as e:
            server_logger.error(f"OSS Delete failed, key: {key}, error: {e}")
