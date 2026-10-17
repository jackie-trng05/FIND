#!/bin/bash
set -e

# One-time, local-only:
# - creates the Azure OIDC app registration (if missing)
# - pushes its identifiers to GitHub Actions secrets.
#
# FIND adaptation: app/credential names are FIND-scoped (no enrolment-app subfolder).

# Prevents Git Bash on Windows from rewriting --scope "/subscriptions/..." into a local file path.
export MSYS_NO_PATHCONV=1

APP_DISPLAY_NAME="find-github-oidc"

echo "=== FIND Cloud Deployment: GitHub Secrets Setup ==="

if ! az account show >/dev/null 2>&1; then
    az login
fi
echo "Logged in to Azure."

if ! gh auth status >/dev/null 2>&1; then
    gh auth login
    echo "Logged in to GitHub."
fi

REPO_URL=$(git config --get remote.origin.url)
REPO_SLUG=$(echo "$REPO_URL" | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')
BRANCH=$(git rev-parse --abbrev-ref HEAD)

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
CLIENT_ID=$(az ad app list --display-name "$APP_DISPLAY_NAME" --query "[0].appId" -o tsv)

if [ -z "$SUBSCRIPTION_ID" ]; then
    echo "No active subscription found on the current Azure login."
    echo "Run 'az account list --output table' to see available subscriptions, then 'az account set --subscription <id>' and re-run this script."
    exit 1
fi

if [ -z "$CLIENT_ID" ]; then
    echo "No app registration named '$APP_DISPLAY_NAME' found. Creating it..."
    CLIENT_ID=$(az ad app create --display-name "$APP_DISPLAY_NAME" --query appId -o tsv)
    az ad sp create --id "$CLIENT_ID"
    echo "Created app registration."
else
    echo "Found existing app registration '$APP_DISPLAY_NAME'."
fi
echo "Fetched subscription ID, tenant ID, and client ID from Azure."

# Re-synced on every run (not just at app creation) because GitHub's OIDC subject claim
# changes if the repo/owner is renamed or transferred, which would otherwise silently
# break login until this credential is brought back in line with the current repo identity.
# Repos renamed/transferred (or created) after 2026-07-15 use GitHub's immutable subject
# format (owner/repo IDs instead of names), so the IDs are fetched live rather than assumed.
OWNER_NAME=$(echo "$REPO_SLUG" | cut -d/ -f1)
REPO_NAME=$(echo "$REPO_SLUG" | cut -d/ -f2)
OWNER_ID=$(gh api "repos/${REPO_SLUG}" --jq '.owner.id')
REPO_ID=$(gh api "repos/${REPO_SLUG}" --jq '.id')
SUBJECT="repo:${OWNER_NAME}@${OWNER_ID}/${REPO_NAME}@${REPO_ID}:ref:refs/heads/${BRANCH}"

FED_CRED_NAME="find-github-actions"
EXISTING_FED_CRED=$(az ad app federated-credential list --id "$CLIENT_ID" --query "[?name=='$FED_CRED_NAME'].id" -o tsv 2>/dev/null || true)

FED_CRED_PARAMS="{\"name\":\"${FED_CRED_NAME}\",\"issuer\":\"https://token.actions.githubusercontent.com\",\"subject\":\"${SUBJECT}\",\"audiences\":[\"api://AzureADTokenExchange\"]}"

if [ -z "$EXISTING_FED_CRED" ]; then
    az ad app federated-credential create --id "$CLIENT_ID" --parameters "$FED_CRED_PARAMS"
    echo "Created federated credential with subject '$SUBJECT'."
else
    az ad app federated-credential update --id "$CLIENT_ID" --federated-credential-id "$FED_CRED_NAME" --parameters "$FED_CRED_PARAMS"
    echo "Synced federated credential to subject '$SUBJECT'."
fi

# Checked independently of app creation above: an earlier run may have created the app but
# failed before granting roles, so re-check/grant on every run rather than assuming it's done.
EXISTING_CONTRIBUTOR=$(az role assignment list --assignee "$CLIENT_ID" --role "Contributor" --scope "/subscriptions/$SUBSCRIPTION_ID" --query "[0].id" -o tsv 2>/dev/null || true)

if [ -z "$EXISTING_CONTRIBUTOR" ]; then
    az role assignment create \
      --assignee "$CLIENT_ID" \
      --role Contributor \
      --scope "/subscriptions/$SUBSCRIPTION_ID"
    echo "Granted Contributor role."
else
    echo "Contributor role already assigned."
fi

# Contributor alone excludes Microsoft.Authorization/roleAssignments/write, which
# deploy-azure.sh's `az containerapp create --registry-identity system` needs to
# auto-grant each container app's managed identity the AcrPull role.
EXISTING_UAA=$(az role assignment list --assignee "$CLIENT_ID" --role "User Access Administrator" --scope "/subscriptions/$SUBSCRIPTION_ID" --query "[0].id" -o tsv 2>/dev/null || true)

if [ -z "$EXISTING_UAA" ]; then
    az role assignment create \
      --assignee "$CLIENT_ID" \
      --role "User Access Administrator" \
      --scope "/subscriptions/$SUBSCRIPTION_ID"
    echo "Granted User Access Administrator role (needed for AcrPull role assignments in deploy-azure.sh)."
else
    echo "User Access Administrator role already assigned."
fi

# Grant the service principal the Directory Readers role so the Azure CLI can resolve
# principals via Microsoft Graph when creating role assignments. Without it,
# deploy-azure.sh's managed-identity registry auth emits "Failed to query ... Graph API"
# warnings (it still works, falling back to the object id). Requires the user running
# this script to be able to manage directory role memberships (tenant admin).
SP_OBJECT_ID=$(az ad sp show --id "$CLIENT_ID" --query id -o tsv)
DIR_READERS_TEMPLATE_ID="88d8e3e3-8f55-4a1e-953a-9b9898b8876b"
DIR_READERS_MEMBER=$(az rest --method GET \
  --uri "https://graph.microsoft.com/v1.0/servicePrincipals/${SP_OBJECT_ID}/memberOf" \
  --query "value[?roleTemplateId=='${DIR_READERS_TEMPLATE_ID}'] | [0].id" -o tsv 2>/dev/null || true)

if [ -n "$DIR_READERS_MEMBER" ]; then
    echo "Service principal already has the Directory Readers role."
else
    DIR_READERS_ROLE_ID=$(az rest --method GET \
      --uri "https://graph.microsoft.com/v1.0/directoryRoles" \
      --query "value[?roleTemplateId=='${DIR_READERS_TEMPLATE_ID}'].id | [0]" -o tsv 2>/dev/null || true)
    if [ -z "$DIR_READERS_ROLE_ID" ]; then
        DIR_READERS_ROLE_ID=$(az rest --method POST \
          --uri "https://graph.microsoft.com/v1.0/directoryRoles" \
          --headers "Content-Type=application/json" \
          --body "{\"roleTemplateId\":\"${DIR_READERS_TEMPLATE_ID}\"}" \
          --query id -o tsv)
    fi
    az rest --method POST \
      --uri "https://graph.microsoft.com/v1.0/directoryRoles/${DIR_READERS_ROLE_ID}/members/\$ref" \
      --headers "Content-Type=application/json" \
      --body "{\"@odata.id\":\"https://graph.microsoft.com/v1.0/directoryObjects/${SP_OBJECT_ID}\"}"
    echo "Granted Directory Readers role to the service principal."
fi

gh secret set AZURE_SUBSCRIPTION_ID --body "$SUBSCRIPTION_ID"
gh secret set AZURE_TENANT_ID --body "$TENANT_ID"
gh secret set AZURE_CLIENT_ID --body "$CLIENT_ID"
echo "Pushed AZURE_SUBSCRIPTION_ID, AZURE_TENANT_ID, and AZURE_CLIENT_ID to GitHub Actions secrets."

echo "=== GitHub Secrets Setup Complete ==="
