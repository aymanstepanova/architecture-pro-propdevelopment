#!/bin/bash
set -e

echo "Создаём ClusterRole и Role для ролевой модели..."

kubectl apply -f ./roles/cluster-config-manager.yaml
kubectl apply -f ./roles/cluster-readonly.yaml
kubectl apply -f ./roles/security-privileged-read.yaml
kubectl apply -f ./roles/namespace-admin.yaml
kubectl apply -f ./roles/namespace-viewer.yaml

echo "Роли созданы."
