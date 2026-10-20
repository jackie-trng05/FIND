#!/bin/bash
set -e

# Deploys all 18 FIND services to an existing Container Apps environment
# (run scripts/deploy-azure-env.sh first).
#
# Ingress plan (FIND is browser-driven via *_PUBLIC_URL env vars):
#   external  -> shared-frontend, shared-api, every student-N-frontend, every student-N-backend
#   internal  -> shared-db, every student-N-db
#
# Cross-service URLs form a cycle (shared-frontend needs student frontend URLs;
# student frontends need shared-frontend's LOGIN_URL/FIND_HOME_URL). Azure Container
# Apps FQDNs are deterministic once the environment exists:
#   external:  https://<app>.<envDefaultDomain>
#   internal:  https://<app>.internal.<envDefaultDomain>
# so every URL is computed up front from the environment's default domain, which
# breaks the cycle without ordering constraints.
#
# Deployment profile: when OPENROUTER_API_KEY is set, the full AI stack is
# deployed — the mcp-server, rag-server and multi-agent-server run as internal
# Container Apps and the LLM (AI-Mode / RAG generation / multi-agent) runs on
# OpenRouter (Ollama is local-only and unavailable in the cloud). When the key
# is absent, AI_MODE/MCP/RAG/MULTI_AGENT stay disabled and those apps are skipped.

echo "=== FIND Cloud Deployment: Azure ==="

RESOURCE_GROUP="${RESOURCE_GROUP:-find-rg}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse HEAD)}"

# Step 1: Read deployment names from resource group tags
REGISTRY_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.registryName" -o tsv)
ENV_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.envName" -o tsv)

if [[ -z "$REGISTRY_NAME" || -z "$ENV_NAME" ]]; then
  echo "Resource group $RESOURCE_GROUP is missing deployment tags. Run scripts/env-setup.sh first." >&2
  exit 1
fi

REGISTRY_SERVER=$(az acr show --name "$REGISTRY_NAME" --resource-group "$RESOURCE_GROUP" --query loginServer -o tsv)

# Step 1b: Provision a shared user-assigned managed identity for ACR pulls and grant it
# AcrPull on the registry. One pre-provisioned identity (instead of a system-assigned
# identity per app) lets us create the role assignment with an explicit object id and
# principal type, which avoids the "Failed to query ... by invoking Graph API" warning
# the implicit per-app grant emits when the deploying identity can't read the directory.
ACR_PULL_IDENTITY_NAME="find-acr-pull"
echo "Ensuring ACR pull identity ${ACR_PULL_IDENTITY_NAME} exists..."
az identity create --resource-group "$RESOURCE_GROUP" --name "$ACR_PULL_IDENTITY_NAME" >/dev/null
ACR_PULL_IDENTITY_ID=$(az identity show --resource-group "$RESOURCE_GROUP" --name "$ACR_PULL_IDENTITY_NAME" --query id -o tsv)
ACR_PULL_PRINCIPAL_ID=$(az identity show --resource-group "$RESOURCE_GROUP" --name "$ACR_PULL_IDENTITY_NAME" --query principalId -o tsv)
REGISTRY_ID=$(az acr show --name "$REGISTRY_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv)

EXISTING_ACRPULL=$(az role assignment list --assignee "$ACR_PULL_PRINCIPAL_ID" --role AcrPull --scope "$REGISTRY_ID" --query "[0].id" -o tsv 2>/dev/null || true)
if [[ -z "$EXISTING_ACRPULL" ]]; then
  echo "Granting AcrPull on the registry to the pull identity..."
  az role assignment create \
    --assignee-object-id "$ACR_PULL_PRINCIPAL_ID" \
    --assignee-principal-type ServicePrincipal \
    --role AcrPull \
    --scope "$REGISTRY_ID" >/dev/null
  # Allow the role assignment to propagate before the apps pull images.
  sleep 30
fi

# Step 2: Resolve the environment's default domain and precompute all FQDNs
DEFAULT_DOMAIN=$(az containerapp env show --name "$ENV_NAME" --resource-group "$RESOURCE_GROUP" \
  --query properties.defaultDomain -o tsv)

if [[ -z "$DEFAULT_DOMAIN" ]]; then
  echo "Could not resolve Container Apps environment default domain. Run scripts/deploy-azure-env.sh first." >&2
  exit 1
fi

ext() { echo "https://$1.${DEFAULT_DOMAIN}"; }            # external app FQDN
intu() { echo "https://$1.internal.${DEFAULT_DOMAIN}"; }   # internal app FQDN

SHARED_FRONTEND_URL=$(ext shared-frontend)
SHARED_API_URL=$(ext shared-api)
SHARED_DB_URL=$(intu shared-db)

S1_FE=$(ext student-1-frontend); S1_BE=$(ext student-1-backend); S1_DB=$(intu student-1-db)
S2_FE=$(ext student-2-frontend); S2_BE=$(ext student-2-backend); S2_DB=$(intu student-2-db)
S3_FE=$(ext student-3-frontend); S3_BE=$(ext student-3-backend); S3_DB=$(intu student-3-db)
S4_FE=$(ext student-4-frontend); S4_BE=$(ext student-4-backend); S4_DB=$(intu student-4-db)
S5_FE=$(ext student-5-frontend); S5_BE=$(ext student-5-backend); S5_DB=$(intu student-5-db)

LOGIN_URL="${SHARED_FRONTEND_URL}/login"
FIND_HOME_URL="${SHARED_FRONTEND_URL}/dashboard"
ALLOWED_ORIGINS="${SHARED_FRONTEND_URL},${S1_FE},${S2_FE},${S3_FE},${S4_FE},${S5_FE}"

# Internal AI-server FQDNs (deterministic once the environment exists), reached
# only by the student backends and the rag-server inside the environment.
MCP_SERVER_URL="$(intu mcp-server)/mcp"
RAG_SERVER_URL=$(intu rag-server)
MULTI_AGENT_SERVER_URL=$(intu multi-agent-server)

# Cloud LLM (OpenRouter) — enabled only when an API key is provided.
OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-}"
LLM_BASE_URL="${OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}"
LLM_MODEL="${OPENROUTER_MODEL:-meta-llama/llama-3.1-8b-instruct}"

