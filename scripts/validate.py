#!/usr/bin/env python3
"""Repository builds, open-webui contract, and separate public-source audit.

Never print rendered values, secret values or raw tool/parser error messages.
"""
import argparse
import base64
import binascii
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
SENSITIVE = {'DATABASE_URL', 'WEBUI_SECRET_KEY', 'OPENAI_API_KEY',
             'OAUTH_CLIENT_SECRET', 'S3_ACCESS_KEY_ID', 'S3_SECRET_ACCESS_KEY'}
# 通用模式入代码（内网地址等）；组织公共镜像仓库、namespace 等公开标识不算私有值。
# 组织专属私有值（内部域名、主机地址等）不入 git，由维护者在 scripts/private-patterns.local
# 维护（每行一个正则，# 为注释），参见 private-patterns.example。
PRIVATE = re.compile(r'\b(?:192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)\b', re.I)
ORG_PATTERNS_FILE = Path(__file__).parent / 'private-patterns.local'
CREDENTIAL = re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bAKIA[A-Z0-9]{16}\b|\bghp_[A-Za-z0-9]{30,}\b|\bsk-[A-Za-z0-9_-]{24,}\b')


class Invalid(Exception):
    pass


def require(condition, rule):
    if not condition:
        raise Invalid(rule)


def private_patterns():
    lines = ORG_PATTERNS_FILE.read_text().splitlines() if ORG_PATTERNS_FILE.exists() else []
    try:
        return [re.compile(line.strip(), re.I) for line in lines
                if line.strip() and not line.lstrip().startswith('#')]
    except re.error:
        raise Invalid('PRIVATE_PATTERN_INVALID') from None


def private_hits(text):
    return bool(PRIVATE.search(text)) or any(pattern.search(text) for pattern in private_patterns())


def documents(text):
    try:
        result = [o for o in yaml.safe_load_all(text) if o is not None]
    except yaml.YAMLError:
        raise Invalid('YAML_PARSE_FAILED') from None
    require(all(isinstance(o, dict) for o in result), 'YAML_OBJECT_REQUIRED')
    return result


def read_yaml(path):
    return documents(path.read_text())


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


def secret_data(obj):
    values = {}
    try:
        for key, value in obj.get('data', {}).items():
            require(isinstance(value, str), 'SECRET_ENCODING_INVALID')
            values[key] = base64.b64decode(value.replace('\n', '').replace('\r', ''), validate=True).decode('utf-8')
    except (ValueError, TypeError, UnicodeError, binascii.Error):
        raise Invalid('SECRET_ENCODING_INVALID') from None
    values.update(obj.get('stringData', {}))
    return values


def placeholder(value):
    value = str(value)
    return not value.strip() or 'CHANGE_ME' in value or bool(re.search(r'<[^>]+>', value))


def example_value(value):
    return bool(re.search(r'(?<![\w-])(?:[\w.-]+\.)?example\.(?:com|net|org)(?=[:/\s]|$)', str(value)))


def check_public(objects):
    for obj in objects:
        require(not private_hits(yaml.safe_dump(obj)), 'PRIVATE_ENVIRONMENT_VALUE')
        require(not CREDENTIAL.search(yaml.safe_dump(obj)), 'CREDENTIAL_SIGNATURE')
        values = secret_data(obj) if obj.get('kind') == 'Secret' else obj.get('data', {})
        for key, value in values.items():
            require(not private_hits(str(value)), 'PRIVATE_ENVIRONMENT_VALUE/' + key)
            require(not CREDENTIAL.search(str(value)), 'CREDENTIAL_SIGNATURE/' + key)
            if obj.get('kind') == 'Secret':
                require(placeholder(value), 'SECRET_NOT_PLACEHOLDER/' + key)
            elif key in SENSITIVE:
                raise Invalid('SENSITIVE_KEY_IN_CONFIGMAP/' + key)


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


