import time
from log.logger import server_logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        server_logger.info(
            f"{request.method} {request.url.path} "
            f"{response.status_code} "
            f"{process_time*1000:.1f}ms " 
            f"- {request.client.host}:{request.client.port} "
        )
        return response
