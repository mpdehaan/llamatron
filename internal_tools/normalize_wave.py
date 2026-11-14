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

"""Raise or lower a WAV file so that its loudest moment is 1 dB below the most a WAV can hold.

    .venv/bin/python internal_tools/normalize_wave.py previews/classic_strum.wav ...

user_scripts/demos_to_wavs.sh runs it on every WAV file it writes, since FluidSynth's files
come out quiet. It is peak normalization, the usual best practice when music is prepared for
streaming or for Apple Music: the whole file moves by one amount, so its quiet and loud parts keep
their difference, and a peak 1 dB below full scale (-1 dBFS, about 89%) leaves the headroom a
conversion to AAC or MP3 needs to keep from distorting. Nothing is compressed or limited.

The work is exporters/wave_level.py's, which the tracker's WAV export shares. It reads and writes
16-bit PCM WAV, which FluidSynth writes, and refuses anything else. A file is written to a new file
beside it and then put in its place, so a file is never left half written. A silent file is left as
it is.
"""

import argparse
import sys
import wave

from llamatron.exporters.wave_level import PEAK_DECIBELS, normalize_wave
from llamatron.strings.errors import ERR_NOT_16_BIT_WAVE

# What it says of each file: the program's own refusal of a file that isn't 16-bit, and what it did.
NOT_16_BIT = ERR_NOT_16_BIT_WAVE
SILENT = '{path}: silent, left as it is'
NORMALIZED = '{path}: peak moved by {change:+.1f} dB to {target:.1f} dB'


def normalize(path, *, peak_decibels=PEAK_DECIBELS):
    """Normalize the WAV file in place, through exporters/wave_level.py, which the WAV export uses too, and return what was done, in words."""
    change = normalize_wave(path, peak_decibels=peak_decibels)
    if change is None:
        return SILENT.format(path=path)
    return NORMALIZED.format(path=path, change=change, target=peak_decibels)


def main(*, argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('paths', nargs='+', help='the WAV files to normalize, each in place')
    arguments = parser.parse_args(argv)
    for path in arguments.paths:
        try:
            print(normalize(path))
        except (ValueError, wave.Error, EOFError) as problem:
            print(problem, file=sys.stderr)
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