def check_openwebui(objects, deploy=False):
    expected = {('Namespace', None), ('ServiceAccount', 'open-webui-sa'),
                ('ConfigMap', 'open-webui'), ('Secret', 'open-webui'),
                ('Service', 'open-webui'), ('Service', 'open-webui-redis'),
                ('Ingress', 'open-webui'), ('Deployment', 'open-webui'),
                ('Deployment', 'open-webui-redis')}
    actual = {(o['kind'], None if o['kind'] == 'Namespace' else o['metadata']['name']) for o in objects}
    require(len(objects) == 9 and actual == expected, 'OPENWEBUI_RESOURCE_CONTRACT')
    lookup = {(o['kind'], o['metadata']['name']): o for o in objects}
    namespace = next(o['metadata']['name'] for o in objects if o['kind'] == 'Namespace')
    require(all(o['metadata'].get('namespace') == namespace for o in objects if o['kind'] != 'Namespace'),
            'NAMESPACE_MISMATCH')
    config = lookup[('ConfigMap', 'open-webui')]['data']
    secrets = secret_data(lookup[('Secret', 'open-webui')])
    require(not (set(config) & set(secrets)), 'DUPLICATE_ENV_SOURCES')
    pod = lookup[('Deployment', 'open-webui')]['spec']['template']['spec']
    container = next((c for c in pod['containers'] if c['name'] == 'open-webui'), None)
    require(container is not None, 'APP_CONTAINER_MISSING')
    require(container.get('envFrom') == [{'configMapRef': {'name': 'open-webui'}},
                                         {'secretRef': {'name': 'open-webui'}}], 'ENV_REFERENCE_MISMATCH')
    require(pod.get('serviceAccountName') == 'open-webui-sa', 'SERVICEACCOUNT_REFERENCE_MISMATCH')
    ingress = lookup[('Ingress', 'open-webui')]['spec']
    host = ingress['rules'][0]['host']
    require(urlsplit(config.get('WEBUI_URL', '')).hostname == host, 'WEBUI_HOST_MISMATCH')
    backend = ingress['rules'][0]['http']['paths'][0]['backend']['service']
    require(backend['name'] == 'open-webui' and backend['port'].get('name') == 'http', 'INGRESS_BACKEND_MISMATCH')
    redis_host = urlsplit(config.get('REDIS_URL', '')).hostname
    require(redis_host in {'open-webui-redis', f'open-webui-redis.{namespace}.svc.cluster.local'},
            'REDIS_NAMESPACE_MISMATCH')
    if config.get('WEBUI_URL', '').startswith('https://'):
        require(any(host in t.get('hosts', []) and t.get('secretName') for t in ingress.get('tls', [])),
                'TLS_HOST_MISMATCH')
    for name in ('open-webui', 'open-webui-redis'):
        service = lookup[('Service', name)]['spec']
        template = lookup[('Deployment', name)]['spec']['template']
        require(all(template['metadata']['labels'].get(k) == v for k, v in service['selector'].items()),
                'SERVICE_SELECTOR_MISMATCH')
    if not deploy:
        return
    values = {**config, **secrets}

    def required(key):
        require(key in values and not placeholder(values[key]) and not example_value(values[key]),
                'DEPLOY_REQUIRED/' + key)

    for key in ('WEBUI_URL', 'DATABASE_URL', 'WEBUI_SECRET_KEY', 'OPENAI_API_BASE_URL', 'OPENAI_API_KEY'):
        required(key)
    require(len(secrets['WEBUI_SECRET_KEY']) >= 32, 'WEBUI_SECRET_KEY_TOO_SHORT')
    require(ingress.get('ingressClassName'), 'INGRESS_CLASS_REQUIRED')
    for obj in objects:
        if obj['kind'] == 'Deployment':
            for c in obj['spec']['template']['spec']['containers']:
                require(not example_value(c['image']), 'EXAMPLE_IMAGE_FOR_DEPLOY')
    database = urlsplit(secrets['DATABASE_URL'])
    require(database.scheme in {'postgresql', 'postgres'} and database.hostname and database.username
            and database.password, 'DATABASE_URL_INVALID')
    require(config.get('STORAGE_PROVIDER') == 's3', 'UNSUPPORTED_STORAGE_PROFILE')
    for key in ('S3_BUCKET_NAME', 'S3_REGION_NAME', 'S3_ACCESS_KEY_ID', 'S3_SECRET_ACCESS_KEY'):
        required(key)
    if 'S3_ENDPOINT_URL' in config:
        required('S3_ENDPOINT_URL')
    if config.get('OAUTH_CLIENT_ID') or config.get('OPENID_PROVIDER_URL'):
        for key in ('OAUTH_CLIENT_ID', 'OPENID_PROVIDER_URL', 'OPENID_REDIRECT_URI', 'OAUTH_CLIENT_SECRET'):
            required(key)
        require(config['OPENID_REDIRECT_URI'] == config['WEBUI_URL'].rstrip('/') + '/oauth/oidc/callback',
                'OIDC_CALLBACK_MISMATCH')
    for toggle, endpoint in [('ENABLE_OTEL', 'OTEL_EXPORTER_OTLP_ENDPOINT'),
                             ('ENABLE_OTEL_TRACES', 'OTEL_EXPORTER_OTLP_ENDPOINT'),
                             ('ENABLE_OTEL_METRICS', 'OTEL_METRICS_EXPORTER_OTLP_ENDPOINT'),
                             ('ENABLE_OTEL_LOGS', 'OTEL_LOGS_EXPORTER_OTLP_ENDPOINT')]:
        if str(config.get(toggle, '')).lower() == 'true':
            required(endpoint)


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
    parser.add_argument('--app', choices=['open-webui'])
    parser.add_argument('--deploy', type=Path, help='Validate configured open-webui overlay, without applying')
    parser.add_argument('--local-test', action='store_true', help='Allow local base for non-release tests only')
    parser.add_argument('--audit-public', action='store_true', help='Whole working-tree publication gate, not history')
    args = parser.parse_args()
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
            check_openwebui(objects, deploy=True)
            print('DEPLOY_INPUT_OK', 'resources=' + str(len(objects)), 'runtime=NOT_CHECKED')
            return 0
        catalog = read_yaml(ROOT / 'catalog.yaml')[0]
        require(catalog.get('apiVersion') == 'opsaid.net/addon-store/v1alpha1'
                and catalog.get('kind') == 'AddonCatalog' and isinstance(catalog.get('items'), list), 'CATALOG_INVALID')
        ids = set()
        for item in catalog['items']:
            require(item['id'] not in ids, 'CATALOG_DUPLICATE_ID')
            ids.add(item['id'])
            for field in ('path', 'docs'):
                target = (ROOT / item[field]).resolve()
                require(target.is_relative_to(ROOT) and target.exists(), 'CATALOG_PATH_INVALID')
        paths = [ROOT / 'template/appname', *sorted((ROOT / 'addons').glob('*')),
                 *sorted((ROOT / 'examples/overlays').glob('*'))]
        failures = 0
        for path in paths:
            if not (path / 'kustomization.yaml').exists():
                continue
            try:
                check_refs(path, allow_local=True)
                _, objects = build(path)
                check_objects(objects)
                if path.name in ids or (args.app and path.name == args.app):
                    check_public(objects)
                    check_openwebui(objects)
                    # Full source audit is a separate release gate, including read-only legacy docs.
                    sources = [path / 'kustomization.yaml', *path.glob('configuration/**/*.env')]
                    for source in sources:
                        require(not source_issues(source), 'PUBLIC_INPUT_INVALID/' + str(source.relative_to(ROOT)))
                print('BUILD_OK', path.relative_to(ROOT), 'resources=' + str(len(objects)))
            except Invalid as error:
                print('CHECK_FAIL', path.relative_to(ROOT), str(error))
                failures += 1
        return int(bool(failures))
    except (Invalid, OSError, subprocess.SubprocessError, KeyError, TypeError, ValueError) as error:
        print('CHECK_FAIL', str(error) if isinstance(error, Invalid) else type(error).__name__, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
