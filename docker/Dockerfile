FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements.txt .
COPY entrypoint.sh .

RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install --with-deps chromium

COPY ../src/* .

ENTRYPOINT ["entrypoint.sh"]

