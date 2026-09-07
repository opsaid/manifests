"""Catalog, public package layout and local Markdown link checks."""
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from .common import read_yaml, require


APP_ID = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
KIND_DIRECTORIES = {
    'Namespace': 'clusters/namespaces', 'LimitRange': 'clusters/namespaces',
    'ResourceQuota': 'clusters/namespaces', 'PriorityClass': 'clusters/priority-classes',
    'CustomResourceDefinition': 'clusters/crds',
    'ConfigMap': 'configuration/configmaps', 'Secret': 'configuration/secrets',
    'Service': 'network/services', 'Ingress': 'network/ingresses', 'NetworkPolicy': 'network/policies',
    'ServiceAccount': 'security/serviceaccounts', 'Role': 'security/roles',
    'RoleBinding': 'security/rolebindings', 'ClusterRole': 'security/clusterroles',
    'ClusterRoleBinding': 'security/clusterrolebindings',
    'PersistentVolumeClaim': 'storage/persistent-volume-claims',
    'PersistentVolume': 'storage/persistent-volumes', 'StorageClass': 'storage/storage-classes',
    'Deployment': 'workloads/deployments', 'StatefulSet': 'workloads/statefulsets',
    'DaemonSet': 'workloads/daemonsets', 'CronJob': 'workloads/cronjobs', 'Job': 'workloads/jobs',
    **{kind: 'gateway' for kind in ('Gateway', 'HTTPRoute', 'GRPCRoute', 'ReferenceGrant',
                                  'TCPRoute', 'TLSRoute', 'UDPRoute')},
}


def check_catalog(root):
    root = root.resolve()
    entries = read_yaml(root / 'catalog.yaml')
    require(len(entries) == 1, 'CATALOG_INVALID')
    catalog = entries[0]
    require(catalog.get('apiVersion') == 'opsaid.net/addon-store/v1alpha1'
            and catalog.get('kind') == 'AddonCatalog' and isinstance(catalog.get('items'), list),
            'CATALOG_INVALID')
    ids = set()
    for item in catalog['items']:
        require(isinstance(item, dict), 'CATALOG_ITEM_INVALID')
        for key in ('id', 'name', 'description', 'path', 'docs', 'upstream'):
            require(isinstance(item.get(key), str) and item[key].strip(), 'CATALOG_FIELD_REQUIRED/' + key)
        app = item['id']
        require(APP_ID.fullmatch(app), 'CATALOG_ID_INVALID')
        require(app not in ids, 'CATALOG_DUPLICATE_ID')
        ids.add(app)
        require(item['path'] == f'addons/{app}' and item['docs'] == f'docs/apps/{app}/README.md',
                'CATALOG_PATH_CONTRACT')
        package, docs = (root / item['path']).resolve(), (root / item['docs']).resolve()
        require(package.is_relative_to(root) and docs.is_relative_to(root)
                and (package / 'kustomization.yaml').is_file() and docs.is_file(), 'CATALOG_PATH_INVALID')
        upstream = urlsplit(item['upstream'])
        require(upstream.scheme == 'https' and upstream.hostname and not upstream.username
                and not upstream.password, 'CATALOG_UPSTREAM_INVALID')
    return ids


def check_layout(package):
    """Check all source manifests, including optional ones; generator inputs are opaque data."""
    package = package.resolve()
    require(APP_ID.fullmatch(package.name), 'APP_ID_INVALID')
    require((package / 'kustomization.yaml').is_file(), 'PACKAGE_ENTRY_MISSING')
    inputs, resources = set(), set()
    for path in sorted(package.rglob('kustomization.yaml')):
        entries = read_yaml(path)
        require(len(entries) == 1, 'KUSTOMIZATION_INVALID')
        config = entries[0]
        generators = [(g, 'configuration/configmaps') for g in config.get('configMapGenerator', [])]
        generators += [(g, 'configuration/secrets') for g in config.get('secretGenerator', [])]
        for generator, expected in generators:
            for field in ('files', 'envs'):
                for value in generator.get(field, []):
                    source = value.split('=', 1)[-1] if field == 'files' else value
                    target = (path.parent / source).resolve()
                    require(target.is_relative_to(package) and target.is_file(), 'GENERATOR_INPUT_MISSING_OR_OUTSIDE')
                    require(target.is_relative_to(package / expected), 'GENERATOR_INPUT_DIRECTORY')
                    inputs.add(target)
        for reference in config.get('resources', []) + config.get('components', []):
            if '://' in reference or reference.startswith('git@'):
                continue
            target = (path.parent / reference).resolve()
            require(target.is_relative_to(package) and target.exists(), 'RESOURCE_PATH_MISSING_OR_OUTSIDE')
            if target.is_dir():
                require((target / 'kustomization.yaml').is_file(), 'RESOURCE_ENTRY_MISSING')
            else:
                require(target.suffix in {'.yaml', '.yml'}, 'RESOURCE_FILE_TYPE')
                resources.add(target)
    require(not (inputs & resources), 'GENERATOR_RESOURCE_OVERLAP')
    for path in sorted(package.rglob('*')):
        if not path.is_file() or path.suffix not in {'.yaml', '.yml'} or path.name == 'kustomization.yaml':
            continue
        if path.resolve() in inputs:
            continue
        require(path.resolve().is_relative_to(package), 'RESOURCE_PATH_MISSING_OR_OUTSIDE')
        objects = read_yaml(path)
        require(bool(objects), 'RESOURCE_FILE_EMPTY')
        for obj in objects:
            directory = KIND_DIRECTORIES.get(obj.get('kind'))
            require(directory is not None, 'RESOURCE_KIND_UNCLASSIFIED/' + str(path.relative_to(package)))
            require(path.parent == package / directory,
                    'RESOURCE_DIRECTORY_MISMATCH/' + str(path.relative_to(package)))


def check_docs(root):
    """Validate local inline/reference Markdown link destinations, not remote URLs or anchors."""
    root = root.resolve()
    count = 0
    for path in sorted(root.rglob('*.md')):
        if any(p in {'.git', '.venv', '__pycache__'} for p in path.relative_to(root).parts):
            continue
        text = re.sub(r'(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$', '', path.read_text())
        text = re.sub(r'`[^`\n]+`', '', text)
        targets = re.findall(r'\[[^\]\n]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+["\'][^\n]*["\'])?\s*\)', text)
        targets += re.findall(r'^\s*\[[^\]]+\]:\s*(<[^>]+>|\S+)', text, re.M)
        for target in targets:
            target = target.strip('<>')
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            destination = (path.parent / unquote(url.path)).resolve()
            require(destination.is_relative_to(root) and destination.exists(),
                    'DOC_LINK_INVALID/' + str(path.relative_to(root)))
            count += 1
    return count
