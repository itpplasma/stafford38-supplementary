#!/usr/bin/env bash
# Bring the supplementary to a formal commit on the workstation.
#
# usage: scripts/sync-formal.sh <formal-commit> [--push] [--reviewed NAME]...
#
# Builds the commit, checks paper-lean-map.json against it, repins, regenerates
# every generated file, runs the browser check and records the verification in
# a worktree under $WT_ROOT/stafford38-supplementary/sync-<sha>-<date>. With
# --push it opens the pull request, adds it to the merge queue, waits for the
# merge and the Pages deploy and removes the worktree. --reviewed names a
# declaration whose changed statement the cards were checked against.
# Rerunning after a failure reuses the worktree, so cards written there are kept.
set -euo pipefail

usage() { sed -n '4p' "$0" | sed 's/^# //' >&2; exit 2; }
target='' push=false reviewed=()
while [ $# -gt 0 ]; do
  case $1 in
    --push) push=true ;;
    --reviewed) [ $# -ge 2 ] || usage; reviewed+=(--reviewed "$2"); shift ;;
    -h|--help) usage ;;
    -*) usage ;;
    *) [ -z "$target" ] || usage; target=$1 ;;
  esac
  shift
done
[ -n "$target" ] || usage

here=$(cd -- "$(dirname -- "$0")" && pwd)
repo=itpplasma/stafford38-supplementary
live=https://itpplasma.github.io/stafford38-supplementary
cache=${STAFFORD38_SYNC_CACHE:-/mnt/storage/cache/stafford38-sync}
wt_root=${WT_ROOT:-/mnt/storage/wt}
cap=${LOCAL_CAP:-/home/ert/code/prompts/scripts/local-cap.sh}
mem=${SYNC_MEM:-32G}
export CHROMIUM_PATH=${CHROMIUM_PATH:-/usr/bin/chromium}
export MPLBACKEND=Agg
formal=$cache/formal
started=$(date +%s)
run='' current=''

die() { echo "sync-formal: $*" >&2; exit 1; }
trap 's=$?; [ $s -eq 0 ] || echo "sync-formal: stopped${current:+ in step \"$current\"}${run:+; logs in $run}" >&2' EXIT

# step NAME COMMAND...: run with its output in $run/NAME.log and stop on failure.
step() {
  local name=$1 t0
  shift
  current=$name t0=$(date +%s)
  echo "[$(date +%T)] $name"
  # errexit is re-enabled inside the subshell, outside any condition, so the step stops at its first failure.
  set +e
  (set -e; "$@") >"$run/$name.log" 2>&1
  local status=$?
  set -e
  if [ $status -ne 0 ]; then
    tail -n 25 "$run/$name.log" >&2
    die "step \"$name\" failed; full log: $run/$name.log"
  fi
  printf '%-28s %6ss\n' "$name" $(($(date +%s) - t0)) >>"$run/timings.txt"
}

