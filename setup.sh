#!/bin/sh

docker build -t picabot .
docker run -d --env-file .env --name picabot --rm picabot
