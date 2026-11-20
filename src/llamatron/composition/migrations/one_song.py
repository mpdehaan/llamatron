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
