# The version and the build date and time are raised once a push, where the program's Rust changed since the last one.
.venv/bin/python internal_tools/bump_version.py --before-push
if ! git diff --quiet -- src/tracker/src/version.rs; then
    git add src/tracker/src/version.rs
    git commit -q -m 'The version is raised for the push.'
fi
echo 'before the push: running every check'
PATH="$HOME/.cargo/bin:$PATH"
cargo test --manifest-path src/Cargo.toml --workspace --release --quiet
for step in load layout migrate save edits pattern_edits render timeline player midi live import screens; do
    .venv/bin/python internal_tools/compare_llamatron.py "$step" > /dev/null || { echo "before the push: the $step comparison failed"; exit 1; }
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

# With --branch NAME, the history as it is here is checked and pushed to that branch of GitHub's alone, by force, as a
# backup or for work in progress, leaving GitHub's main, the version and the website as they are.
if [ "${1:-}" = "--branch" ]; then
    target="${2:?--branch needs the name of the branch to push to}"
    if [ "$target" = "main" ] || [ "$target" = "gh-pages" ]; then
        echo "not pushed: --branch is for a branch other than main and gh-pages" >&2
        exit 1
    fi
    PATH="$HOME/.cargo/bin:$PATH"
    cargo test --manifest-path src/Cargo.toml --workspace --quiet
    for step in load layout migrate save edits pattern_edits render timeline player midi live import screens; do
        .venv/bin/python internal_tools/compare_llamatron.py "$step" > /dev/null || { echo "before the push: the $step comparison failed"; exit 1; }
    done
    git push --force origin "HEAD:refs/heads/$target"
    exit 0
fi

branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$branch" != "main" ]; then
    echo "not pushed: this is the branch $branch, and only main is pushed and published" >&2
    exit 1
fi
# The version and the build date and time are raised once a push, where the program's Rust changed since the last one.
.venv/bin/python internal_tools/bump_version.py --before-push
if ! git diff --quiet -- src/tracker/src/version.rs; then
    git add src/tracker/src/version.rs
    git commit -q -m 'The version is raised for the push.'
fi
echo 'before the push: running every check'
PATH="$HOME/.cargo/bin:$PATH"
cargo test --manifest-path src/Cargo.toml --workspace --release --quiet
for step in load layout migrate save edits pattern_edits render timeline player midi live import screens; do
    .venv/bin/python internal_tools/compare_llamatron.py "$step" > /dev/null || { echo "before the push: the $step comparison failed"; exit 1; }
done
internal_tools/rebuild_docs.sh
git push origin main
internal_tools/publish_docs.sh
