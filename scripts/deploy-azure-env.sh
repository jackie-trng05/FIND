#!/bin/bash
set -e

# Creates the Container Apps environment (run scripts/build-images.sh first,
# scripts/deploy-azure.sh after).
# Kept separate from deploy-azure.sh for OIDC token timing — the CI workflow runs a
# fresh `azure/login@v2` before this slow step and another before deploy-azure.sh.

echo "=== FIND Cloud Deployment: Container Apps Environment ==="

RESOURCE_GROUP="${RESOURCE_GROUP:-find-rg}"

# Step 1: Read deployment names from resource group tags
ENV_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.envName" -o tsv)
LOCATION=$(az group show --name "$RESOURCE_GROUP" --query "tags.location" -o tsv)

if [[ -z "$ENV_NAME" || -z "$LOCATION" ]]; then
  echo "Resource group $RESOURCE_GROUP is missing deployment tags. Run scripts/env-setup.sh first." >&2
  exit 1
fi

# Step 2: Create Container Apps environment
echo "Creating Container Apps environment..."
az containerapp env create \
  --name "$ENV_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION"

echo "=== Container Apps Environment Ready ==="
