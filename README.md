## run http server

```shell
docker run --rm -p 8000:8000 -v ./.env:/app/.env news-crawler server
```


## run crawler

```shell
docker run --rm -v ./.env:/app/.env news-crawler crawler
```