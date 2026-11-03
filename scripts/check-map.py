#!/usr/bin/env python3
"""Check paper-lean-map.json against a built formal checkout.

`dump` asks Lean (scripts/MapDeclarations.lean) for every declaration the map
names, every theorem compared by the formal comparator files and every
Stafford38.Paper declaration, and writes their fingerprints. `compare` reads
the dumps of the previously pinned and the new formal commit and fails, naming
the card, when a mapped declaration is missing or lives in another file, when
its statement (or a definition's body) changed, when a compared theorem has no
card, or when a Stafford38.Paper declaration that is new since the previous
pin has no card.
"""
from pathlib import Path
import argparse, json, re, subprocess, sys, tempfile

root = Path(__file__).resolve().parent.parent
LEAN = Path(__file__).resolve().parent / 'MapDeclarations.lean'
MAIN = 'main'
# Modules imported together with the project modules, as in scripts/LeanDag.lean.
MAIN_ROOTS = ('Solution', 'FixedSourceSolution')
PAPER = 'Stafford38.Paper'
GENERATED_SUFFIX = re.compile(r'eq_\d+|eq_def|inj|injEq|sizeOf_spec|ext_iff')


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True)


def module_of(file):
    return file.removesuffix('.lean').replace('/', '.')


def group_of(file):
    if file.startswith('Stafford38/') or module_of(file) in MAIN_ROOTS:
        return MAIN
    return module_of(file)


def map_entries(mapping):
    """(card, entry) for every formal declaration named by a card."""
    def walk(card, x):
        if isinstance(x, dict):
            if ('name' in x and 'file' in x and x.get('repo', 'formal') == 'formal'
                    and not x.get('module_only')):
                yield card, x
            for v in x.values():
                yield from walk(card, v)
        elif isinstance(x, list):
            for v in x:
                yield from walk(card, v)
    for item in mapping['items']:
        card = f"{item['kind']} {item['number']}" if item.get('number') else item['id']
        yield from walk(card, item.get('lean', []))


def card_names(mapping):
    names = set()
    def walk(x):
        if isinstance(x, dict):
            if isinstance(x.get('name'), str):
                names.add(x['name'])
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(mapping['items'])
    return names


def comparators(formal):
    out = []
    for path in sorted(formal.glob('comparator*.json')):
        data = json.loads(path.read_text())
        for name in data['theorem_names']:
            out.append((path.name, group_of(data['solution_module'] + '.lean'), name))
    return out


def dump(args):
    formal = args.formal.resolve()
    mapping = json.loads((root / 'paper-lean-map.json').read_text())
    tracked = set(git(formal, 'ls-files', '*.lean').split())
    built = lambda f: (formal / '.lake/build/lib/lean' / f).with_suffix('.olean').exists()
    groups = {MAIN: (set(MAIN_ROOTS), set())}
    lexical = {}
    for _, entry in map_entries(mapping):
        file, group = entry['file'], group_of(entry['file'])
        if group == MAIN:
            if file in tracked:
                groups[MAIN][0].add(module_of(file))
            groups[MAIN][1].add(entry['name'])
        elif file in tracked and built(file):
            groups.setdefault(group, ({group}, set()))[1].add(entry['name'])
        else:
            # Files outside the Lake libraries (tests, docs) are checked by name only.
            text = (formal / file).read_text() if (formal / file).exists() else ''
            last = entry['name'].rpartition('.')[2]
            lexical[f'{file}:{entry["name"]}'] = bool(
                re.search(r'(?<![\w.])' + re.escape(last) + r'(?![\w])', text))
    for _, group, name in comparators(formal):
        groups.setdefault(group, ({group}, set()))[1].add(name)
    # Every project module, so a Stafford38.Paper declaration is seen wherever it lives.
    groups[MAIN][0].update(module_of(f) for f in tracked if f.startswith('Stafford38/'))
    groups[MAIN][1].add(PAPER + '.*')
    result = {}
    with tempfile.TemporaryDirectory(prefix='map-check-') as scratch:
        for group, (modules, names) in sorted(groups.items()):
            mods, lst, out = (Path(scratch) / n for n in ('modules.txt', 'names.txt', 'out.json'))
            mods.write_text('\n'.join(sorted(modules)) + '\n')
            lst.write_text('\n'.join(sorted(names)) + '\n')
            subprocess.run(['lake', 'env', 'lean', '--run', str(LEAN), str(mods), str(lst), str(out)],
                           cwd=formal, check=True)
            result[group] = json.loads(out.read_text())
    args.out.write_text(json.dumps(dict(
        formal_commit=git(formal, 'rev-parse', 'HEAD').strip(),
        toolchain=(formal / 'lean-toolchain').read_text().strip(),
        comparators=comparators(formal), groups=result, lexical=lexical), ensure_ascii=False) + '\n')
    print(f'{sum(map(len, result.values()))} declarations from {len(result)} import groups; '
          f'{len(lexical)} checked by name')


