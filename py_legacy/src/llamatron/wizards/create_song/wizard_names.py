# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The song wizard's names and ranges that its pages read as well as its parts: the keys of a section's and a player's fields,
the ranges of the gauges, and the choices a field offers. A part of the wizard's front door, beside wizard_choices.py and
wizard_limits.py, it imports nothing of the wizard, so that every part of it can name these from here."""


# From hook_writing.py,
# The habits a style or a song says its hook and its chorus's body are written by.
HOOK_WRITING = 'hook_writing'
BODY_WRITING = 'body_writing'
# A hook's behaviors and gauges are music_theory/hooks/hook_bars.py's.

# From song_plan.py,
SONG_PLAN_ENERGY = 'energy'
# Whether a place of the form rises, where the song says so itself.
SONG_PLAN_RISES = 'rises'
SONG_PLAN_SETUP = 'setup'
NOT_AT_ALL = 'not at all'
# What a place of the form may say of its scene: a tempo, the tempo it reaches by its end, and the root and the type of a scale of its own.
TEMPO_OF_PLACE = 'tempo'
TEMPO_END_OF_PLACE = 'tempo_end'
ROOT_OF_PLACE = 'root'
TYPE_OF_PLACE = 'type'
# A section that fades: softer bar by bar to this share of what is written, from all of it where no plan says how loud the section is.
SONG_PLAN_FADES = 'fades'
# How soft a fade goes where the section says no level: to silence, a velocity and a share of what is written alike.
FADED = 0
UNFADED = 100
# A fade's own level, the percentage of each note's written velocity a fade in starts from and a fade out ends at, from silence to the notes as written; the bars a fade takes, the whole section where
# none is said; and whether the fade is a fade in, which a section that opens the song has, where any other fades out.
FADE_LEVEL = 'fade_level'
FADE_OVER = 'fade_over'
LOUDEST_FADE_LEVEL = UNFADED
# Energy: its limits, the kind's where a style says nothing, the middle that Contrast pulls about, and the usual Contrast and growth.
LOWEST_ENERGY = 1
HIGHEST_ENERGY = 10

# From interplay.py,
# How busy the fills, the answers and the riff are.
INTERPLAY_LEAST_BUSY = 0
INTERPLAY_MOST_BUSY = 20

# From breaks.py,
# How far a break is cut up, from as written to every slice but the first open to a swap.
LEAST_CUT = 1
MOST_CUT = 8

# A loudness level's names and the drums a bar may name are music_theory/composing/notation.py's.
# A player's dynamics, from every note alike to twice the style's distances.
LEAST_DYNAMICS = 0
MOST_DYNAMICS = 10

# From characters.py,
CHARACTERS_LOWEST = 0
CHARACTERS_HIGHEST = 20

# From joins.py,
# The fields of what a section leaves with.
JOINS_LEAVES = 'leaves'

# From arranger.py,
ARRANGER_CHORDS = 'chords'

# From melody.py,
MELODY_HEIGHT = 'height'

# From riffs.py,
# How a riff's notes are drawn, what lies between a heavy riff's accents, how many bars it has, what the riff does as the
# chords change, and what it does under the tune.
RIFF_NOTES = 'notes'
ACCENT_CHORDS = 'chords on the accents'
RIFF_BETWEEN = 'between'
RIFF_BAR_COUNT = 'bars'
RIFF_WITH_CHORDS = 'with chords'
MOVES_WHOLE = 'moves with each chord'
STAYS_HOME = 'stays on the home chord'
