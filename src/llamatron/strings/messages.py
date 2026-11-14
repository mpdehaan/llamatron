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
"""What the tracker says: the status line's notes, dialog titles, questions, prompts and the notes under a page's fields.

Each constant starts with MSG_. A message that says what went wrong is an error, in errors.py.
"""

from llamatron.composition.file_format import Section, SetlistSetting, SongSetting
from llamatron.strings.labels import PageName

# Shared by several pages: a field with no value, and a song or scene with no scale in a sentence.
MSG_NO_SCALE = 'no scale'
MSG_NO_SEED = 'no seed'

# tui/app.py
MSG_QUIT_UNSAVED_NOTE = 'unsaved changes'
MSG_QUIT_UNSAVED_QUESTION = 'The set has unsaved changes.'

# tui/screens/arrange_page.py
# Dialogs and messages.
MSG_DELETE_SCENE_QUESTION = 'Delete scene {name}?'
MSG_DELETE_TRACK_QUESTION = 'Delete track {name}?'
MSG_DELETE_CLIP_QUESTION = 'Delete the clip on track {track}?'
MSG_GRABBERS_STOP = '{count} clip(s) that grab from it will stop grabbing.'
MSG_PATTERN_FOR_CLIP_TITLE = 'Pattern for this clip'
MSG_COPIED_CLIP = 'copied the clip: press V on another cell to paste it'
MSG_PASTED_WITHOUT_GRAB = 'pasted without its grab from {track}, which would go round in a circle here'
# The scene page.
MSG_SCENE_NAME_PROMPT = 'Scene name'
MSG_SCENE_SCALE_TITLE = 'Scene scale'
MSG_CLIP_SCALE_TITLE = 'Clip scale'
MSG_SONG_TIME_SIGNATURE_PROMPT = 'Time signature, such as 6/8'
MSG_SCENE_LENGTH_NOTE = '  Length    {length}  (its longest clip that does not loop, with repeats)'
MSG_PROBLEM_NOTE = '  Problem   {problem}'
# The clip page.
MSG_CLIP_NAME_PROMPT = 'Clip name'
MSG_CLIP_LENGTH_NOTE = '  Length    {length}  of a {scene} scene'
MSG_LOOP_NOTE = '  Plays until the other clips are done. One clip in a scene must not loop.'
MSG_MORPH_HINT_NOTE = '  Set Repeat above 1 to choose a pattern to morph to.'
MSG_GRAB_HINT_NOTE = '  Grab track only changes Grab steps, and this pattern has none yet.'

# tui/screens/page.py and tui/key_table.py: the key names, the labels and the words every page shares
MSG_SEARCH_STATUS = '/{text}'
# The current song, at the right of every header.
MSG_HELP_TITLE = 'Help: {where}, {panel}'

# tui/document.py
# How uses are described: one line each, like "song one, scene 2 (verse), track bass".
MSG_USE_SCENE = 'scene {number} ({name})'
MSG_USE_SONG_SCENE = 'song {song}, {scene}'
MSG_USE_SONG_SCENE_TRACK = 'song {song}, {scene}, track {track}'
MSG_USE_CHAIN = 'chain {name}'
MSG_USE_SONG = 'song {name}'
MSG_USE_SONG_TRACK = 'song {song}, track {track}'

# tui/screens/list_page.py and tui/screens/field_page.py
MSG_DELETE_TITLE = 'Delete'
# tui/screens/arrange_page.py: the picker of chains to add to a cell from its details.
MSG_ADD_CHAIN_TITLE = 'Add a chain'
MSG_DELETE_QUESTION = 'Delete {what}?'
MSG_ALSO_DELETES_CLIPS = 'This also deletes its {count} clip(s).'

