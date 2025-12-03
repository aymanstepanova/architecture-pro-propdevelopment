# Задание 5. Управление трафиком внутри кластера Kubertnetes

## 1. Подготовка
Для включения сетевых политик нужно перезапустить кластер с новыми настройками.

Остановить текущий кластер:

```shell
minikube delete
```

1. Запустить новый, сразу с CNI, который поддерживает NetworkPolicy, например Calico:

```shell
minikube start --cni=calico
```

2. Создать namespace.

```shell
kubectl create namespace traffic-demo
```
3. Создать поды и сервисы.

```shell

# back-end-api
kubectl run back-end-api-app \
  --image=nginx \
  --labels=role=back-end-api \
  --expose \
  --port=80 \
  -n traffic-demo

# admin-back-end-api
kubectl run admin-back-end-api-app \
  --image=nginx \
  --labels=role=admin-back-end-api \
  --expose \
  --port=80 \
  -n traffic-demo
```

4. Проверка подов и сервисов.

```shell
kubectl get pods,svc -n traffic-demo
```


## 2. Сетевые политики (файл `non-admin-api-allow.yaml`)

Файл содержит **три** NetworkPolicy:

1. `deny-all-api-ingress` — по умолчанию запрещает входящий трафик ко всем API-сервисам (`back-end-api`, `admin-back-end-api`).
2. `non-admin-api-allow` — разрешает трафик **front-end -> back-end-api** на порт 80.
3. `admin-api-allow` — разрешает трафик **admin-front-end -> admin-back-end-api** на порт 80.

То есть:
* мы изолируем API-поды от всех остальных,
* но разрешаем парные связи UI <-> соответствующий API.


Применение:

```bash
kubectl apply -f non-admin-api-allow.yaml
```

Проверка, что политики применены:

```bash
kubectl get networkpolicy -n traffic-demo
```

---

## 3. Проверка трафика между сервисами

### 3.1. front-end ->  back-end-api (должно работать)

```bash
kubectl run test-frontend --rm -i -t --image=alpine -n traffic-demo --labels=role=front-end -- sh
```

Внутри проверяем соединение командой:
```shell
nc -zv back-end-api-app 80
```
Или имитируем вызов сервиса
```sh
apk add --no-cache wget
wget -qO- --timeout=2 http://back-end-api-app
```

Ожидаем: ответ HTML nginx (тихий успех, если без ошибок).


### 3.2. Любой другой pod → back-end-api (НЕ должно работать)

Например, с admin-front-end:

```bash
kubectl run test-admin-front --rm -i -t --image=alpine -n traffic-demo -- sh
```

Внутри:
```shell
nc -zv back-end-api-app 80
```
или
```sh
apk add --no-cache wget
wget -qO- --timeout=2 http://back-end-api-app
```

Ожидаем: таймаут / ошибка соединения (networkpolicy режет трафик).

### 3.3. admin-front-end → admin-back-end-api (должно работать)

```bash
kubectl run test-admin-ui --rm -i -t --image=alpine -n traffic-demo --labels=role=admin-front-end -- sh
```


Внутри:
```shell
nc -zv admin-back-end-api-app 80
#admin-back-end-api-app (10.100.255.8:80) open
```

```sh
apk add --no-cache wget
wget -qO- --timeout=2 http://admin-back-end-api-app
```

Ожидаем успешный ответ nginx.

### 3.4. front-end → admin-back-end-api (НЕ должно работать)

```bash
kubectl run test-front --rm -i -t --image=alpine -n traffic-demo --labels=role=front-end -- sh
```

Внутри:

```sh
apk add --no-cache wget
wget -qO- --timeout=2 http://admin-back-end-api-app
```

Ожидаем таймаут / ошибка соединения.


