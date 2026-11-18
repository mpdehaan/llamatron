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

"""The MacroComposer's words: the names it gives the parts and scenes of a song it makes, the notes it writes into the song,
and the imaginary players' names, which people see for a complexity from 1 to 4.

Each constant starts with MSG_.
"""

# macro_composer/arranger.py
MSG_PART_AT_LEVEL = '{} at {}'
MSG_PART_BESIDE = '{} {}: {}'
MSG_SECTION_START_PART = '{} start'
MSG_TIMING_CHAIN = '{} timing'
MSG_PLAYED_BY = '{}: {}. {}'
MSG_PLAYED_BY_OWN = '{}: a player of gauges set one by one.'
MSG_MADE_SONG_NOTES = '{title}: a {style} song, {template}, made by the MacroComposer from the style template and the song\'s picks.\n\n{picks}\n\n{form}\n'
MSG_MADE_PICK = '{}: {}.'
MSG_MADE_SCENE = 'Scene {}, {}, {} bars.'
MSG_PART_OF_SECTION = '{} {}'
# The pattern of a kind of section's tune once a person has written it by hand, which every section of the kind plays.
MSG_OWN_TUNE_PART = '{kind} tune'
# The instrument made for a piece of the kit that sounds as a General MIDI sound.
MSG_PIECE_INSTRUMENT = '{} sound'
# The muted track a made song's chords are written on, in capitals to show it is a guide and no instrument, its instrument, and the generator that follows it.
MSG_CHORDS_TRACK = 'CHORDS'
MSG_CHORDS_INSTRUMENT = 'chords guide'
MSG_FOLLOW_CHORDS_NAME = 'follow chords'
MSG_REPEATED_SCENE = '{} {}'

# macro_composer/song_plan.py: what a planned section says of itself in the song's notes.
MSG_PLAN_ENERGY = 'Energy {}.'
MSG_PLAN_LEAVES_TAIL = 'Leaves with: {}.'
MSG_PLAN_LEAVES_FILL = 'Leaves with a fill, {}.'
MSG_PLAN_SET_UP = 'Last bar on chord {}.'
MSG_PLAN_HOOK = 'The hook: {}.'
MSG_PLAN_STAGE = 'Its shape: {}.'
# macro_composer/hook_kinds.py: a hook's kind in words, its contour, its rhythm and its odd detail.
MSG_HOOK_KIND = '{}, {}, {}'

# macro_composer/players.py
# A player's name, the first name and the family's, and each list from complexity 1 to 4.
MSG_PLAYER = '{} {}'
MSG_PLAYER_FAMILIES = ('Llama', 'Alpaca', 'Vicuna', 'Guanaco')
MSG_DRUMMERS = ('Larry', 'Lucy', 'Thomas', 'Animal')
MSG_BASS_PLAYERS = ('Michael', 'Sam', 'Peter', 'Chester')
MSG_RHYTHM_PLAYERS = ('Eric', 'Jane', 'Graham', 'Sark')
MSG_LEAD_PLAYERS = ('George', 'Edmund', 'Dave', 'Ed')
MSG_KEYS_PLAYERS = ('Susan', 'Egon', 'Ralph', 'Eleanor')
MSG_SESSION_PLAYERS = ('Session', 'Session', 'Session', 'Session')
