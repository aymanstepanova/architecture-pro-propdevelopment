#!/bin/bash
set -e

echo "Связываем ServiceAccount'ы с ролями..."

kubectl apply -f bind-roles.yaml -o yaml

echo "RoleBinding и ClusterRoleBinding созданы."
