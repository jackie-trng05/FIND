#!/bin/bash
set -e

# Validates the deployed FIND entry point (shared-frontend, the public home/login
# page) and writes reports/deploy/deployment-results.md as evidence.

RESOURCE_GROUP="${RESOURCE_GROUP:-find-rg}"
REPORT_FILE="reports/deploy/deployment-results.md"
APP_NAME="shared-frontend"

echo "=== FIND Cloud Deployment: Deployment Testing ==="

# Step 1: Get the shared-frontend Container App FQDN
APP_URL=$(az containerapp show \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)

if [[ -z "$APP_URL" ]]; then
  echo "Could not resolve $APP_NAME FQDN. Run scripts/deploy-azure.sh first." >&2
  exit 1
fi

# Step 2: Validate the entry point responds (retry while the app cold-starts)
echo "Validating https://$APP_URL ..."
HTTP_STATUS="000"
for i in $(seq 1 20); do
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "https://$APP_URL" || echo "000")
  if [[ "$HTTP_STATUS" == "200" ]]; then
    break
  fi
  echo "Attempt $i: HTTP $HTTP_STATUS - waiting for the app to become ready..."
  sleep 15
done

if [[ "$HTTP_STATUS" == "200" ]]; then
  STATUS="Success"
  VALIDATION="HTTP $HTTP_STATUS OK"
else
  STATUS="Failed"
  VALIDATION="HTTP $HTTP_STATUS"
fi

# Step 3: Write deployment-results.md
mkdir -p reports/deploy
cat > "$REPORT_FILE" <<EOF
# FIND Deployment Report

## Azure Container Apps

Deployment Status: $STATUS

Entry Point App: $APP_NAME (shared frontend)

Entry Point URL: https://$APP_URL

Validation Result: $VALIDATION

Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)

Reviewer Notes: (pending review)
EOF

echo "=== Deployment Testing Complete ==="
cat "$REPORT_FILE"
