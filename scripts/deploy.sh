#!/bin/bash

# Deploy Snippet Answer Generator to Azure Container Apps
# Uses Azure Container Registry (ACR) build + Bicep template
# ACR build avoids WSL2 SSL issues with Docker push

set -e

# Configuration (derived from infra/parameters.json)
RESOURCE_GROUP="snippet-answer-rg"
LOCATION="switzerlandnorth"
ACR_NAME="snippetansweracr"
ACR_IMAGE="snippetansweracr.azurecr.io/snippet-answer:latest"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 Deploying Snippet Answer Generator to Azure using ACR build..."
echo "   Project root: $PROJECT_ROOT"

# --- Prerequisites -----------------------------------------------------------
echo "🔍 Checking prerequisites..."

if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first."
    exit 1
fi

if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure. Please run 'az login' first."
    exit 1
fi

ACCOUNT=$(az account show --query '[name, id]' -o tsv)
echo "   Azure account: $ACCOUNT"
echo "✅ Prerequisites check passed"

# --- Step 1: Resource Group ---------------------------------------------------
echo "📦 Checking resource group: $RESOURCE_GROUP"
if ! az group show --name "$RESOURCE_GROUP" &> /dev/null; then
    echo "   Creating resource group in $LOCATION..."
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none
    echo "   ✅ Resource group created"
else
    echo "   ✅ Resource group exists"
fi

# --- Step 2: Azure Container Registry ----------------------------------------
echo "🏗️  Checking Azure Container Registry: $ACR_NAME"
if ! az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    echo "   Creating Azure Container Registry..."
    az acr create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$ACR_NAME" \
        --sku Basic \
        --admin-enabled true \
        --output none
    echo "   ✅ ACR created"
else
    echo "   ✅ ACR already exists"
fi

# --- Step 3: Build image in ACR ----------------------------------------------
echo "🔨 Building image in ACR (this may take several minutes)..."
echo "   Building directly in Azure — no local Docker needed"
az acr build \
    --registry "$ACR_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --image "snippet-answer:latest" \
    --file Dockerfile \
    "$PROJECT_ROOT"
echo "✅ Image built and pushed to ACR"

# --- Step 4: Deploy via Bicep template ----------------------------------------
echo "🚀 Deploying infrastructure via Bicep template..."
az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$PROJECT_ROOT/infra/main.bicep" \
    --parameters "$PROJECT_ROOT/infra/parameters.json" \
    --output none
echo "✅ Bicep deployment complete"

# --- Step 4b: Force new revision to pull fresh image --------------------------
# Container Apps caches the :latest tag; an env-var change forces a new pull.
echo "🔄 Forcing new revision to pull fresh image..."
az containerapp update \
    --name "snippet-answer" \
    --resource-group "$RESOURCE_GROUP" \
    --set-env-vars "DEPLOY_TIMESTAMP=$(date +%s)" \
    --output none
echo "✅ New revision created"

# --- Step 5: Display results --------------------------------------------------
APP_URL=$(az containerapp show \
    --name "snippet-answer" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" \
    --output tsv 2>/dev/null || echo "")

echo ""
echo "🎉 Deployment completed successfully!"
if [ -n "$APP_URL" ]; then
    echo "📱 Application URL: https://$APP_URL"
else
    echo "📱 Application URL: (run the command below to retrieve it)"
    echo "   az containerapp show --name snippet-answer --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv"
fi
echo ""
echo "📊 To monitor your application:"
echo "   az containerapp logs show --name snippet-answer --resource-group $RESOURCE_GROUP --follow"
echo ""
echo "🔧 To scale your application:"
echo "   az containerapp update --name snippet-answer --resource-group $RESOURCE_GROUP --min-replicas 1 --max-replicas 5"
echo ""
echo "🔄 To update the app (after code changes):"
echo "   az acr build --registry $ACR_NAME --image snippet-answer:latest --file Dockerfile ."
echo "   az deployment group create -g $RESOURCE_GROUP --template-file infra/main.bicep --parameters infra/parameters.json"
echo ""
echo "🗑️  To clean up all resources:"
echo "   az group delete --resource-group $RESOURCE_GROUP --yes --no-wait"
