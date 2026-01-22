#!/bin/bash
# Remove Kilo AI Microservices from K3s

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAMESPACE="${1:-default}"

echo "=========================================="
echo "Kilo AI Microservices - K3s Teardown"
echo "=========================================="
echo "Namespace: $NAMESPACE"
echo ""

read -p "Are you sure you want to remove all Kilo services? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo "[1/3] Removing Deployments..."
kubectl delete -n "$NAMESPACE" -f "$SCRIPT_DIR"/*-deployment.yaml --ignore-not-found

echo "[2/3] Removing Services..."
kubectl delete -n "$NAMESPACE" -f "$SCRIPT_DIR"/*-service.yaml --ignore-not-found

echo "[3/3] Removing PersistentVolumeClaims..."
read -p "Also delete PersistentVolumeClaims (DATA WILL BE LOST)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    kubectl delete -n "$NAMESPACE" -f "$SCRIPT_DIR"/*-persistentvolumeclaim.yaml --ignore-not-found
    echo "PVCs deleted."
else
    echo "PVCs preserved."
fi

echo ""
echo "Teardown complete."
