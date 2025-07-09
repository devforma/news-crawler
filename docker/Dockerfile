FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements.txt .
COPY entrypoint.sh .

ENV TZ=Asia/Shanghai

RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt update && apt install -y tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir -r requirements.txt && \
    playwright install --with-deps --no-shell chromium && \
    rm -rf /var/lib/apt/lists/*

COPY src/. .

ENTRYPOINT ["/app/entrypoint.sh"]