json() { python3 -c 'import json,sys; d=json.load(open(sys.argv[1]))
for k in sys.argv[2].split("."): d=d[k]
print(d)' "$1" "$2"; }

capped() { "$cap" --mem "$mem" "$@"; }

# Every module of the Stafford38 library and every Lake library root, as scripts/verify.sh builds them.
build_formal() {
  cd "$formal"
  lake exe cache get
  local libs
  libs=$(python3 -c 'import tomllib,pathlib
for lib in tomllib.load(open("lakefile.toml","rb")).get("lean_lib",[]):
    if pathlib.Path(lib["name"]+".lean").exists(): print(lib["name"])')
  # shellcheck disable=SC2046
  capped lake build $(git ls-files 'Stafford38/*.lean' | sed 's/\.lean$//; s#/#.#g') $libs
}

checkout_formal() {
  git -C "$formal" checkout -q --detach "$1"
  [ -z "$(git -C "$formal" status --porcelain --untracked-files=no)" ] || die "formal build checkout $formal has local changes"
}

dump_map() {
  capped python3 "$here/check-map.py" dump --map "$wt/paper-lean-map.json" --formal "$formal" --out "$1"
}

tools_key() { cat "$here/check-map.py" "$here/MapDeclarations.lean" | sha256sum | cut -c1-12; }

# Lean declaration fingerprints of a formal commit, cached per commit and tool version.
dump_cached() {
  local sha=$1 out=$2 cached=$cache/dumps/$1-$(tools_key).json
  if [ -s "$cached" ]; then
    cp "$cached" "$out"
    echo "reusing $cached"
    return
  fi
  checkout_formal "$sha"
  build_formal
  dump_map "$out"
  mkdir -p "$cache/dumps"
  cp "$out" "$cached"
}

setup_generator() {
  local commit base bundle dir
  commit=$(json "$wt/manifest.json" generator.commit)
  base=$(json "$wt/manifest.json" generator.base_commit)
  bundle=$(json "$wt/manifest.json" generator.bundle)
  dir=$cache/generator/$commit
  if [ ! -d "$dir/node_modules" ] || [ "$(git -C "$dir" rev-parse HEAD 2>/dev/null)" != "$commit" ]; then
    rm -rf "$dir"
    mkdir -p "$dir"
    git -C "$dir" init -q .
    git -C "$dir" remote add origin https://github.com/itpplasma/paper-lean-audit.git
    git -C "$dir" fetch -q --filter=blob:none --depth=1 origin "$base"
    git -C "$dir" fetch -q "$wt/$bundle" 'refs/heads/*:refs/remotes/bundle/*'
    git -C "$dir" checkout -q "$commit"
    (cd "$dir" && npm ci)
  fi
  [ -z "$(git -C "$dir" status --porcelain --untracked-files=no)" ] || die "generator checkout $dir has local changes"
  echo "$dir" >"$run/generator.path"
}

setup_global() {
  local commit dir=$cache/global
  commit=$(json "$wt/paper-lean-map.json" sources.global.commit)
  [ -d "$dir/.git" ] || git clone -q https://github.com/itpplasma/global-stafford-formal.git "$dir"
  if [ ! -e "$dir/.lake/sync-built-$commit" ]; then
    git -C "$dir" fetch -q origin
    git -C "$dir" checkout -q --detach "$commit"
    (cd "$dir" && lake exe cache get && capped lake build)
    touch "$dir/.lake/sync-built-$commit"
  fi
}

# The frozen manuscript, built once per paper commit in an isolated checkout.
setup_paper() {
  local commit dir files
  commit=$(json "$wt/paper-lean-map.json" sources.paper.commit)
  dir=$cache/paper/$commit
  if [ ! -s "$dir/build/human_readable_main.pdf" ]; then
    rm -rf "$dir"
    mkdir -p "$dir/build"
    git clone -q https://github.com/itpplasma/stafford38-paper.git "$dir/checkout"
    git -C "$dir/checkout" checkout -q --detach "$commit"
    files=$(python3 -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1]))["sources"]["paper"]["snapshot"]["files"]))' "$wt/paper-lean-map.json")
    for f in $files; do cp "$dir/checkout/$f" "$dir/build/"; done
    (cd "$dir/build" && SOURCE_DATE_EPOCH=$(git -C "$dir/checkout" log -1 --format=%ct) FORCE_SOURCE_DATE=1 \
      latexmk -pdf -interaction=nonstopmode -halt-on-error human_readable_main.tex)
  fi
  echo "$dir" >"$run/paper.path"
}

