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

# MIDI values, as notes and CC messages carry them.
MIN_VELOCITY, MAX_VELOCITY = 1, 127
MIN_CC_NUMBER, MAX_CC_NUMBER = 0, 127
MIN_CC_VALUE, MAX_CC_VALUE = 0, 127

# A step's probability is a percentage.
MIN_PROBABILITY, MAX_PROBABILITY = 0, 100

# Counts that start at one.
MIN_STEPS = 1
MIN_DEGREE = 1
MIN_RATCHET = 1
MIN_REPEAT = 1
MIN_ACCUMULATOR_LIMIT = 1

# Octaves as Live numbers them, where MIDI note 60 is C3.
MIN_LIVE_OCTAVE, MAX_LIVE_OCTAVE = -2, 8

# How far a track can move its notes, in scale notes, either way.
MAX_TRANSPOSE = 24
