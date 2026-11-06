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

"""What each setting is when a song file leaves it out.

Every setting has a default, so that a file written by an older version of llamatron still
loads, and an empty file is an empty song.
"""

DEFAULT_TEMPO = 120
DEFAULT_LENGTH = '1/16'
GRANULARITIES = ['1/16', '1/32', '1/64', '1/128', '1/256']
DEFAULT_GRANULARITY = GRANULARITIES[0]
DEFAULT_OCTAVE = 3
DEFAULT_DRUM_OCTAVE = 1
DEFAULT_SEED = 1
DEFAULT_VELOCITY = 127
DEFAULT_PROBABILITY = 100
DEFAULT_RATCHET = 1
DEFAULT_REPEAT = 1
DEFAULT_TRANSPOSE = 0
DEFAULT_ACCUMULATOR_LIMIT = 36
