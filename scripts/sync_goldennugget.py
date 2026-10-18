#!/usr/bin/env python3
"""Refresh GoldenNugget UI snapshots without touching independent widgets."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SCOPES = (
    'src/gui',
    'src/qt/custom_elements',
    'src/qt/icon',
    'src/qt/gui',
    'src/qt/fonts',
    'src/qt/credits',
    'styles',
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT.parent / 'GoldenNugget')
    parser.add_argument('--check', action='store_true', help='Report drift without writing files')
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    if source == ROOT or ROOT.is_relative_to(source) or source.is_relative_to(ROOT):
        parser.error('Source must be a separate GoldenNugget checkout')
    for scope in SCOPES:
        if not (source / scope).is_dir():
            parser.error(f'Missing source directory: {source / scope}')

    revision = subprocess.check_output(
        ['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True,
    ).strip()
    files = {}
    changed = []
    for scope in SCOPES:
        for path in sorted((source / scope).rglob('*')):
            if not path.is_file() or '__pycache__' in path.parts or path.suffix == '.pyc':
                continue
            relative = path.relative_to(source)
            data = path.read_bytes()
            files[relative.as_posix()] = hashlib.sha256(data).hexdigest()
            target = ROOT / relative
            if not target.is_file() or target.read_bytes() != data:
                changed.append(relative.as_posix())
                if not args.check:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)

    resources = ET.Element('RCC')
    bundle = ET.SubElement(resources, 'qresource', prefix='/')
    for name in sorted(files):
        path = Path(name)
        if name.startswith('src/qt/') and path.suffix in {'.svg', '.png', '.webp', '.ttf'}:
            ET.SubElement(bundle, 'file').text = path.relative_to('src/qt').as_posix()
    ET.indent(resources, space='    ')
    resource_text = ET.tostring(resources, encoding='unicode') + '\n'
    resource_path = ROOT / 'src/qt/resources.qrc'
    resource_changed = not resource_path.is_file() or resource_path.read_text() != resource_text
    if resource_changed:
        changed.append('src/qt/resources.qrc')
        if not args.check:
            resource_path.write_text(resource_text)

    manifest = json.dumps({
        'source': 'GoldenNugget',
        'revision': revision,
        'scopes': list(SCOPES),
        'files': files,
    }, indent=2, sort_keys=True) + '\n'
    manifest_path = ROOT / 'goldennugget-ui.json'
    metadata_changed = not manifest_path.is_file() or manifest_path.read_text() != manifest
    if args.check:
        for name in changed:
            print(f'Out of sync: {name}')
        if metadata_changed:
            print('Out of sync: goldennugget-ui.json')
        if changed or metadata_changed:
            return 1
        print(f'All {len(files)} UI files match GoldenNugget {revision[:12]}.')
    else:
        manifest_path.write_text(manifest)
        print(f'Synchronized {len(changed)} of {len(files)} UI files from {revision[:12]}.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
