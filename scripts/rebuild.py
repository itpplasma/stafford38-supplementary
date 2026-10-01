#!/usr/bin/env python3
"""Rebuild the frozen reviewer HTML from exact public source commits."""
from pathlib import Path
import json, subprocess, tempfile
root = Path(__file__).resolve().parent.parent
mapping = json.loads((root / 'paper-lean-map.json').read_text())
manifest = json.loads((root / 'manifest.json').read_text())
with tempfile.TemporaryDirectory(prefix='paper-lean-review-') as scratch:
    arguments = []
    sources = dict(mapping['sources'])
    sources['generator'] = manifest['generator']
    for name, source in sources.items():
        destination = Path(scratch) / name
        subprocess.run(['git', 'init', '-q', str(destination)], check=True)
        subprocess.run(['git', '-C', str(destination), 'remote', 'add', 'origin', 'https://github.com/' + source['repo'] + '.git'], check=True)
        subprocess.run(['git', '-C', str(destination), 'fetch', '--filter=blob:none', '--depth=1', 'origin', source['commit']], check=True)
        if name == 'generator':
            subprocess.run(['git', '-C', str(destination), 'checkout', '-q', 'FETCH_HEAD'], check=True)
            generator = destination
        else:
            arguments.extend(['--source', name + '=' + str(destination)])
    subprocess.run(['npm', 'ci'], cwd=generator, check=True)
    subprocess.run(['node', str(generator / 'build.mjs'), '--map', str(root / 'paper-lean-map.json'), '--check', '--out', str(root), *arguments], check=True)
p = root / 'index.html'
p.write_text(p.read_text().replace('https://itpplasma.github.io/stafford38-formal/lean_proof_details.pdf', './lean_proof_details.pdf'))
print('Frozen HTML rebuilt from pinned public inputs. PDF hashes are in manifest.json.')
