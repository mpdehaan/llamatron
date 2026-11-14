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

# What it does: install FluidSynth and the GeneralUser GS SoundFont on a Mac, offering Homebrew first, so that every example plays with no synthesizer

# Install FluidSynth and a General MIDI SoundFont on a Mac, so that llamatron plays every example in
# real time, and makes the demos' WAV files, with no synthesizer and no DAW:
#
#     sh user_scripts/install_fluidsynth.sh
#
# It needs Homebrew, the Mac's package manager. When Homebrew isn't there it offers to install it,
# and installs nothing unless you say yes. Then it installs FluidSynth with Homebrew, if it isn't
# installed, and downloads the free GeneralUser GS SoundFont (by S. Christian Collins, about 32 MB)
# into ~/soundfonts, if it isn't there. Running it again does nothing that's already done, and it
# never deletes anything.
#
# On an Apple Silicon Mac it uses only the Apple Silicon Homebrew in /opt/homebrew, run as arm64,
# never an Intel Homebrew in /usr/local, which runs under Rosetta and would install Intel programs.
# SOUNDFONT_DIR puts the SoundFont elsewhere, though llamatron looks for it in ~/soundfonts.
# It is plain sh, so it needs nothing installed first, make included.

set -eu

SOUNDFONT_URL='https://github.com/mrbumpy409/GeneralUser-GS/raw/main/GeneralUser-GS.sf2'
SOUNDFONT_DIR="${SOUNDFONT_DIR:-$HOME/soundfonts}"
SOUNDFONT="$SOUNDFONT_DIR/GeneralUser-GS.sf2"
HOMEBREW_INSTALLER='https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh'

if [ "$(uname -s)" != 'Darwin' ]; then
    echo "This script is for macOS. Elsewhere, install FluidSynth with your system's packages and put a"
    echo "General MIDI SoundFont at $SOUNDFONT."
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
FLUIDSYNTH="$BREW_PREFIX/bin/fluidsynth"

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

if [ ! -x "$BREW" ]; then
    echo "Homebrew, the Mac's package manager, is needed to install FluidSynth, and it isn't in $BREW_PREFIX."
    if [ -n "$APPLE_SILICON" ] && [ -x /usr/local/bin/brew ]; then
        echo "There is an Intel Homebrew in /usr/local, which isn't used, since it would install Intel programs."
    fi
    if asked_yes "Install Homebrew now, from https://brew.sh? It asks for your password."; then
        native /bin/bash -c "$(curl -fsSL "$HOMEBREW_INSTALLER")"
    else
        echo "Nothing was installed. Install Homebrew from https://brew.sh, then run this script again."
        exit 1
    fi
    if [ ! -x "$BREW" ]; then
        echo "Homebrew still isn't in $BREW_PREFIX, so nothing more was installed." >&2
        exit 1
    fi
fi

if [ -x "$FLUIDSYNTH" ]; then
    echo "FluidSynth is installed: $FLUIDSYNTH"
else
    echo "Installing FluidSynth with $BREW"
    native "$BREW" install fluid-synth
fi
if [ ! -x "$FLUIDSYNTH" ]; then
    echo "FluidSynth still isn't at $FLUIDSYNTH after installing." >&2
    exit 1
fi

if [ -s "$SOUNDFONT" ]; then
    echo "The SoundFont is in place: $SOUNDFONT"
else
    echo "Downloading the GeneralUser GS SoundFont into $SOUNDFONT_DIR"
    mkdir -p "$SOUNDFONT_DIR"
    curl --fail --location --progress-bar --output "$SOUNDFONT.part" "$SOUNDFONT_URL"
    mv "$SOUNDFONT.part" "$SOUNDFONT"
fi

echo
echo "FluidSynth is ready. Open an example and play it in real time:"
echo "    .venv/bin/llamatron examples/learning/13_classic_strum.yml"
echo "then press A for Arrange, go to the top left corner with the arrows, and press Space."
