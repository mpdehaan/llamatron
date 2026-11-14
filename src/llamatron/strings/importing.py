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
"""What the MIDI import names and says: the names it gives what it makes, and what it tells about a file and about what it made.

The import (importers/) names tracks, scenes and patterns with these, and the import dialog
shows the lines about the file and the song.
"""

# importers/voices.py
# A track that plays both hands is split at middle C into its treble and its bass, and a part that
# plays several notes at once into voices lettered from the top, like up a, up b.
MSG_TREBLE_PART = '{track} treble'
MSG_BASS_PART = '{track} bass'
MSG_VOICE_PART = '{part} {letter}'
MSG_VOICE_LETTERS = 'abcdefghijklmnopqrstuvwxyz'
# A drum sound that General MIDI doesn't name, numbered from 1.
MSG_UNNAMED_DRUM = 'perc {number}'
# The General MIDI names of the drum sounds, by note number, short enough for a track's name.
MSG_DRUM_NAMES = {
    35: 'acoustic kick', 36: 'kick', 37: 'side stick', 38: 'snare', 39: 'clap', 40: 'electric snare',
    41: 'low floor tom', 42: 'closed hat', 43: 'high floor tom', 44: 'pedal hat', 45: 'low tom', 46: 'open hat',
    47: 'low mid tom', 48: 'high mid tom', 49: 'crash', 50: 'high tom', 51: 'ride', 52: 'china', 53: 'ride bell',
    54: 'tambourine', 55: 'splash', 56: 'cowbell', 57: 'second crash', 58: 'vibraslap', 59: 'second ride',
    60: 'high bongo', 61: 'low bongo', 62: 'muted high conga', 63: 'open high conga', 64: 'low conga',
    65: 'high timbale', 66: 'low timbale', 67: 'high agogo', 68: 'low agogo', 69: 'cabasa', 70: 'maracas',
    71: 'short whistle', 72: 'long whistle', 73: 'short guiro', 74: 'long guiro', 75: 'claves',
    76: 'high wood block', 77: 'low wood block', 78: 'muted cuica', 79: 'open cuica', 80: 'muted triangle',
    81: 'open triangle',
}

# importers/midi_reading.py
# What a MIDI track with no name is called, numbered from 1 among the file's tracks.
MSG_UNNAMED_MIDI_TRACK = 'track {number}'

# importers/writing.py
# A scene is named after the bars it plays, counted from 1, or the one bar.
MSG_SCENE_BARS = 'bars {first}-{last}'
MSG_SCENE_BAR = 'bar {first}'
# Where an error places what the import made, which only a fault of the import's own can raise.
MSG_WHERE_IMPORTED = 'imported song'

# importers/midi_import.py
# What an import had to change, each said only when it happened, so that a song that sounds as the file does says
# nothing. Each is a sentence, since the dialog after an import lists them.
MSG_WARN_MOVED = '{count} notes were moved to the nearest step.'
MSG_WARN_SWUNG = '{count} notes were moved to the nearest step. They sit a little off the steps, as a swing, a groove or a live performance plays them, and the import makes no groove yet.'
MSG_WARN_LENGTHS_CHANGED = '{count} notes are held for whole steps, being longer than a gate can be.'
MSG_WARN_TOO_LOW = '{count} notes were left out, too low to write as a degree.'
MSG_WARN_TEMPOS_MOVED = '{count} tempo changes were moved to where a scene could start.'
MSG_WARN_UNENDED = '{count} notes the file never ended are held to the end of their track.'
MSG_WARN_LEFT_OUT = '{count} pitch bend and aftertouch messages were left out, which llamatron cannot send.'
MSG_WARN_CONTROLS_LEFT_OUT = '{count} CC messages were left out, of CC {numbers}, since a track has four CC lanes.'
MSG_WARN_CONTROLS_NO_NOTES = '{count} CC messages were left out, sent on a channel that plays no notes.'
MSG_WARN_CONTROLS_OFF = '{count} CC messages were left out, with Import CCs off.'
MSG_WARN_CONTROLS_MOVED = '{count} CC messages fell between steps, and are sent on a step or lost to a later one.'
MSG_WARN_NUMBERS_JOIN = ', '

# tui/dialogs/import_dialog.py: the user's design of 2026-11-10, a dialog of fields over the file picker.
# The title says what is imported, since the main screen's cell only says Import (the user's choice of 2026-11-10).
MSG_IMPORT_TITLE = 'Import MIDI file'
MSG_IMPORT_FOUND = 'found: {tracks} tracks, {bars} bars, {time_signature}, {tempo} bpm, {keys}'
MSG_IMPORT_KEYS_JOIN = ' then '
MSG_IMPORT_MORE_KEYS = '{first} then {count} more keys'
MSG_IMPORT_MAKES = 'makes {tracks} tracks, {patterns} patterns, {scenes} scenes'
MSG_IMPORT_MAKES_LONG = 'makes {tracks} tracks, {patterns} patterns ({long} longer than {longest} steps), {scenes} scenes'
MSG_IMPORT_SHARED = '{count} patterns the set has already'
MSG_IMPORT_SONG_NAME = 'Song name'
MSG_IMPORT_LONGEST = 'Longest pattern'
MSG_IMPORT_UNIQUE_NAMES = 'Use unique names'
MSG_IMPORT_CHORDS = 'Chords'
MSG_IMPORT_CONTROLS = 'Import CCs'
MSG_IMPORT_STEP_SIZE = 'Step size'
MSG_IMPORT_STEPS = '{count} steps'
MSG_IMPORT_AS_CHORDS = 'as chords'
MSG_IMPORT_AS_TRACKS = 'as extra tracks'
MSG_IMPORT_AUTO_STEP = 'auto ({size})'
MSG_IMPORT_BUTTONS = ('Import', 'Cancel')
MSG_IMPORT_SONG_PROMPT = 'Song name'

# tui/dialogs/imported_dialog.py: the dialog after an import, the user's design of 2026-11-10.
MSG_IMPORTED_TITLE = 'Import complete'
MSG_IMPORTED_SONG = 'Song imported as ({name}).'
MSG_IMPORTED_COUNTS = 'It has {tracks} tracks, {patterns} new patterns and {scenes} scenes.'
MSG_IMPORTED_NO_WARNINGS = 'Import complete with no warnings.'
MSG_IMPORTED_WARNINGS = 'Import complete with these warnings:'
MSG_IMPORTED_BUTTON = 'OK'

# tui/screens/importing.py
MSG_IMPORTED = 'imported song ({name}): {tracks} tracks, {patterns} patterns, {scenes} scenes'
