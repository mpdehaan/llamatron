# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The ranges that values in a song file must fall in, shared by the objects that check and play them."""

# MIDI's own ranges, for velocities, CC numbers and CC values, are in llamatron.model.values.midi.

# A step's probability is a percentage.
MIN_PROBABILITY = 0
MAX_PROBABILITY = 100
# The longest name the tracker lets a person type for anything named, and the room a list keeps for a name; a
# longer name in an older file still loads, and is shown cut.
MAX_NAME_LENGTH = 30
# A clip's name may be longer, such as the import's S14:i'1,i'2,i'3,i'4,i'5, and is shown cut to MAX_NAME_LENGTH.
MAX_CLIP_NAME_LENGTH = 60

# Counts that start at one.
MIN_STEPS = 1
MIN_DEGREE = 1
MIN_RATCHET = 1
MIN_REPEAT = 1

# The most times a scene plays, and the most times a clip plays its pattern, in a file and on the Scene and Clip pages alike.
MAX_SCENE_REPEAT = 999
# The fewest and the most bars a scene's ramp takes.
MIN_RAMP_BARS = 1
MAX_RAMP_BARS = 9999
MAX_CLIP_REPEAT = 9999

# How far either way a drift's version moves a step's velocity.
MAX_DRIFT_VELOCITY = 127
# The range of a draw's values, and how many slots a draw may hold.
MIN_DRAW_VALUE = -99
MAX_DRAW_VALUE = 99
MIN_DRAW_SLOTS = 1
MAX_DRAW_SLOTS = 64
# How many statements about the registers one table holds, and the largest number a statement may be written with.
MAX_STATEMENTS = 4
MAX_STATEMENT_NUMBER = 9999
# The least a register's allowed increment may be: a register no step may add to just has no adds.
MIN_ALLOWED_INC_MAX = 1
# How far a drift moves notes along the scale either way, a fixed amount or at random: an octave of a seven-note scale.
MAX_DRIFT_DEGREE = 7
# A progression holds from one to this many chords, each a degree of the scale from 1 to MAX_PROGRESSION_DEGREE, inverted at most MAX_PROGRESSION_INVERSION times.
MIN_PROGRESSION_CHORDS = 1
MAX_PROGRESSION_CHORDS = 32
MIN_PROGRESSION_DEGREE = 1
MAX_PROGRESSION_DEGREE = 7
MAX_PROGRESSION_INVERSION = 2
# A pattern's Inversion row goes to the third inversion, which only a chord of four notes or more has; a triad plays a third as its second.
INVERSIONS = [1, 2, 3]
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
# How early a keyswitch may be sent before its note, in milliseconds.
# What an accented step adds to its velocity, on a track and on an instrument.
MIN_STEP_ACCENT = 0
MAX_STEP_ACCENT = 127
MIN_KEYSWITCH_LEAD = 0
MAX_KEYSWITCH_LEAD = 500
# The percentages each shape runs between: the share of notes that play, how loud they play, and how long, as a share of what's written.
MIN_DENSITY = 0
MAX_DENSITY = 100
# A velocity of an instrument, a track, a scene or a clip, and each end of a velocity ramp, a percentage of what it scales:
# 0 silences, 100 changes nothing, 200 doubles.
MIN_VELOCITY_PERCENT = 0
MAX_VELOCITY_PERCENT = 200
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
# Tempo, in quarter notes a minute, within Live's own limits, 20 to 999: no song or scene plays slower or faster.
MIN_TEMPO = 20
MAX_TEMPO = 999
# A scene's tempo and each end of a tempo ramp, a percentage of the tempo it scales, from a tenth, since a tempo times nothing
# means nothing, to four times; a tempo played is never below MIN_TEMPO nor above MAX_TEMPO either, so that a song at 200 can
# still fall to 20.
MIN_TEMPO_PERCENT = 10
MAX_TEMPO_PERCENT = 400

# The fewest and the most notes of the scale a pattern says it was written for: a pentatonic scale to the chromatic.
MIN_SCALE_LENGTH = 5
MAX_SCALE_LENGTH = 12
# What a new pattern is written for unless told otherwise: a scale of seven notes.
NEW_PATTERN_SCALE_LENGTH = 7

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

# A MIDI instrument's own delay, in milliseconds, its notes sent that much earlier.
MIN_INSTRUMENT_LATENCY = 0
MAX_INSTRUMENT_LATENCY = 500
# A built-in sound's ranges: up to three oscillators, each detuned up to a semitone in cents either way, its levels and the
# envelope's times in milliseconds, its volume up to half again as loud as full (the output guard keeps the mix from
# clipping), its voices, a drum's five knobs and its choke groups; a SID voice's pulse sweep in percent of width a second
# either way, its interval in semitones either way, up to eight steps of arpeggio and two seconds of glide; a Pocket voice's
# sixteen levels, its envelope and sweep paces in the chip's ticks, 0 holding still, and its sweep's step; the four effect
# blocks, the bitcrusher's bits and rate.
MAX_OSCILLATORS = 3
MAX_DETUNE_CENTS = 100
MAX_PERCENT = 100
MAX_VOLUME_PERCENT = 150
MAX_ENVELOPE_MS = 10000
MAX_VOICES = 8
KNOB_COUNT = 5
MAX_KNOB = 127
MAX_CHOKE = 16
MAX_PULSE_SWEEP = 100
MAX_INTERVAL = 24
MAX_ARPEGGIO_STEPS = 8
MAX_GLIDE_MS = 2000
MAX_CHIP_LEVEL = 15
MAX_CHIP_PACE = 7
MIN_SWEEP_STEP = 1
MAX_SWEEP_STEP = 7
EFFECT_BLOCKS = 4
MIN_BITS = 1
MAX_BITS = 16
MAX_HOLD_RATE = 48000
