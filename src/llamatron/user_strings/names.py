# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Names the program gives to things: how a copy or a new thing is numbered, and what a thing with no name is called.

Each constant starts with MSG_.
"""


# macro_composer/composer.py
# A generator named for its kind where a generator of another kind has its name, as kick rush beside kick drag, a set file
# listing every generator in one list where no two share a name; each kind's word is in labels.py.
MSG_NAMED_FOR_KIND = '{name} {word}'

# composition/naming.py
# How a copy or a new thing is numbered, like bass-2, what joins the number, and a new scale's name, like F_harmonic_minor,
# with the name older files gave one, like F Harmonic Minor.
MSG_NUMBER_JOINT = '-'
MSG_NUMBERED_NAME = '{base}-{number}'
# What the parts of a pattern split into new patterns are named after: the pattern, and then a number.
MSG_SPLIT_BASE = '{name}-split'
MSG_DEFAULT_SCALE_NAME = '{root}_{kind}'
MSG_LEGACY_SCALE_NAME = '{root} {kind}'

# tui/document.py
# How a scene with no name is described.
MSG_DOCUMENT_UNNAMED_SCENE = 'unnamed'
MSG_SCENE_WITHOUT_A_NAME = 'scene'

# composition/defaults.py: the names given to a new set's song and to each new thing, numbered from 1
# What a song is called until it's renamed: the one a new set starts with, and the one an older
# file's single song gets when the file's name can't be used.
MSG_DEFAULT_SONG_NAME = 'untitled'
# What a new scene or track is called, by its number from 1: a new song starts with one of each, and the
# Arrange page names the ones it adds the same way, to be renamed on their own pages.
MSG_NEW_SCENE_NAME = 'scene-{number}'
MSG_NEW_TRACK_NAME = 'track-{number}'
# The track a pattern's preview plays on, in the copy of the set the preview plays (tui/pattern_preview.py).
MSG_PREVIEW_TRACK_NAME = '(preview)'
MSG_PREVIEW_PATTERN_NAME = '(sound)'
MSG_NEW_PATTERN_NAME = 'pattern-{number}'
# The word each kind of new thing is named with, before its dash and number (composition/naming.py's new_name); a blank pattern
# made on an empty cell of Arrange takes its track's name for its word.
MSG_NEW_PATTERN_WORD = 'pattern'
MSG_NEW_GROUP_WORD = 'group'
MSG_NEW_SCENE_WORD = 'scene'
MSG_NEW_TRACK_WORD = 'track'
MSG_NEW_GROOVE_WORD = 'groove'
MSG_NEW_RIFF_WORD = 'riff'
MSG_NEW_INSTRUMENT_WORD = 'instrument'
MSG_NEW_SCALE_WORD = 'scale'
MSG_NEW_SONG_WORD = 'song'

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
MSG_DRAW_WORD = 'draw'
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
