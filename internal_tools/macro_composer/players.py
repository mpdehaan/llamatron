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

"""The imaginary players a song may be given: for each instrument, four of rising complexity.

A file says how a player plays as a complexity from 1 to 4 and never by a name; the names are for people, shown by the wizard
and written into a made song's notes. A player's name and instrument are the same in every style, and who the player is
underneath, what the player picks and how the player keeps time, is each style template's to say (the user's design). Every
player is imaginary. The family name says the complexity: a Llama is plain and dependable, an Alpaca tasteful and serving the
song, a Vicuna wilder and busier, a Guanaco the most advanced.
"""

PLAIN = 1
TASTEFUL = 2
WILD = 3
ADVANCED = 4
COMPLEXITIES = (PLAIN, TASTEFUL, WILD, ADVANCED)
FAMILIES = {PLAIN: 'Llama', TASTEFUL: 'Alpaca', WILD: 'Vicuna', ADVANCED: 'Guanaco'}
MSG_FAMILIES = {
    PLAIN: 'plain and dependable', TASTEFUL: 'tasteful, serves the song', WILD: 'wilder and busier', ADVANCED: 'the most advanced',
}
# The instruments that have players of their own; any other instrument is played by a Session player.
DRUMS = 'drums'
BASS = 'bass'
RHYTHM = 'rhythm'
LEAD = 'lead'
KEYS = 'keys'
SESSION = 'session'
FIRST_NAMES = {
    DRUMS: {PLAIN: 'Larry', TASTEFUL: 'Lucy', WILD: 'Thomas', ADVANCED: 'Sark'},
    BASS: {PLAIN: 'Michael', TASTEFUL: 'Sammy', WILD: 'Peter', ADVANCED: 'Chester'},
    RHYTHM: {PLAIN: 'Eric', TASTEFUL: 'Jane', WILD: 'Graham', ADVANCED: 'Grover'},
    LEAD: {PLAIN: 'George', TASTEFUL: 'Edmund', WILD: 'Dave', ADVANCED: 'Ed'},
    KEYS: {PLAIN: 'Susan', TASTEFUL: 'Sam', WILD: 'Ralph', ADVANCED: 'Eleanor'},
    SESSION: {PLAIN: 'Session', TASTEFUL: 'Session', WILD: 'Session', ADVANCED: 'Session'},
}
INSTRUMENTS = tuple(FIRST_NAMES)
MSG_PLAYER = '{} {}'


def player_name(*, instrument, complexity):
    """The name people see for the player of an instrument at a complexity."""
    return MSG_PLAYER.format(FIRST_NAMES[instrument][complexity], FAMILIES[complexity])
