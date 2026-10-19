#!/bin/bash
set -e

# Creates the ACR and builds/pushes all 21 FIND service images.
#
# FIND is one integrated application: 3 shared services + 5 student modules
# (frontend/backend/database each) + 3 shared AI servers (mcp/rag/multi-agent)
# = 21 images. Each service directory is a self-contained Docker build context
# with its own Dockerfile.

echo "=== FIND Cloud Deployment: Image Build ==="

RESOURCE_GROUP="${RESOURCE_GROUP:-find-rg}"
IMAGE_TAG="latest"

# Step 1: Read the registry name from resource group tags
REGISTRY_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.registryName" -o tsv)

if [[ -z "$REGISTRY_NAME" ]]; then
  echo "Resource group $RESOURCE_GROUP is missing deployment tags. Run scripts/env-setup.sh first." >&2
  exit 1
fi

# Step 2: Create Azure Container Registry.
# Admin user stays DISABLED: images are pushed with the Azure identity (OIDC in CI,
# `az login` locally) via `az acr login`, not a stored username/password.
# ACR Tasks (`az acr build`) are not available on this subscription tier, so images
# are built locally with Docker and pushed instead.
echo "Creating Azure Container Registry..."
az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$REGISTRY_NAME" \
  --sku Basic \
  --admin-enabled false

# Ensure admin stays disabled even if the registry already existed (e.g. from a prior run).
az acr update --name "$REGISTRY_NAME" --admin-enabled false

# Step 2b: Wait for the registry's DNS name to propagate before pushing.
# A fresh ACR can report "created" before *.azurecr.io resolves, causing
# the first `docker push` to fail with "no such host".
LOGIN_SERVER="${REGISTRY_NAME}.azurecr.io"
echo "Waiting for $LOGIN_SERVER to resolve..."
for i in $(seq 1 24); do
  if getent hosts "$LOGIN_SERVER" >/dev/null 2>&1; then
    echo "$LOGIN_SERVER is resolvable."
    break
  fi
  if [[ "$i" -eq 24 ]]; then
    echo "Timed out waiting for $LOGIN_SERVER to resolve." >&2
    exit 1
  fi
  sleep 5
done

# Step 2c: Authenticate Docker to the registry with the Azure identity (passwordless).
# The workflow signs in with OIDC via azure/login; locally this uses your `az login`.
# The identity already holds subscription-wide Contributor (which permits push), but
# grant AcrPush at the registry scope too so it also works on ABAC-enabled registries,
# then allow for role-assignment propagation before logging in.
echo "Ensuring the current identity can push to $REGISTRY_NAME..."
REGISTRY_ID=$(az acr show --name "$REGISTRY_NAME" --query id -o tsv)
PRINCIPAL=$(az account show --query user.name -o tsv)
if [[ -n "$PRINCIPAL" && -n "$REGISTRY_ID" ]]; then
  EXISTING_ACRPUSH=$(az role assignment list --assignee "$PRINCIPAL" --role AcrPush --scope "$REGISTRY_ID" --query "[0].id" -o tsv 2>/dev/null || true)
  if [[ -z "$EXISTING_ACRPUSH" ]]; then
    echo "Granting AcrPush on the registry to $PRINCIPAL..."
    az role assignment create --assignee "$PRINCIPAL" --role AcrPush --scope "$REGISTRY_ID" >/dev/null || true
  fi
fi

echo "Logging Docker in to $LOGIN_SERVER via az acr login..."
for i in $(seq 1 10); do
  if az acr login --name "$REGISTRY_NAME"; then
    break
  fi
  if [[ "$i" -eq 10 ]]; then
    echo "az acr login failed after waiting for role propagation." >&2
    exit 1
  fi
  echo "az acr login not ready (attempt $i); waiting for role propagation..."
  sleep 15
done

# Step 3: Build and push all 21 container images.
# Each entry is "image-name|build-context|dockerfile". Frontends build from the repo
# root so their images can bake in the shared CSS/JS that compose provides via volumes.
# The mcp-server and rag-server likewise build from the repo root so they can bake in the
# docs/README evidence their shared tools read.
SERVICES=(
  "shared-frontend|.|shared/frontend/Dockerfile"
  "shared-api|shared/backend|shared/backend/Dockerfile"
  "shared-db|shared/database|shared/database/Dockerfile"
  "student-1-frontend|.|student-1/frontend/Dockerfile"
  "student-1-backend|student-1/backend|student-1/backend/Dockerfile"
  "student-1-db|student-1/database|student-1/database/Dockerfile"
  "student-2-frontend|.|student-2/frontend/Dockerfile"
  "student-2-backend|student-2/backend|student-2/backend/Dockerfile"
  "student-2-db|student-2/database|student-2/database/Dockerfile"
  "student-3-frontend|.|student-3/frontend/Dockerfile"
  "student-3-backend|student-3/backend|student-3/backend/Dockerfile"
  "student-3-db|student-3/database|student-3/database/Dockerfile"
  "student-4-frontend|.|student-4/frontend/Dockerfile"
  "student-4-backend|student-4/backend|student-4/backend/Dockerfile"
  "student-4-db|student-4/database|student-4/database/Dockerfile"
  "student-5-frontend|.|student-5/frontend/Dockerfile"
  "student-5-backend|student-5/backend|student-5/backend/Dockerfile"
  "student-5-db|student-5/database|student-5/database/Dockerfile"
  "mcp-server|.|mcp-server/Dockerfile"
  "rag-server|.|rag-server/Dockerfile"
  "multi-agent-server|multi-agent-server|multi-agent-server/Dockerfile"
)

for entry in "${SERVICES[@]}"; do
  IFS='|' read -r IMAGE_NAME CONTEXT DOCKERFILE <<< "$entry"
  echo "Building and pushing ${IMAGE_NAME} image (context: ${CONTEXT}, dockerfile: ${DOCKERFILE})..."
  docker build --file "$DOCKERFILE" --tag "${LOGIN_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}" "$CONTEXT"
  docker push "${LOGIN_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}"
done

echo "=== Image Build Complete ==="