def paper_declarations(data):
    return {n: e for n, e in data['groups'][MAIN].items()
            if n.startswith(PAPER + '.') and not e['generated']
            and e['kind'] in ('theorem', 'def', 'inductive', 'opaque', 'axiom')
            and not GENERATED_SUFFIX.fullmatch(n.rpartition('.')[2])}


def compare(args):
    old, new = (json.loads(p.read_text()) for p in (args.old, args.new))
    mapping = json.loads((root / 'paper-lean-map.json').read_text())
    reviewed = set(args.reviewed)
    same_toolchain = old['toolchain'] == new['toolchain']
    at = f"formal {new['formal_commit'][:7]}"
    failures, checked = [], 0
    for card, entry in map_entries(mapping):
        name, file, group = entry['name'], entry['file'], group_of(entry['file'])
        checked += 1
        if group not in new['groups']:
            if not new['lexical'].get(f'{file}:{name}'):
                failures.append(f'{card}: {name} not found in {file} at {at}')
            continue
        now, before = new['groups'][group].get(name), old['groups'].get(group, {}).get(name)
        if now is None:
            failures.append(f'{card}: {name} does not exist at {at} (map file {file})')
            continue
        if group == MAIN and now['module'] != module_of(file):
            failures.append(f'{card}: {name} is declared in {now["module"]} at {at}, the map says {file}')
        if before is None or name in reviewed:
            continue
        if same_toolchain:
            changed_type = now['type_hash'] != before['type_hash']
            changed_body = now['body_hash'] != before['body_hash']
        else:
            changed_type, changed_body = now['type'] != before['type'], False
        if changed_type:
            failures.append(f'{card}: the type of {name} changed since formal {old["formal_commit"][:7]}; '
                            f'now: {" ".join(now["type"].split())[:300]}')
        elif changed_body:
            failures.append(f'{card}: the definition of {name} changed since formal {old["formal_commit"][:7]}')
    carded = card_names(mapping)
    for comparator, group, name in new['comparators']:
        if name not in new['groups'].get(group, {}):
            failures.append(f'{comparator}: compared theorem {name} is not declared at {at}')
        if name not in carded:
            failures.append(f'{comparator}: compared theorem {name} has no card')
    added = sorted(set(paper_declarations(new)) - set(paper_declarations(old)) - carded)
    for name in added:
        failures.append(f'new declaration {name} ({new["groups"][MAIN][name]["module"]}) has no card')
    if not same_toolchain:
        print(f'Lean toolchain changed ({old["toolchain"]} -> {new["toolchain"]}): '
              'statements compared as printed, definition bodies not compared.')
    if failures:
        print(f'map check FAILED at {at}: {len(failures)} problems', file=sys.stderr)
        for line in failures:
            print('  ' + line, file=sys.stderr)
        sys.exit(1)
    print(f'map check passed at {at}: {checked} mapped declarations present and unchanged since formal '
          f'{old["formal_commit"][:7]}{" (reviewed: " + ", ".join(sorted(reviewed)) + ")" if reviewed else ""}; '
          f'{len(new["comparators"])} compared theorems and {len(paper_declarations(new))} {PAPER} '
          f'declarations covered or unchanged.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    d = sub.add_parser('dump', help='fingerprint the declarations of a built formal checkout')
    d.add_argument('--formal', type=Path, required=True)
    d.add_argument('--out', type=Path, required=True)
    c = sub.add_parser('compare', help='compare the dumps of the old and the new formal pin')
    c.add_argument('old', type=Path)
    c.add_argument('new', type=Path)
    c.add_argument('--reviewed', action='append', default=[], metavar='NAME',
                   help='declaration whose changed statement the cards were checked against')
    args = parser.parse_args()
    dump(args) if args.command == 'dump' else compare(args)


if __name__ == '__main__':
    main()
