# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Which part each track of a song plays, found from its notes alone (music_theory/analysis/roles.py), for the measures. A
track's name is never read, since nothing about the set is assumed."""

from llamatron.music_theory.analysis import roles


def roles_of(performance):
    """Return each sounding track's role, by the track, as the measures' Role names it."""
    return roles.roles_of(parts=performance.tracks, bars=performance.bars(), beats_per_bar=performance.beats_per_bar)


def tracks_in_role(*, roles, role):
    return [track for track, its_role in roles.items() if its_role == role]
