#!/usr/bin/env python3
"""Build validated gallery packs and a version-1 source index."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    parser.add_argument('--repository', default='WindyWin/agent-pet-gallery')
    parser.add_argument('--tag', default='v1.0.0')
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("Build on Linux: import verification relies on isolated XDG_DATA_HOME storage.")
    args.output.mkdir(parents=True, exist_ok=True)
    base = f'https://github.com/{args.repository}/releases/download/{args.tag}'
    entries = []
    for source in sorted((ROOT / 'assets').iterdir()):
        metadata = json.loads((source / 'pack.json').read_text(encoding='utf-8'))
        id = metadata['id']
        name = f'{id}-{metadata["version"]}.agentpet'
        archive = args.output / name
        with tempfile.TemporaryDirectory(prefix='gallery-pack-') as temporary:
            folder = Path(temporary) / id
            shutil.copytree(source, folder)
            terms = Path(metadata['terms'])
            (folder / terms.parent).mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / terms, folder / terms)
            subprocess.run([sys.executable, str(ROOT / 'scripts/pack.py'), str(folder),
                            '-o', str(archive.absolute()), '--app', str(args.app.absolute())], check=True)
            # Exercise the actual archive importer in an isolated Linux data directory.
            env = dict(os.environ, XDG_DATA_HOME=str(Path(temporary) / 'data'))
            subprocess.run([str(args.app.absolute()), 'import', str(archive.absolute())],
                           input='yes\n', text=True, env=env, check=True)
            installed = Path(env['XDG_DATA_HOME']) / 'agent-pet/packs/pets' / id
            if not (installed / 'pack.json').is_file():
                raise RuntimeError(f'{id}: import did not commit the pack')
        preview = f'{id}-preview.png'
        shutil.copyfile(source / 'preview.png', args.output / preview)
        entry = {key: metadata[key] for key in ('kind', 'id', 'version', 'name', 'author', 'license', 'schema', 'minAppVersion')}
        entry.update(description=f'{metadata["name"]} for Agent Pet. See the included artwork terms.',
                     preview=f'{base}/{preview}', download=f'{base}/{name}',
                     bytes=archive.stat().st_size, sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
        entries.append(entry)
    (args.output / 'index.json').write_text(json.dumps({'schema_version': 1, 'packs': entries},
                                                    ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
