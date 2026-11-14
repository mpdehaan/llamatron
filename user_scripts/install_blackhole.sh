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

# What it does: install BlackHole 2ch, the loopback audio device the demo recorder records the sound from, on a Mac, offering Homebrew first

# Install BlackHole 2ch, a free loopback audio device, so that the demo recorder can record a take's
# sound along with its picture (docs/RECORDING.md):
#
#     sh user_scripts/install_blackhole.sh
#
# It needs Homebrew, the Mac's package manager. When Homebrew isn't there it offers to install it,
# and it asks again before installing BlackHole, which is an audio driver: macOS asks for your
# password, and the Mac's audio restarts. It installs nothing unless you say yes, and does nothing
# when BlackHole is installed already. It never deletes anything. Afterwards it says how to make the
# Multi-Output Device that lets you hear a take while it records.
#
# On an Apple Silicon Mac it uses only the Apple Silicon Homebrew in /opt/homebrew, run as arm64,
# never an Intel Homebrew in /usr/local. It is plain sh, so it needs nothing installed first.

set -eu

HOMEBREW_INSTALLER='https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh'
BLACKHOLE_DRIVER='/Library/Audio/Plug-Ins/HAL/BlackHole2ch.driver'

if [ "$(uname -s)" != 'Darwin' ]; then
    echo "This script is for macOS, where the demo recorder runs."
    exit 1
fi

# Which Homebrew to use, by the Mac's hardware rather than by how this shell runs, since a shell
# under Rosetta reports an Intel machine.
if [ "$(sysctl -n hw.optional.arm64 2>/dev/null || echo 0)" = '1' ]; then
    BREW_PREFIX='/opt/homebrew'
    APPLE_SILICON='yes'
else
    BREW_PREFIX='/usr/local'
    APPLE_SILICON=''
fi
BREW="$BREW_PREFIX/bin/brew"

# Runs a command as the Mac's own architecture: arm64 on Apple Silicon, even from a shell under Rosetta.
native() {
    if [ -n "$APPLE_SILICON" ]; then
        arch -arm64 "$@"
    else
        "$@"
    fi
}

# Asks a yes or no question, and answers no when nobody is at the keyboard to say.
asked_yes() {
    answer=''
    if [ -t 0 ]; then
        printf '%s [y/N] ' "$1"
        read -r answer || answer=''
    fi
    [ "$answer" = 'y' ] || [ "$answer" = 'Y' ]
}

if [ -d "$BLACKHOLE_DRIVER" ]; then
    echo "BlackHole 2ch is installed: $BLACKHOLE_DRIVER"
else
    if [ ! -x "$BREW" ]; then
        echo "Homebrew, the Mac's package manager, is needed to install BlackHole, and it isn't in $BREW_PREFIX."
        if [ -n "$APPLE_SILICON" ] && [ -x /usr/local/bin/brew ]; then
            echo "There is an Intel Homebrew in /usr/local, which isn't used."
        fi
        if asked_yes "Install Homebrew now, from https://brew.sh? It asks for your password."; then
            native /bin/bash -c "$(curl -fsSL "$HOMEBREW_INSTALLER")"
        else
            echo "Nothing was installed. Install Homebrew from https://brew.sh, or BlackHole from https://existential.audio/blackhole/, then run this again."
            exit 1
        fi
        if [ ! -x "$BREW" ]; then
            echo "Homebrew still isn't in $BREW_PREFIX, so nothing more was installed." >&2
            exit 1
        fi
    fi
    if asked_yes "Install BlackHole 2ch, an audio driver, with Homebrew? macOS asks for your password and the audio restarts."; then
        native "$BREW" install --cask blackhole-2ch
    else
        echo "BlackHole was not installed."
        exit 1
    fi
    if [ ! -d "$BLACKHOLE_DRIVER" ]; then
        echo "BlackHole still isn't at $BLACKHOLE_DRIVER after installing; restarting the Mac may finish it." >&2
        exit 1
    fi
fi

if ! command -v swift >/dev/null 2>&1; then
    echo
    echo "The recorder also needs the swift command, from Xcode's command line tools, to find BlackHole: run"
    echo "    xcode-select --install"
fi

echo
echo "BlackHole is ready. To hear a take while it records, make a Multi-Output Device of your speakers and BlackHole:"
echo "open Audio MIDI Setup (open -a 'Audio MIDI Setup'), press + at the bottom left, choose Create Multi-Output Device,"
echo "tick your speakers or headphones and BlackHole 2ch, and tick Drift Correction on BlackHole. Then record a take:"
echo "    sh user_scripts/record.sh --sound fluidsynth examples/learning/01_hello_world.yml"