# Receipt of scripts/verify.sh in the form of the earlier receipts.
verify_formal() {
  local cached=$cache/verify/$target.receipt
  if [ -s "$cached" ]; then
    cp "$cached" "$run/formal-verify.receipt"
    echo "reusing $cached"
    return
  fi
  cd "$formal"
  # The Palomar bootstrap accepts exactly bubblewrap 0.12.0; a copy in $cache/bin takes precedence.
  [ ! -x "$cache/bin/bwrap" ] || export PATH=$cache/bin:$PATH
  [ "$(bwrap --version 2>/dev/null)" = "bubblewrap 0.12.0" ] ||
    die "scripts/verify.sh needs bubblewrap 0.12.0 (found: $(bwrap --version 2>&1)); place that binary at $cache/bin/bwrap"
  capped bash scripts/verify.sh >"$run/verify-output.log" 2>&1
  {
    cat "$run/verify-output.log"
    echo "verify exit 0"
    for log in .lake/verification/*terminal-dependency-guard.log; do
      grep -E '^root:|strict dependency guard passed' "$log" || true
    done
    cat .lake/verification/*dependency-routes.log 2>/dev/null | { grep -h 'dependency route passed' || true; } | sort -u
  } | scrub >"$run/formal-verify.receipt"
  mkdir -p "$cache/verify"
  cp "$run/formal-verify.receipt" "$cached"
}

# Local paths stay out of committed receipts.
scrub() { sed -e "s#$wt/##g; s#$wt#.#g; s#$formal/##g; s#$formal#.#g; s#$cache#<cache>#g; s#$HOME#~#g"; }

repin() {
  python3 - "$wt" "$target" "$receipt" <<'PY'
import json, os, re, subprocess, sys
from pathlib import Path
wt, new, receipt = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
def load(p): return json.loads((wt / p).read_text())
def save(p, d): (wt / p).write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
for p in ('paper-lean-map.json', 'manifest.json', 'version.json'):
    raw = (wt / p).read_text()
    if json.dumps(json.loads(raw), indent=2, ensure_ascii=False) + '\n' != raw:
        raise SystemExit(f'{p} is not in the canonical JSON layout; refusing to rewrite it')
cache_formal = Path(os.environ['SYNC_FORMAL'])
subject = subprocess.check_output(['git', '-C', str(cache_formal), 'log', '-1', '--format=%s', new], text=True).strip()
subject = re.sub(r'\s*\(#\d+\)$', '', subject)
lake = {p['name']: p['rev'] for p in json.loads(subprocess.check_output(
    ['git', '-C', str(cache_formal), 'show', new + ':lake-manifest.json'], text=True))['packages']}
changed = []
for p in ('paper-lean-map.json', 'manifest.json'):
    d = load(p)
    s = d['sources']
    s['formal']['commit'] = new
    s['formal']['note'] = f'Formal proof at commit {new[:7]}: {subject}.'
    for name, pkg in (('library', 'algebraicAnalysis'), ('mathlib', 'mathlib')):
        if s[name]['commit'] != lake[pkg]:
            changed.append(name)
            s[name]['commit'] = lake[pkg]
            if name == 'library':
                s[name]['note'] = f'AlgebraicAnalysis dependency pinned by formal commit {new[:7]}.'
    if p == 'manifest.json':
        fv = d['formal_verification']
        fv.update(source=new, status='passed', receipt=f'{receipt}/formal-verify.log')
    save(p, d)
v = load('version.json')
v['formal'] = new
save('version.json', v)
print('repinned formal' + (', ' + ', '.join(sorted(set(changed))) if changed else ''))
Path(os.environ['SYNC_RUN'], 'repinned-dependencies').write_text(' '.join(sorted(set(changed))))
PY
}

update_readme() {
  python3 - "$wt/README.md" "${target:0:7}" "$receipt" <<'PY'
import re, sys
path, short, receipt = sys.argv[1:]
text = open(path).read()
pattern = re.compile(r'The Lean sources are pinned to formal commit\s+[0-9a-f]{7,40}, which passes the repository verifier\s*'
                     r'\(\[log\]\([^)]*\)\)\.')
new = (f'The Lean sources are pinned to formal commit\n{short}, which passes the repository verifier\n'
       f'([log]({receipt}/formal-verify.log)).')
text, count = pattern.subn(new, text)
if count != 1:
    raise SystemExit(f'README.md: expected one formal pin sentence, found {count}; update the pattern in sync-formal.sh')
open(path, 'w').write(text)
PY
}

write_receipt_readme() {
  local paper subject
  paper=$(json "$wt/paper-lean-map.json" sources.paper.commit)
  subject=$(git -C "$formal" log -1 --format=%s "$target")
  cat >"$wt/$receipt/README.md" <<EOF
# Formal sync to ${target:0:7} ($(date +'%-d %B %Y'))

The manuscript is unchanged (paper commit \`$paper\`). The Lean sources move
from formal commit \`$old\` to \`$target\`
($subject).

- \`formal-verify.log\`: the repository verifier \`scripts/verify.sh\` run on
  \`$target\`, followed by the root and route lines of its dependency guards.
- \`map-check.log\`: every declaration named by a card exists at this commit in
  the file the card names, and its statement is unchanged since \`${old:0:7}\`
  unless listed as reviewed; every theorem of the comparator files and every
  \`Stafford38.Paper\` declaration added since \`${old:0:7}\` has a card.
- \`reader-build.log\`, \`browser.json\`, \`paper-build.log\` and
  \`verification.json\`: the reader build, the browser check of every card and
  the isolated build of the paper PDF.

Source pages, Lean references and both proof graphs are regenerated from the
pinned sources; the cards themselves are not re-reviewed by this update.
EOF
}

regenerate() {
  local gen global=$cache/global
  gen=$(cat "$run/generator.path")
  cd "$wt"
  git rm -rqf --ignore-unmatch sources/formal
  rm -rf sources/formal
  if grep -qw library "$run/repinned-dependencies"; then
    git rm -rqf --ignore-unmatch sources/library
    rm -rf sources/library
  fi
  python3 scripts/rebuild.py --skip-install --source generator="$gen" --source formal="$formal" \
    --source library="$formal/.lake/packages/algebraicAnalysis" --source mathlib="$formal/.lake/packages/mathlib" \
    >"$run/reader-build.raw.log" 2>&1 || { cat "$run/reader-build.raw.log"; return 1; }
  scrub <"$run/reader-build.raw.log" >"$run/reader-build.log"
  python3 scripts/extract-lean-references.py --formal "$formal" --global "$global"
  python3 scripts/link-lean-references.py
  python3 scripts/build-lean-dag.py --formal "$formal"
  python3 scripts/build-proof-dag.py
  python3 scripts/build-definitions.py --formal "$formal"
  rm -rf scripts/__pycache__
}

generated_paths=(README.md manifest.json paper-lean-map.json version.json index.html lean-dag.html proof-dag.html definitions.html
                 SHA256SUMS human_readable_main.pdf sources verification/lean-dag verification/lean-references verification/definitions)

commit_paths() {
  local message=$1
  cd "$wt"
  git add -A -- "${generated_paths[@]}" "$receipt"
  local stray
  stray=$( (git diff --name-only; git ls-files --others --exclude-standard) | sort -u)
  [ -z "$stray" ] || { echo "$stray" | head -20; die "files outside the generated set changed; inspect $wt"; }
  git diff --cached --quiet || git commit -q -m "$message"
}

record() {
  local paper gen test_log
  paper=$(cat "$run/paper.path")
  gen=$(cat "$run/generator.path")
  test_log=$(json "$wt/manifest.json" checks.generator_tests.log)
  cd "$wt"
  python3 scripts/record-manuscript-verification.py --paper "$paper/checkout" --paper-build "$paper/build" \
    --generator "$gen" --test-log "$test_log" \
    --tests-not-rerun "Generator unchanged at its pinned commit; only the formal pin and map cards changed." \
    --browser-receipt "$run/reader-check/browser.json" --reader-log "$run/reader-build.log" \
    --receipt-dir "$receipt" --formal-repinned
  rm -rf scripts/__pycache__
}

final_checks() {
  cd "$wt"
  sha256sum -c --quiet SHA256SUMS
  if git diff origin/main -- . ':!sources' | grep -E '^\+' | grep -E '/mnt/|/home/|/var/tmp/|/tmp/'; then
    echo "local paths in the added lines above"
    return 1
  fi
  [ -z "$(git status --porcelain)" ]
  [ "$(json version.json formal)" = "$target" ]
}

land() {
  local short=${target:0:7} url num merge_sha state id deadline body
  cd "$wt"
  git push -q -u origin "$branch"
  body=$run/pr-body.md
  cat >"$body" <<EOF
Pins the reader's Lean sources to formal commit $short (previously ${old:0:7}) and regenerates the source pages, Lean references, both proof graphs and the reader.

The map check, the repository verifier at $short, the browser check of every card and the isolated paper build pass; receipts are in \`$receipt/\`. The manuscript is unchanged.

Chris&AI
EOF
  url=$(gh pr create -R "$repo" --base main --head "$branch" --title "Pin the Lean sources to formal $short" --body-file "$body")
  num=${url##*/}
  echo "opened $url"
  # The merge queue squashes; --auto enqueues once the required check has passed.
  gh pr merge "$num" -R "$repo" --auto || gh pr merge "$num" -R "$repo"
  deadline=$(($(date +%s) + 5400))
  while :; do
    state=$(gh pr view "$num" -R "$repo" --json state -q .state)
    [ "$state" = MERGED ] && break
    [ "$state" = CLOSED ] && die "pull request $url was closed"
    if gh run list -R "$repo" --event merge_group -L 5 --json headBranch,conclusion \
         -q ".[]|select(.conclusion==\"failure\" and (.headBranch|contains(\"pr-$num-\")))|.headBranch" | grep -q .; then
      die "merge queue checks failed for $url"
    fi
    [ "$(date +%s)" -lt "$deadline" ] || die "pull request $url not merged after 90 minutes"
    sleep 30
  done
  merge_sha=$(gh pr view "$num" -R "$repo" --json mergeCommit -q .mergeCommit.oid)
  echo "merged as $merge_sha"
  deadline=$(($(date +%s) + 900))
  until id=$(gh run list -R "$repo" --workflow pages.yml --commit "$merge_sha" --json databaseId -q '.[0].databaseId') && [ -n "$id" ]; do
    [ "$(date +%s)" -lt "$deadline" ] || die "no Pages run for $merge_sha"
    sleep 15
  done
  gh run watch "$id" -R "$repo" --exit-status >/dev/null || die "Pages deploy run $id failed"
  deadline=$(($(date +%s) + 900))
  until [ "$(curl -fsS "$live/version.json?sync=$(date +%s)" | python3 -c 'import json,sys; print(json.load(sys.stdin)["formal"])' 2>/dev/null)" = "$target" ]; do
    [ "$(date +%s)" -lt "$deadline" ] || die "live version.json does not show $target after 15 minutes"
    sleep 20
  done
  echo "live: $live/version.json shows formal $target"
}

