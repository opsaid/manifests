"""Open WebUI public and deployment input contract; no cluster operations."""
from urllib.parse import urlsplit

from .common import require, secret_data, placeholder, example_value


def check(objects, deploy=False):
    expected = {('Namespace', None), ('ServiceAccount', 'open-webui-sa'),
                ('ConfigMap', 'open-webui'), ('Secret', 'open-webui'),
                ('Service', 'open-webui'), ('Service', 'redis'),
                ('Ingress', 'open-webui'), ('Deployment', 'open-webui'),
                ('Deployment', 'redis')}
    actual = {(o['kind'], None if o['kind'] == 'Namespace' else o['metadata']['name']) for o in objects}
    # TLS Secret 为可选第 10 个资源：存在时必须是合法 kubernetes.io/tls 证书材料。
    tls_secret = next((o for o in objects if o.get('kind') == 'Secret' and o['metadata']['name'] == 'open-webui-tls'), None)
    require(tls_secret is None or (tls_secret.get('type') == 'kubernetes.io/tls'
            and {'tls.crt', 'tls.key'} <= set(tls_secret.get('data', {}))), 'TLS_SECRET_INVALID')
    if tls_secret is not None:
        expected |= {('Secret', 'open-webui-tls')}
    require(len(objects) == len(expected) and actual == expected, 'OPENWEBUI_RESOURCE_CONTRACT')
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
    require(redis_host in {'redis', f'redis.{namespace}.svc.cluster.local'},
            'REDIS_NAMESPACE_MISMATCH')
    if config.get('WEBUI_URL', '').startswith('https://'):
        require(any(host in t.get('hosts', []) and t.get('secretName') for t in ingress.get('tls', [])),
                'TLS_HOST_MISMATCH')
    for name in ('open-webui', 'redis'):
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

