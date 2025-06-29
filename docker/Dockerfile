FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements.txt .
COPY entrypoint.sh .

RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir -r requirements.txt && \
    playwright install --with-deps chromium && \
    rm -rf /var/lib/apt/lists/*

COPY src/. .

ENTRYPOINT ["entrypoint.sh"]