# tui/screens/main_page.py, tui/screens/file_page.py and tui/screens/everywhere.py
MSG_QUIT_TITLE = PageName.QUIT
MSG_SONG_SCALE_TITLE = 'Song scale'
# The notes under the Set File page's fields.
MSG_FILE_NOTE = '  Path          {path}'
MSG_EXPORTS_NOTE = '  Exports to    {where}'
# Opening, saving and exporting, from any page.
MSG_UNSAVED_TITLE = 'Unsaved changes'
MSG_UNSAVED_CONTINUE = 'This set has unsaved changes, which will be lost. Continue?'
MSG_STARTED_NEW = 'started a new set'
MSG_OPENED = 'opened {path}'
MSG_SAVE_AS_PROMPT = 'Save as'
MSG_REPLACE_FILE_TITLE = 'Replace file'
MSG_REPLACE_FILE_QUESTION = 'Replace {path}?'
MSG_SAVED = 'saved {path}'
MSG_FILE_UNCHANGED = 'no changes to save: {path} is up to date'
MSG_FILE_CHANGED_ELSEWHERE_TITLE = 'File changed'
MSG_FILE_CHANGED_ELSEWHERE_QUESTION = '{path} has changed since it was opened or saved here. Write over it?'
# A protected set, like the demos, is never saved over: Ctrl+S offers a copy, and the Set File page turns the protection off.
MSG_PROTECTED_TITLE = 'Protected set'
MSG_PROTECTED_EXPLAINED = '{path} is protected, so it is not written over. Protected on the Set File page turns that off.'
MSG_PROTECTED_SAVE_COPY_QUESTION = 'Save a copy under another name?'
MSG_PROTECTED_CHOOSE_ANOTHER_NAME = 'Choose another name for the copy.'
# composition/corrections.py and tui/dialogs/corrections_dialog.py: a set file that holds values that cannot be
# used, each with an allowed value near it. One line for each, with its place in the file, then the question.
MSG_CORRECTED = '{where}: {name} {found} becomes {used}'
MSG_CORRECTED_TO_DEFAULT = '{where}: {name} {found} becomes the default'
MSG_CORRECTED_SEVERAL = '{where}: {name}, {count} out of range, nearest allowed used'
MSG_CORRECTIONS_TITLE = 'Values that cannot be used'
MSG_CORRECTIONS_INTRO = '{file} holds values that cannot be used. Opening the set changes each one:'
MSG_CORRECTIONS_MORE = 'and {count} more'
MSG_CORRECTIONS_WARNING = 'The composition may sound different. The file stays as it is until the set is saved.'
MSG_CORRECTIONS_QUESTION = 'Open the set with these changes?'
# Exports are named after the set's file and written beside it, so an unsaved set is saved first.
MSG_SAVE_BEFORE_EXPORT_TITLE = 'Save first'
MSG_SAVE_BEFORE_EXPORT = 'Exports are named after the set and written beside its file, so the set has to be saved first.'
# What X offers, in the order of EXPORT_KINDS: a Live set, then the three kinds of MIDI files.
MSG_EXPORT_TITLE = 'Export song {name}'
# Only a Live set asks before it's written over, and only the first time in a session, as the user asked.
MSG_REPLACE_EXPORT_TITLE = 'Overwrite'
# Choosing the WAV export, which plays only the tracks whose instrument plays through FluidSynth.
MSG_WAV_EXPORT_TITLE = 'WAV export'
MSG_WAV_EXPORT_NOTE = 'Only the tracks whose instrument plays through FluidSynth are in the WAV export. Export it?'
MSG_REPLACE_EXPORT_QUESTION = 'Are you sure you want to overwrite {path}?'
MSG_EXPORT_REPLACES_LIVE_WORK = 'Anything saved over it in Live is lost. Save your own work under another name.'
MSG_EXPORTED = 'exported the {name} to {path}'

