#!/bin/bash
set -e

# Creates the resource group and tags it with generated deployment names.
#
# FIND adaptation: the integrated app has fixed Container App names (shared-* and
# student-N-*), so only the globally-unique registry and environment names are
# generated/tagged here. deploy-azure.sh derives every Container App name directly.

RESOURCE_GROUP="${RESOURCE_GROUP:-find-rg}"
LOCATION="${LOCATION:-australiaeast}"

echo "=== FIND Cloud Deployment: Environment Setup ==="

echo "Registering required resource providers (skips if already registered)..."
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait
az provider register --namespace Microsoft.ContainerRegistry --wait

EXISTING_REGISTRY=$(az group show --name "$RESOURCE_GROUP" --query "tags.registryName" -o tsv 2>/dev/null || true)

if [[ -n "$EXISTING_REGISTRY" ]]; then
  echo "Resource group $RESOURCE_GROUP is already configured — reusing existing names."
  az group show --name "$RESOURCE_GROUP" --query tags -o table
  exit 0
fi

REGISTRY_NAME="findregistry${RANDOM}"
ENV_NAME="find-aca-env-${RANDOM}"

echo "Creating resource group..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

echo "Tagging resource group with deployment names..."
az group update \
  --name "$RESOURCE_GROUP" \
  --tags registryName="$REGISTRY_NAME" envName="$ENV_NAME" location="$LOCATION"

echo "=== Environment Setup Complete ==="
az group show --name "$RESOURCE_GROUP" --query tags -o table
