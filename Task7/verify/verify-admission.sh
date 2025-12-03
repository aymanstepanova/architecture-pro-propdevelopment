#!/usr/bin/env bash
set -euo pipefail

NS="audit-zone"

echo "==> Создаём namespace с PodSecurity=restricted"
kubectl apply -f 01-create-namespace.yaml

echo "==> Применяем ConstraintTemplates..."
kubectl apply -f gatekeeper/constraint-templates/privileged.yaml
kubectl apply -f gatekeeper/constraint-templates/hostpath.yaml
kubectl apply -f gatekeeper/constraint-templates/runasnonroot.yaml

echo "==> Применяем Constraints..."
kubectl apply -f gatekeeper/constraints/privileged.yaml
kubectl apply -f gatekeeper/constraints/hostpath.yaml
kubectl apply -f gatekeeper/constraints/runasnonroot.yaml

echo "==> Проверяем, что НЕБЕЗОПАСНЫЕ манифесты отклоняются..."

for f in insecure-manifests/*.yaml; do
  echo "---"
  echo "Пробуем применить $f (ожидаем ОШИБКУ)"
  if kubectl apply -f "$f"; then
    echo "ОШИБКА: $f применился успешно, но должен был быть отклонён"
    exit 1
  else
    echo "OK: $f отклонён admission controller / Gatekeeper"
  fi
done



echo "==> Проверяем, что БЕЗОПАСНЫЕ манифесты проходят..."

for f in secure-manifests/*.yaml; do
  echo "---"
  echo "Применяем $f (ожидаем УСПЕХ)"
  kubectl apply -f "$f"
done

echo "==> Все проверки пройдены."
