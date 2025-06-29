from tortoise import Tortoise
from tortoise.backends.base.config_generator import generate_config
from settings import Settings

# 初始化数据库连接
async def init_db(settings: Settings):
    await Tortoise.init(
        db_url=_compose_db_url(settings=settings),
        modules={'models': ['database.models']}
    )

async def close_db():
    await Tortoise.close_connections()

# 组合数据库URL
def _compose_db_url(settings: Settings) -> str:
    return f'postgres://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_dbname}?maxsize={settings.postgres_connection_pool_size}'

# 生成Tortoise配置
def generate_tortoise_config(settings: Settings):
    return generate_config(
        _compose_db_url(settings=settings),
        app_modules={'models': ['database.models']}
    )