# tui/history.py: what the status line says after an undo or a redo, and how it names what changed.
MSG_UNDONE = 'undone: {what}'
MSG_RESTORED = 'restored: {what}'
MSG_NOTHING_TO_UNDO = 'nothing to undo'
MSG_NOTHING_TO_REDO = 'nothing to redo'
# When an undo or redo takes away what the open page showed, the tracker goes back to the page it came from.
MSG_BACK_FROM = '{status}, back from {page}'
MSG_CHANGED_NAMED = '{kind} ({name})'
MSG_CHANGED_IN_SONG = 'song ({song}): {what}'
MSG_CHANGED_SCENE = 'scene {number}'
MSG_CHANGED_THE_SET = 'the set'
MSG_CHANGED_WORDS = {
    Section.SCALES: 'scale', Section.PATTERNS: 'pattern', Section.ARPS: 'arp', Section.AUTO_RATCHETS: 'AutoRatchet', Section.DRIFTS: 'drift', Section.PROGRESSIONS: 'progression', Section.VOICE_LEADINGS: 'voice leading', Section.STRUMS: 'Strum', Section.EUCLIDS: 'Euclid', Section.GLIDES: 'Glide', Section.SHORTENS: 'Shorten', Section.RUSHES: 'Rush', Section.DRAGS: 'Drag', Section.HOCKETS: 'Hocket', Section.DENSITIES: 'Density', Section.SWELLS: 'Swell',
    Section.ARTICULATES: 'Articulate',
    Section.CHAINS: 'chain', Section.GROOVES: 'groove', Section.INSTRUMENTS: 'instrument', Section.SONGS: 'song', Section.TRACKS: 'track', Section.REGISTERS: 'register',
    SetlistSetting.TITLE: 'title', SetlistSetting.AUTHOR: 'author', SetlistSetting.DESCRIPTION: 'description', SetlistSetting.NOTES: 'notes',
    SetlistSetting.STEP_SIZE: 'step size', SetlistSetting.DEFAULT_OCTAVE: 'default octave', SetlistSetting.DEFAULT_DRUM_OCTAVE: 'default drum octave',
    SetlistSetting.OCTAVE_LABELS: 'octave labels', SetlistSetting.PROTECTED: 'protected',
    SetlistSetting.DEFAULT_FOLLOW_ACTION: 'default follow action', SetlistSetting.REAL_TIME: 'real time',
    SongSetting.TEMPO: 'tempo', SongSetting.TIME_SIGNATURE: 'time signature', SongSetting.SCALE: 'scale', SongSetting.SEED: 'seed', SongSetting.GROOVE: 'groove',
}

# The Songs page.
MSG_NEW_SONG_PROMPT = 'New song name'
MSG_RENAME_SONG_PROMPT = 'Rename song'

# tui/screens/track_editor.py
MSG_RENAME_TRACK_PROMPT = 'Rename track'
MSG_EDITING = 'editing: Tab reaches Save and Cancel, Esc cancels'
MSG_CLEAR_NOTES_TITLE = 'Clear the notes'
MSG_CLEAR_NOTES_QUESTION = 'Delete all of the notes?'
MSG_NO_NOTES_NOTE = '  No notes yet. Press E to write some.'
# A protected set's notes can only be read, since the set is kept as it is.
MSG_NO_NOTES_PROTECTED = '  No notes. The set is protected, so they cannot be written here.'
MSG_NOTES_PROTECTED = 'the set is protected, so its notes can only be read'
MSG_NEW_PATTERN_PROMPT = 'New pattern name'
MSG_NEW_CHAIN_PROMPT = 'New chain name'
MSG_RENAME_CHAIN_PROMPT = 'Rename chain'
MSG_RENAME_GENERATOR_PROMPT = 'Rename {label}'
MSG_COPIED_TO = 'copied to {name}'
MSG_CC_PROMPT = 'CC {number} number'
MSG_TRANSPOSE_NOTE = '  Transpose counts notes of the scale, so 7 is an octave in a seven-note scale.'
# The first choice of the chain editor's picker, which makes a new generator, the dialog of its kinds, and what a new one is called, numbered after the first.
MSG_NEW_GENERATOR_CHOICE = '(new generator)'
MSG_NEW_GENERATOR_KIND_TITLE = 'New generator: which kind?'
MSG_NEW_GENERATOR_NAMED = '{kind} 1'
MSG_ADD_TO_CHAIN_TITLE = 'Add to chain'
MSG_ADD_CHAIN_TITLE = 'Add a chain'
MSG_CHANGE_STEP_TITLE = 'Change step'
MSG_OFFSETS_NOTE = '  Steps start again with each chord. A blank step is silent. Tab: next row'
MSG_RENAME_SCALE_PROMPT = 'Rename scale'

# tui/screens/scale_page.py
MSG_ROOT_TITLE = 'Root note'
MSG_KIND_TITLE = 'Kind of {root} scale'
MSG_SCALE_USES_NOTE = '  Used by {count} song(s) and scene(s).'
MSG_SCALE_NOTES_DETAIL = '{root} {kind}: {notes}'

