#!/usr/bin/env python3
"""Repository structure/builds, registered application contracts, and public-source audit.

Never print rendered values, secret values or raw tool/parser error messages.
"""
import argparse
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

import yaml

from checks.common import Invalid, require, documents, read_yaml, secret_data, placeholder, example_value
from checks.open_webui import check as check_openwebui
from checks.repository import APP_ID, check_catalog, check_layout, check_docs

CONTRACTS = {'open-webui': check_openwebui}


def check_contract(app, objects, deploy=False):
    require(app in CONTRACTS, 'APP_CONTRACT_MISSING')
    CONTRACTS[app](objects, deploy=deploy)


ROOT = Path(__file__).resolve().parents[1]
SENSITIVE = {'DATABASE_URL', 'WEBUI_SECRET_KEY', 'OPENAI_API_KEY',
             'OAUTH_CLIENT_SECRET', 'S3_ACCESS_KEY_ID', 'S3_SECRET_ACCESS_KEY'}
# 通用模式入代码（内网地址等）；组织公共镜像仓库、namespace 等公开标识不算私有值。
# 组织专属私有值（内部域名、主机地址等）不入 git，由维护者在 scripts/private-patterns.local
# 维护（每行一个正则，# 为注释），参见 private-patterns.example。
PRIVATE = re.compile(r'\b(?:192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)\b', re.I)
ORG_PATTERNS_FILE = Path(__file__).parent / 'private-patterns.local'
CREDENTIAL = re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bAKIA[A-Z0-9]{16}\b|\bghp_[A-Za-z0-9]{30,}\b|\bsk-[A-Za-z0-9_-]{24,}\b')


def private_patterns():
    lines = ORG_PATTERNS_FILE.read_text().splitlines() if ORG_PATTERNS_FILE.exists() else []
    try:
        return [re.compile(line.strip(), re.I) for line in lines
                if line.strip() and not line.lstrip().startswith('#')]
    except re.error:
        raise Invalid('PRIVATE_PATTERN_INVALID') from None


def private_hits(text):
    return bool(PRIVATE.search(text)) or any(pattern.search(text) for pattern in private_patterns())


def build(path):
    result = subprocess.run(['kustomize', 'build', str(path)], capture_output=True, text=True)
    if result.returncode:
        # Tool errors can embed configuration. Report a useful category, never the raw input.
        detail = result.stderr.lower()
        category = next((label for token, label in [
            ('no such file', 'MISSING_FILE'), ('does not exist', 'MISSING_TARGET'),
            ('unable to parse', 'INVALID_PATCH'), ('cannot find', 'MISSING_TARGET'),
            ('failed to find', 'MISSING_TARGET'), ('merge', 'MERGE_FAILED'),
            ('git', 'REMOTE_FETCH_FAILED')] if token in detail), 'RENDER_FAILED')
        raise Invalid('BUILD_FAILED/' + category)
    return result.stdout, documents(result.stdout)


def check_public(objects):
    for obj in objects:
        require(not private_hits(yaml.safe_dump(obj)), 'PRIVATE_ENVIRONMENT_VALUE')
        require(not CREDENTIAL.search(yaml.safe_dump(obj)), 'CREDENTIAL_SIGNATURE')
        values = secret_data(obj) if obj.get('kind') == 'Secret' else obj.get('data', {})
        # TLS 证书例外（维护者口径）：证书文件允许随 overlay 提交在 configuration/secrets/
        # 下，kubernetes.io/tls Secret 的 tls.crt/tls.key 不按占位符/凭据签名检查，仅要求非空。
        tls_material = obj.get('type') == 'kubernetes.io/tls'
        for key, value in values.items():
            require(not private_hits(str(value)), 'PRIVATE_ENVIRONMENT_VALUE/' + key)
            if tls_material and key in {'tls.crt', 'tls.key'}:
                require(str(value).strip(), 'TLS_SECRET_EMPTY/' + key)
                continue
            require(not CREDENTIAL.search(str(value)), 'CREDENTIAL_SIGNATURE/' + key)
            if obj.get('kind') == 'Secret':
                require(placeholder(value), 'SECRET_NOT_PLACEHOLDER/' + key)
            elif key in SENSITIVE:
                raise Invalid('SENSITIVE_KEY_IN_CONFIGMAP/' + key)


