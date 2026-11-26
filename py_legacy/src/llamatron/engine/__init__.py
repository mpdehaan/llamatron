# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Engine: what makes a song into music. clips/ holds the finished clips a song is realized into and the grid that maps
them to tracks and scenes, and timing/ turns finished clips into timed notes in ticks, with the groove, the strum, rushes and
drags and keyswitches applied, for the exporters and for real-time playback alike. The realizer and the generators join it."""
