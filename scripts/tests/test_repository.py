from copy import deepcopy
from pathlib import Path
from contextlib import redirect_stdout
import io
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import validate


class WorkloadTests(unittest.TestCase):
    def workload(self, kind='Deployment'):
        return {'apiVersion': 'apps/v1', 'kind': kind, 'metadata': {'name': 'app'},
                'spec': {'selector': {'matchLabels': {'app': 'app'}},
                         'template': {'metadata': {'labels': {'app': 'app'}},
                                      'spec': {'containers': [{'name': 'app', 'image': 'example/app:1.0'}]}}}}

    def test_missing_and_mismatched_selectors_fail(self):
        for kind in ('Deployment', 'StatefulSet', 'DaemonSet'):
            good = self.workload(kind)
            validate.check_objects([good])
            for selector, rule in ((None, 'WORKLOAD_SELECTOR_MISSING'),
                                   ({'matchLabels': {}}, 'WORKLOAD_SELECTOR_INVALID'),
                                   ({'matchLabels': {'app': 'other'}}, 'WORKLOAD_SELECTOR_MISMATCH')):
                with self.subTest(kind=kind, selector=selector):
                    bad = deepcopy(good)
                    bad['spec']['selector'] = selector
                    with self.assertRaisesRegex(validate.Invalid, rule):
                        validate.check_objects([bad])

    def test_selector_expressions(self):
        for operator, key, values in (('In', 'app', ['app']), ('NotIn', 'missing', ['app']),
                                      ('Exists', 'app', []), ('DoesNotExist', 'missing', [])):
            selector = {'matchExpressions': [{'key': key, 'operator': operator, 'values': values}]}
            validate.check_selector(selector, {'app': 'app'})
        with self.assertRaisesRegex(validate.Invalid, 'WORKLOAD_SELECTOR_MISMATCH'):
            validate.check_selector({'matchExpressions': [{'key': 'app', 'operator': 'NotIn', 'values': ['app']}]},
                                    {'app': 'app'})
        with self.assertRaisesRegex(validate.Invalid, 'WORKLOAD_SELECTOR_INVALID'):
            validate.check_selector({'matchExpressions': [{'key': 'app', 'operator': 'Exists', 'values': ['app']}]},
                                    {'app': 'app'})

    def test_template_renders_valid_selectors(self):
        _, objects = validate.build(validate.ROOT / 'template/appname')
        validate.check_objects(objects)
        self.assertEqual({o['kind'] for o in objects}, {'Namespace', 'ConfigMap', 'Deployment', 'Service'})


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='repository-check-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.write('scripts/kustomize-version.txt', (validate.ROOT / 'scripts/kustomize-version.txt').read_text())
        self.package = self.root / 'addons/demo'
        self.write('addons/demo/clusters/namespaces/demo.yaml',
                   {'apiVersion': 'v1', 'kind': 'Namespace', 'metadata': {'name': 'demo'}})
        self.write('addons/demo/kustomization.yaml', {'resources': ['clusters/namespaces/demo.yaml']})
        self.write('docs/apps/demo/README.md', '# Demo\n')
        self.item = {'id': 'demo', 'name': 'Demo', 'description': 'Example package', 'path': 'addons/demo',
                     'docs': 'docs/apps/demo/README.md', 'upstream': 'https://git.example.com/demo'}
        self.catalog([])

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content if isinstance(content, str) else yaml.safe_dump(content))
        return path

    def catalog(self, items):
        self.write('catalog.yaml', {'apiVersion': 'opsaid.net/addon-store/v1alpha1',
                                   'kind': 'AddonCatalog', 'items': items})

    def test_catalog_requires_metadata_entry_and_docs(self):
        self.catalog([self.item])
        self.assertEqual(validate.check_catalog(self.root), {'demo'})
        for field in self.item:
            bad = dict(self.item)
            bad.pop(field)
            self.catalog([bad])
            with self.assertRaisesRegex(validate.Invalid, 'CATALOG_FIELD_REQUIRED'):
                validate.check_catalog(self.root)
        self.catalog([self.item, self.item])
        with self.assertRaisesRegex(validate.Invalid, 'CATALOG_DUPLICATE_ID'):
            validate.check_catalog(self.root)
        self.catalog([self.item])
        (self.package / 'kustomization.yaml').unlink()
        with self.assertRaisesRegex(validate.Invalid, 'CATALOG_PATH_INVALID'):
            validate.check_catalog(self.root)

    def test_catalog_rejects_paths_outside_contract(self):
        self.catalog([{**self.item, 'docs': '../README.md'}])
        with self.assertRaisesRegex(validate.Invalid, 'CATALOG_PATH_CONTRACT'):
            validate.check_catalog(self.root)
        self.catalog([self.item])
        docs = self.root / 'docs/apps/demo/README.md'
        docs.unlink()
        docs.mkdir()
        with self.assertRaisesRegex(validate.Invalid, 'CATALOG_PATH_INVALID'):
            validate.check_catalog(self.root)

    def test_layout_distinguishes_generator_input_from_manifest(self):
        config = {'resources': ['clusters/namespaces/demo.yaml'],
                  'configMapGenerator': [{'name': 'demo', 'files': ['settings.yaml=configuration/configmaps/settings.yaml']}]}
        self.write('addons/demo/kustomization.yaml', config)
        self.write('addons/demo/configuration/configmaps/settings.yaml', {'kind': 'not-a-kubernetes-resource', 'setting': True})
        validate.check_layout(self.package)
        config['resources'].append('configuration/configmaps/settings.yaml')
        self.write('addons/demo/kustomization.yaml', config)
        with self.assertRaisesRegex(validate.Invalid, 'GENERATOR_RESOURCE_OVERLAP'):
            validate.check_layout(self.package)

    def test_layout_rejects_misplaced_secret_and_missing_reference(self):
        misplaced = self.write('addons/demo/configuration/configmaps/secret.yaml',
                               {'apiVersion': 'v1', 'kind': 'Secret', 'metadata': {'name': 'demo'}})
        with self.assertRaisesRegex(validate.Invalid, 'RESOURCE_DIRECTORY_MISMATCH'):
            validate.check_layout(self.package)
        misplaced.unlink()
        self.write('addons/demo/kustomization.yaml', {'resources': ['missing.yaml']})
        with self.assertRaisesRegex(validate.Invalid, 'RESOURCE_PATH_MISSING_OR_OUTSIDE'):
            validate.check_layout(self.package)

    def test_layout_rejects_unknown_kind_and_outside_generator(self):
        unknown = self.write('addons/demo/clusters/crds/custom.yaml',
                             {'apiVersion': 'example.com/v1', 'kind': 'CustomInstance', 'metadata': {'name': 'demo'}})
        with self.assertRaisesRegex(validate.Invalid, 'RESOURCE_KIND_UNCLASSIFIED'):
            validate.check_layout(self.package)
        unknown.unlink()
        self.write('addons/shared.env', 'SETTING=example\n')
        self.write('addons/demo/kustomization.yaml', {'configMapGenerator': [{'name': 'demo', 'envs': ['../shared.env']}]})
        with self.assertRaisesRegex(validate.Invalid, 'GENERATOR_INPUT_MISSING_OR_OUTSIDE'):
            validate.check_layout(self.package)

    def test_docs_checks_inline_and_reference_links_but_ignores_code(self):
        self.write('docs/README.md', '[demo](apps/demo/README.md)\n[demo][app]\n\n[app]: apps/demo/README.md\n'
                   '```markdown\n[placeholder](missing.md)\n```\n`[example](missing.md)`\n[remote](https://example.com)\n')
        self.assertEqual(validate.check_docs(self.root), 2)
        for text in ('[broken](missing.md)', '[reference]: missing.md', '[outside](../../missing.md)'):
            self.write('docs/README.md', text)
            with self.assertRaisesRegex(validate.Invalid, 'DOC_LINK_INVALID'):
                validate.check_docs(self.root)

    def run_main(self, *args):
        output = io.StringIO()
        with patch.object(validate, 'ROOT', self.root), patch.object(sys, 'argv', ['validate.py', *args]), redirect_stdout(output):
            status = validate.main()
        return status, output.getvalue()

    def test_app_selection_and_contract_dispatch(self):
        self.write('addons/unrelated/kustomization.yaml', {'resources': ['missing.yaml']})
        checker = Mock()
        with patch.dict(validate.CONTRACTS, {'demo': checker}):
            status, output = self.run_main('--app', 'demo')
        self.assertEqual(status, 0)
        checker.assert_called_once()
        self.assertNotIn('unrelated', output)
        self.assertIn('contract=PASSED', output)
        with self.assertRaisesRegex(validate.Invalid, 'APP_CONTRACT_MISSING'):
            validate.check_contract('unregistered', [])

    def test_build_only_does_not_claim_contract_and_catalog_requires_checker(self):
        status, output = self.run_main('--app', 'demo', '--build-only')
        self.assertEqual(status, 0)
        self.assertIn('contract=NOT_CHECKED', output)
        with patch('sys.stderr', new_callable=io.StringIO) as errors:
            status, _ = self.run_main('--app', 'demo')
        self.assertEqual(status, 1)
        self.assertIn('APP_CONTRACT_MISSING', errors.getvalue())
        self.catalog([self.item])
        with patch('sys.stderr', new_callable=io.StringIO) as errors:
            status, _ = self.run_main('--app', 'demo', '--build-only')
        self.assertEqual(status, 1)
        self.assertIn('APP_CONTRACT_MISSING', errors.getvalue())

    def test_template_can_be_instantiated(self):
        package = self.root / 'sample'
        shutil.copytree(validate.ROOT / 'template/appname', package)
        for path in package.rglob('*.yaml'):
            path.write_text(path.read_text().replace('appname', 'sample'))
        for path in list(package.rglob('appname.yaml')):
            path.rename(path.with_name('sample.yaml'))
        validate.check_layout(package)
        _, objects = validate.build(package)
        validate.check_objects(objects)
        self.assertEqual(len(objects), 4)
        self.assertTrue(all(o['metadata']['name'] == 'sample' for o in objects))
        entry = package / 'kustomization.yaml'
        config = yaml.safe_load(entry.read_text())
        config['resources'] += ['network/ingresses/sample.yaml', 'clusters/namespaces/limit-range.yaml',
                                'clusters/namespaces/memory-quota.yaml']
        entry.write_text(yaml.safe_dump(config))
        _, objects = validate.build(package)
        validate.check_objects(objects)
        self.assertEqual(len(objects), 7)
        ingress = next(o for o in objects if o['kind'] == 'Ingress')
        self.assertNotIn('ingressClassName', ingress['spec'])
        self.assertEqual(ingress['spec']['rules'][0]['host'], 'sample.example.com')


if __name__ == '__main__':
    unittest.main()
