import base64
from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import validate

module = importlib.util.spec_from_file_location('render_private', SCRIPTS / 'render-private.py')
render_private = importlib.util.module_from_spec(module)
module.loader.exec_module(render_private)


class StoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='addon-contract-')
        cls.root = Path(cls.temporary.name)
        cls.upstream = cls.root / 'upstream'
        shutil.copytree(validate.ROOT / 'addons/open-webui', cls.upstream / 'addons/open-webui',
                        ignore=shutil.ignore_patterns('README.md'))
        cls.base = cls.upstream / 'addons/open-webui'
        cls.template = cls.root / 'template'
        shutil.copytree(validate.ROOT / 'examples/overlays/open-webui', cls.template)
        config = yaml.safe_load((cls.template / 'kustomization.yaml').read_text())
        config['resources'] = [os.path.relpath(cls.base, cls.template)]
        (cls.template / 'kustomization.yaml').write_text(yaml.safe_dump(config))
        _, cls.base_objects = validate.build(cls.base)
        _, cls.example_objects = validate.build(cls.template)
        for args in (['init', '-q', str(cls.upstream)], ['-C', str(cls.upstream), 'add', '.'],
                     ['-C', str(cls.upstream), '-c', 'user.name=Contract Test', '-c',
                      'user.email=contract@example.com', 'commit', '-qm', 'Fixture']):
            subprocess.run(['git', *args], check=True, capture_output=True)
        cls.revision = subprocess.run(['git', '-C', str(cls.upstream), 'rev-parse', 'HEAD'],
                                      check=True, capture_output=True, text=True).stdout.strip()

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def overlay(self):
        directory = Path(tempfile.mkdtemp(dir=self.root)) / 'overlay'
        shutil.copytree(self.template, directory)
        path = directory / 'kustomization.yaml'
        config = yaml.safe_load(path.read_text())
        config['resources'] = [os.path.relpath(self.base, directory)]
        path.write_text(yaml.safe_dump(config))
        return directory

    def obj(self, objects, kind, name='open-webui'):
        return next(o for o in objects if o['kind'] == kind and o['metadata']['name'] == name)

    def test_base_and_example_contract(self):
        for objects in (self.base_objects, self.example_objects):
            validate.check_objects(objects)
            validate.check_public(objects)
            validate.check_openwebui(objects)
        base = self.obj(self.base_objects, 'ConfigMap')['data']
        example = self.obj(self.example_objects, 'ConfigMap')['data']
        self.assertNotEqual(base['WEBUI_URL'], example['WEBUI_URL'])
        self.assertEqual(base['HF_HUB_OFFLINE'], example['HF_HUB_OFFLINE'])
        secret = validate.secret_data(self.obj(self.example_objects, 'Secret'))
        self.assertIn('postgres.example.com', secret['DATABASE_URL'])
        self.assertIn('OAUTH_CLIENT_SECRET', secret)
        for name in ('open-webui', 'redis'):
            base_image = self.obj(self.base_objects, 'Deployment', name)['spec']['template']['spec']['containers'][0]['image']
            overlay_image = self.obj(self.example_objects, 'Deployment', name)['spec']['template']['spec']['containers'][0]['image']
            self.assertTrue(overlay_image.startswith('registry.cn-hangzhou.aliyuncs.com/opsaid/'))
            self.assertEqual(base_image.rsplit(':', 1)[1], overlay_image.rsplit(':', 1)[1])
        pod = self.obj(self.example_objects, 'Deployment')['spec']['template']['spec']
        resources = pod['containers'][0]['resources']
        self.assertEqual(resources['requests']['memory'], '2Gi')
        self.assertEqual(resources['limits']['memory'], '4Gi')

    def test_missing_env_fails(self):
        overlay = self.overlay()
        (overlay / 'configuration/configmaps/open-webui.env').unlink()
        with self.assertRaisesRegex(validate.Invalid, 'BUILD_FAILED'):
            validate.build(overlay)

    def test_stale_patch_fails(self):
        overlay = self.overlay()
        path = overlay / 'kustomization.yaml'
        path.write_text(path.read_text().replace('/spec/rules/0/host', '/spec/rules/9/host'))
        with self.assertRaisesRegex(validate.Invalid, 'BUILD_FAILED'):
            validate.build(overlay)

    def test_namespace_string_requires_override(self):
        objects = deepcopy(self.example_objects)
        for obj in objects:
            if obj['kind'] == 'Namespace':
                obj['metadata']['name'] = 'renamed-ns'
            else:
                obj['metadata']['namespace'] = 'renamed-ns'
        self.obj(objects, 'ConfigMap')['data']['REDIS_URL'] = self.obj(self.base_objects, 'ConfigMap')['data']['REDIS_URL']
        with self.assertRaisesRegex(validate.Invalid, 'REDIS_NAMESPACE_MISMATCH'):
            validate.check_openwebui(objects)

    def test_tls_host_mismatch(self):
        objects = deepcopy(self.example_objects)
        self.obj(objects, 'Ingress')['spec']['tls'][0]['hosts'] = ['wrong.example.com']
        with self.assertRaisesRegex(validate.Invalid, 'TLS_HOST_MISMATCH'):
            validate.check_openwebui(objects)

    def test_tls_secret_generator_optional(self):
        overlay = self.overlay()
        path = overlay / 'kustomization.yaml'
        config = yaml.safe_load(path.read_text())
        config['secretGenerator'].append({
            'name': 'open-webui-tls',
            'type': 'kubernetes.io/tls',
            'files': ['tls.crt=configuration/secrets/tls/tls.crt',
                      'tls.key=configuration/secrets/tls/tls.key'],
            'options': {'disableNameSuffixHash': True},
        })
        path.write_text(yaml.safe_dump(config))
        tls_dir = overlay / 'configuration/secrets/tls'
        tls_dir.mkdir(parents=True)
        (tls_dir / 'tls.crt').write_text('-----BEGIN CERTIFICATE-----\nZmFrZS1jZXJ0\n-----END CERTIFICATE-----\n')
        (tls_dir / 'tls.key').write_text('-----BEGIN PRIVATE KEY-----\nZmFrZS1rZXk=\n-----END PRIVATE KEY-----\n')
        _, objects = validate.build(overlay)
        validate.check_objects(objects)
        validate.check_public(objects)
        validate.check_openwebui(objects)
        self.assertEqual(len(objects), 10)
        bad = deepcopy(objects)
        tls = next(o for o in bad if o.get('kind') == 'Secret' and o['metadata']['name'] == 'open-webui-tls')
        tls['type'] = 'Opaque'
        with self.assertRaisesRegex(validate.Invalid, 'TLS_SECRET_INVALID'):
            validate.check_openwebui(bad)
        tls['type'] = 'kubernetes.io/tls'
        tls['data'].pop('tls.key')
        with self.assertRaisesRegex(validate.Invalid, 'TLS_SECRET_INVALID'):
            validate.check_openwebui(bad)

    def test_encoded_private_value_and_unmarked_secret(self):
        for value, rule in [('postgresql://app:CHANGE_ME@' + '192.168.' + '1.2/db', 'PRIVATE_ENVIRONMENT_VALUE'),
                            ('unit-test-credential', 'SECRET_NOT_PLACEHOLDER')]:
            objects = deepcopy(self.base_objects)
            self.obj(objects, 'Secret')['data']['DATABASE_URL'] = base64.b64encode(value.encode()).decode()
            with self.assertRaisesRegex(validate.Invalid, rule):
                validate.check_public(objects)

    def test_wrapped_base64_is_supported(self):
        value = base64.b64encode(b'CHANGE_ME').decode()
        self.assertEqual(validate.secret_data({'data': {'TOKEN': value[:4] + '\n' + value[4:] + '\n'}}),
                         {'TOKEN': 'CHANGE_ME'})

    def test_invalid_secret_encoding_rejected(self):
        for value in (None, 'not-base64!'):
            with self.assertRaisesRegex(validate.Invalid, 'SECRET_ENCODING_INVALID'):
                validate.secret_data({'data': {'TOKEN': value}})

    def test_floating_ref_rejected_before_fetch(self):
        overlay = self.overlay()
        path = overlay / 'kustomization.yaml'
        config = yaml.safe_load(path.read_text())
        for suffix in ('', '?ref=main', '?ref=HEAD'):
            config['resources'] = ['https://git.example.com/app.git//base' + suffix]
            path.write_text(yaml.safe_dump(config))
            with self.assertRaisesRegex(validate.Invalid, 'REMOTE_REF_NOT_PINNED'):
                validate.check_refs(overlay)

    def test_placeholders_rejected_for_deploy(self):
        with self.assertRaisesRegex(validate.Invalid, 'DEPLOY_REQUIRED'):
            validate.check_openwebui(self.example_objects, deploy=True)

    def test_duplicate_resources_rejected(self):
        with self.assertRaisesRegex(validate.Invalid, 'DUPLICATE_RESOURCE'):
            validate.check_objects(self.base_objects + [self.base_objects[0]])

    def test_files_merge_replaces_whole_data_key(self):
        directory = Path(tempfile.mkdtemp(dir=self.root))
        base, overlay = directory / 'base', directory / 'overlay'
        base.mkdir(); overlay.mkdir()
        (base / 'settings.yaml').write_text('keep: base\noverride: base\n')
        (overlay / 'settings.yaml').write_text('override: overlay\n')
        (base / 'kustomization.yaml').write_text(yaml.safe_dump({
            'configMapGenerator': [{'name': 'settings', 'files': ['settings.yaml'], 'literals': ['other=kept']}]}))
        (overlay / 'kustomization.yaml').write_text(yaml.safe_dump({
            'resources': ['../base'], 'configMapGenerator': [
                {'name': 'settings', 'behavior': 'merge', 'files': ['settings.yaml']}]}))
        _, objects = validate.build(overlay)
        self.assertEqual(objects[0]['data']['settings.yaml'], 'override: overlay\n')
        self.assertEqual(objects[0]['data']['other'], 'kept')

    def configured_overlay(self):
        overlay = self.overlay()
        path = overlay / 'kustomization.yaml'
        config = yaml.safe_load(path.read_text())
        config['resources'] = [self.upstream.as_uri() + '//addons/open-webui?ref=' + self.revision]
        config.pop('images')
        config['patches'][0]['patch'] = config['patches'][0]['patch'].replace('open-webui.apps.example.com', 'webui.internal')
        path.write_text(yaml.safe_dump(config))
        path = overlay / 'configuration/configmaps/open-webui.env'
        path.write_text(path.read_text().replace('open-webui.apps.example.com', 'webui.internal')
                        .replace('s3.example.com', 'storage.internal'))
        payload = ('DATABASE_URL=postgresql://app:unit-test-password@postgres.internal:5432/openwebui\n'
                   'WEBUI_SECRET_KEY=unit-test-session-signing-key-with-32-characters\n'
                   'OPENAI_API_KEY=unit-test-api-key\nS3_ACCESS_KEY_ID=unit-test-access\n'
                   'S3_SECRET_ACCESS_KEY=unit-test-secret\n')
        secrets_file = overlay.parent / 'runtime.env'
        secrets_file.write_text(payload)
        secrets_file.chmod(0o600)
        return overlay, secrets_file

    def test_private_render_with_pinned_git_and_cleanup(self):
        overlay, secrets_file = self.configured_overlay()
        original = (overlay / 'configuration/secrets/open-webui.env').read_bytes()
        output = overlay.parent / 'rendered.yaml'
        # The Git fixture uses file:// in a temporary repository: no external service or real secret.
        render_private.render(overlay, secrets_file, output)
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        self.assertEqual((overlay / 'configuration/secrets/open-webui.env').read_bytes(), original)
        objects = validate.read_yaml(output)
        validate.check_openwebui(objects, deploy=True)
        self.assertIn('unit-test-password', validate.secret_data(self.obj(objects, 'Secret'))['DATABASE_URL'])
        with self.assertRaisesRegex(validate.Invalid, 'OUTPUT_ALREADY_EXISTS'):
            render_private.render(overlay, secrets_file, output)

    def test_private_render_rejects_missing_secret_without_output(self):
        overlay, secrets_file = self.configured_overlay()
        secrets_file.write_text('WEBUI_SECRET_KEY=CHANGE_ME\n')
        output = overlay.parent / 'rendered.yaml'
        with self.assertRaisesRegex(validate.Invalid, 'DEPLOY_REQUIRED'):
            render_private.render(overlay, secrets_file, output)
        self.assertFalse(output.exists())

    def test_private_render_rejects_readable_secret_file(self):
        overlay, secrets_file = self.configured_overlay()
        secrets_file.chmod(0o644)
        with self.assertRaisesRegex(validate.Invalid, 'SECRET_FILE_REQUIRES_MODE_0600'):
            render_private.render(overlay, secrets_file, overlay.parent / 'rendered.yaml')

    def test_output_symlink_cannot_bypass_git_boundary(self):
        overlay, secrets_file = self.configured_overlay()
        link = overlay.parent / 'linked-checkout'
        link.symlink_to(self.upstream, target_is_directory=True)
        with self.assertRaisesRegex(validate.Invalid, 'OUTPUT_MUST_BE_OUTSIDE_GIT'):
            render_private.render(overlay, secrets_file, link / 'subdirectory/../rendered.yaml')

    def test_enabled_oidc_requires_complete_input(self):
        overlay, secrets_file = self.configured_overlay()
        output = overlay.parent / 'rendered.yaml'
        render_private.render(overlay, secrets_file, output)
        objects = validate.read_yaml(output)
        self.obj(objects, 'ConfigMap')['data']['OAUTH_CLIENT_ID'] = 'test-client'
        with self.assertRaisesRegex(validate.Invalid, 'DEPLOY_REQUIRED/OPENID_PROVIDER_URL'):
            validate.check_openwebui(objects, deploy=True)

    def test_public_audit_scans_nested_docs_without_values(self):
        directory = Path(tempfile.mkdtemp(dir=self.root))
        path = directory / 'nested/README.md'
        path.parent.mkdir()
        value = '192.168.' + '2.4'
        path.write_text('endpoint: ' + value)
        log = io.StringIO()
        with redirect_stdout(log):
            self.assertTrue(validate.audit(directory))
        self.assertIn('nested/README.md:1', log.getvalue())
        self.assertNotIn(value, log.getvalue())

    def test_public_audit_includes_shared_skill_references(self):
        directory = Path(tempfile.mkdtemp(dir=self.root))
        path = directory / '.agents/skills/app/references/config.md'
        path.parent.mkdir(parents=True)
        value = '192.168.' + '3.5'
        path.write_text('endpoint: ' + value)
        log = io.StringIO()
        with redirect_stdout(log):
            self.assertTrue(validate.audit(directory))
        self.assertIn('.agents/skills/app/references/config.md:1', log.getvalue())
        self.assertNotIn(value, log.getvalue())

    def test_org_patterns_loaded_from_untracked_file(self):
        pattern_file = Path(tempfile.mkdtemp(dir=self.root)) / 'private-patterns.local'
        pattern_file.write_text('# comment\nunit-test-private-ns\n')
        original = validate.ORG_PATTERNS_FILE
        validate.ORG_PATTERNS_FILE = pattern_file
        try:
            self.assertTrue(validate.private_hits('image: registry.example.com/unit-test-private-ns/app:1'))
            self.assertFalse(validate.private_hits('image: registry.example.com/app:1'))
        finally:
            validate.ORG_PATTERNS_FILE = original

    def test_invalid_org_pattern_fails_closed(self):
        pattern_file = Path(tempfile.mkdtemp(dir=self.root)) / 'private-patterns.local'
        pattern_file.write_text('([unclosed\n')
        original = validate.ORG_PATTERNS_FILE
        validate.ORG_PATTERNS_FILE = pattern_file
        try:
            with self.assertRaisesRegex(validate.Invalid, 'PRIVATE_PATTERN_INVALID'):
                validate.private_hits('anything')
        finally:
            validate.ORG_PATTERNS_FILE = original


if __name__ == '__main__':
    unittest.main()
