# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Files saved before 1.0.39 held one song, its settings at the top and no list of songs; the song takes the file's name."""

SINCE = '1.0.39'
SONGS = 'songs'
# The keys such a file held at the top, which belong to its one song.
ONE_SONG_KEYS = ('tempo', 'time_signature', 'entry_size', 'scale', 'seed', 'groove', 'registers', 'tracks', 'scenes')
# The song's name where the file's name is not known.
UNNAMED_SONG = 'song'


def is_before(data):
    return SONGS not in data and any(key in data for key in ONE_SONG_KEYS)


def moved(*, data, conversion):
    if SONGS in data:
        return data
    name = conversion.get_one_song_name() or UNNAMED_SONG
    moved_data = {key: value for key, value in data.items() if key not in ONE_SONG_KEYS}
    moved_data[SONGS] = {name: {key: data[key] for key in ONE_SONG_KEYS if key in data}}
    return moved_data
