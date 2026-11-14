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

# What it does: turn every demo into a WAV file in previews/ in one go, making the General MIDI previews first and playing them through FluidSynth, which it installs the first time

# Turn llamatron's General MIDI previews into WAV audio files with FluidSynth, to listen to anywhere
# or share, with no MIDI player needed. It sets up everything it needs the first time:
#
#     sh user_scripts/demos_to_wavs.sh                        # every demo, its preview made first
#     sh user_scripts/demos_to_wavs.sh previews/classic_strum.mid   # only the files named
#
# Each time, it:
#   1. runs user_scripts/install_fluidsynth.sh, which installs FluidSynth with Homebrew and downloads the free
#      GeneralUser GS SoundFont into ~/soundfonts, each only if it isn't there;
#   2. checks for the virtual environment that user_scripts/setup.sh makes;
#   3. with no files named, makes the preview MIDI files first, with user_scripts/demos_to_midi.sh;
#   4. writes a WAV file beside each preview, like previews/classic_strum.wav, writing over the ones
#      it made before, and normalizes each (internal_tools/normalize_wave.py): the whole file raised until its
#      loudest moment is 1 dB below the most a WAV holds, the usual headroom for streaming, so that
#      every demo is about as loud as the next and none distorts.
#
# sh user_scripts/play_demo.sh lists the WAV files and plays the one picked with afplay, macOS's own command line
# audio player, which plays it and exits without opening Music or adding the file to a library
# (Ctrl+C stops it); afplay previews/classic_strum.wav plays one directly.
#
# It is careful by design. It never deletes anything, and it writes only .wav files beside the .mid
# files it reads, besides what user_scripts/install_fluidsynth.sh installs. It changes no configuration file.
# On an Apple Silicon Mac it uses only the Apple Silicon Homebrew in /opt/homebrew, run as arm64,
# never an Intel Homebrew in /usr/local (user_scripts/install_fluidsynth.sh says more). It is plain sh, so that
# sh user_scripts/demos_to_wavs.sh works.

set -eu

PREVIEWS='previews'
SOUNDFONT="$HOME/soundfonts/GeneralUser-GS.sf2"
SAMPLE_RATE='44100'
PYTHON='.venv/bin/python'
NORMALIZE='internal_tools/normalize_wave.py'

# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

if [ ! -x "$PYTHON" ]; then
    echo "There's no $PYTHON: run sh user_scripts/setup.sh first." >&2
    exit 1
fi

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
    "$PYTHON" "$NORMALIZE" "$wave"
    written=$((written + 1))
done

echo "WAV files written: $written"
echo "Pick one to play with: sh user_scripts/play_demo.sh"
