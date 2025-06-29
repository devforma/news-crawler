import aiohttp
import json
from typing import Any

class HttpClient:
    _http_connector: aiohttp.TCPConnector | None = None
    _http_timeout: aiohttp.ClientTimeout | None = None

    @classmethod
    async def init(cls, conn_limit: int = 10, conn_limit_per_host: int = 10, timeout: int = 10):
        cls._http_connector = aiohttp.TCPConnector(limit=conn_limit, limit_per_host=conn_limit_per_host, verify_ssl=False)
        cls._http_timeout = aiohttp.ClientTimeout(total=timeout)
    
    @classmethod
    async def get(cls, url: str, headers: dict[str, str] = {}) -> Any:
        if cls._http_connector is None:
            raise ConnectionError("Http connector not initialized")
        
        async with aiohttp.ClientSession(connector=cls._http_connector) as session:
            async with session.get(url, headers=headers, timeout=cls._http_timeout) as response:
                return await response.json()

    @classmethod
    async def post(cls, url: str, data: Any, headers: dict[str, str] = {}) -> Any:
        if cls._http_connector is None:
            raise ConnectionError("Http connector not initialized")

        headers["Content-Type"] = "application/json"
        async with aiohttp.ClientSession(connector=cls._http_connector) as session:
            async with session.post(url, headers=headers, data=json.dumps(list(data.keys())), timeout=cls._http_timeout) as response:
                return await response.json()