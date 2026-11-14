#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# What it does: build the documentation website from GUIDE.md and docs/ into web_docs/, with VitePress, installing what it needs

# The site is VitePress (https://vitepress.dev), which needs Node.js 18 or later. On a Mac it uses the
# Homebrew that matches the machine, /opt/homebrew on Apple Silicon and /usr/local on Intel, and when its
# Node.js is missing or too old it offers to install it with Homebrew, installing nothing without a yes.
# Then, in .docs_site/ (ignored by git, and outside internal_tools/ so that the tests' walks of its Python
# never reach node_modules), it installs VitePress and its plugins at the versions
# internal_tools/docs_site/package.json and package-lock.json pin, stages the pages
# (internal_tools/stage_docs_site.py), and builds the site into web_docs/, replacing what was there.
#
#     internal_tools/build_docs.sh
#     internal_tools/build_docs.sh preview     # build, then serve web_docs/ at http://localhost:4173/llamatron/

set -eu
cd "$(dirname "$0")/.."

SOURCES='internal_tools/docs_site'
SITE='.docs_site'
STAGING="$SITE/site"
OUT="$(pwd)/web_docs"
PYTHON='.venv/bin/python'
NEEDED_NODE=18

if [ "$(sysctl -n hw.optional.arm64 2>/dev/null || echo 0)" = '1' ]; then
    BREW_PREFIX='/opt/homebrew'
else
    BREW_PREFIX='/usr/local'
fi
PATH="$BREW_PREFIX/bin:$PATH"
export PATH

# Asks a yes or no question, and answers no when nobody is at the keyboard to say.
asked_yes() {
    answer=''
    if [ -t 0 ]; then
        printf '%s [y/N] ' "$1"
        read -r answer || answer=''
    fi
    [ "$answer" = 'y' ] || [ "$answer" = 'Y' ]
}

node_major() {
    "$BREW_PREFIX/bin/node" -v 2>/dev/null | sed 's/^v\([0-9]*\).*/\1/'
}

if [ ! -x "$BREW_PREFIX/bin/node" ] || [ "$(node_major)" -lt "$NEEDED_NODE" ]; then
    if [ ! -x "$BREW_PREFIX/bin/brew" ]; then
        echo "Node.js $NEEDED_NODE or later is needed, and Homebrew isn't in $BREW_PREFIX to install it: see https://brew.sh" >&2
        exit 1
    fi
    if asked_yes "Node.js $NEEDED_NODE or later is needed to build the site. Install it with Homebrew now?"; then
        "$BREW_PREFIX/bin/brew" install node
    else
        echo "Nothing was built. Install Node.js $NEEDED_NODE or later, then run this again." >&2
        exit 1
    fi
fi

mkdir -p "$SITE"
cp "$SOURCES/package.json" "$SITE/package.json"
if [ -f "$SOURCES/package-lock.json" ]; then
    cp "$SOURCES/package-lock.json" "$SITE/package-lock.json"
fi
echo "Installing VitePress into $SITE/node_modules"
(cd "$SITE" && npm install --no-audit --no-fund --no-update-notifier --loglevel=error)
cp "$SITE/package-lock.json" "$SOURCES/package-lock.json"

"$PYTHON" internal_tools/stage_docs_site.py --out "$STAGING"
mkdir -p "$STAGING/.vitepress"
cp "$SOURCES/vitepress_config/config.mts" "$STAGING/.vitepress/config.mts"

echo "Building the site into web_docs/"
(cd "$SITE" && LLAMATRON_SITE_OUT="$OUT" npx vitepress build site)
# GitHub Pages runs a site through Jekyll unless it holds .nojekyll, and Jekyll leaves out files starting with an underscore.
touch "$OUT/.nojekyll"

if [ "${1:-}" = 'preview' ]; then
    (cd "$SITE" && LLAMATRON_SITE_OUT="$OUT" npx vitepress preview site)
fi
