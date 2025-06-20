# !/bin/bash

set -ex

aws ecr get-login-password --region us-east-2 --profile kendall | docker login --username AWS --password-stdin 340531845404.dkr.ecr.us-east-2.amazonaws.com
docker buildx build --platform linux/amd64 -t tgov_linux . --provenance=false
export tag=$(date +%s)
docker tag tgov_linux 340531845404.dkr.ecr.us-east-2.amazonaws.com/tgov:$tag
docker tag tgov_linux 340531845404.dkr.ecr.us-east-2.amazonaws.com/tgov:latest
docker push 340531845404.dkr.ecr.us-east-2.amazonaws.com/tgov:$tag
docker push 340531845404.dkr.ecr.us-east-2.amazonaws.com/tgov:latest