def check_selector(selector, labels):
    require(isinstance(selector, dict) and bool(selector), 'WORKLOAD_SELECTOR_MISSING')
    require(isinstance(labels, dict), 'POD_LABELS_INVALID')
    matches = selector.get('matchLabels', {})
    expressions = selector.get('matchExpressions', [])
    require(isinstance(matches, dict) and isinstance(expressions, list)
            and bool(matches or expressions), 'WORKLOAD_SELECTOR_INVALID')
    require(all(labels.get(k) == v for k, v in matches.items()), 'WORKLOAD_SELECTOR_MISMATCH')
    for expression in expressions:
        require(isinstance(expression, dict), 'WORKLOAD_SELECTOR_INVALID')
        key, operator = expression.get('key'), expression.get('operator')
        values = expression.get('values', [])
        require(isinstance(key, str) and key and isinstance(values, list)
                and all(isinstance(v, str) for v in values), 'WORKLOAD_SELECTOR_INVALID')
        if operator in {'In', 'NotIn'}:
            require(bool(values), 'WORKLOAD_SELECTOR_INVALID')
            matched = key in labels and labels[key] in values
            if operator == 'NotIn':
                matched = not matched
        elif operator in {'Exists', 'DoesNotExist'}:
            require(not values, 'WORKLOAD_SELECTOR_INVALID')
            matched = key in labels if operator == 'Exists' else key not in labels
        else:
            raise Invalid('WORKLOAD_SELECTOR_INVALID')
        require(matched, 'WORKLOAD_SELECTOR_MISMATCH')


def check_objects(objects):
    identities = set()
    for obj in objects:
        meta = obj.get('metadata', {})
        identity = (obj.get('apiVersion', '').split('/')[0] if '/' in obj.get('apiVersion', '') else '',
                    obj.get('kind'), meta.get('namespace', ''), meta.get('name'))
        require(identity[1] and identity[3], 'RESOURCE_IDENTITY_MISSING')
        require(identity not in identities, 'DUPLICATE_RESOURCE')
        identities.add(identity)
        if obj.get('kind') in {'Deployment', 'StatefulSet', 'DaemonSet'}:
            check_selector(obj['spec'].get('selector'),
                           obj['spec']['template'].get('metadata', {}).get('labels', {}))
            pod = obj['spec']['template']['spec']
            for container in pod.get('containers', []) + pod.get('initContainers', []):
                image = container.get('image', '')
                last = image.rsplit('/', 1)[-1]
                require(('@sha256:' in image and len(image.rsplit('@sha256:', 1)[1]) == 64)
                        or (':' in last and last.rsplit(':', 1)[1] not in {'', 'latest'}), 'IMAGE_NOT_PINNED')


def check_refs(path, allow_local=False, visited=None):
    visited = set() if visited is None else visited
    path = path.resolve()
    if path in visited:
        return
    visited.add(path)
    config = read_yaml(path / 'kustomization.yaml')[0]
    for ref in config.get('resources', []) + config.get('components', []):
        remote = '://' in ref or ref.startswith('git@')
        if remote:
            params = parse_qs(urlsplit(ref.removeprefix('git::')).query)
            revision = params.get('ref', [''])[0]
            require(bool(re.fullmatch(r'[0-9a-f]{40}|[a-z0-9-]+-v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?', revision)),
                    'REMOTE_REF_NOT_PINNED')
        else:
            target = (path / ref).resolve()
            if target.is_dir():
                require(allow_local, 'LOCAL_BASE_NOT_ALLOWED_FOR_DEPLOY')
                check_refs(target, allow_local, visited)


def source_issues(path):
    text = path.read_text()
    issues = []
    for number, line in enumerate(text.splitlines(), 1):
        if private_hits(line):
            issues.append((number, 'PRIVATE_ENVIRONMENT_VALUE'))
        if CREDENTIAL.search(line):
            issues.append((number, 'CREDENTIAL_SIGNATURE'))
        if path.suffix == '.env' and not line.lstrip().startswith('#'):
            key, _, value = line.partition('=')
            if key in SENSITIVE and not placeholder(value):
                issues.append((number, 'SECRET_NOT_PLACEHOLDER/' + key))
    if path.suffix in {'.yaml', '.yml'}:
        try:
            for obj in read_yaml(path):
                if obj.get('kind') == 'Secret':
                    check_public([obj])
        except Invalid as error:
            issues.append((0, str(error)))
    return issues


