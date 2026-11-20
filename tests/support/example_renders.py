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


def first_song_grid(path):
    """Return the grid of a set file's first song, rendered with its own seed, as render_file gives it."""
    return rendered_example(path=path)[0][1]
