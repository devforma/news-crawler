## run http server

```shell
docker run -d --name news-crawler-server --rm -p 8000:8000 -v ./.env:/app/.env news-crawler server
```


## run crawler

```shell
docker run -d --name news-crawler-crawler-1 --rm -v ./.env:/app/.env news-crawler crawler
```