#!/usr/bin/env python3
"""Rebuild the reviewer HTML from pinned public and bundled local commits."""
from pathlib import Path
import argparse, json, shutil, subprocess, tempfile
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', action='append', default=[], metavar='NAME=PATH',
                    help='Use an existing Git checkout instead of fetching this source.')
args = parser.parse_args()
overrides = {}
for entry in args.source:
    name, separator, directory = entry.partition('=')
    if not separator or not name or not directory:
        parser.error('--source requires NAME=PATH')
    overrides[name] = Path(directory).resolve()
root = Path(__file__).resolve().parent.parent
mapping = json.loads((root / 'paper-lean-map.json').read_text())
manifest = json.loads((root / 'manifest.json').read_text())
with tempfile.TemporaryDirectory(prefix='paper-lean-review-') as scratch:
    arguments = []
    sources = dict(mapping['sources'])
    sources['generator'] = manifest['generator']
    unknown = set(overrides) - set(sources)
    if unknown:
        parser.error('unknown source names: ' + ', '.join(sorted(unknown)))
    for name, source in sources.items():
        if name in overrides:
            destination = overrides[name]
        else:
            destination = Path(scratch) / name
            subprocess.run(['git', 'init', '-q', str(destination)], check=True)
            subprocess.run(['git', '-C', str(destination), 'remote', 'add', 'origin', 'https://github.com/' + source['repo'] + '.git'], check=True)
            subprocess.run(['git', '-C', str(destination), 'fetch', '--filter=blob:none', '--depth=1', 'origin', source.get('base_commit', source['commit'])], check=True)
            if source.get('bundle'):
                subprocess.run(['git', '-C', str(destination), 'fetch', str(root / source['bundle']),
                                'refs/heads/*:refs/remotes/bundle/*'], check=True)
            historical = mapping.get('manuscript_sources', {}).get(name, {}).get('commit')
            if historical and historical != source['commit']:
                subprocess.run(['git', '-C', str(destination), 'fetch', '--filter=blob:none', '--depth=1', 'origin', historical], check=True)
        subprocess.run(['git', '-C', str(destination), 'cat-file', '-e', source['commit'] + '^{commit}'], check=True)
        if name == 'generator':
            if name not in overrides:
                subprocess.run(['git', '-C', str(destination), 'checkout', '-q', source['commit']], check=True)
            elif subprocess.check_output(['git', '-C', str(destination), 'rev-parse', 'HEAD'], text=True).strip() != source['commit']:
                raise SystemExit('Generator override must be checked out at its pinned commit')
            generator = destination
        else:
            arguments.extend(['--source', name + '=' + str(destination)])
    subprocess.run(['npm', 'ci'], cwd=generator, check=True)
    subprocess.run(['node', str(generator / 'build.mjs'), '--map', str(root / 'paper-lean-map.json'), '--check', '--out', str(root), *arguments], check=True)
p = root / 'index.html'
rendered = root / (mapping.get('output_stem', 'stafford38-paper-lean-audit') + '.html')
if rendered != p:
    shutil.copyfile(rendered, p)
    rendered.unlink()
p.write_text(p.read_text().replace('https://itpplasma.github.io/stafford38-formal/lean_proof_details.pdf', './lean_proof_details.pdf'))
version_path = root / 'version.json'
version = json.loads(version_path.read_text())
version['release_version'] = manifest['version']
version_path.write_text(json.dumps(version, indent=2) + '\n')
print('HTML rebuilt from pinned sources. Preserved PDF hashes are in manifest.json.')