# tui/screens/pattern_editor.py, its two drawings and the rows in tui/components/
MSG_GATE_PROMPT = 'Gate'
MSG_STEP_SIZE_PROMPT = "Step size (blank for the song's)"
MSG_TIME_SIGNATURE_PROMPT = "Time signature (blank for the song's)"
MSG_DESCRIBE_EMPTY = 'Step {step}: empty'
MSG_DESCRIBE_TIED = 'Step {step}: tie, holding the note before it'
MSG_DESCRIBE_NOTE = 'Step {step}: {sound}, gate {gate}{chord}'
MSG_DESCRIBE_CHORD = ', chord {chord}'
# What the description line calls the sound of a step marked to grab, whose note is whatever the other track played.
MSG_GRABBED_SOUND = 'the grabbed note'
MSG_DESCRIBE_GATE_OVERRIDDEN = ' (the ties after it override it)'
MSG_IN_SCALE = ' in {scale}'
MSG_DEGREE_WITHOUT_SCALE = 'degree {degree}, no scale'
# What the editor's keys do, in its legend.
# The munge dialog, which rearranges a pattern's steps around the cursor, in the order of Munge.
MSG_MUNGE_TITLE = 'Munge'
MSG_RECONFIGURE_TITLE = 'Reconfigure'
# Prompts, dialogs and messages.
MSG_NUMBER_PROMPT = '{row} ({low} to {high})'
MSG_PLAY_DIRECTION_TITLE = 'Play direction'
MSG_LOAD_OVER_TITLE = 'Load over'
MSG_LOAD_OVER_CHOICE_TITLE = 'Load over {name}'
MSG_LOAD_OVER_QUESTION = 'Replace everything in {name} with a copy of {other}?'
MSG_STEPS_PROMPT = 'Number of steps'
MSG_SHORTEN_TITLE = 'Shorten pattern'
MSG_SHORTEN_QUESTION = 'This removes {count} step(s) that hold something. Continue?'
MSG_CHANGE_TYPE_TITLE = 'Change pattern type'
MSG_CHANGE_TYPE_QUESTION = 'This pattern will use {what}, which clears the notes it has now. Continue?'
MSG_CHANGE_TYPE_EMPTY_QUESTION = 'This pattern will use {what}. Continue?'
MSG_RENAME_PATTERN_PROMPT = 'Rename pattern'
# tui/dialogs/chord_dialog.py and tui/chord_text.py: the Chord dialog, shared by the pattern editor and a progression's chord editor.
MSG_CHORD_DIALOG_TITLE = 'Chord: {where}'
MSG_CHORD_OF_STEP = 'step {step} of {pattern}'
MSG_CHORD_OF_PROGRESSION = 'chord {chord} of {progression}'
MSG_QUALITY_SINGLE_NOTE = '(single note)'
MSG_QUALITY_FROM_SCALE = "(the scale's own)"
MSG_SCALE_NOT_BORROWED = "(the clip's own)"
MSG_CHORD_SENTENCE = 'In {scale}, the chord on {degree} is {name}.'
MSG_CHORD_OWN_SENTENCE = "In {scale}, the clip's own, the chord is {name}."
MSG_NOTE_SENTENCE = 'In {scale}, the note on {degree} is {name}.'
MSG_CHORD_NOTES = 'Notes: {notes}'
MSG_CHORD_NO_SCALE_KNOWN = 'No scale is known here, so the chord has no name yet.'
# What the status line says of the chord under the cursor while nothing else is said.
MSG_CHORD_RESTING = '{where}: in {scale}, the chord on {degree} is {name} ({notes})'
MSG_CHORD_RESTING_OWN = '; in {scale} it is {name}'
MSG_RESTING_STEP = 'step {step}'
MSG_RESTING_CHORD = 'chord {chord}'

# tui/screens/registers_page.py
MSG_REGISTER_PROMPT = '{label} ({lowest} to {highest})'

# tui/screens/grooves_page.py
MSG_RENAME_GROOVE_PROMPT = 'Rename groove'

