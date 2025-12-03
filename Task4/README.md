## Задание 4. Защита доступа к кластеру Kubernetes

Этот документ описывает ролевую модель доступа к Kubernetes, порядок развёртывания инфраструктуры для тестирования и последовательность выполнения скриптов.

Решение основано на оргструктуре компании и требованиях по разграничению прав пользователей.

---

## 1. Ролевая модель (RBAC)
Отдельным файлом: [roles.md](roles.md)

### Категории ролей

| Роль                         | Права роли                                                                                                | Область                 |  Группы пользователей                                                           |
|------------------------------|-----------------------------------------------------------------------------------------------------------|-------------------------|---------------------------------------------------------------------------------|
| **cluster-config-manager**   | Управление конфигурацией приложений: Deployments, StatefulSet, Jobs, Services, Ingress, ConfigMap, Secret | Все бизнес-неймспейсы   |  DevOps-инженеры платформенной команды; инженеры эксплуатации доменов           |
| **cluster-readonly**         | Только чтение ресурсов (Pod, Deployment, Service, Events, ConfigMap)                                      | Все NS, кроме системных |  Архитекторы; аналитики; аудит; руководители направлений                        |
| **security-privileged-read** | Просмотр всех Secret, ConfigMap, RBAC, Node, NS                                                           | Весь кластер            |  Специалист по информационной безопасности                                      |
| **namespace-admin**          | Полный CRUD ресурсов внутри одного неймспейса, локальный RBAC                                             | Конкретный неймспейс    |  Команда разработки в конкретном домене/сервисе (например, команда tenant-core) |
| **namespace-viewer**         | Просмотр ресурсов в своём NS без доступа к Secret                                                         | Конкретный неймспейс    |  Операционные команды; менеджеры продукта; support команды                      |

### Группы пользователей

* **Роль для привилегированные действий**: security-privileged-read
* **Только просмотр** : cluster-readonly
* **Настройка кластера**: cluster-config-manager

---

## 2. Используемые скрипты

Проект включает три скрипта:

| Скрипт                             | Назначение                                                        |
|------------------------------------|-------------------------------------------------------------------|
| **create_users_and_namespaces.sh** | Создание неймспейсов и пользователей (ServiceAccount)             |
| **create_roles.sh**                | Создание ролей (ClusterRole / Role)                               |
| **bind_roles.sh**                  | Привязка пользователей к ролям (RoleBinding / ClusterRoleBinding) |

Все скрипты можно запускать независимо. Формат — idempotent: повторный запуск не приводит к ошибкам.

---

#  3. Порядок применения

Ниже перечислены обязательные шаги для корректного развёртывания среды.

---

## 3.1. Шаг 1 — Запуск пустого Minikube

```bash
minikube start
```

Проверка:

```bash
kubectl get nodes
```

---

## 3.2. Шаг 2 — Создать пользователей и неймспейсы

Запуск скрипта:

```bash
bash create_users_and_namespaces.sh
```

Проверить:

```bash
kubectl get ns
kubectl get sa -A
```

---

## 3.3. Шаг 3 — Создать роли (RBAC)

```bash
bash create_roles.sh
```

Проверить созданные роли:

```bash
kubectl get clusterrole --show-labels=true | grep propdevelopment
```

---

## 3.4. Шаг 4 — Привязать пользователей к ролям

```bash
bash bind_roles.sh
```

Проверка:

```bash
kubectl get clusterrolebinding --show-labels=true | grep propdevelopment
kubectl get rolebinding -n tenant-core
```
### Таблица соответствия пользователей и ролей

| Пользователь (ServiceAccount) | Назначенная роль (Role)    | Область действия (namespace или весь кластер)                   | Комментарий                                                                                                                                     |
|-------------------------------|----------------------------|-----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| **sa-devops-platform**        | `cluster-config-manager`   | Весь кластер, но только ресурсы приложений в бизнес-неймспейсах | Пользователь из DevOps/платформенной команды. Имеет CRUD для Deployments, Services, Secret и т.п., но не имеет прав cluster-admin.              |
| **sa-security**               | `security-privileged-read` | Весь кластер                                                    | Специалист по информационной безопасности. Видит все Secret, ConfigMap, RBAC, Nodes, Namespaces. Полностью read-only.                           |
| **sa-tenant-admin**           | `namespace-admin`          | Только `tenant-core`                                            | Админ команды tenant-core. Может создавать/обновлять/удалять ресурсы своего неймспейса и управлять локальным RBAC. Не имеет прав вне namespace. |
| **sa-tenant-viewer**          | `namespace-viewer`         | Только `tenant-core`                                            | Наблюдатель (операционный менеджер/аналитик). Может читать Pod, Deployment, Service, логи, ConfigMap. Не видит Secret. Не может менять ресурсы. |


# 4. Очистка среды (при необходимости)

```bash
minikube delete
```

---

# 6. Состав проекта

```
.
├── roles.md
├── README.md
├── create_users_and_namespaces.sh
├── create_roles.sh
└── bind_roles.sh
└── bind_roles.yaml
└── roles
└───── cluster-config-manager.yaml      
└───── cluster-readonly.yaml            
└───── security-privileged-read.yaml     
└───── namespace-admin.yaml         
└───── namespace-viewer.yaml        
```

---
