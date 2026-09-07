#!/usr/bin/env python3
"""Render a pinned private open-webui overlay in a temporary copy; never apply."""
import argparse
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile

import validate


def render(overlay, secrets_file, output):
    overlay, secrets_file = overlay.resolve(), secrets_file.resolve()
    output = output.parent.resolve() / output.name
    validate.require(not output.exists(), 'OUTPUT_ALREADY_EXISTS')
    validate.require(output.parent.is_dir() and not output.parent.is_symlink(), 'OUTPUT_PARENT_REQUIRED')
    validate.require(not any((p / '.git').exists() for p in [output.parent, *output.parents]),
                     'OUTPUT_MUST_BE_OUTSIDE_GIT')
    validate.require(not (stat.S_IMODE(secrets_file.stat().st_mode) & 0o077), 'SECRET_FILE_REQUIRES_MODE_0600')
    validate.require(not any(p.is_symlink() for p in overlay.rglob('*')), 'OVERLAY_SYMLINK_NOT_SUPPORTED')
    validate.check_refs(overlay)
    version = validate.subprocess.run(['kustomize', 'version'], check=True, capture_output=True, text=True).stdout.strip()
    validate.require(version == (validate.ROOT / 'scripts/kustomize-version.txt').read_text().strip(),
                     'KUSTOMIZE_VERSION_MISMATCH')
    # Do not print, interpolate in a shell, or persist the injected data in the checkout.
    payload = secrets_file.read_text()
    keys = set()
    for line in payload.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        key, separator, value = line.partition('=')
        validate.require(separator and key in validate.SENSITIVE and key not in keys, 'SECRET_INPUT_KEY_INVALID')
        keys.add(key)
    validate.require(keys, 'SECRET_INPUT_EMPTY')
    with tempfile.TemporaryDirectory(prefix='addon-private-') as directory:
        private = Path(directory) / 'overlay'
        shutil.copytree(overlay, private, ignore=shutil.ignore_patterns('.git', '.agents', '.venv', '__pycache__'))
        destination = private / 'configuration/secrets/open-webui.env'
        validate.require(destination.is_file(), 'SECRET_GENERATOR_FILE_MISSING')
        destination.write_text(payload)
        destination.chmod(0o600)
        rendered, objects = validate.build(private)
        validate.check_objects(objects)
        validate.check_contract('open-webui', objects, deploy=True)
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, 'w') as stream:
                stream.write(rendered)
        except BaseException:
            output.unlink(missing_ok=True)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--overlay', required=True, type=Path)
    parser.add_argument('--secrets-file', required=True, type=Path, help='Mode 0600 dotenv supplied by your secret store')
    parser.add_argument('--output', required=True, type=Path, help='New file outside Git; created with mode 0600')
    args = parser.parse_args()
    try:
        render(args.overlay, args.secrets_file, args.output)
    except (validate.Invalid, OSError, validate.subprocess.SubprocessError, KeyError, ValueError, TypeError) as error:
        print('PRIVATE_RENDER_FAILED', str(error) if isinstance(error, validate.Invalid) else type(error).__name__, file=sys.stderr)
        return 1
    print('PRIVATE_RENDER_OK', 'mode=0600', 'runtime=NOT_CHECKED', 'apply=NOT_EXECUTED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
