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

from llamatron.strings.macro_composer import (MSG_BASS_PLAYERS, MSG_DRUMMERS, MSG_KEYS_PLAYERS, MSG_LEAD_PLAYERS, MSG_PLAYER, MSG_PLAYER_FAMILIES,
                                             MSG_RHYTHM_PLAYERS, MSG_SESSION_PLAYERS)

PLAIN = 1
TASTEFUL = 2
WILD = 3
ADVANCED = 4
COMPLEXITIES = (PLAIN, TASTEFUL, WILD, ADVANCED)
FAMILIES = dict(zip(COMPLEXITIES, MSG_PLAYER_FAMILIES))
# The instruments that have players of their own; any other instrument is played by a Session player.
DRUMS = 'drums'
BASS = 'bass'
RHYTHM = 'rhythm'
LEAD = 'lead'
KEYS = 'keys'
SESSION = 'session'
FIRST_NAMES = {
    DRUMS: dict(zip(COMPLEXITIES, MSG_DRUMMERS)),
    BASS: dict(zip(COMPLEXITIES, MSG_BASS_PLAYERS)),
    RHYTHM: dict(zip(COMPLEXITIES, MSG_RHYTHM_PLAYERS)),
    LEAD: dict(zip(COMPLEXITIES, MSG_LEAD_PLAYERS)),
    KEYS: dict(zip(COMPLEXITIES, MSG_KEYS_PLAYERS)),
    SESSION: dict(zip(COMPLEXITIES, MSG_SESSION_PLAYERS)),
}
INSTRUMENTS = tuple(FIRST_NAMES)


def player_name(*, instrument, complexity):
    """The name people see for the player of an instrument at a complexity."""
    return MSG_PLAYER.format(FIRST_NAMES[instrument][complexity], FAMILIES[complexity])
