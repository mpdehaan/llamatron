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

"""What each setting is when a set file leaves it out.

Every setting has a default, so that a file written by an older version of llamatron still
loads, and an empty file is an empty song.
"""

from llamatron.composition.file_format import AtLimit, FollowAction, OctaveLabels

DEFAULT_TEMPO = 120
FIRST_NUMBER = 1
# How long each step of a pattern is, unless the pattern sets its own.
DEFAULT_STEP_SIZE = '1/16'
# The song's time signature, which a pattern can set its own in place of. It only changes what's
# drawn: the beats in the pattern editor, and the bars a DAW draws.
DEFAULT_TIME_SIGNATURE = '4/4'
# Octaves count from C0, MIDI note 0, so a new note starts in the octave of middle C, MIDI 60, and a
# new drum hit two octaves lower, where MIDI 36 is the first pad of a Drum Rack in Live.
DEFAULT_OCTAVE = 5
DEFAULT_DRUM_OCTAVE = 3
# The tracker shows octaves with Live's labels, which number middle C's octave 3, unless the song says otherwise.
DEFAULT_OCTAVE_LABELS = OctaveLabels.LIVE
# What a clip does when its scene is done in real-time playback, unless the clip or the set says otherwise.
DEFAULT_FOLLOW_ACTION = FollowAction.WITH_SCENE
# Whether a start reaching any clip of a scene launches the whole scene in real-time playback.
DEFAULT_LAUNCH_TOGETHER = True
# An instrument's channel, as people number them.
DEFAULT_CHANNEL = 1
# Whether the set plays in real time, which the first instrument added turns on.
DEFAULT_REAL_TIME = False
# A set the user makes is theirs to save over; the sets shipped in examples/ turn this on.
DEFAULT_PROTECTED = False
# No seed means every render is a new take; a seed makes a song render the same every time.
DEFAULT_SEED = None
DEFAULT_VELOCITY = 127
DEFAULT_PROBABILITY = 100
DEFAULT_RATCHET = 1
DEFAULT_REPEAT = 1
DEFAULT_TRANSPOSE = 0
# A register runs from its minimum to its maximum, starts at its default, and stops at the ends
# unless it's set to wrap.
DEFAULT_REGISTER_MINIMUM = 0
DEFAULT_REGISTER_MAXIMUM = 10
DEFAULT_REGISTER_VALUE = 0
DEFAULT_AT_LIMIT = AtLimit.STOP
DEFAULT_RESET_EACH_SCENE = False
# The most a step may add to a register or take from it, unless the register says otherwise: enough for every example written before the limit came (the user's choice of 2026-11-11).
DEFAULT_ALLOWED_INC_MAX = 20
DEFAULT_GROOVE_CELL_LENGTH = '1/16'
# The factory groove that moves nothing, FactoryGroove.NONE, which groove.py checks matches.
DEFAULT_GROOVE = 'none'
# When an edit made while a song plays is heard, unless the song says: at the next bar, as a launch by hand waits for it.
DEFAULT_LIVE_RESPONSIVENESS = 'next_bar'
