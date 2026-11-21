# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Arpeggiator plugin's schema: the ranges its settings may hold, which its model checks and its editor offers."""

MAX_OFFSETS = 16
# How many octaves it can play a chord across, and how far one offset can move a note.
MIN_OCTAVE_RANGE = 1
MAX_OCTAVE_RANGE = 4
MAX_OFFSET = 24
