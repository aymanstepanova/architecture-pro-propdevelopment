#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import argparse
import sys
from typing import List, Dict, Any

def check_secret_access(log_entry: Dict[str, Any]) -> bool:
    """Доступ к secrets (get)."""
    try:
        ref = log_entry.get('objectRef', {}) or {}
        return ref.get('resource') == 'secrets' and log_entry.get('verb') == 'get'
    except (AttributeError, KeyError):
        return False

def check_kubectl_exec(log_entry: Dict[str, Any]) -> bool:
    """kubectl exec: subresource == exec, verb == create."""
    try:
        ref = log_entry.get('objectRef', {}) or {}
        return log_entry.get('verb') == 'create' and ref.get('subresource') == 'exec'
    except (AttributeError, KeyError):
        return False

def check_privileged_pod_creation(log_entry: Dict[str, Any]) -> bool:
    """Создание pod'а с securityContext.privileged = true."""
    try:
        ref = log_entry.get('objectRef', {}) or {}
        if ref.get('resource') != 'pods' or log_entry.get('verb') != 'create':
            return False

        request_object = log_entry.get('requestObject', {}) or {}
        spec = request_object.get('spec', {}) or {}
        containers = spec.get('containers', []) or []

        for container in containers:
            security_context = container.get('securityContext', {}) or {}
            if security_context.get('privileged') is True:
                return True
    except (AttributeError, KeyError, TypeError):
        return False
    return False

def check_rbac_escalation(log_entry: Dict[str, Any]) -> bool:
    """RoleBinding/ClusterRoleBinding с roleRef.name == cluster-admin."""
    try:
        ref = log_entry.get('objectRef', {}) or {}
        if log_entry.get('verb') != 'create':
            return False
        if ref.get('resource') not in ('rolebindings', 'clusterrolebindings'):
            return False

        req = log_entry.get('requestObject', {}) or {}
        role_ref = req.get('roleRef', {}) or {}
        return role_ref.get('name') == 'cluster-admin'
    except (AttributeError, KeyError):
        return False

def check_audit_policy_change(log_entry: Dict[str, Any], raw_line: str) -> bool:
    """Попытки удалить/изменить audit-policy.yaml."""
    try:
        verb = log_entry.get('verb')
        if verb not in ('delete', 'update', 'patch'):
            return False
        ref = log_entry.get('objectRef', {}) or {}
        name = (ref.get('name') or '').lower()
        uri = (log_entry.get('requestURI') or '').lower()
        if 'audit-policy' in name or 'audit-policy' in uri:
            return True
    except Exception:
        pass

    # запасной вариант: просто поиск по строке
    return 'audit-policy' in raw_line.lower()

def get_username(event: Dict[str, Any]) -> str:
    user = event.get('user', {}) or {}
    return user.get('username', '<unknown>')

def format_location(event: Dict[str, Any]) -> str:
    ref = event.get('objectRef', {}) or {}
    return f"resource={ref.get('resource')}, namespace={ref.get('namespace')}, name={ref.get('name')}"

