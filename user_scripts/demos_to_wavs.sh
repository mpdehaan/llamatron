#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: turn every demo into a WAV file in output/previews/ in one go, making the General MIDI previews first and playing them through FluidSynth, which it installs the first time

# Turn llamatron's General MIDI previews into WAV audio files with FluidSynth, to listen to anywhere
# or share, with no MIDI player needed. It sets up everything it needs the first time:
#
#     sh user_scripts/demos_to_wavs.sh                        # every demo, its preview made first
#     sh user_scripts/demos_to_wavs.sh output/previews/classic_strum.mid   # only the files named
#
# Each time, it runs user_scripts/install_fluidsynth.sh, which installs FluidSynth with Homebrew and downloads the free
# GeneralUser GS SoundFont the first time and does nothing after; makes every demo's General MIDI preview with
# user_scripts/demos_to_midi.sh where no files are named; and plays each preview through FluidSynth into a WAV file
# beside it.

set -eu

PREVIEWS='output/previews'
SOUNDFONT="$HOME/soundfonts/GeneralUser-GS.sf2"
SAMPLE_RATE='44100'

# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."


if [ "$(uname -s)" != 'Darwin' ]; then
    echo "This script is for macOS." >&2
    exit 1
fi

# FluidSynth and the SoundFont, installed by the same script people run (it does nothing that's already done), and
# FluidSynth found where it puts it: the Apple Silicon Homebrew's, which only an Apple Silicon Mac has, or an Intel Mac's.
sh user_scripts/install_fluidsynth.sh
if [ "$(sysctl -n hw.optional.arm64 2>/dev/null || echo 0)" = '1' ]; then
    FLUIDSYNTH='/opt/homebrew/bin/fluidsynth'
    APPLE_SILICON='yes'
else
    FLUIDSYNTH='/usr/local/bin/fluidsynth'
    APPLE_SILICON=''
fi

# Runs a command as the Mac's own architecture: arm64 on Apple Silicon, even from a shell under Rosetta.
native() {
    if [ -n "$APPLE_SILICON" ]; then
        arch -arm64 "$@"
    else
        "$@"
    fi
}

# With no files named, every demo is done from the start: the preview MIDI files are made afresh first, so that one command
# turns every demo into a WAV file.
if [ "$#" -eq 0 ]; then
    sh user_scripts/demos_to_midi.sh
fi

# The files named, or every preview: the positional parameters are the one list plain sh has.
if [ "$#" -eq 0 ]; then
    for midi in "$PREVIEWS"/*.mid; do
        [ -e "$midi" ] && set -- "$@" "$midi"
    done
fi
if [ "$#" -eq 0 ]; then
    echo "No MIDI files in $PREVIEWS/: sh user_scripts/demos_to_midi.sh made none" >&2
    exit 1
fi

written=0
for midi in "$@"; do
    case "$midi" in
        *.mid) ;;
        *) echo "Skipping $midi, which isn't a .mid file"; continue ;;
    esac
    if [ ! -f "$midi" ]; then
        echo "Skipping $midi, which doesn't exist"
        continue
    fi
    wave="${midi%.mid}.wav"
    echo "Writing $wave"
    native "$FLUIDSYNTH" -n -i -q -r "$SAMPLE_RATE" -F "$wave" "$SOUNDFONT" "$midi" >/dev/null
    written=$((written + 1))
done

echo "WAV files written: $written"
