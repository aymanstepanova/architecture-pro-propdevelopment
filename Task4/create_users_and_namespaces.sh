#!/bin/bash
set -e

echo ""
echo "Создаём неймспейсы PropDevelopment..."
echo "--------------------------------------------"

kubectl create namespace platform --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace tenant-core --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace sales --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace finance --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace data --dry-run=client -o yaml | kubectl apply -f -

echo ""
echo "Создаём ServiceAccount'ы (условные пользователи)..."
echo "--------------------------------------------"

# Платформенная / DevOps команда (настройка кластера)
kubectl create serviceaccount sa-devops-platform -n platform --dry-run=client -o yaml | kubectl apply -f -

# Специалист по ИБ (привилегированный доступ к секретам и RBAC)
kubectl create serviceaccount sa-security -n platform --dry-run=client -o yaml | kubectl apply -f -

# Команда tenant-core: админ своего неймспейса
kubectl create serviceaccount sa-tenant-admin -n tenant-core --dry-run=client -o yaml | kubectl apply -f -

# Операционная команда tenant-core: только просмотр
kubectl create serviceaccount sa-tenant-viewer -n tenant-core --dry-run=client -o yaml | kubectl apply -f -

echo ""
echo "ServiceAccount'ы и неймспейсы созданы."
echo "--------------------------------------------"

kubectl get ns
