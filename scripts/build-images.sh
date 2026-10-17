#!/bin/bash
set -e

# Creates the ACR and builds/pushes all 18 FIND service images.
#
# FIND is one integrated application: 3 shared services + 5 student modules
# (frontend/backend/database each) = 18 images. Each service directory is a
# self-contained Docker build context with its own Dockerfile.

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
# Admin user is enabled so images can be pushed with `docker login` from CI:
# ACR Tasks (`az acr build`) are not available on this subscription tier, so images
# are built locally with Docker and pushed instead.
echo "Creating Azure Container Registry..."
az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$REGISTRY_NAME" \
  --sku Basic \
  --admin-enabled true

# Ensure admin is enabled even if the registry already existed (e.g. from a prior run).
az acr update --name "$REGISTRY_NAME" --admin-enabled true

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

# Step 2c: Authenticate Docker to the registry using its admin credentials.
echo "Logging Docker in to $LOGIN_SERVER..."
ACR_USERNAME=$(az acr credential show --name "$REGISTRY_NAME" --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$REGISTRY_NAME" --query "passwords[0].value" -o tsv)
echo "$ACR_PASSWORD" | docker login "$LOGIN_SERVER" --username "$ACR_USERNAME" --password-stdin

# Step 3: Build and push all 18 container images.
# Each entry is "image-name|build-context".
SERVICES=(
  "shared-frontend|shared/frontend"
  "shared-api|shared/backend"
  "shared-db|shared/database"
  "student-1-frontend|student-1/frontend"
  "student-1-backend|student-1/backend"
  "student-1-db|student-1/database"
  "student-2-frontend|student-2/frontend"
  "student-2-backend|student-2/backend"
  "student-2-db|student-2/database"
  "student-3-frontend|student-3/frontend"
  "student-3-backend|student-3/backend"
  "student-3-db|student-3/database"
  "student-4-frontend|student-4/frontend"
  "student-4-backend|student-4/backend"
  "student-4-db|student-4/database"
  "student-5-frontend|student-5/frontend"
  "student-5-backend|student-5/backend"
  "student-5-db|student-5/database"
)

for entry in "${SERVICES[@]}"; do
  IMAGE_NAME="${entry%%|*}"
  CONTEXT="${entry##*|}"
  echo "Building and pushing ${IMAGE_NAME} image (context: ${CONTEXT})..."
  docker build --tag "${LOGIN_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}" "./${CONTEXT}"
  docker push "${LOGIN_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}"
done

echo "=== Image Build Complete ==="
