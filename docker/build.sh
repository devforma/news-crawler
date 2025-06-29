#!/bin/bash

cp -r ../src .

docker build -t news-crawler:latest .