land_and_clean() {
  current=land
  land
  current=cleanup
  git -C "$here" worktree remove "$wt"
  git -C "$here" branch -D "$branch"
  git -C "$here" push -q origin --delete "$branch" 2>/dev/null || true
  echo "sync-formal: done; worktree removed"
}

# --- resolve the commit and the worktree ---
mkdir -p "$cache/runs"
[ -d "$formal/.git" ] || git clone -q https://github.com/itpplasma/stafford38-formal.git "$formal"
git -C "$formal" fetch -q origin
target=$(git -C "$formal" rev-parse --verify "$target^{commit}") || die "unknown formal commit $target"
git -C "$formal" merge-base --is-ancestor "$target" origin/main || die "$target is not on formal main"
lane=sync-${target:0:7}-$(date +%Y%m%d)
branch=$lane
wt=$wt_root/stafford38-supplementary/$lane
run=$cache/runs/$lane
receipt=verification/formal-${target:0:7}-$(date +%Y%m%d)
mkdir -p "$run"
export SYNC_FORMAL=$formal SYNC_RUN=$run
git -C "$here" fetch -q origin
prepared=false
if [ -d "$wt" ]; then
  [ "$(git -C "$wt" rev-parse --abbrev-ref HEAD)" = "$branch" ] || die "$wt exists on another branch"
  if [ -n "$(git -C "$wt" log --oneline origin/main..HEAD)" ]; then
    # A finished earlier run: only landing remains.
    (final_checks) >/dev/null 2>&1 ||
      die "$wt has sync commits but is incomplete; remove it (git worktree remove --force $wt; git branch -D $branch) and rerun"
    prepared=true
  fi
  echo "reusing worktree $wt"
