# Task 7 — Аудит и обеспечение соответствия политике безопасности контейнеров

## 1. Что сделано

1. Создан namespace `audit-zone` с уровнем PodSecurity `restricted` через файл `01-create-namespace.yaml`.
2. Подготовлены **небезопасные** манифесты в `insecure-manifests/`:
   - `01-privileged-pod.yaml` — использует `privileged: true`.
   - `02-hostpath-pod.yaml` — использует `hostPath` том.
   - `03-root-user-pod.yaml` — под запускается от пользователя с UID `0`.
3. Подготовлены **безопасные** манифесты в `secure-manifests/`:
   - `01-secure.yaml` — убран `privileged`, добавлены `runAsNonRoot: true`, `readOnlyRootFilesystem: true`, дроп capability.
   - `02-secure.yaml` — заменён `hostPath` на `emptyDir`, добавлены настройки `runAsNonRoot` и `readOnlyRootFilesystem`.
   - `03-secure.yaml` — под запускается от непривилегированного пользователя, только `runAsNonRoot: true` и `readOnlyRootFilesystem: true`.
4. Настроен OPA Gatekeeper:
   - ConstraintTemplates в `gatekeeper/constraint-templates/`:
     - `privileged.yaml` — запрещает `privileged: true` и требует `readOnlyRootFilesystem: true`.
     - `hostpath.yaml` — запрещает использование `hostPath` в томах.
     - `runasnonroot.yaml` — требует `runAsNonRoot: true` (на уровне пода или контейнера).
   - Constraints в `gatekeeper/constraints/`:
     - `privileged.yaml`
     - `hostpath.yaml`
     - `runasnonroot.yaml`
5. Подготовлен файл политики аудита `audit-policy.yaml`, логирующий:
   - операции с Pod в namespace `audit-zone`,
   - изменения объектов Gatekeeper (ConstraintTemplates и Constraints).
6. Подготовлены скрипты в `verify/`:
   - `verify-admission.sh` — комплексная проверка:
     - создаётся namespace,
     - применяются Gatekeeper шаблоны и ограничения,
     - проверяется, что **insecure** манифесты отклоняются,
     - проверяется, что **secure** манифесты успешно создаются.
   - `validate-security.sh` — дополнительные проверки:
     - выводит labels namespace,
     - показывает зарегистрированные ConstraintTemplates и Constraints,
     - показывает состояние pod'ов в `audit-zone`.

## 2. Как воспроизвести проверку

1. Создание кластера и применение политик:
   * создать файл audit-policy.yaml в директории ~\.minikube\files\etc\ssl\certs - audit-policy.yaml
   * стартовать кластер, передав политику аудита в качестве параметра.
   * установить gatekeeper в работающем кластере

```bash
minikube start --extra-config=apiserver.audit-policy-file=/etc/ssl/certs/audit-policy.yaml --extra-config=apiserver.audit-log-path=-
# установка gatekeeper
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/release-3.16/deploy/gatekeeper.yaml
```


2. Перейти в каталог `Task7/`:


Перейти в папку с заданием.
```bash
cd Task7
```

3. Сделать скрипты исполняемыми:

```bash
chmod +x verify/verify-admission.sh
chmod +x verify/validate-security.sh
```

4. Запустить основную проверку:

```bash
./verify/verify-admission.sh
```

Ожидаемый результат:

 * все манифесты из `insecure-manifests/` **отклоняются** admission controller / Gatekeeper,
 * все манифесты из `secure-manifests/` **успешно создаются** в namespace `audit-zone`.

5. Дополнительно можно выполнить:

```bash
./verify/validate-security.sh
```

Скрипт покажет:

 * labels namespace `audit-zone`,
 * зарегистрированные ConstraintTemplates и Constraints,
 * созданные pod'ы и их securityContext.

## 3. Критерии успешности

* PodSecurity Admission с уровнем `restricted` применён к namespace `audit-zone`.
* Gatekeeper активно применяет ограничения:
    * `privileged: true` запрещён,
    * `hostPath` запрещён,
    * `runAsNonRoot: true` обязателен,
    * `readOnlyRootFilesystem: true` обязателен.
* Небезопасные pod'ы не проходят валидацию (ошибки при `kubectl apply`).
* Безопасные pod'ы успешно создаются.
* Аудит Kubernetes настроен для отслеживания операций над pod'ами и объектами Gatekeeper.

