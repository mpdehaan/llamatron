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

"""The ranges that values in a song file must fall in, shared by the objects that check and play them."""

# MIDI's own ranges, for velocities, CC numbers and CC values, are in llamatron.music.midi.

# A step's probability is a percentage.
MIN_PROBABILITY = 0
MAX_PROBABILITY = 100

# Counts that start at one.
MIN_STEPS = 1
MIN_DEGREE = 1
MIN_RATCHET = 1
MIN_REPEAT = 1

# The most times a scene plays, and the most times a clip plays its pattern, in a file and on the Scene and Clip pages alike.
MAX_SCENE_REPEAT = 999
MAX_CLIP_REPEAT = 9999

# The range of a register's settings, and of what a step can add to one.
MIN_REGISTER_VALUE = -127
MAX_REGISTER_VALUE = 127
# The least a register's allowed increment may be: a register no step may add to just has no adds.
MIN_ALLOWED_INC_MAX = 1
# How far a drift moves notes along the scale either way, a fixed amount or at random: an octave of a seven-note scale.
MAX_DRIFT_DEGREE = 7
# A progression holds from one to this many chords, each a degree of the scale from 1 to MAX_PROGRESSION_DEGREE, inverted at most MAX_PROGRESSION_INVERSION times.
MIN_PROGRESSION_CHORDS = 1
MAX_PROGRESSION_CHORDS = 16
MIN_PROGRESSION_DEGREE = 1
MAX_PROGRESSION_DEGREE = 7
MAX_PROGRESSION_INVERSION = 2
# A pattern's Inversion row goes to the third inversion, which only a chord of four notes or more has; a triad plays a third as its second.
INVERSIONS = [1, 2, 3]
# A strum's fade, how much quieter its last string is than its first, and its loose timing, how much each string's spacing varies, as percentages.
MAX_STRUM_FADE = 50
MAX_LOOSE_TIMING = 50
MIN_STRUM_PERCENT = 0
# A Euclidean rhythm spreads from 1 to this many hits over as many steps or fewer, and a mask with hits but no steps set spreads them over a bar of sixteenths.
MIN_EUCLID = 1
MAX_EUCLID = 32
DEFAULT_EUCLID_STEPS = 16
NO_ROTATION = 0
# A Glide's, a Shorten's, a Rush's or a Drag's row holds from 1 to this many steps; a shortened note plays this share of itself at least and most, and a rush or a drag moves a note by up to half a step.
MAX_STEP_ROW = 16
MIN_STEP_ROW = 1
MIN_SHORTEN = 10
MAX_SHORTEN = 95
MAX_RUSH_OR_DRAG = 50
# General MIDI's sounds, numbered as people number them; a program change sends one less.
MIN_GM_SOUND = 1
MAX_GM_SOUND = 128
GM_FAMILY_SIZE = 8
# The percentages each shape runs between: the share of notes that play, how loud they play, and how long, as a share of what's written.
MIN_DENSITY = 0
MAX_DENSITY = 100
MIN_SWELL = 0
MAX_SWELL = 200
MIN_ARTICULATE = 10
MAX_ARTICULATE = 200
# How much louder a Swell generator makes the notes on strong beats, as a percentage.
MIN_ACCENT = 0
MAX_ACCENT = 50

# Octaves as song files number them, from C0, which is MIDI note 0, to the octave of G10, the top note.
MIN_OCTAVE = 0
MAX_OCTAVE = 10
# Tempo, in quarter notes a minute. Live's own limit is 999.
MIN_TEMPO = 10
MAX_TEMPO = 999

# The longest a step or a gate can be, in whole notes: four bars of 4/4.
MAX_STEP_SIZE = 4
MAX_GATE = 4

# How far a track can move its notes, in scale notes, either way.
MAX_TRANSPOSE = 24

# The editor's limits for a pattern's size, its ratchets and how far a ratchet slice can move, which
# the file doesn't check: a file can hold more, but the editor offers these.
MAX_STEPS = 4096
MAX_RATCHET = 16
MAX_RATCHET_OFFSET = 24

# A groove's amounts are percentages of a cell, kept small enough that notes can't change order.
MIN_GROOVE_AMOUNT = -50
MAX_GROOVE_AMOUNT = 50
MIN_GROOVE_CELLS = 1
MAX_GROOVE_CELLS = 32
MAX_GROOVE_CELL_LENGTH = 1