else
  git -C "$here" worktree add -q -b "$branch" "$wt" origin/main
fi
base=$(git -C "$wt" merge-base HEAD origin/main)
old=$(git -C "$wt" show "$base:manifest.json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["sources"]["formal"]["commit"])')
[ "$old" = "$(git -C "$wt" show "$base:paper-lean-map.json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["sources"]["formal"]["commit"])')" ] ||
  die "manifest.json and paper-lean-map.json pin different formal commits"
[ "$old" != "$target" ] || die "the supplementary is already pinned to formal $target"
echo "formal $old -> $target; worktree $wt; logs $run"
if $prepared; then
  $push || { echo "sync-formal: $wt is already prepared; rerun with --push to land it"; exit 0; }
  land_and_clean
  exit 0
fi

# --- build and check the map ---
: >"$run/timings.txt"
step formal-old-pin dump_cached "$old" "$run/map-old.json"
step formal-checkout checkout_formal "$target"
step formal-build build_formal
step map-dump dump_map "$run/map-new.json"
mkdir -p "$cache/dumps" && cp "$run/map-new.json" "$cache/dumps/$target-$(tools_key).json"
current=map-check
if ! python3 "$here/check-map.py" compare --map "$wt/paper-lean-map.json" "$run/map-old.json" "$run/map-new.json" "${reviewed[@]}" >"$run/map-check.log" 2>&1; then
  cat "$run/map-check.log" >&2
  die "add or correct the cards in $wt/paper-lean-map.json (or pass --reviewed NAME after checking a changed statement), then rerun $0 $target"
fi
cat "$run/map-check.log"
step formal-verify verify_formal

# --- helper checkouts (cached) ---
step generator setup_generator
step global-build setup_global
step paper-build setup_paper

# --- repin and regenerate ---
mkdir -p "$wt/$receipt"
step repin repin
cp "$run/formal-verify.receipt" "$wt/$receipt/formal-verify.log"
scrub <"$run/map-check.log" >"$wt/$receipt/map-check.log"
cp "$wt/$(dirname "$(json "$wt/manifest.json" checks.receipt)")/migration.json" "$wt/$receipt/migration.json"
write_receipt_readme
step readme update_readme
step regenerate regenerate
step commit-repin commit_paths "Pin formal ${target:0:7} and regenerate the reader

Repin the Lean sources to $target, regenerate source pages, Lean
references, both proof graphs and the reader, and record the verifier
and map-check receipts."

# --- browser check and verification record ---
gen=$(cat "$run/generator.path")
rm -rf "$run/reader-check"
step browser-check env NODE_PATH="$gen/node_modules" timeout 1800 node "$wt/scripts/check-reader-cdp.mjs" "$wt" "$run/reader-check" "$wt/$receipt/migration.json"
step record record
step commit-record commit_paths "Record reader, browser and PDF verification for formal ${target:0:7}"
step final-checks final_checks

total=$(($(date +%s) - started))
echo "--- timings"; cat "$run/timings.txt"; echo "total ${total}s"
echo "sync-formal: $wt is ready on branch $branch ($(git -C "$wt" rev-parse --short HEAD))"
if $push; then
  land_and_clean
else
  echo "Not pushed; rerun with --push to land it."
fi
