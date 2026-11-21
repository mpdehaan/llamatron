# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Helpers that tests share for turning song data or a set file into finished clips.

Most tests describe one song the way files did before sets existed, with its tracks and scenes
beside the patterns it plays, because that reads best. as_setlist lays that out as a set of one
song, so that the same data builds a Setlist, a Song or a Document.
"""

import os

from llamatron.caching.memory import Memory
from llamatron.engine.realizer.song_realizer import SongRealizer
from llamatron.interface.tracker.document import Document
from llamatron.model.file.setlist_writer import dump_setlist
from llamatron.model.objects.setlist import Setlist
from llamatron.model.schema import defaults
from llamatron.model.schema.file_format import Section, SongSetting
from llamatron.user_strings import names

# Every document a test makes checks what it remembers: an answer kept after what it came from changed fails the test (caching/memory.py).
Memory.check_every_answer()

# The sets in examples/ that are meant to sound good rather than to teach one feature: every other set there is a demo.
PIECES = ('mainstreet_hoedown.yml', 'minimal_techno.yml')
SET_ENDING = '.yml'
# What a test's song data may hold for the seed its render draws from: the tests' own way of repeating a take, which no file
# holds and nothing but these helpers reads, since every play and export of a song draws its random parts afresh.
TEST_SEED = 'seed'
# The keys of one song's data that belong to the song when it is wrapped as a set, the rest being the set's.
SONG_KEYS = (SongSetting.TEMPO, SongSetting.TIME_SIGNATURE, SongSetting.ENTRY_SIZE, SongSetting.SCALE, SongSetting.GROOVE, Section.REGISTERS, Section.DRAWS, Section.TRACKS, Section.SCENES)


def as_setlist(data, *, song_name=names.MSG_DEFAULT_SONG_NAME):
    """Return data as a set's, as the objects write it: one song's data, its settings, tracks and scenes at the top, becomes a set
    holding that song, the untitled song unless named, and a set's stays as it is."""
    if not isinstance(data, dict) or Section.SONGS in data:
        return data
    held = {key: value for key, value in data.items() if key not in SONG_KEYS}
    held[Section.SONGS] = {song_name: {key: data[key] for key in SONG_KEYS if key in data}}
    return held


def setlist_from_data(data):
    """Return the Setlist that a set's or one song's data describes, checked the way a file is."""
    return Setlist.from_data(data=as_setlist(data))


def song_from_data(data):
    """Return the one Song that a song's data describes, or the first song of a set's data, which an empty file gets as untitled."""
    setlist = setlist_from_data(data)
    if not setlist.get_song_names():
        setlist.add_new_song(names.MSG_DEFAULT_SONG_NAME)
    return setlist.get_song(setlist.first_song_name())


def song_from_file(path):
    """Return the first song of a set file."""
    setlist = Setlist.read_file(path)
    return setlist.get_song(setlist.first_song_name())


def dump_song_data(data):
    """Return one song's data written out as a set file's text, the way the tracker saves."""
    return dump_setlist(as_setlist(data))


def seed_of(data):
    """Return the seed a test's song data gives its render, or None for a new take."""
    return data.get(TEST_SEED) if isinstance(data, dict) else None


def without_seed(data):
    """Return a test's song data without the seed it gives its render, which no file holds."""
    return {key: value for key, value in data.items() if key != TEST_SEED} if isinstance(data, dict) else data


def render_data(data):
    """Return the ClipGrid of finished clips that a song's data renders into, drawn from the seed the data gives, if any."""
    return SongRealizer(song_from_data(without_seed(data)), seed=seed_of(data)).render()


def render_song(song, *, seed=None):
    """Return the ClipGrid of finished clips that a Song renders into, its random parts drawn from a seed where one is given."""
    return SongRealizer(song, seed=seed).render()


def render_file(path):
    """Return the ClipGrid of finished clips that a set file's first song renders into."""
    return SongRealizer(song_from_file(path)).render()


def estimate_data(data):
    """Return how long each scene of a song's data lasts, as SongRealizer.estimate() gives it."""
    return SongRealizer(song_from_data(without_seed(data)), seed=seed_of(data)).estimate()


def is_demo(path):
    """Return whether a path names one of the demos in examples/: any set there that isn't one of the pieces."""
    name = os.path.basename(path)
    return name.endswith(SET_ENDING) and name not in PIECES


# The scene the starter clip is in, in a new set.
STARTER_SCENE = 0


def bare_document():
    """Return a new Document with the starter pattern and the clip that plays it removed, for a test that builds a song from nothing."""
    document = Document()
    document.change(document.song().get_scene(STARTER_SCENE).remove_clip_slot, names.MSG_NEW_TRACK_NAME.format(number=defaults.FIRST_NUMBER))
    document.delete_named(section=Section.PATTERNS, name=names.MSG_NEW_PATTERN_NAME.format(number=defaults.FIRST_NUMBER))
    return document