if [[ -n "$OPENROUTER_API_KEY" ]]; then
  AI_ENABLED=1
  echo "OPENROUTER_API_KEY detected: deploying the full AI stack on OpenRouter."
  # The OpenRouter key is injected as a Container Apps secret (secretref:llm-api-key),
  # never inlined as a plaintext env var. OLLAMA_* names are reused as the generic
  # OpenAI-compatible endpoint/model knobs (see services/config.py and the servers).
  PROFILE="AI_MODE_ENABLED=true MCP_ENABLED=true RAG_ENABLED=true MULTI_AGENT_ENABLED=true \
LLM_API_KEY=secretref:llm-api-key \
OLLAMA_BASE_URL=$LLM_BASE_URL OLLAMA_MODEL=$LLM_MODEL OLLAMA_REVIEW_MODEL=$LLM_MODEL \
MCP_SERVER_URL=$MCP_SERVER_URL RAG_SERVER_URL=$RAG_SERVER_URL MULTI_AGENT_SERVER_URL=$MULTI_AGENT_SERVER_URL"
  SECRET_ARGS=(--secrets "llm-api-key=$OPENROUTER_API_KEY")
else
  AI_ENABLED=0
  echo "OPENROUTER_API_KEY not set: deploying with the AI stack disabled."
  PROFILE="AI_MODE_ENABLED=false MCP_ENABLED=false RAG_ENABLED=false MULTI_AGENT_ENABLED=false"
  SECRET_ARGS=()
fi

