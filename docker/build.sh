#!/bin/bash

cp -r ../src .

docker build -t devforma/news-crawler:latest .

rm -r ./src