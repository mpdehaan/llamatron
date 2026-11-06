# llamatron: a Python language and framework for producing MIDI clips.
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

"""Reads a song written in the YAML song format, and builds a ClipGrid from it.

A file has song settings, named scales, patterns, tracks, arps, auto_ratchets, chains and scenes. A
pattern holds one list per row, all as long as its step count, which mirrors the pattern editor:
degree, duration, accidental, octave, chord, velocity, probability, ratchet and glide. A step with
no degree is a rest, and a step with no duration uses the song's default, so every step takes time.
Octaves are absolute, and are numbered the way Live displays them. A drum pattern has note letters
instead of degrees.

A scene launches clips and has no length of its own. A clip plays its pattern repeat times and then
stays silent while the others finish, unless it has loop: true, which plays it until the longest
clip that doesn't loop has finished. At least one clip in a scene must not loop. A clip with a
repeat above 1 can morph into a second pattern across its repeats. Scales come from the scene, and
then the song. Probability is rolled here from the song's seed, so that a song always renders the
same. See the examples folder for complete songs, and raise SongFileError for anything wrong.

A clip can take its rhythm from another pattern with rhythm_from, and then its pattern gives the
notes. They match step by step, and the notes carry on across repeats and skip any rests, so lists
of different lengths drift apart. A clip's grab_track names another track in the same scene, like
the Cirklon's note grab: each of the pattern's grab steps plays the note that track most recently
started (the lowest, for a chord), after its chain, so a silent track gives the last note it
played. Clips that grab in a circle are refused. A pattern's direction sets the order its steps
play in, and a clip's direction overrides it. A step's ratchet_offset moves each ratchet slice further along the scale. A step's note_add and velocity_add
add to running totals that apply from that step on, across the clip's repeats, and clear at the
pattern's accumulator_limit.
"""

import yaml

# The file format's lists and defaults are imported from here by the rest of the program until
# song_file.py is gone, so they stay importable under these names.
from llamatron.composition.file_format import (  # noqa: F401
    ACCIDENTALS, CC_ROWS, CHORD_SYMBOLS, DEFAULT_ACCUMULATOR_LIMIT, DEFAULT_DRUM_OCTAVE, DEFAULT_LENGTH,
    DEFAULT_OCTAVE, DEFAULT_PROBABILITY, DEFAULT_RATCHET, DEFAULT_SEED, DEFAULT_TEMPO, DEFAULT_VELOCITY,
    DIRECTIONS, FIXED_CHORDS, FORWARD, GRANULARITIES, LIVE_OCTAVE_OFFSET, MAX_LIVE_OCTAVE, MAX_TRANSPOSE,
    MIN_LIVE_OCTAVE, NAMED_GENERATORS, NOTE_LETTERS, NOTE_ROWS, PATTERN_ROWS, SCALE_CHORDS, TOGGLE_ROWS,
)
from llamatron.composition.cell import MORPH_STYLES  # noqa: F401
from llamatron.composition.generator_settings import GENERATOR_SETTINGS
from llamatron.composition.song import Song
from llamatron.composition.song_file_error import SongFileError
from llamatron.playback.song_renderer import SongRenderer

# The generators a chain step can name.
GENERATORS = GENERATOR_SETTINGS


class SongBuilder:
    """Reads a song file's data into a Song and renders it, until callers use those directly."""

    def __init__(self, data):
        self.song = Song.from_data(data)
        self._renderer = SongRenderer(self.song)

    def build(self):
        """Return the song's finished clips as a ClipGrid."""
        return self._renderer.render()

    def estimate(self):
        """Return how long each written-out scene and its clips last, in seconds."""
        return self._renderer.estimate()


def load_song(path):
    """Return a Song from a song file, or raise SongFileError if something's wrong with it."""
    try:
        with open(path, encoding='utf-8') as file:
            data = yaml.safe_load(file)
    except OSError as error:
        raise SongFileError(f'can\'t read {path}: {error.strerror}') from error
    except yaml.YAMLError as error:
        raise SongFileError(f'{path} isn\'t valid YAML: {error}') from error
    return SongBuilder(data).build()
