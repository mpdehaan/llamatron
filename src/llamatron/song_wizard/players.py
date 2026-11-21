# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The imaginary players a song may be given: for each instrument, four of rising complexity.

A file says how a player plays as a complexity from 1 to 4 and never by a name; the names are for people, shown by the wizard
and written into a made song's notes. A player's name and instrument are the same in every style, and who the player is
underneath, what the player picks and how the player keeps time, is each style template's to say. Every
player is imaginary. The family name says the complexity: a Llama is plain and dependable, an Alpaca tasteful and serving the
song, a Vicuna wilder and busier, a Guanaco the most advanced.
"""

from llamatron.user_strings import song_wizard as wizard_text

PLAIN = 1
TASTEFUL = 2
WILD = 3
ADVANCED = 4
COMPLEXITIES = (PLAIN, TASTEFUL, WILD, ADVANCED)
FAMILIES = dict(zip(COMPLEXITIES, wizard_text.MSG_PLAYER_FAMILIES))
# The instruments that have players of their own; any other instrument is played by a Session player.
DRUMS = 'drums'
BASS = 'bass'
RHYTHM = 'rhythm'
LEAD = 'lead'
KEYS = 'keys'
SESSION = 'session'
FIRST_NAMES = {
    DRUMS: dict(zip(COMPLEXITIES, wizard_text.MSG_DRUMMERS)),
    BASS: dict(zip(COMPLEXITIES, wizard_text.MSG_BASS_PLAYERS)),
    RHYTHM: dict(zip(COMPLEXITIES, wizard_text.MSG_RHYTHM_PLAYERS)),
    LEAD: dict(zip(COMPLEXITIES, wizard_text.MSG_LEAD_PLAYERS)),
    KEYS: dict(zip(COMPLEXITIES, wizard_text.MSG_KEYS_PLAYERS)),
    SESSION: dict(zip(COMPLEXITIES, wizard_text.MSG_SESSION_PLAYERS)),
}
INSTRUMENTS = tuple(FIRST_NAMES)


def player_name(*, instrument, complexity):
    """The name people see for the player of an instrument at a complexity."""
    return wizard_text.MSG_PLAYER.format(FIRST_NAMES[instrument][complexity], FAMILIES[complexity])
