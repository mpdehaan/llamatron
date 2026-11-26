# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What each setting is when a set file leaves it out.

Every setting has a default, so that a file written by an older version of llamatron still
loads, and an empty file is an empty song.
"""

from llamatron.model.schema.file_format import FollowAction, OctaveLabels

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
# A keyswitch is sent at the same moment as its note, before it, unless the instrument says earlier, and always at one velocity.
DEFAULT_KEYSWITCH_LEAD = 0
KEYSWITCH_VELOCITY = 100
# Whether the set plays in real time, which the first instrument added turns on.
DEFAULT_REAL_TIME = False
# A set the user makes is theirs to save over; the sets shipped in examples/ turn this on.
DEFAULT_PROTECTED = False
DEFAULT_VELOCITY = 127
# What an accented step adds to its velocity: a track's own part, and its instrument's, which a track's is added to.
DEFAULT_TRACK_ACCENT = 15
DEFAULT_INSTRUMENT_ACCENT = 0
DEFAULT_PROBABILITY = 100
DEFAULT_RATCHET = 1
DEFAULT_REPEAT = 1
DEFAULT_TRANSPOSE = 0
# A new draw: eight blank slots moving forward, its values bounded by the widest range, its conditions only looking at it.
DEFAULT_DRAW_SLOT_COUNT = 8
DEFAULT_DRAW_CONDITIONS_REDRAW = False
# The most a step may add to a register or take from it, unless the register says otherwise: enough for every example written before the limit came.
DEFAULT_ALLOWED_INC_MAX = 20
DEFAULT_GROOVE_CELL_LENGTH = '1/16'
# The factory groove that moves nothing, FactoryGroove.NONE, which groove.py checks matches.
DEFAULT_GROOVE = 'none'
# When an edit made while a song plays is heard, unless the song says: at the next bar, as a launch by hand waits for it.
DEFAULT_LIVE_RESPONSIVENESS = 'next_bar'

# A new built-in instrument's sound: a Basic sound of one saw, a short pluck of an envelope, four voices, at 80 percent, its
# effect blocks empty; a drum's knobs all in the middle; a SID voice a half-width pulse with no sweep, ring, sync, arpeggio
# or glide; a Pocket voice a quarter-duty pulse starting at full level and holding it, with no sweep, its wave a triangle
# and its noise the long hiss. A bitcrusher chosen starts at 8 bits with no change of rate, drive at a third, warm.
DEFAULT_INSTRUMENT_LATENCY = 0
DEFAULT_ATTACK_MS = 5
DEFAULT_DECAY_MS = 300
DEFAULT_SUSTAIN_PERCENT = 60
DEFAULT_RELEASE_MS = 200
DEFAULT_VOICES = 4
DEFAULT_SOUND_VOLUME = 80
DEFAULT_KNOB = 64
DEFAULT_OSCILLATOR_LEVEL = 100
DEFAULT_PULSE_WIDTH = 50
DEFAULT_INTERVAL = 7
DEFAULT_START_LEVEL = 15
DEFAULT_SWEEP_STEP = 3
DEFAULT_CRUSH_BITS = 8
DEFAULT_CRUSH_RATE = 0
DEFAULT_DRIVE_AMOUNT = 33
# A filter chosen starts a ladder low-pass at 1200 Hz, a little resonance, its envelope opening it two octaves and falling over
# a quarter second, half key tracking, no drive; every effect starts fully mixed in.
DEFAULT_CUTOFF = 1200
DEFAULT_RESONANCE = 25
DEFAULT_ENVELOPE_AMOUNT = 50
DEFAULT_ENVELOPE_ATTACK = 2
DEFAULT_ENVELOPE_DECAY = 250
DEFAULT_KEY_TRACK = 50
DEFAULT_FILTER_DRIVE = 0
DEFAULT_MIX = 100
# An LFO chosen starts a gentle sine vibrato: five hertz, a twentieth of its range (about half a semitone of pitch), each note
# starting it again.
DEFAULT_LFO_RATE = 50
# Fishline starts as the classic squelch: its cutoff low, its resonance high, a strong envelope over 400 ms, notes accented
# at a velocity of 110 or more, a 60 ms slide and a little drive.
DEFAULT_ACID_CUTOFF = 400
DEFAULT_ACID_RESONANCE = 70
DEFAULT_ENV_MOD = 60
DEFAULT_FILTER_DECAY_MS = 400
DEFAULT_ACCENT = 60
DEFAULT_ACCENT_THRESHOLD = 110
DEFAULT_ACCENT_SWEEP = 50
DEFAULT_SLIDE_MS = 60
DEFAULT_ACID_DRIVE = 30
DEFAULT_AMP_DECAY_MS = 1500
DEFAULT_SOFT_ATTACK = 30
DEFAULT_ACCENT_DECAY_MS = 200
DEFAULT_LFO_DEPTH = 5
# A voice of parts: the snappy ADSR's attack curve, the RC timer's law; a vactrol's strike in tenths of a millisecond, its
# memory and stability (stable, as the user likes); a low-pass gate's open cutoff and ping in tenths of a millisecond.
DEFAULT_ATTACK_CURVE = 50
DEFAULT_STRIKE_WIDTH = 20
DEFAULT_MEMORY = 30
DEFAULT_STABILITY = 100
DEFAULT_GATE_OPEN = 7000
DEFAULT_PING_WIDTH = 10
DEFAULT_SID_ATTACK = 0
DEFAULT_SID_DECAY = 9
DEFAULT_SID_SUSTAIN = 10
DEFAULT_SID_RELEASE = 9
