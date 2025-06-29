#!/bin/bash

if [ "$1" = "crawler" ]; then
    exec python crawler.py
fi

if [ "$1" = "server" ]; then
    exec python server.py
fi