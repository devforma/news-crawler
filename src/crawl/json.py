from log.logger import crawl_logger
from jsonpath_ng import parse
from dataclasses import dataclass

from util.http import HttpClient

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
}

# 爬取列表页
async def crawl_list_using_json(url: str, rule: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    if len(rule) < 4:
        crawl_logger.error(f"CrawlList using json failed: {url} rule length is less than 4")
        return {}, {}

    extract_rule = JsonExtractRule(
        base_path=rule[0],
        title_path=rule[1],
        url_path=rule[2],
        compose_template=rule[3],
        display_url=rule[4] if len(rule) == 5 else ""
    )
    try:
        data = await HttpClient.get(url, headers=headers)
        return extract_json_data(data, extract_rule)

    except Exception as e:
        crawl_logger.error(f"CrawlList using json failed: {url} {e}")
        return {}, {}


@dataclass
class JsonExtractRule:
    base_path: str
    title_path: str
    url_path: str
    compose_template: str
    display_url: str


# 提取json数据，返回url到标题的映射
def extract_json_data(root: dict, rule: JsonExtractRule) -> tuple[dict[str, str], dict[str, str]]:
    # 解析jsonpath表达式
    base_expr = parse(rule.base_path)
    title_expr = parse(rule.title_path)
    url_expr = parse(rule.url_path)
    display_url_expr = parse(rule.display_url) if rule.display_url else None

    results = {}
    display_url_results = {}

    url_list = base_expr.find(root)  # 提取列表
    for item in url_list:
        title = title_expr.find(item.value)[0].value  # 提取标题
        url = url_expr.find(item.value)[0].value  # 提取url

        # 根据预设模板拼接url
        if rule.compose_template:
            url = rule.compose_template.replace("$", url)
        results[url] = title

        if display_url_expr: # 如果配置了显示url，则将显示url和url拼接起来
            display_url = display_url_expr.find(item.value)[0].value
            display_url_results[url] = display_url

    return results, display_url_results
