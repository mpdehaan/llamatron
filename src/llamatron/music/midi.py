# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Facts about MIDI that the whole program shares: its ranges, and how notes are counted."""

MIN_MIDI_NUMBER = 0
MAX_MIDI_NUMBER = 127
MIN_VELOCITY = 1
MAX_VELOCITY = 127
MIN_CC_NUMBER = 0
MAX_CC_NUMBER = 127
MIN_CC_VALUE = 0
MAX_CC_VALUE = 127
# Channels as people and devices number them; the byte sent is one less.
MIN_CHANNEL = 1
MAX_CHANNEL = 16
HALF_STEPS_PER_OCTAVE = 12
