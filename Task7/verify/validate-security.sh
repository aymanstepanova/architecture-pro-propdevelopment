#!/usr/bin/env bash
set -euo pipefail

NS="audit-zone"

echo "==> Проверяем PodSecurity labels на namespace ${NS}"
kubectl get ns "${NS}" --show-labels

echo
echo "==> Проверяем наличие ConstraintTemplates..."
kubectl get constrainttemplates

echo
echo "==> Проверяем наличие Constraints..."
kubectl get constraints --all-namespaces || true

echo
echo "==> Проверяем статус pod'ов в ${NS}"
kubectl get pods -n "${NS}" -o wide

echo
echo "==> Проверка описаний secure pod'ов на наличие securityContext..."
for p in pod-secure-no-privileged pod-secure-no-hostpath pod-secure-non-root; do
  echo "---"
  echo "Pod: $p"
  kubectl get pod "$p" -n "${NS}" -o yaml | grep -A3 -n "securityContext" || true
done

echo
echo "==> Скрипт validate-security.sh завершён."
