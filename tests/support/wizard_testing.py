# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Helpers the tests of the song wizard share: the set, its data and its song as the wizard's choices make them."""

from llamatron.model.file import version

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
