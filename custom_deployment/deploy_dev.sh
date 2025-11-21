#!/bin/bash

# ==============================================================================
# Script to deploy RAGFlow and tail specific logs
# Usage: ./deploy_dev.sh
# ==============================================================================

# 1. Locate the docker-compose file
if [ -f "custom_deployment/docker-compose.yml" ]; then
    COMPOSE_FILE="custom_deployment/docker-compose.yml"
    echo "📂 Detected execution from Root directory."
elif [ -f "docker-compose.yml" ]; then
    COMPOSE_FILE="docker-compose.yml"
    echo "📂 Detected execution from 'custom_deployment' directory."
else
    echo "❌ Error: Could not find 'docker-compose.yml'."
    echo "Please run this script from the 'ragflow' root directory or 'custom_deployment'."
    exit 1
fi

# 2. Deploy environment in detached mode
echo "----------------------------------------------------------------"
echo "🚀 Deploying RAGFlow Environment via Docker Compose..."
echo "----------------------------------------------------------------"

# --remove-orphans cleans up containers not defined in the compose file
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

# Check if deployment command succeeded
if [ $? -ne 0 ]; then
    echo "❌ Deployment failed."
    exit 1
fi

echo "✅ Deployment successful."
echo ""

# 3. Stream logs for Backend and Frontend only
echo "----------------------------------------------------------------"
echo "📜 Streaming logs for: ragflow-backend & ragflow-frontend"
echo "💡 (Press Ctrl+C to stop watching logs - containers will keep running)"
echo "----------------------------------------------------------------"

docker compose -f "$COMPOSE_FILE" logs -f ragflow-backend ragflow-frontend