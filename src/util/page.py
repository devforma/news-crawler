import hashlib

# 检查文章是否命中关键词
def is_hit_keywords(title: str, content: str, filter_keywords: str) -> bool:
    if not filter_keywords:
        return True

    keywords = filter_keywords.split(",")
    text = f"{title} {content}"
    return any(keyword in text for keyword in keywords)

# 获取页面url签名
def get_signature(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()