# deploy_app <name> <image> <target-port> <internal|external> <env-var...>
# All apps authenticate to ACR with the shared user-assigned managed identity
# ($ACR_PULL_IDENTITY_ID, granted AcrPull above) — no registry credentials are stored.
deploy_app() {
  local name="$1" image="$2" port="$3" ingress="$4"
  shift 4
  local existing_app
  existing_app=$(az containerapp list --resource-group "$RESOURCE_GROUP" \
    --query "[?name=='${name}'].name" -o tsv)
  echo "Deploying ${name} with image tag ${IMAGE_TAG}..."
  if [[ -n "$existing_app" ]]; then
    az containerapp identity assign \
      --name "$name" --resource-group "$RESOURCE_GROUP" \
      --user-assigned "$ACR_PULL_IDENTITY_ID" >/dev/null
    az containerapp registry set \
      --name "$name" --resource-group "$RESOURCE_GROUP" \
      --server "$REGISTRY_SERVER" --identity "$ACR_PULL_IDENTITY_ID" >/dev/null
    if [[ ${#SECRET_ARGS[@]} -gt 0 ]]; then
      az containerapp secret set \
        --name "$name" --resource-group "$RESOURCE_GROUP" \
        "${SECRET_ARGS[@]}" >/dev/null
    fi
    az containerapp revision set-mode \
      --name "$name" --resource-group "$RESOURCE_GROUP" --mode single >/dev/null
    az containerapp ingress enable \
      --name "$name" --resource-group "$RESOURCE_GROUP" \
      --type "$ingress" --target-port "$port" >/dev/null
    az containerapp update \
      --name "$name" \
      --resource-group "$RESOURCE_GROUP" \
      --image "${REGISTRY_SERVER}/${image}:${IMAGE_TAG}" \
      --cpu 0.25 --memory 0.5Gi \
      --min-replicas 1 --max-replicas 1 \
      --set-env-vars "$@"
    return
  fi
  az containerapp create \
    --name "$name" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$ENV_NAME" \
    --image "${REGISTRY_SERVER}/${image}:${IMAGE_TAG}" \
    --target-port "$port" \
    --ingress "$ingress" \
    --registry-server "$REGISTRY_SERVER" \
    --registry-identity "$ACR_PULL_IDENTITY_ID" \
    --user-assigned "$ACR_PULL_IDENTITY_ID" \
    --revisions-mode single \
    --cpu 0.25 --memory 0.5Gi \
    --min-replicas 1 --max-replicas 1 \
    "${SECRET_ARGS[@]}" \
    --env-vars "$@"
}

# --- Databases (internal) -----------------------------------------------------
deploy_app shared-db    shared-db    6000 internal PORT=6000
deploy_app student-1-db student-1-db 6001 internal PORT=6001
deploy_app student-2-db student-2-db 6002 internal PORT=6002
deploy_app student-3-db student-3-db 6003 internal PORT=6003
deploy_app student-4-db student-4-db 6004 internal PORT=6004
deploy_app student-5-db student-5-db 6005 internal PORT=6005

# --- Shared API (external) ----------------------------------------------------
# COOKIE_SECURE=true marks the session cookie Secure and enables HSTS (served
# over TLS by Container Apps) — B5 endpoint security / B6 data-in-transit.
deploy_app shared-api shared-api 5000 external \
  PORT=5000 \
  SHARED_DB_URL="$SHARED_DB_URL" \
  COOKIE_DOMAIN="$DEFAULT_DOMAIN" \
  COOKIE_SECURE=true \
  ALLOWED_ORIGINS="$ALLOWED_ORIGINS"

# --- Shared AI servers (internal, deployed only when AI is enabled) ----------
# Reached by the student backends (and the rag-server) over internal ingress.
if [[ "$AI_ENABLED" == "1" ]]; then
  deploy_app mcp-server mcp-server 16050 internal \
    MCP_PORT=16050 \
    SHARED_DB_URL="$SHARED_DB_URL" \
    STUDENT_1_DB_URL="$S1_DB" \
    STUDENT_2_DB_URL="$S2_DB" \
    STUDENT_3_DB_URL="$S3_DB" \
    STUDENT_4_DB_URL="$S4_DB" \
    STUDENT_5_DB_URL="$S5_DB"

  deploy_app rag-server rag-server 16070 internal \
    PORT=16070 \
    AI_MODE_ENABLED=true \
    MCP_SERVER_URL="$MCP_SERVER_URL" \
    LLM_API_KEY=secretref:llm-api-key \
    OLLAMA_BASE_URL="$LLM_BASE_URL" \
    OLLAMA_MODEL="$LLM_MODEL"

  deploy_app multi-agent-server multi-agent-server 16080 internal \
    PORT=16080 \
    SHARED_DB_URL="$SHARED_DB_URL" \
    STUDENT_1_DB_URL="$S1_DB" \
    STUDENT_2_DB_URL="$S2_DB" \
    STUDENT_3_DB_URL="$S3_DB" \
    STUDENT_4_DB_URL="$S4_DB" \
    STUDENT_5_DB_URL="$S5_DB" \
    LLM_API_KEY=secretref:llm-api-key \
    OLLAMA_BASE_URL="$LLM_BASE_URL" \
    OLLAMA_MODEL="$LLM_MODEL" \
    OLLAMA_REVIEW_MODEL="$LLM_MODEL"
fi

# --- Student backends (external) ---------------------------------------------
deploy_app student-1-backend student-1-backend 5001 external \
  PORT=5001 \
  SHARED_API_URL="$SHARED_API_URL" \
  DATABASE_SERVICE_URL="$S1_DB" \
  BACKEND_PUBLIC_URL="$S1_BE" \
  FRONTEND_PUBLIC_URL="$S1_FE" \
  $PROFILE

deploy_app student-2-backend student-2-backend 5002 external \
  PORT=5002 \
  DATABASE_SERVICE_URL="$S2_DB" \
  BACKEND_PUBLIC_URL="$S2_BE" \
  FRONTEND_PUBLIC_URL="$S2_FE" \
  SHARED_API_URL="$SHARED_API_URL" \
  APPLICATIONS_DB_URL="$S3_DB" \
  APPLICATIONS_PUBLIC_URL="$S3_FE" \
  $PROFILE

deploy_app student-3-backend student-3-backend 5003 external \
  PORT=5003 \
  DATABASE_SERVICE_URL="$S3_DB" \
  POSTINGS_DB_URL="$S2_DB" \
  SHARED_API_URL="$SHARED_API_URL" \
  SHARED_DB_URL="$SHARED_DB_URL" \
  STUDENT_1_DB_URL="$S1_DB" \
  INTERVIEWS_DB_URL="$S4_DB" \
  BACKEND_PUBLIC_URL="$S3_BE" \
  FRONTEND_PUBLIC_URL="$S3_FE" \
  INTERVIEWS_PUBLIC_URL="$S4_FE" \
  EVALUATIONS_PUBLIC_URL="$S5_FE" \
  $PROFILE

deploy_app student-4-backend student-4-backend 5004 external \
  PORT=5004 \
  DATABASE_SERVICE_URL="$S4_DB" \
  APPLICATIONS_DB_URL="$S3_DB" \
  POSTINGS_DB_URL="$S2_DB" \
  SHARED_DB_URL="$SHARED_DB_URL" \
  SHARED_API_URL="$SHARED_API_URL" \
  FRONTEND_PUBLIC_URL="$S4_FE" \
  BACKEND_PUBLIC_URL="$S4_BE" \
  $PROFILE

deploy_app student-5-backend student-5-backend 5005 external \
  PORT=5005 \
  DATABASE_SERVICE_URL="$S5_DB" \
  SHARED_API_URL="$SHARED_API_URL" \
  SHARED_DB_URL="$SHARED_DB_URL" \
  APPLICATIONS_DB_URL="$S3_DB" \
  POSTINGS_DB_URL="$S2_DB" \
  INTERVIEWS_DB_URL="$S4_DB" \
  FRONTEND_PUBLIC_URL="$S5_FE" \
  BACKEND_PUBLIC_URL="$S5_BE" \
  $PROFILE

# --- Student frontends (external) --------------------------------------------
deploy_app student-1-frontend student-1-frontend 3000 external \
  PORT=3000 \
  BACKEND_PUBLIC_URL="$S1_BE" \
  SHARED_API_PUBLIC_URL="$SHARED_API_URL" \
  LOGIN_URL="$LOGIN_URL" \
  FIND_HOME_URL="$FIND_HOME_URL"

deploy_app student-2-frontend student-2-frontend 3002 external \
  PORT=3002 \
  BACKEND_PUBLIC_URL="$S2_BE" \
  SHARED_API_PUBLIC_URL="$SHARED_API_URL" \
  LOGIN_URL="$LOGIN_URL" \
  FIND_HOME_URL="$FIND_HOME_URL"

deploy_app student-3-frontend student-3-frontend 3003 external \
  PORT=3003 \
  BACKEND_SERVICE_URL="$S3_BE" \
  BACKEND_PUBLIC_URL="$S3_BE" \
  SHARED_API_PUBLIC_URL="$SHARED_API_URL" \
  LOGIN_URL="$LOGIN_URL" \
  FIND_HOME_URL="$FIND_HOME_URL" \
  JOB_POSTINGS_URL="$S2_FE"

deploy_app student-4-frontend student-4-frontend 3004 external \
  PORT=3004 \
  BACKEND_PUBLIC_URL="$S4_BE" \
  SHARED_API_PUBLIC_URL="$SHARED_API_URL" \
  LOGIN_URL="$LOGIN_URL" \
  FIND_HOME_URL="$FIND_HOME_URL" \
  APPLICATIONS_PUBLIC_URL="$S3_FE"

deploy_app student-5-frontend student-5-frontend 3005 external \
  PORT=3005 \
  BACKEND_PUBLIC_URL="$S5_BE" \
  FIND_HOME_URL="$FIND_HOME_URL" \
  SHARED_API_PUBLIC_URL="$SHARED_API_URL" \
  LOGIN_URL="$LOGIN_URL" \
  APPLICATIONS_PUBLIC_URL="$S3_FE" \
  INTERVIEWS_PUBLIC_URL="$S4_FE"

# --- Shared frontend (external, public entry point) --------------------------
deploy_app shared-frontend shared-frontend 3000 external \
  PORT=3000 \
  COOKIE_SECURE=true \
  ALLOWED_ORIGINS="$ALLOWED_ORIGINS" \
  STUDENT_1_FRONTEND_URL="$S1_FE" \
  STUDENT_2_FRONTEND_URL="$S2_FE" \
  STUDENT_3_FRONTEND_URL="$S3_FE" \
  STUDENT_4_FRONTEND_URL="$S4_FE" \
  STUDENT_5_FRONTEND_URL="$S5_FE" \
  SHARED_API_PUBLIC_URL="$SHARED_API_URL"

echo "=== Deployment Complete ==="
echo "FIND entry point (shared frontend): ${SHARED_FRONTEND_URL}"
echo ""
echo "Validate with: curl -I ${SHARED_FRONTEND_URL}"
