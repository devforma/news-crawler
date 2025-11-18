import asyncio
from http import HTTPStatus
import dashscope
from dashscope.api_entities.dashscope_response import Message

class Bailian:
    _api_key: str = ""
    _interpretation_app_id: str = ""

    summary_prompt = """
# 角色
你是世界一流的新闻主编，擅长根据文章的内容进行重点总结摘要。

## 技能
### 语言翻译
如果新闻内容为英文，必须流畅地翻译为中文

### 新闻摘要
- 为新闻编写内容摘要，清晰地概括这篇文章的主要内容，可以直接引用原文，不自己杜撰任何内容。尽可能详细地描述清楚这个新闻讲了一件什么事情、重点、背景、影响是什么。

要求：
- 摘要内容必须简洁明了。
- 保持客观公正，不引入个人观点或偏见。
- 不允许偷懒，需要全面准确，不能敷衍了事。如果内容有问题无法生成摘要，请返回'大模型生成摘要失败，请查看原文'"""

    @classmethod
    def init(cls, api_key: str, interpretation_app_id: str):
        cls._api_key = api_key
        cls._interpretation_app_id = interpretation_app_id


    @classmethod
    async def trigger_agent(cls, api_key:str, app_id: str) -> str:
        res = await asyncio.to_thread(dashscope.Application.call,
            app_id=app_id,
            api_key=api_key,
            prompt="触发",
            stream=False,
        )

        if res.status_code != HTTPStatus.OK:
            return f"大模型调用失败，响应码: {res.status_code}, 错误信息: {res.message}"
        else:
            return res.output.text

    @classmethod
    async def text_summary(cls, title: str, content: str) -> str:
        if content == "":
            return "文章内容采集失败，请查看原文"

        response = await dashscope.AioGeneration.call(
            api_key=cls._api_key,
            model="qwen-turbo",
            messages=[
                Message(
                    role="system",
                    content=cls.summary_prompt,
                ),
                Message(
                    role="user",
                    content=f"网页内容如下：\n\n标题：\n{title}\n\n正文：\n{content}",
                ),
            ],
            stream=False,
            result_format="text",
        )
        if response.status_code != HTTPStatus.OK:
            return f"大模型生成摘要失败，响应码: {response.status_code}, 错误信息: {response.message}"
        else:
            return response.output.text

    @classmethod
    async def rag_interpretation(cls, title: str, content: str) -> str:
        query = f"""网页markdown内容如下：\n\n标题：\n{title}\n\n正文：\n{content}"""
        response = await asyncio.to_thread(dashscope.Application.call,
            app_id=cls._interpretation_app_id,
            api_key=cls._api_key,
            prompt=query,
            stream=False,
        )
        if response.status_code != HTTPStatus.OK:
            return f"大模型调用失败，响应码: {response.status_code}, 错误信息: {response.message}"
        else:
            return response.output.text
