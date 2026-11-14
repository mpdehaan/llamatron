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
"""Names the program gives to things: how a copy or a new thing is numbered, and what a thing with no name is called.

Each constant starts with MSG_.
"""

# composition/naming.py
# How a copy or a new thing is numbered, like bass 2, and a new scale's name, like F Harmonic Minor.
MSG_NUMBERED_NAME = '{base} {number}'
MSG_DEFAULT_SCALE_NAME = '{root} {kind}'

# tui/document.py
# How a scene with no name is described.
MSG_DOCUMENT_UNNAMED_SCENE = 'unnamed'
MSG_SCENE_WITHOUT_A_NAME = 'scene'

# composition/defaults.py: the names given to a new set's song and to each new thing, numbered from 1
# What a song is called until it's renamed: the one a new set starts with, and the one an older
# file's single song gets when the file's name can't be used.
MSG_DEFAULT_SONG_NAME = 'untitled'
# What a new scene or track is called, by its number from 1: a new song starts with one of each, and the
# Arrange page names the ones it adds the same way, to be renamed on their own pages, as the user asked on 2026-11-07.
MSG_NEW_SCENE_NAME = 'scene {number}'
MSG_NEW_TRACK_NAME = 'track {number}'
# The track a pattern's preview plays on, in the copy of the set the preview plays (tui/pattern_preview.py).
MSG_PREVIEW_TRACK_NAME = '(preview)'
MSG_NEW_PATTERN_NAME = 'pattern {number}'
# A blank pattern made on an empty cell of Arrange is named after its track, the user's design (tui/screens/arrange_page.py).
MSG_TRACK_PATTERN_NAME = '{track} {number}'
MSG_NEW_GROOVE_NAME = 'groove {number}'
MSG_NEW_INSTRUMENT_NAME = 'instrument {number}'

# composition/sections.py
# How error messages name the file as a whole, and one object in each section of named objects.
MSG_THE_FILE = 'the file'
MSG_PATTERN_WORD = 'pattern'
MSG_CHAIN_WORD = 'chain'
MSG_GROOVE_WORD = 'groove'
MSG_INSTRUMENT_WORD = 'instrument'
MSG_SCALE_WORD = 'scale'
MSG_TRACK_WORD = 'track'
MSG_REGISTER_WORD = 'register'
MSG_SONG_WORD = 'song'

# playback/written_scene.py
# A scene with no name of its own is named by its number, and a repeat adds its number to the name.
MSG_UNNAMED_SCENE = 'Scene {number}'
# How error messages name a scene.
MSG_SCENE_DESCRIPTION = 'scene {number} ({name})'

# exporters/exports.py
# What each kind of export is called in a sentence, such as "exported the MIDI stems to ...".
MSG_ABLETON_EXPORT_LABEL = 'Ableton set'
MSG_MIDI_FILE_EXPORT_LABEL = 'MIDI file'
MSG_GENERAL_MIDI_EXPORT_LABEL = 'MIDI (General MIDI)'
MSG_WAV_EXPORT_LABEL = 'WAV (FluidSynth)'
MSG_STEMS_EXPORT_LABEL = 'MIDI stems'
MSG_CLIP_TREE_EXPORT_LABEL = 'MIDI clips'
