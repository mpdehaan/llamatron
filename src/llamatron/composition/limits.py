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

"""The ranges that values in a song file must fall in, shared by the objects that check and play them."""

# MIDI's own ranges, for velocities, CC numbers and CC values, are in llamatron.midi.

# A step's probability is a percentage.
MIN_PROBABILITY = 0
MAX_PROBABILITY = 100

# Counts that start at one.
MIN_STEPS = 1
MIN_DEGREE = 1
MIN_RATCHET = 1
MIN_REPEAT = 1

# The range of a register's settings, and of what a step can add to one.
MIN_REGISTER_VALUE = -127
MAX_REGISTER_VALUE = 127

# Octaves as Live numbers them, where MIDI note 60 is C3.
MIN_LIVE_OCTAVE = -2
MAX_LIVE_OCTAVE = 8
# Tempo, in quarter notes a minute. Live's own limit is 999.
MIN_TEMPO = 10
MAX_TEMPO = 999

# The longest a step or a gate can be, in whole notes: four bars of 4/4.
MAX_STEP_SIZE = 4
MAX_GATE = 4

# How far a track can move its notes, in scale notes, either way.
MAX_TRANSPOSE = 24