def first_or_none(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    return events[0] if events else {}

def main():
    parser = argparse.ArgumentParser(
        description="Фильтрует лог-файл аудита Kubernetes и формирует audit-extract.json и analysis.md",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "logfile",
        help="Путь к файлу аудита Kubernetes (формат JSON lines: по одному событию на строку)"
    )
    parser.add_argument(
        "--extract",
        default="audit-extract.json",
        help="Имя файла для выжимки подозрительных событий (по умолчанию audit-extract.json)"
    )
    parser.add_argument(
        "--report",
        default="analysis.md",
        help="Имя файла отчёта (по умолчанию analysis.md)"
    )
    args = parser.parse_args()

    secret_access_events: List[Dict[str, Any]] = []
    exec_events: List[Dict[str, Any]] = []
    privileged_pod_events: List[Dict[str, Any]] = []
    rbac_events: List[Dict[str, Any]] = []
    audit_policy_events: List[Dict[str, Any]] = []

    try:
        with open(args.logfile, 'r', encoding='utf-8') as f:
            for line in f:
                raw_line = line.strip()
                if not raw_line:
                    continue

                try:
                    log_entry = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue

                if check_secret_access(log_entry):
                    secret_access_events.append(log_entry)

                if check_kubectl_exec(log_entry):
                    exec_events.append(log_entry)

                if check_privileged_pod_creation(log_entry):
                    privileged_pod_events.append(log_entry)

                if check_rbac_escalation(log_entry):
                    rbac_events.append(log_entry)

                if check_audit_policy_change(log_entry, raw_line):
                    audit_policy_events.append(log_entry)

    except FileNotFoundError:
        print(f"Ошибка: файл логов не найден по пути '{args.logfile}'", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}", file=sys.stderr)
        sys.exit(1)

    # ---------- audit-extract.json ----------
    # Собираем все события и убираем дубликаты по auditID (если есть)
    all_suspicious: List[Dict[str, Any]] = []
    all_suspicious += secret_access_events
    all_suspicious += exec_events
    all_suspicious += privileged_pod_events
    all_suspicious += rbac_events
    all_suspicious += audit_policy_events

    unique_events: List[Dict[str, Any]] = []
    seen_ids = set()

    for ev in all_suspicious:
        audit_id = ev.get("auditID")
        if audit_id:
            if audit_id in seen_ids:
                continue
            seen_ids.add(audit_id)
        unique_events.append(ev)

    with open(args.extract, "w", encoding="utf-8") as out_f:
        json.dump(unique_events, out_f, indent=2, ensure_ascii=False)

    # ---------- analysis.md ----------
    first_secret = first_or_none(secret_access_events)
    first_priv = first_or_none(privileged_pod_events)
    first_exec = first_or_none(exec_events)
    first_rbac = first_or_none(rbac_events)
    first_audit = first_or_none(audit_policy_events)

    secrets_user = get_username(first_secret) if first_secret else "подозрительных событий не обнаружено"
    secrets_loc = format_location(first_secret) if first_secret else "-"

    priv_user = get_username(first_priv) if first_priv else "подозрительных событий не обнаружено"
    priv_loc = format_location(first_priv) if first_priv else "-"

    exec_user = get_username(first_exec) if first_exec else "подозрительных событий не обнаружено"
    exec_loc = format_location(first_exec) if first_exec else "-"

    rbac_user = get_username(first_rbac) if first_rbac else "подозрительных событий не обнаружено"
    rbac_loc = format_location(first_rbac) if first_rbac else "-"

    audit_user = get_username(first_audit) if first_audit else "подозрительных событий не обнаружено"
    audit_loc = format_location(first_audit) if first_audit else "-"

    compromised_reasons: List[str] = []
    if rbac_events:
        compromised_reasons.append(
            "- сервисному аккаунту или пользователю были назначены права cluster-admin через RoleBinding/ClusterRoleBinding."
        )
    if privileged_pod_events:
        compromised_reasons.append(
            "- в кластере создан привилегированный pod, который может быть использован для доступа к ноде и токенам."
        )

    if compromised_reasons:
        compromised_text = "Обнаружены признаки возможной компрометации кластера:\n\n" + "\n".join(compromised_reasons)
    else:
        compromised_text = (
            "Явных признаков полной компрометации кластера не обнаружено."
        )

    rbac_issues: List[str] = []
    if secret_access_events:
        rbac_issues.append(
            "- сервисным аккаунтам или пользователям разрешён доступ к секретам (возможно, в системных namespace), "
            "что нарушает принцип минимально необходимых привилегий."
        )
    if rbac_events:
        rbac_issues.append(
            "- разрешено создавать RoleBinding/ClusterRoleBinding с ролью cluster-admin без дополнительных ограничений и процесса согласования."
        )
    if privileged_pod_events:
        rbac_issues.append(
            "- отсутствуют ограничения на создание привилегированных pod'ов (нет жёстких Pod Security/PSA-политик)."
        )
    if exec_events:
        rbac_issues.append(
            "- пользователям разрешён exec в pod'ы (включая системные), что повышает риск несанкционированного доступа к критическим сервисам."
        )

    if not rbac_issues:
        rbac_issues_text = (
            "По данным аудита явных проблем в политике RBAC не выявлено, однако рекомендуется проверить соблюдение "
            "принципа минимально необходимых привилегий и ограничить доступ к системным namespace."
        )
    else:
        rbac_issues_text = "\n".join(rbac_issues)

    report_lines = [
        "# Отчёт по результатам анализа Kubernetes Audit Log",
        "",
        "## Подозрительные события",
        "",
        "1. Доступ к секретам:",
        f"   - Кто: {secrets_user}",
        f"   - Где: {secrets_loc}",
        "   - Почему подозрительно: доступ к объектам типа Secret может привести к утечке токенов, паролей и других чувствительных данных, "
        "особенно при доступе к секретам в системных пространствах имён.",
        "",
        "2. Привилегированные поды:",
        f"   - Кто: {priv_user}",
        f"   - Комментарий: {priv_loc}. Создание pod'а с `securityContext.privileged=true` даёт контейнеру расширенный доступ к ноде и "
        "может быть использовано для эскалации привилегий.",
        "",
        "3. Использование kubectl exec в чужом поде:",
        f"   - Кто: {exec_user}",
        f"   - Что делал: {exec_loc}. Операции `exec` позволяют выполнять команды внутри pod'а и могут быть признаком разведки или "
        "попытки закрепиться внутри кластера.",
        "",
        "4. Создание RoleBinding с правами cluster-admin:",
        f"   - Кто: {rbac_user}",
        f"   - К чему привело: {rbac_loc}. Назначение роли `cluster-admin` даёт полный контроль над кластером и считается критической эскалацией привилегий.",
        "",
        "5. Удаление audit-policy.yaml:",
        f"   - Кто: {audit_user}",
        f"   - Возможные последствия: {audit_loc}. Попытки удалить или изменить политику аудита могут быть направлены на сокрытие последующей вредоносной активности.",
        "",
        "## Вывод",
        "",
        compromised_text,
        "",
        "### Ошибки в политике RBAC",
        "",
        rbac_issues_text,
        "",
    ]

    with open(args.report, "w", encoding="utf-8") as rep_f:
        rep_f.write("\n".join(report_lines))

    print(f"Готово.\nПодозрительных событий: {len(unique_events)}")
    print(f"Выжимка: {args.extract}")
    print(f"Отчёт:   {args.report}")

if __name__ == "__main__":
    main()
