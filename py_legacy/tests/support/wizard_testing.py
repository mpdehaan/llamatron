# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Helpers the tests of the song wizard share: the set, its data and its song as the wizard's choices make them, and the style
templates, read once a process."""

import copy
import functools

from llamatron.model.file import version
from llamatron.wizards.create_song import arranger

# The name every song the tests have the wizard make goes by.
SONG_NAME = 'made'


def made_set(choices):
    """Return the set the wizard's choices make, its one song under SONG_NAME."""
    return choices.made_setlist(name=SONG_NAME, version=version.VERSION)


def made_data(choices):
    """Return the data of the set the wizard's choices make."""
    setlist = made_set(choices)
    return setlist.to_data()


def made_song(choices):
    """Return the song the wizard's choices make."""
    setlist = made_set(choices)
    return setlist.get_song(SONG_NAME)


@functools.cache
def _style_read(name):
    return arranger.style_named(name)


def style_template(name):
    """Return a style template as arranger.style_named reads it, read from its file once a process, since the largest takes a
    tenth of a second to read, and copied, so that a test that changes it changes no other test's."""
    return copy.deepcopy(_style_read(name))
