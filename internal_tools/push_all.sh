# The version and the build date and time are raised once a push, where the program's Rust changed since the last one.
.venv/bin/python internal_tools/bump_version.py --before-push
if ! git diff --quiet -- native/tracker/src/version.rs; then
    git add native/tracker/src/version.rs
    git commit -q -m 'The version is raised for the push.'
fi
echo 'before the push: running every check'
PATH="$HOME/.cargo/bin:$PATH"
cargo test --manifest-path native/Cargo.toml --workspace --release --quiet
for step in load layout migrate save edits pattern_edits render timeline player midi live import screens; do
    .venv/bin/python internal_tools/compare_llamatron2.py "$step" > /dev/null || { echo "before the push: the $step comparison failed"; exit 1; }
done
#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: raise the version where the program's Rust changed since the last push, run every check, which must pass, then bring the documentation website up to date with internal_tools/rebuild_docs.sh,
# which commits what changed, push main to GitHub and then publish the website, in that order, so that the screenshots
# and the website are rebuilt only at a push and never describe code nobody can get. It stops if the push fails, never
# pushes with --force, and runs only on main. It is the one command that sends anything to GitHub: Claude runs it when
# asked to push.

set -eu
cd "$(dirname "$0")/.."

branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$branch" != "main" ]; then
    echo "not pushed: this is the branch $branch, and only main is pushed and published" >&2
    exit 1
fi
# The version and the build date and time are raised once a push, where the program's Python changed since the last one.
.venv/bin/python internal_tools/bump_version.py --before-push
if ! git diff --quiet -- src/llamatron/model/file/version.py; then
    git add src/llamatron/model/file/version.py
    git commit -q -m 'The version is raised for the push.'
fi
# The commit check rewrites only the files each commit changed, so once a push both fixers go over every file, and the push stops
# where they change one, since a change to one module can rarely leave another file breaking a rule.
before=$(git diff --stat)
internal_tools/constants_by_module.sh --write > /dev/null
internal_tools/sort_imports.sh --write > /dev/null
if [ "$(git diff --stat)" != "$before" ]; then
    echo 'before the push: the fixers changed files, which are to be looked at and committed first:'
    git diff --stat
    exit 1
fi
echo 'before the push: running every test'
internal_tools/test.sh
internal_tools/rebuild_docs.sh
git push origin main
internal_tools/publish_docs.sh
