#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: build the built-in synths' daemon, llamatron-synth, from native/synth/, offering to install Rust first

# Build the daemon that plays llamatron's built-in synths:
#
#     sh internal_tools/build_synth.sh
#
# It checks what building needs and offers to install what is missing, installing nothing unless you say yes: Rust,
# through rustup, the Rust project's installer, into your home folder; on a Mac, Apple's command line tools; on
# Linux it says which package holds the sound library headers, since installing those needs your system's package
# manager. Then it builds native/synth/ into native/synth/target/release/llamatron-synth, where llamatron finds it.
# Running it again rebuilds only what changed. docs/BUILDING_THE_SYNTH.md explains each step.

set -eu
cd "$(dirname "$0")/.."

RUSTUP_URL='https://sh.rustup.rs'
MANIFEST='native/synth/Cargo.toml'
BUILT='native/synth/target/release/llamatron-synth'

# Asks a yes or no question, and answers no when nobody is at the keyboard to say.
asked_yes() {
    answer=''
    if [ -t 0 ]; then
        printf '%s [y/N] ' "$1"
        read -r answer || answer=''
    fi
    [ "$answer" = 'y' ] || [ "$answer" = 'Y' ]
}

if [ -x "$HOME/.cargo/bin/cargo" ]; then
    PATH="$HOME/.cargo/bin:$PATH"
fi

if [ "$(uname -s)" = 'Darwin' ] && ! xcode-select -p >/dev/null 2>&1; then
    echo "Building needs Apple's command line tools (a compiler and linker), which aren't installed."
    if asked_yes "Install them now? A window from Apple asks you to confirm."; then
        xcode-select --install || true
        echo "When Apple's installer has finished, run this script again."
    else
        echo "Nothing was installed, and nothing was built."
    fi
    exit 1
fi

if [ "$(uname -s)" = 'Linux' ] && ! pkg-config --exists alsa 2>/dev/null; then
    echo "Building needs the ALSA sound library's headers and pkg-config, which weren't found."
    echo "Install them with your system's packages, such as: sudo apt install libasound2-dev pkg-config"
    echo "(on Fedora: sudo dnf install alsa-lib-devel pkgconf), then run this script again."
    exit 1
fi

if ! command -v cargo >/dev/null 2>&1; then
    echo "Building needs Rust, which isn't installed. rustup, the Rust project's installer, puts it in your home folder"
    echo "(~/.cargo and ~/.rustup), needs no password, and can remove it again with: rustup self uninstall"
    if asked_yes "Install Rust now, from $RUSTUP_URL?"; then
        curl --proto '=https' --tlsv1.2 -sSf "$RUSTUP_URL" | sh -s -- -y --profile minimal
        PATH="$HOME/.cargo/bin:$PATH"
    else
        echo "Nothing was installed, and nothing was built. The built-in synths play on llamatron's slower Python engine."
        exit 1
    fi
fi

# On an Apple Silicon Mac a Rust installed for Intel builds a program that runs slowly under Rosetta.
if [ "$(uname -s)" = 'Darwin' ] && [ "$(sysctl -n hw.optional.arm64 2>/dev/null || echo 0)" = '1' ]; then
    if rustc -vV | grep -q 'host: x86_64'; then
        echo "Rust here builds Intel programs, which would run under Rosetta. Switch it to Apple Silicon with:"
        echo "    rustup set default-host aarch64-apple-darwin && rustup toolchain install stable"
        exit 1
    fi
fi

cargo build --release --manifest-path "$MANIFEST"
echo "Built $BUILT. llamatron plays its built-in synths through it from now on."
