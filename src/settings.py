from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    # api server
    api_server_host: str = Field(description="API server host", default="0.0.0.0")
    api_server_port: int = Field(description="API server port", default=8000)

    # database
    postgres_host: str = Field(description="PostgreSQL host", default="localhost")
    postgres_port: int = Field(description="PostgreSQL port", default=5432)
    postgres_user: str = Field(description="PostgreSQL user", default="postgres")
    postgres_password: str = Field(description="PostgreSQL password", default="postgres")
    postgres_dbname: str = Field(description="PostgreSQL database name", default="news_crawler")
    postgres_connection_pool_size: int = Field(description="PostgreSQL connection pool size", default=10)

    # nats
    nats_host: str = Field(description="NATS host", default="localhost")
    nats_port: int = Field(description="NATS port", default=4222)
    nats_auth_token: str = Field(description="NATS auth token", default="")

    # dingtalk
    dingtalk_accesskey_id: str = Field(description="Dingtalk accesskey id", default="")
    dingtalk_accesskey_secret: str = Field(description="Dingtalk accesskey secret", default="")
    dingtalk_robot_code: str = Field(description="Dingtalk robot code", default="")

    # dashscope
    dashscope_api_key: str = Field(description="Dashscope api key", default="")

    # url deduplicate api
    url_deduplicate_api: str = Field(description="URL deduplicate api", default="")