from http import HTTPStatus
import dashscope
from dashscope.api_entities.dashscope_response import Message

class Bailian:
    _api_key: str = ""

    @classmethod
    def init(cls, api_key: str):
        cls._api_key = api_key

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
                    content="你是一个专业的内容分析和总结助手。你的任务是从给定的网页文本内容中生成一段简洁精炼的摘要。请用中文回复，纯文本，不要输出markdown格式，不要输出任何其他内容。如果无法根据内容生成摘要，请返回失败原因。",
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
            return f"调用通义千问进行内容摘要失败，响应码: {response.status_code}, 错误信息: {response.message}"
        else:
            return response.output.text
