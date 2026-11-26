# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The song wizard: a set made from structured data that says what to play. composer.py turns a
song's input, its parts, bands and form, into a set's data, deciding nothing; decomposer.py writes an existing set as an
input; arranger.py makes an input from a song's picks and a style template of style_templates/, a style's traits with how
common each value is; melody.py sketches a tune by rule where a song gives none; players.py names the imaginary players a
song's complexities stand for; notation.py and shaping.py write parts as a pattern's rows and shape their velocity. It
fetches nothing and looks nothing up. internal_tools/song_wizard_compose.sh runs it, and a wizard in the tracker is to use it."""
