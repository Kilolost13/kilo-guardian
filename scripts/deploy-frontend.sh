#!/bin/bash
# Safe frontend deployment with versioned images to prevent drift

set -e

cd "$(dirname "$0")/../frontend/kilo-react-frontend"

echo "🔨 Building React app..."
npm run build

echo "🐳 Building Docker image with timestamp tag..."
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_TAG="kilo/frontend:${TIMESTAMP}"

docker build -t "$IMAGE_TAG" .
docker tag "$IMAGE_TAG" kilo/frontend:latest

echo "📦 Importing image to k3s..."
docker save "$IMAGE_TAG" | sudo k3s ctr images import -

echo "🚀 Updating Kubernetes deployment..."
kubectl set image deployment/kilo-frontend frontend="$IMAGE_TAG" -n kilo-guardian
kubectl patch deployment kilo-frontend -n kilo-guardian -p "{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"frontend\",\"imagePullPolicy\":\"Never\"}]}}}}"

echo "⏳ Waiting for rollout..."
kubectl rollout status deployment/kilo-frontend -n kilo-guardian --timeout=120s

echo "✅ Frontend deployed successfully with tag: ${IMAGE_TAG}"