def audit(root):
    failures = 0
    for path in sorted(root.rglob('*')):
        if any(part in {'.git', '.venv', '__pycache__'} for part in path.relative_to(root).parts):
            continue
        if not path.is_file() or path.suffix not in {'.env', '.yaml', '.yml', '.md', '.json', '.txt'}:
            continue
        for line, rule in source_issues(path):
            print('PUBLIC_AUDIT_FAIL', str(path.relative_to(root)) + ':' + str(line), rule)
            failures += 1
    print('PUBLIC_AUDIT', f'findings={failures}', 'history=NOT_CHECKED', 'manual_review=REQUIRED')
    return bool(failures)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--app', help='Check one addon and its example; requires an application contract')
    parser.add_argument('--build-only', action='store_true', help='With --app: structure/build checks without an application contract')
    mode.add_argument('--deploy', type=Path, help='Validate configured open-webui overlay, without applying')
    parser.add_argument('--local-test', action='store_true', help='Allow local base for non-release tests only')
    mode.add_argument('--audit-public', action='store_true', help='Whole working-tree publication gate, not history')
    args = parser.parse_args()
    if args.build_only and not args.app:
        parser.error('--build-only requires --app')
    if args.local_test and not args.deploy:
        parser.error('--local-test requires --deploy')
    try:
        version = subprocess.run(['kustomize', 'version'], check=True, capture_output=True, text=True).stdout.strip()
        require(version == (ROOT / 'scripts/kustomize-version.txt').read_text().strip(), 'KUSTOMIZE_VERSION_MISMATCH')
        print('KUSTOMIZE', version)
        if args.audit_public:
            return int(audit(ROOT))
        if args.deploy:
            check_refs(args.deploy, args.local_test)
            _, objects = build(args.deploy)
            check_objects(objects)
            check_contract('open-webui', objects, deploy=True)
            print('DEPLOY_INPUT_OK', 'resources=' + str(len(objects)), 'runtime=NOT_CHECKED')
            return 0
        ids = check_catalog(ROOT)
        require(ids <= CONTRACTS.keys(), 'APP_CONTRACT_MISSING')
        print('DOCS_OK', 'local_links=' + str(check_docs(ROOT)))
        if args.app:
            require(APP_ID.fullmatch(args.app), 'APP_ID_INVALID')
            require((ROOT / 'addons' / args.app / 'kustomization.yaml').is_file(), 'APP_NOT_FOUND')
            require(args.build_only or args.app in CONTRACTS, 'APP_CONTRACT_MISSING')
            paths = [ROOT / 'addons' / args.app]
            example = ROOT / 'examples/overlays' / args.app
            if example.is_dir():
                paths.append(example)
        else:
            paths = [ROOT / 'template/appname',
                     *sorted(p for p in (ROOT / 'addons').iterdir() if p.is_dir()),
                     *sorted(p for p in (ROOT / 'examples/overlays').iterdir() if p.is_dir())]
        failures = 0
        for path in paths:
            try:
                require((path / 'kustomization.yaml').is_file(), 'PACKAGE_ENTRY_MISSING')
                if path.parent == ROOT / 'addons' or path == ROOT / 'template/appname':
                    check_layout(path)
                check_refs(path, allow_local=True)
                _, objects = build(path)
                check_objects(objects)
                contract = not args.build_only and (path.name in ids or path.name in CONTRACTS)
                if contract:
                    check_public(objects)
                    check_contract(path.name, objects)
                    # Full source audit is a separate release gate, including read-only legacy docs.
                    sources = [path / 'kustomization.yaml', *path.glob('configuration/**/*.env')]
                    for source in sources:
                        require(not source_issues(source), 'PUBLIC_INPUT_INVALID/' + str(source.relative_to(ROOT)))
                print('BUILD_OK', path.relative_to(ROOT), 'resources=' + str(len(objects)),
                      'contract=' + ('PASSED' if contract else 'NOT_CHECKED'))
            except Invalid as error:
                print('CHECK_FAIL', path.relative_to(ROOT), str(error))
                failures += 1
        return int(bool(failures))
    except (Invalid, OSError, subprocess.SubprocessError, KeyError, TypeError, ValueError) as error:
        print('CHECK_FAIL', str(error) if isinstance(error, Invalid) else type(error).__name__, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
