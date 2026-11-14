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
"""Helpers that tests share for turning song data or a set file into finished clips.

Most tests describe one song the way files did before sets existed, with its tracks and scenes
beside the patterns it plays, because that reads best. as_setlist lays that out as a set of one
song, so that the same data builds a Setlist, a Song or a Document.
"""

import os

from llamatron.composition.defaults import FIRST_NUMBER
from llamatron.composition.file_format import Section
from llamatron.composition.setlist import Setlist, as_setlist_data
from llamatron.composition.setlist_writer import dump_setlist
from llamatron.playback.song_renderer import SongRenderer
from llamatron.strings.names import MSG_DEFAULT_SONG_NAME, MSG_NEW_PATTERN_NAME, MSG_NEW_TRACK_NAME
from llamatron.support.memory import Memory
from llamatron.tui.document import Document

# Every document a test makes checks what it remembers: an answer kept after what it came from changed fails the test (support/memory.py).
Memory.check_every_answer()

# The sets in examples/ that are meant to sound good rather than to teach one feature: every other set there is a demo.
PIECES = ('mainstreet_hoedown.yml', 'minimal_techno.yml')
SET_ENDING = '.yml'


def as_setlist(data):
    """Return data as a set's: one song's data becomes a set holding it as the untitled song, and a set's stays as it is."""
    if not isinstance(data, dict) or Section.SONGS in data:
        return data
    return as_setlist_data(data=data, song_name=MSG_DEFAULT_SONG_NAME)


def setlist_from_data(data):
    """Return the Setlist that a set's or one song's data describes, checked the way a file is."""
    return Setlist.from_data(data=as_setlist(data))


def song_from_data(data):
    """Return the one Song that a song's data describes, or the first song of a set's data, which an empty file gets as untitled."""
    setlist = setlist_from_data(data)
    if not setlist.get_song_names():
        setlist.add_new_song(MSG_DEFAULT_SONG_NAME)
    return setlist.get_song(setlist.first_song_name())


def song_from_file(path):
    """Return the first song of a set file."""
    setlist = Setlist.read_file(path)
    return setlist.get_song(setlist.first_song_name())


def dump_song_data(data):
    """Return one song's data written out as a set file's text, the way the tracker saves."""
    return dump_setlist(as_setlist(data))


def render_data(data):
    """Return the ClipGrid of finished clips that a song's data renders into."""
    return SongRenderer(song_from_data(data)).render()


def render_song(song, *, seed=None):
    """Return the ClipGrid of finished clips that a Song renders into, with a seed in place of the song's if one is given."""
    return SongRenderer(song, seed=seed).render()


def render_file(path):
    """Return the ClipGrid of finished clips that a set file's first song renders into."""
    return SongRenderer(song_from_file(path)).render()


def estimate_data(data):
    """Return how long each scene of a song's data lasts, as SongRenderer.estimate() gives it."""
    return SongRenderer(song_from_data(data)).estimate()


def is_demo(path):
    """Return whether a path names one of the demos in examples/: any set there that isn't one of the pieces."""
    name = os.path.basename(path)
    return name.endswith(SET_ENDING) and name not in PIECES


# The scene the starter clip is in, in a new set.
STARTER_SCENE = 0


def bare_document():
    """Return a new Document with the starter pattern and the clip that plays it removed, for a test that builds a song from nothing."""
    document = Document()
    document.delete_clip_slot(index=STARTER_SCENE, track=MSG_NEW_TRACK_NAME.format(number=FIRST_NUMBER))
    document.delete_named(section=Section.PATTERNS, name=MSG_NEW_PATTERN_NAME.format(number=FIRST_NUMBER))
    return document
