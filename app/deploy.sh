#!/usr/bin/env bash
# Build the app image and push it to this deployment's ACR.
# Reads names from Terraform outputs of the selected workspace.
#   ./app/deploy.sh v1            build locally with Docker and push (default)
#   ./app/deploy.sh v1 --acr      build in Azure with ACR Tasks (not allowed on free-trial subscriptions)
set -euo pipefail

TAG="${1:?usage: ./deploy.sh <tag> [--acr]   e.g. v1}"
MODE="${2:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
TF_DIR="$HERE/../deploy/terraform/azure/infra"

ACR_NAME="$(terraform -chdir="$TF_DIR" output -raw acr_name)"
ACR_SERVER="$(terraform -chdir="$TF_DIR" output -raw acr_login_server)"
IMAGE="$ACR_SERVER/dqlite-api:$TAG"
echo "==> workspace: $(terraform -chdir="$TF_DIR" workspace show)   image: $IMAGE"

if [ "$MODE" = "--acr" ]; then
  az acr build --registry "$ACR_NAME" --image "dqlite-api:$TAG" --platform linux/amd64 "$HERE"
else
  # App Service runs linux/amd64; on Apple Silicon Docker builds it under emulation.
  docker build --platform linux/amd64 -t "$IMAGE" "$HERE"
  az acr login --name "$ACR_NAME"
  docker push "$IMAGE"
fi

echo
echo "Image pushed: $IMAGE"
echo "Next: set app_image = \"dqlite-api:$TAG\" in the environment .tfvars and run terraform apply."