# tui/screens/instruments_page.py and tui/screens/instrument_editor.py
MSG_RENAME_INSTRUMENT_PROMPT = 'Rename instrument'
MSG_DEVICE_TITLE = 'MIDI device'
MSG_GM_SOUND_TITLE = 'General MIDI sound'
MSG_CHANNEL_PROMPT = 'Channel ({lowest} to {highest})'

# tui/screens/main_page.py
MSG_REAL_TIME_ON = 'real time on: tracks with an instrument play through it'
MSG_REAL_TIME_OFF = 'real time off'
MSG_REAL_TIME_OFF_STOPPED = 'real time off: stopped what was playing'

# tui/transport.py and the pages that play: the status line's notes about real-time playback.
MSG_SCENE_NUMBER = 'scene {number}'
MSG_CLIP_ON_TRACK = 'clip ({name}) on track ({track})'
MSG_PLAYING_FROM = 'playing from {scene}'
MSG_PLAYING_CLIP = 'playing {clip} on its own'
MSG_LISTENING = 'listening to ({name}) through track ({track})'
MSG_STARTS_AT_NEXT_BAR = '{what} starts at the next bar'
# The visualizer key on Arrange when the Set File page hides every visualizer mode.
MSG_EVERY_VISUALIZER_HIDDEN = 'every visualizer is hidden on the Set File page'
MSG_STOPPED = 'stopped'
# tui/transport.py: an edit made while the song plays that can't be heard, which the status line says, what plays going on as it was.
MSG_LIVE_EDIT_NOT_HEARD = 'the edit cannot be heard while playing: {problem}'
MSG_LIVE_EDIT_NEEDS_A_DEVICE = 'the edit plays through a MIDI device not open yet, so it is heard from the next launch'
MSG_STOPPED_TRACK = 'stopped track ({track})'
MSG_SILENCED = 'silenced {channels} channels on {devices} devices'
MSG_NOTHING_TO_SILENCE = 'no instrument has a connected device to silence'
MSG_LISTEN_TRACK_TITLE = 'Listen through which track?'
MSG_LISTEN_INSTRUMENT_TITLE = 'Listen through which instrument?'

# tui/screens/groove_editor.py
MSG_GROOVE_NOTE = '  Each cell is {length} of a whole note. An amount is a percentage of a cell: + plays late, - plays early.'
MSG_GROOVE_REPEATS_NOTE = '  The row repeats from the start of each scene, and a note takes the amount of the cell its time falls in.'
MSG_FACTORY_GROOVE_NOTE = '  A factory groove, which cannot be changed. C on the Grooves page copies it to one you can edit.'

# tui/screens/groove_choice.py: the Groove field on the Song, Scene and Track pages
MSG_SONG_GROOVE_TITLE = 'Song groove'
MSG_PREVIEW_INSTRUMENT_TITLE = 'Preview instrument'
MSG_SCENE_GROOVE_TITLE = 'Scene groove'
MSG_TRACK_GROOVE_TITLE = 'Track groove'

# tui/screens/chords_editor.py: the line above a progression's chords, and the title of the picker of named progressions.
MSG_CHORDS_NOTE = 'each chord moves the clip from chord I, in the song\'s scale'
MSG_PROGRESSION_PICKER_TITLE = 'Progressions'

# tui/screens/euclid_fields.py: the title of the picker of named rhythms.
MSG_RHYTHM_PICKER_TITLE = 'Rhythms'

# tui/screens/step_row_editor.py: the line above a row of steps, saying what a step that's on does.
MSG_STEP_ROW_NOTES = {
    Section.GLIDES: 'a note starting on a step that is on glides into the next note',
    Section.SHORTENS: 'a note starting on a step that is on plays short',
    Section.RUSHES: 'a note starting on a step that is on plays early',
    Section.DRAGS: 'a note starting on a step that is on plays late',
}

# tui/screens/list_page.py and tui/screens/arrange_page.py: Move mode, the user's design.
MSG_MOVING = 'moving {what}: the arrows carry it, Enter drops it'
MSG_MOVING_SCENE = 'scene ({name})'
MSG_MOVING_TRACK = 'track ({name})'
MSG_MOVING_CLIP = 'clip ({name})'
MSG_MOVING_ROW = '({name})'
