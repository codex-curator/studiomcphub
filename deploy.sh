#!/bin/bash
# Deploy StudioMCPHub to Cloud Run
set -e

PROJECT_ID="the-golden-codex-1111"
REGION="us-west1"
SERVICE_NAME="studiomcphub"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo "=== Deploying StudioMCPHub ==="
echo "Project: ${PROJECT_ID}"
echo "Region:  ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo ""

# Build and push
echo "[1/3] Building container image..."
gcloud builds submit --tag "${IMAGE}" --project="${PROJECT_ID}"

# Deploy to Cloud Run
echo "[2/3] Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image="${IMAGE}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --platform=managed \
    --allow-unauthenticated \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=1 \
    --max-instances=10 \
    --timeout=300 \
    --set-env-vars="GCP_PROJECT=${PROJECT_ID},GCP_REGION=${REGION}"

# Get URL
echo "[3/3] Getting service URL..."
URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --format="value(status.url)")

echo ""
echo "=== Deployment Complete ==="
echo "Service URL: ${URL}"
echo "Health:      ${URL}/health"
echo "MCP Card:    ${URL}/.well-known/mcp.json"
echo "LLMs.txt:    ${URL}/llms.txt"
echo "Pricing:     ${URL}/pricing"
echo ""
echo "Connect your MCP client:"
echo "  {\"mcpServers\": {\"studiomcphub\": {\"url\": \"${URL}/mcp\"}}}"
