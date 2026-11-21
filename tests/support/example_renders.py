# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Each example set read and rendered once a process, for the checks that every example runs in its own class
(tests/app/test_every_example.py): a class's checks share one reading and one render of its example instead of each making its own.

What these return is shared, so a check never changes it: a check that changes a set reads its own with Setlist.read_file.
"""

import functools

from llamatron.composition.setlist import Setlist
from llamatron.playback.song_renderer import SongRenderer


@functools.lru_cache(maxsize=None)
def example_setlist(path):
    """Return the set a file holds, read once, to be read and never changed."""
    return Setlist.read_file(path)


@functools.lru_cache(maxsize=None)
def rendered_example(*, path, seed=None):
    """Return each song of a set file with its grid, (name, grid) in the set's order, rendered once for a seed, or with each song's own."""
    setlist = example_setlist(path)
    return tuple((name, SongRenderer(setlist.get_song(name), seed=seed).render()) for name in setlist.get_song_names())


def first_song_grid(path, *, seed=None):
    """Return the grid of a set file's first song, the one a file opens on, rendered with its own seed or the one given."""
    first = example_setlist(path).first_song_name()
    return next(grid for name, grid in rendered_example(path=path, seed=seed) if name == first)
