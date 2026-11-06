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

"""Facts about MIDI that the whole program shares: its ranges, and how notes are counted."""

MIN_MIDI_NUMBER, MAX_MIDI_NUMBER = 0, 127
MIN_VELOCITY, MAX_VELOCITY = 1, 127
MIN_CC_NUMBER, MAX_CC_NUMBER = 0, 127
MIN_CC_VALUE, MAX_CC_VALUE = 0, 127
HALF_STEPS_PER_OCTAVE = 12
