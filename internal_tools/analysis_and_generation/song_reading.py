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

"""Read the song a tool was pointed at: a MIDI file as it is, or a llamatron set's song rendered to its real notes, with its name
and where it came from, shared by the tools that describe a song."""

from llamatron.composition.setlist import Setlist
from llamatron.genres.hearing.midi_file import performance_of_midi
from llamatron.genres.hearing.performance import performance_of

MIDI_SUFFIXES = ('.mid', '.midi')
SONG_OF = '{path}, song {number} of {count}'
WHICH_SONG = 'the set has {count} songs; name one with --song: {songs}'
NO_SUCH_SONG = 'no song called ({name}) in the set; its songs: {songs}'
JOIN = ', '


def performance_and_name(*, path, song):
    """Return the performance to explain, its name and where it came from: a MIDI file read as it is, or a set's song rendered."""
    if path.suffix.lower() in MIDI_SUFFIXES:
        return performance_of_midi(path), path.stem, str(path)
    setlist = Setlist.read_file(str(path))
    names = setlist.get_song_names()
    if song is None and len(names) != 1:
        raise SystemExit(WHICH_SONG.format(count=len(names), songs=JOIN.join(names)))
    chosen = song if song is not None else names[0]
    if chosen not in names:
        raise SystemExit(NO_SUCH_SONG.format(name=chosen, songs=JOIN.join(names)))
    return performance_of(setlist.get_song(chosen)), chosen, SONG_OF.format(path=path, number=names.index(chosen) + 1, count=len(names))
