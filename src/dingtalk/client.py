import json
import time
from alibabacloud_dingtalk.oauth2_1_0.client import Client as OAuthClient
from alibabacloud_dingtalk.robot_1_0.client import Client as RobotClient
from alibabacloud_dingtalk.oauth2_1_0.models import GetAccessTokenRequest
from alibabacloud_dingtalk.robot_1_0.models import BatchSendOTORequest, BatchSendOTOHeaders
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util.models import RuntimeOptions


class DingTalkClient:
    _token_cache: str = ""
    _token_expire: float = 0
    _robot_code: str = ""
    _accesskey_id: str = ""
    _accesskey_secret: str = ""
    _robot_client: RobotClient
    _oauth_client: OAuthClient

    @classmethod
    async def init(cls, accesskey_id: str, accesskey_secret: str, robot_code: str):
        cls._token_cache = ""
        cls._token_expire = 0
        cls._robot_code = robot_code
        cls._accesskey_id = accesskey_id
        cls._accesskey_secret = accesskey_secret

        config = open_api_models.Config(
            access_key_id=accesskey_id,
            access_key_secret=accesskey_secret,
            protocol="https",
        )

        cls._robot_client = RobotClient(config)
        cls._oauth_client = OAuthClient(config)

    @classmethod
    async def send_message(cls, user_id: str, title: str, summary: str, url: str, source: str = ""):
        await cls._robot_client.batch_send_otowith_options_async(
            request=BatchSendOTORequest(
                msg_key="sampleMarkdown",
                user_ids=[user_id],
                robot_code=cls._robot_code,
                msg_param=json.dumps(
                    {
                        "title": "订阅内容更新",
                        "text": f"""#### **{title}**

<font color="#4c4c4c">{summary}</font>

**[>> 查看原文 <<]({url})**

---

<font color="#9c9c9c">{source}</font>""",
                    }
                ),
            ),
            headers=BatchSendOTOHeaders(
                x_acs_dingtalk_access_token=await cls.get_access_token(),
            ),
            runtime=RuntimeOptions(),
        )

    @classmethod
    async def get_access_token(cls):
        current_time = time.time()

        if cls._token_cache != "" and current_time < cls._token_expire:
            return cls._token_cache

        try:
            res = await cls._oauth_client.get_access_token_async(
                request=GetAccessTokenRequest(app_key=cls._accesskey_id, app_secret=cls._accesskey_secret)
            )
        except Exception as e:
            raise Exception(f"Failed to get dingtalk accesstoken: {e}")

        if res.body.access_token:
            cls._token_cache = res.body.access_token
            cls._token_expire = current_time + (res.body.expire_in or 300)
            return cls._token_cache
        else:
            raise Exception(f"Failed to get dingtalk accesstoken")