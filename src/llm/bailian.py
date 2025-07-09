import asyncio
from http import HTTPStatus
import dashscope
from dashscope.api_entities.dashscope_response import Message

class Bailian:
    _api_key: str = ""
    _interpretation_app_id: str = ""

    summary_prompt = """
    你是一个专业的内容摘要总结助手。你的任务是从给定的网页文本内容中生成一段简洁精炼的中文摘要。如果原文内容是英语，需要生成中文摘要，纯文本，不要输出markdown格式，不要输出除了摘要内容本身以外的任何其他内容，禁止输出“摘要”二字。如果无法生成摘要，请返回'大模型生成摘要失败，请查看原文'。
    """

    @classmethod
    def init(cls, api_key: str, interpretation_app_id: str):
        cls._api_key = api_key
        cls._interpretation_app_id = interpretation_app_id

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
