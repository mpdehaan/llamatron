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
"""The names of things on screen: page names, field labels, column headings, crumbs, row labels and a picker's choices.

Each constant starts with MSG_, and the classes Crumb and Column group the words many pages share.
"""

from llamatron.composition.file_format import (
    CONDITION_ROWS, AtLimit, DriftValue, FollowAction, LiveResponsiveness, NamedProgression, Shape, ShapePart, EuclidPart, NamedRhythm, Restart, Section, StrumDirection, StrumPart, UpstrokeStrings, REGISTER_ADD_ROWS, REGISTER_NOTE_ROWS, REGISTER_SET_ROWS, REGISTER_VELOCITY_ROWS, ChordSymbol, Direction, GateModifier, OctaveLabels, RegisterSetting, Row,
    Approach, ChordColor, ScaleKind, ReadyBar, SingleNotes, Stroke, Tuning,
)
from llamatron.tui.keys import RowSection


def register_labels(*, rows, label):
    """Return each register's row in a group of register rows with its label, like ax_note with AX+Note."""
    return {row: label.format(name=name) for name, row in rows.items()}


# tui/dialogs/quit_dialog.py
# The quit dialog's buttons, in the order of QUIT_WITHOUT_SAVING, SAVE_THEN_QUIT and CANCEL: quitting without
# saving comes first, and is what ENTER does, because Quit is never pressed by accident; the dialog only appears when there are
# changes to lose.
MSG_QUIT_BUTTONS = ('Quit without saving', 'Save, then Quit', 'CANCEL')
# A message's one button.
MSG_OK_BUTTON = 'OK'
# The buttons of a dialog that is finished or cancelled, in that order.
MSG_OK_CANCEL_BUTTONS = ('OK', 'CANCEL')
# The confirm dialog's two buttons, in the order they're drawn and the arrows move: yes first, since ENTER presses the selected one.
MSG_CONFIRM_BUTTONS = ('YES', 'NO')

# tui/screens/arrange/arrange_page.py
# A scene's field for each register it can reset, like "Reset AX".
MSG_RESET_LABEL = 'Reset {name}'
MSG_SONG_OPTION = '(song)'
MSG_SCENE_OPTION = '(scene)'
MSG_NAME_LABEL = 'Name'
MSG_SCALE_LABEL = 'Scale'
MSG_TEMPO_LABEL = 'Tempo'
MSG_TIME_SIGNATURE_LABEL = 'Time signature'
# How long a note placed on the piano roll lasts, unless the pattern says otherwise: blank is one step.
MSG_ENTRY_SIZE_LABEL = 'Entry size'
MSG_TEMPO_RAMP_LABEL = 'Tempo ramps to'
MSG_REPEAT_LABEL = 'Repeat'
MSG_PATTERN_LABEL = 'Pattern'
MSG_CHAINS_LABEL = 'Chains'
MSG_LOOP_LABEL = 'Loop'
MSG_DIRECTION_LABEL = 'Direction'
MSG_MORPH_TO_LABEL = 'Morph to'
MSG_MORPH_DIRECTION_LABEL = 'Morph direction'
MSG_GRAB_TRACK_LABEL = 'Grab track'

# tui/screens/set/instrument_editor.py and tui/screens/arrange/track_editor.py
MSG_DEVICE_LABEL = 'Device'
MSG_CHANNEL_LABEL = 'Channel'
MSG_INSTRUMENT_LABEL = 'Instrument'
# The clip page's buttons for real-time playback.
MSG_PLAY_LABEL = 'Play'
MSG_STOP_LABEL = 'Stop'
# What a clip does in real-time playback when its scene is done, which no export reads, and the set's default for it.
MSG_FOLLOW_ACTION_LABEL = 'Advance'
MSG_DEFAULT_FOLLOW_ACTION_LABEL = 'Default follow action'
MSG_FOLLOW_ACTION_NAMES = {FollowAction.WITH_SCENE: 'With Scene', FollowAction.NEXT: 'Next', FollowAction.OFF: 'Off'}
MSG_LAUNCH_TOGETHER_LABEL = 'Launch together'

# tui/screens/shared/page.py and tui/key_table.py: the key names, the labels and the words every page shares
# The file crumb, right after the title on every page: the file's name, or this before the set is saved.
MSG_NO_FILE_CRUMB = '(unsaved)'
# The file crumb carries the current song too: minimal_techno.yml, song: minimal techno.
# The theme's stripe on a page that edits one thing: what it edits and its name.
MSG_EDITING_CAPTION = 'EDITING {what}: {name}'
MSG_CAPTION_WORDS = {
    Section.SONGS: 'song', Section.PATTERNS: 'pattern', Section.CHAINS: 'chain', Section.SCALES: 'scale', Section.GROOVES: 'groove',
    Section.INSTRUMENTS: 'instrument', Section.TRACKS: 'track', Section.ARPS: 'arpeggiator', Section.AUTO_RATCHETS: 'AutoRatchet',
    Section.DRIFTS: 'drift', Section.PROGRESSIONS: 'progression', Section.VOICE_LEADINGS: 'voice leading', Section.STRUMS: 'strum',
    Section.EUCLIDS: 'Euclid', Section.DENSITIES: 'density', Section.SWELLS: 'swell', Section.ARTICULATES: 'articulate',
    Section.GLIDES: 'glide', Section.SHORTENS: 'shorten', Section.RUSHES: 'rush', Section.DRAGS: 'drag', Section.HOCKETS: 'hocket', Section.GUITARIFIES: 'guitarify',
}
MSG_SCENE_CAPTION_WORD = 'scene'
MSG_CLIP_CAPTION_WORD = 'clip'
MSG_CLIP_CAPTION_NAME = '({scene}, {track})'
MSG_SET_CRUMB = 'set: {file}'
MSG_SONG_CRUMB = 'song: {song}'
# The F1 dialog's panels, in the order Tab turns through them: every key, then what the page is about.
MSG_HELP_PANELS = ('keys', 'about this page')

# AboutDialog: the cowsay cow saying the program's name, then the version, the links, a quote and the license.
# A clip's crumb: the pairing of a scene and a track, where the grid's row and column meet, rather than a hierarchy.
MSG_CLIP_CRUMB = 'clip: ({scene}, {track})'
# A scene's crumb under ARRANGE, which says what it is because scenes have no list page of their own.
MSG_SCENE_CRUMB = 'scene: {name}'
MSG_TRACK_CRUMB = 'track: {name}'
# The pattern editor's crumb when a clip opened it, after the crumbs of the page the clip was on.
MSG_PATTERN_CRUMB = 'pattern: {name}'
# The crumb of a thing that has a list page of its own above it, which is its name alone.
MSG_ITEM_CRUMB = '{name}'
# A named thing opened from another page, after that page's crumbs, like ARRANGE › chain: half, as a pattern opened from a clip reads.
MSG_OPENED_ITEM_CRUMB = '{word}: {name}'



class PageName:
    """What the main screen calls each page and each action, beside its key, which a page's crumbs and buttons use too."""

    FILE = 'File/Global'
    SONGS = 'Songs'
    PATTERNS = 'Patterns'
    CHAINS = 'Chains'
    GENERATORS = 'Generators'
    SCALES = 'Scales'
    GROOVES = 'Grooves'
    INSTRUMENTS = 'Instruments'
    REGISTERS = 'Registers'
    ARRANGE = 'Arrange'
    # What the main screen's Arrange cell is called while the set's Real Time switch is on, since Arrange then plays the song too.
    ARRANGE_PLAY = 'Arrange/Play'
    # The main screen's switch for real-time playback, beside the pages: a cell with a mark in place of a count.
    REAL_TIME = 'Real Time'
    SAVE = 'Save'
    OPEN = 'Open'
    EXPORT = 'Export'
    IMPORT = 'Import'
    UNDO = 'Undo'
    REDO = 'Redo'
    QUIT = 'Quit'
    HELP = 'Help'
    ABOUT = 'About'


class Crumb:
    """The pages' names in the header, which say where a page was reached from."""

    MAIN_SCREEN = 'MAIN SCREEN'
    FILE = 'FILE/GLOBAL'
    SONGS = 'SONGS'
    WIZARD = 'SONG WIZARD'
    NOTES = 'NOTES'
    OPEN = 'OPEN'
    IMPORT_MIDI = 'IMPORT MIDI'
    PATTERNS = 'PATTERNS'
    CHAINS = 'CHAINS'
    GENERATORS = 'GENERATORS'
    CHORDS = 'CHORDS'
    VOICE_LEADING = 'VOICE LEADING'
    STEPS = 'STEPS'
    STROKES = 'STROKES'
    OFFSETS = 'OFFSETS'
    SCALES = 'SCALES'
    GROOVES = 'GROOVES'
    INSTRUMENTS = 'INSTRUMENTS'
    REGISTERS = 'REGISTERS'
    ARRANGE = 'ARRANGE'


# tui/document.py
# Each direction, and what it does.
MSG_DIRECTION_NAMES = {
    Direction.FORWARD: 'first step to last', Direction.REVERSE_A: 'step 1, then backward from the last',
    Direction.REVERSE_B: 'last step to first', Direction.ALTERNATE: 'forward, then reverse',
    Direction.PENDULUM: 'forward and back without repeating the ends', Direction.RANDOM: 'any step',
    Direction.BROWNIAN: 'on 50%, back 25%, stay 25%', Direction.EITHERWAY: 'on or back, 50% each',
}


class Column:
    """The headings of the lists' columns."""

    NAME = 'NAME'
    TYPE = 'TYPE'
    # tui/dialogs/chord_dialog.py: the Chord dialog's four lists.
    SELECT_QUALITY = 'SELECT QUALITY'
    INVERSION = 'INV.'
    TENSIONS = 'TENSIONS'
    BORROW_SCALE = 'BORROW FROM SCALE'
    STEPS = 'STEPS'
    TRACKS = 'TRACKS'
    TIME = 'TIME'
    USED = 'USED'
    SCALE = 'SCALE'
    CURRENT = 'CURRENT'
    TEMPO = 'TEMPO'
    SCENES = 'SCENES'
    NOTES = 'NOTES'
    STEP = 'STEP'
    GENERATOR = 'GENERATOR'
    ORDER = 'ORDER'
    COUNTS = 'COUNTS'
    CHAIN = 'CHAIN'
    EVERY = 'EVERY'
    RANGE = 'RANGE'
    SOURCE = 'SOURCE'
    SPREAD = 'SPREAD'
    RHYTHM = 'RHYTHM'
    CHORDS = 'CHORDS'
    DIRECTION = 'DIRECTION'
    CELLS = 'CELLS'
    CELL = 'CELL'
    FROM = 'FROM'
    DEVICE = 'DEVICE'
    CHANNEL = 'CH'
    # Each list's first column says what choosing a row picks, where every list said NAME.
    SELECT_PATTERN = 'SELECT PATTERN'
    SELECT_SONG = 'SELECT SONG'
    SELECT_SCALE = 'SELECT SCALE'
    SELECT_CHAIN = 'SELECT CHAIN'
    SELECT_GROOVE = 'SELECT GROOVE'
    SELECT_INSTRUMENT = 'SELECT INSTRUMENT'
    SELECT_ANY_GENERATOR = 'SELECT GENERATOR'
    KIND = 'KIND'
    SELECT_CHAIN_LINKS = 'SELECT CHAIN LINKS (generators)'
    SELECT_FILE = 'SELECT FILE'
    # A generator page's first column, with the kind's name, like SELECT ARPEGGIATOR.


# tui/screens/set/file_page.py and tui/screens/set/song_page.py
# The File and Song pages' fields, and how they show what has no value.
MSG_GENRE_LABEL = 'Genre'
# When an edit made while the song plays is heard, the Song page's field and its choices.
MSG_LIVE_RESPONSIVENESS_LABEL = 'Live response'
MSG_PREVIEW_INSTRUMENT_LABEL = 'Preview instrument'
# What the Preview instrument field shows when the song names none: Listen plays a pattern through General MIDI's piano in FluidSynth.
MSG_PREVIEW_INSTRUMENT_UNSET = '(General MIDI piano)'
MSG_LIVE_RESPONSIVENESS_NAMES = {LiveResponsiveness.NEXT_BAR: 'next bar', LiveResponsiveness.CLIP_RESTART: 'clip restart', LiveResponsiveness.ASAP: 'ASAP'}
MSG_TITLE_LABEL = 'Title'
MSG_AUTHOR_LABEL = 'Author'
MSG_SEED_LABEL = 'Seed'
MSG_STEP_SIZE_LABEL = 'Step size'
MSG_DEFAULT_OCTAVE_LABEL = 'Default octave'
MSG_DEFAULT_DRUM_OCTAVE_LABEL = 'Default drum octave'
MSG_OCTAVE_LABELS_LABEL = 'Octave labels'
# tui/screens/set/visualizer_fields.py: the visualizer mode Arrange shows first, what none of a song's own is called, and the section that hides modes.
MSG_VISUALIZER_LABEL = 'Visualizer'
MSG_SETS_VISUALIZER_CHOICE = "(set's)"
# The File/Global page's sections.
MSG_NOTES_AND_OCTAVES_SECTION = 'Notes & Octaves'
MSG_VISUALIZERS_SECTION = 'Visualizers'
MSG_HIDE_VISUALIZERS_LABEL = 'Hide Visualizers'
MSG_PROTECTED_LABEL = 'Protected'
# How each choice of octave labels is shown, saying where middle C, MIDI note 60, falls in it.
MSG_OCTAVE_LABEL_NAMES = {OctaveLabels.LIVE: 'Live (middle C is C3)', OctaveLabels.LLAMATRON: 'llamatron (middle C is C5)'}
# The Description field is one line saying what the set is, like the tune it plays, typed in a prompt. The Notes field shows
# the notes' first line, or that there are none; ENTER opens the Notes page editing.
MSG_DESCRIPTION_LABEL = 'Description'
MSG_NOTES_LABEL = 'Notes'
MSG_EXPORT_CHOICES = ['Ableton Live set', 'MIDI (Stems)', 'MIDI (Single File)', 'MIDI (Clips)', 'MIDI (General MIDI)', 'WAV (FluidSynth)']

# tui/screens/arrange/track_editor.py
# The two buttons under the text while editing, which Tab reaches and Left and Right move between.
MSG_NOTES_BUTTONS = ('Save', 'CANCEL')
# The lists of named things.
MSG_DRUM_KIND = 'drum'
# tui/screens/pattern/patterns_page.py: a group's heading, the heading of the patterns in no group, the two buttons that add, and
# the entry of the Group picker that makes a group. A button has no +, so that + and - mean only closed and open.
MSG_GROUP_HEADING = '{mark} {name} ({count})'
MSG_UNGROUPED = 'Ungrouped'
MSG_NEW_PATTERN_BUTTON = '[ New Pattern ]'
MSG_NEW_GROUP_BUTTON = '[ New Pattern Group ]'
MSG_NEW_GROUP_NAME_LABEL = 'New Group Name: '
MSG_NOTES_KIND = 'notes'
MSG_ARP_LABEL = 'arpeggiator'
MSG_AUTO_RATCHET_LABEL = 'AutoRatchet'
MSG_DRIFT_LABEL = 'Drift'
# tui/screens/generators/drift_editor.py: its own fields, then each version's values, shown as A and B side by side.
MSG_EVERY_LABEL = 'Every'
MSG_STEPS_TO_B_LABEL = 'Steps to B'
MSG_DRIFT_DIRECTION_LABEL = 'Direction'
MSG_DRIFT_VALUE_LABELS = {
    DriftValue.AX_ADD: 'AX+=', DriftValue.BX_ADD: 'BX+=', DriftValue.CX_ADD: 'CX+=', DriftValue.DX_ADD: 'DX+=', DriftValue.VELOCITY: 'Vel+=',
    DriftValue.PROBABILITY: 'Prob \u00b1', DriftValue.DEGREE: 'Degree +', DriftValue.DEGREE_RANDOM: 'Degree random', DriftValue.SCALE: 'Scale',
    DriftValue.SCALE_PROBABILITY: 'Scale prob', DriftValue.ROOT: 'Root', DriftValue.ROOT_PROBABILITY: 'Root prob',
}
# A version row's two values, the one the cursor is on marked like the offsets editor's cursor.
MSG_DRIFT_PAIR = '{a:<10}{b}'
MSG_DRIFT_PICKED = '<{value}>'
# tui/screens/generators/shape_fields.py: each shape's name, which heads its section, and its parts' labels, the shape's name in front on the Scene and clip pages.
MSG_SHAPE_NAMES = {Shape.DENSITY: 'Density', Shape.SWELL: 'Swell', Shape.ARTICULATE: 'Articulate'}
MSG_SHAPE_FIELD_LABELS = {ShapePart.START: '{shape} start', ShapePart.END: '{shape} end', ShapePart.OVER: '{shape} over', ShapePart.THEN: '{shape} then'}
MSG_SHAPE_PART_LABELS = {ShapePart.START: 'Start', ShapePart.END: 'End', ShapePart.OVER: 'Over', ShapePart.THEN: 'Then'}
MSG_WHOLE_SPAN = '(whole)'
# tui/screens/generators/chords_editor.py: a progression's fields, and the chord editor's rows, which the progression editor shares.
MSG_PROGRESSION_LABEL = 'Progression'
# tui/screens/generators/voice_leading_editor.py: a voice leading's name in a prompt, and its toggle.
MSG_VOICE_LEADING_LABEL = 'Voice leading'
MSG_HOCKET_LABEL = 'Hocket'
# tui/screens/generators/guitarify_editor.py, tui/screens/generators/guitar_bar_editor.py: a Guitarify's name, its two sections, their fields, and what its choices are called.
MSG_GUITARIFY_LABEL = 'Guitarify'
MSG_GUITAR_SHAPE_SECTION = 'Shape'
MSG_GUITAR_STROKES_SECTION = 'Strokes'
MSG_GUITAR_SHAPE_LABEL = 'Shape chords'
MSG_GUITAR_TUNING_LABEL = 'Tuning'
MSG_GUITAR_POSITION_LABEL = 'Position'
MSG_GUITAR_CAPO_LABEL = 'Capo'
MSG_GUITAR_STRINGS_LABEL = 'Strings'
MSG_GUITAR_SINGLE_NOTES_LABEL = 'Single notes'
MSG_GUITAR_STROKES_LABEL = 'Play strokes'
MSG_GUITAR_BAR_LABEL = 'Bar'
MSG_GUITAR_LET_RING_LABEL = 'Let ring'
MSG_GUITAR_SPREAD_LABEL = 'Spread'
MSG_GUITAR_FADE_LABEL = 'Fade'
MSG_GUITAR_LOOSE_TIMING_LABEL = 'Loose timing'
MSG_GUITAR_UPSTROKE_LABEL = 'Upstroke strings'
MSG_GUITAR_TUNING_NAMES = {Tuning.STANDARD: 'standard', Tuning.DROP_D: 'drop D', Tuning.OPEN_G: 'open G', Tuning.OPEN_D: 'open D', Tuning.DADGAD: 'DADGAD'}
MSG_GUITAR_SINGLE_NOTES_NAMES = {
    SingleNotes.LEAVE: 'leave', SingleNotes.POWER_CHORD: 'power chord', SingleNotes.SCALE_CHORD: 'scale chord', SingleNotes.OCTAVE: 'octave',
    SingleNotes.THIRD_ABOVE: 'third above', SingleNotes.DOUBLE_STOP: 'double stop',
}
MSG_GUITAR_COLOR_LABEL = 'Color'
MSG_GUITAR_COLOR_NAMES = {ChordColor.AS_WRITTEN: 'as written', ChordColor.ADD_9: 'add 9', ChordColor.SUS_2: 'sus 2', ChordColor.SUS_4: 'sus 4', ChordColor.NO_THIRD: 'no third'}
MSG_GUITAR_APPROACH_LABEL = 'Approach'
MSG_GUITAR_APPROACH_NAMES = {Approach.OFF: 'off', Approach.FROM_BELOW: 'from below', Approach.FROM_ABOVE: 'from above'}
MSG_GUITAR_STROKE_NAMES = {
    Stroke.NOTHING: 'nothing', Stroke.DOWN: 'down', Stroke.UP: 'up', Stroke.MUTE: 'mute', Stroke.STAB: 'stab', Stroke.BASS: 'bass', Stroke.MUTED_BASS: 'muted bass',
    Stroke.ALT_BASS: 'alt bass', Stroke.SQUEAL: 'squeal',
    Stroke.STRING_1: 'string 1', Stroke.STRING_2: 'string 2', Stroke.STRING_3: 'string 3', Stroke.STRING_4: 'string 4',
}
MSG_READY_BAR_NAMES = {
    ReadyBar.FOLK_STRUM: 'folk strum', ReadyBar.BOOM_CHICK: 'boom-chick', ReadyBar.TRAVIS_PICK: 'travis pick', ReadyBar.CROSSPICK: 'crosspick',
    ReadyBar.FOUR_TO_THE_BAR: 'four to the bar', ReadyBar.BACKBEAT: 'backbeat', ReadyBar.BOOGIE: 'boogie', ReadyBar.SHUFFLE: 'shuffle', ReadyBar.SCRATCH: 'scratch',
    ReadyBar.ALL_DOWN: 'all down', ReadyBar.ARENA: 'arena', ReadyBar.CHUG: 'chug', ReadyBar.GALLOP: 'gallop', ReadyBar.THRASH: 'thrash', ReadyBar.TREMOLO: 'tremolo',
    ReadyBar.CHIME: 'chime', ReadyBar.ROLL_UP: 'roll up', ReadyBar.ROLL_DOWN: 'roll down', ReadyBar.HELD: 'held',
    ReadyBar.SKANK: 'skank', ReadyBar.DISCO: 'disco', ReadyBar.PEDAL_RIFF: 'pedal riff', ReadyBar.POWER_GROOVE: 'power groove',
    ReadyBar.FIVE_BEAT: 'five beat', ReadyBar.STRUM_AND_CLICK: 'strum and click', ReadyBar.SLOW_PICK: 'slow pick', ReadyBar.FOUR_STOMPS: 'four stomps',
}
MSG_OWN_BAR = 'custom'
MSG_STROKE_ROW_LABEL = 'Stroke'
MSG_ACCENT_ROW_LABEL = 'Accent'
MSG_READY_BARS_TITLE = 'Ready-made bar'
MSG_SOURCE_TRACK_LABEL = 'Source track'
MSG_ROOT_IN_BASS_LABEL = 'Keep the root in the bass'
# tui/screens/generators/strum_fields.py: a strum's section and its fields, Strum in front where the strum is one section among others, and what its choices are called.
MSG_STRUM_LABEL = 'Strum'
MSG_STRUM_FIELD_LABELS = {
    StrumPart.DIRECTION: 'Strum direction', StrumPart.SPREAD: 'Strum spread', StrumPart.FADE: 'Strum fade', StrumPart.LOOSE_TIMING: 'Strum loose timing',
    StrumPart.UPSTROKE_STRINGS: 'Strum upstrokes',
}
MSG_STRUM_PART_LABELS = {
    StrumPart.DIRECTION: 'Direction', StrumPart.SPREAD: 'Spread', StrumPart.FADE: 'Fade', StrumPart.LOOSE_TIMING: 'Loose timing',
    StrumPart.UPSTROKE_STRINGS: 'Upstroke strings',
}
MSG_STRUM_WORDS = {
    StrumDirection.BY_THE_BEAT: 'by the beat', StrumDirection.DOWN_UP: 'down up', UpstrokeStrings.TOP_3: 'top 3', UpstrokeStrings.TOP_4: 'top 4',
}
MSG_TRACK_STRUM_CHOICE = '(track)'
# tui/screens/generators/restart_field.py: when a generator starts over, as its editor names the choices.
MSG_RESTART_LABEL = 'Restart'
# tui/screens/generators/step_row_editor.py: a Glide's, a Shorten's, a Rush's and a Drag's names, fields and the row's labels.
MSG_GLIDE_LABEL = 'Glide'
MSG_SHORTEN_LABEL_NAME = 'Shorten'
MSG_RUSH_LABEL = 'Rush'
MSG_DRAG_LABEL = 'Drag'
MSG_GLIDE_AMOUNT_LABEL = 'Glide amount'
MSG_SHORTEN_LABEL = 'Shorten amount'
MSG_RUSH_AMOUNT_LABEL = 'Rush amount'
MSG_DRAG_AMOUNT_LABEL = 'Drag amount'
MSG_STEPS_LABEL = 'Steps'
MSG_STEP_ROW_LABEL = 'Step'
MSG_STEP_ROW_NAMES = {Section.GLIDES: 'Glide', Section.SHORTENS: 'Shorten', Section.RUSHES: 'Rush', Section.DRAGS: 'Drag'}
MSG_RESTART_NAMES = {Restart.EVERY_CLIP: 'every clip', Restart.ON_NEW_SCENE: 'on new scene', Restart.WHOLE_SONG: 'whole song'}
# tui/screens/generators/euclid_fields.py: a mask's section and fields, Euclid in front in a section, and the named rhythms the Hits field's H offers.
MSG_EUCLID_LABEL = 'Euclid'
MSG_EUCLID_FIELD_LABELS = {EuclidPart.HITS: 'Euclid hits', EuclidPart.STEPS: 'Euclid steps', EuclidPart.ROTATE: 'Euclid rotate', EuclidPart.STEP: 'Euclid step'}
MSG_EUCLID_PART_LABELS = {EuclidPart.HITS: 'Hits', EuclidPart.STEPS: 'Steps', EuclidPart.ROTATE: 'Rotate', EuclidPart.STEP: 'Step'}
MSG_RHYTHM_NAMES = {
    NamedRhythm.TRESILLO: 'tresillo, Cuba', NamedRhythm.CINQUILLO: 'cinquillo, Cuba', NamedRhythm.KHAFIF_E_RAMAL: 'khafif-e-ramal, Persia',
    NamedRhythm.AKSAK: 'aksak, Turkey', NamedRhythm.VENDA: 'Venda, South Africa', NamedRhythm.BEMBE: 'bembé, West Africa',
    NamedRhythm.SAMBA: 'samba, Brazil', NamedRhythm.BOSSA_NOVA: 'bossa nova, Brazil',
}
MSG_CHORDS_LABEL = 'Chords'
MSG_CHORD_ROW_LABEL = 'Chord'
MSG_NUMERAL_ROW_LABEL = 'Degree'
MSG_CHORD_NAME_ROW_LABEL = 'Name'
MSG_PROGRESSION_ACCIDENTAL_ROW_LABEL = '#/b'
MSG_INVERSION_ROW_LABEL = 'Inv.'
MSG_PROGRESSION_SCALE_ROW_LABEL = 'Scale'
MSG_PROGRESSION_QUALITY_ROW_LABEL = 'Quality'
MSG_PROGRESSION_TENSIONS_ROW_LABEL = 'Tens.'
# The named progressions H offers, by the key composition/progressions.py names each with, in two groups.
MSG_PROGRESSION_GROUPS = ['Pop and rock', 'Blues, jazz, folk and more']
MSG_PROGRESSION_NAMES = {
    NamedProgression.POP: 'Pop', NamedProgression.FIFTIES: 'Fifties', NamedProgression.SAD_POP: 'Sad pop', NamedProgression.EPIC: 'Epic', NamedProgression.HOPEFUL: 'Hopeful', NamedProgression.ROCK: 'Rock',
    NamedProgression.MIXOLYDIAN_ROCK: 'Mixolydian rock', NamedProgression.POWER_BALLAD: 'Power ballad', NamedProgression.GRUNGE: 'Grunge', NamedProgression.PUNK: 'Punk',
    NamedProgression.ROYAL_ROAD: 'Royal road', NamedProgression.HIP_HOP_LOOP: 'Hip hop loop', NamedProgression.TWELVE_BAR_BLUES: 'Twelve-bar blues',
    NamedProgression.QUICK_CHANGE_BLUES: 'Quick-change blues', NamedProgression.EIGHT_BAR_BLUES: 'Eight-bar blues', NamedProgression.JAZZ_TURNAROUND: 'Jazz turnaround',
    NamedProgression.LONG_TURNAROUND: 'Long turnaround', NamedProgression.CIRCLE_OF_FIFTHS: 'Circle of fifths', NamedProgression.RHYTHM_CHANGES: 'Rhythm changes',
    NamedProgression.FOLK: 'Folk, country', NamedProgression.GOSPEL: 'Gospel', NamedProgression.PACHELBEL: 'Pachelbel', NamedProgression.ANDALUSIAN: 'Andalusian', NamedProgression.MINOR: 'Minor',
}
# tui/screens/generators/time_field.py: what the list of times calls a dotted or triplet length, where its written fraction says nothing to a musician.
MSG_TIME_NAMES = {
    '1/24': '1/16 triplet', '3/32': 'dotted 1/16', '1/12': '1/8 triplet', '3/16': 'dotted 1/8', '1/6': '1/4 triplet',
}
MSG_ACCENT_LABEL = 'Accent'
# The track editor.
MSG_DRUM_LABEL = 'Drum'
MSG_MUTE_LABEL = 'Mute'
MSG_TRANSPOSE_LABEL = 'Transpose'
# The octaves the track's instrument plays, which the piano roll marks; Bksp goes back to the end of the MIDI range.
MSG_LOWEST_OCTAVE_LABEL = 'Lowest octave'
MSG_HIGHEST_OCTAVE_LABEL = 'Highest octave'
MSG_CC_LABEL = 'CC {number}'
# The track editor's register bindings: a CC lane's register, and the velocity's.
MSG_CC_REGISTER_LABEL = 'CC{number} Reg'
MSG_VELOCITY_REGISTER_LABEL = 'Vel Reg'
MSG_STEP_LABEL = 'Step'
MSG_ORDER_LABEL = 'Order'
MSG_OCTAVE_RANGE_LABEL = 'Octave range'
MSG_OCTAVE_JUMP_LABEL = 'Octave jump'
MSG_OFFSETS_LABEL = 'Offsets'
MSG_COUNTS_LABEL = 'Counts'
MSG_STEP_ROW_LABEL = ' Step'
MSG_OFFSET_ROW_LABEL = ' Offset'
# The offsets editor's rows of register adds, under the Offset row, and the arp editor's adds on every note.
MSG_STEP_ADD_ROW_LABEL = ' {name}+='
MSG_ARP_NOTE_ADD_LABEL = '{name}+= per note'

# tui/screens/set/scale_page.py
MSG_ROOT_LABEL = 'Root'
MSG_KIND_LABEL = 'Kind'
# Names to show where the full ones are too long to fit.
MSG_SHORT_SCALE_NAMES = {
    ScaleKind.WHOLE_HALF_DIMINISHED: 'whole half dim', ScaleKind.HALF_WHOLE_DIMINISHED: 'half whole dim',
    ScaleKind.LYDIAN_DOMINANT: 'lydian dom', ScaleKind.BEBOP_DOMINANT: 'bebop dom', ScaleKind.PHRYGIAN_DOMINANT: 'phrygian dom',
}

# tui/screens/pattern/pattern_editor.py, its two drawings and the rows in tui/components/
# How each register's rows are labelled: AX+Note moves the note by AX, AX+Vel adds AX to the
# velocity, and AX+= adds to AX.
MSG_REGISTER_NOTE_LABEL = '{name}+Note'
MSG_REGISTER_VELOCITY_LABEL = '{name}+Vel'
MSG_REGISTER_ADD_LABEL = '{name}+='
MSG_REGISTER_SET_LABEL = '{name}='
# A condition row is labelled by the two registers it compares, like AX,BX.
MSG_CONDITION_LABEL = 'AX,{name}'
# The rows on screen. Degree always shows, and the rest depend on the set of rows showing.
MSG_ROW_LABELS = {
    Row.DEGREE: 'Degree', Row.GATE: 'Gate', Row.DOT: 'Dot', Row.ACCIDENTAL: '#/b', Row.OCTAVE: 'Octave', Row.CHORD: 'Chord', Row.INVERSION: 'Inversion',
    Row.TENSION: 'Tension', Row.CHORD_SCALE: 'Scale',
    Row.VELOCITY: 'Velocity', Row.PROBABILITY: 'Probability', Row.GLIDE: 'Glide', Row.TIE: 'Tie', Row.RATCHET: 'Ratchet',
    Row.RATCHET_OFFSET: 'Ratchet Offset', Row.GRAB: 'Grab', Row.KEYSWITCH: 'Keyswitch',
    Row.CC1: 'CC 1', Row.CC2: 'CC 2', Row.CC3: 'CC 3', Row.CC4: 'CC 4', Row.SLIDE: 'Slide',
    **register_labels(rows=REGISTER_NOTE_ROWS, label=MSG_REGISTER_NOTE_LABEL),
    **register_labels(rows=REGISTER_VELOCITY_ROWS, label=MSG_REGISTER_VELOCITY_LABEL),
    **register_labels(rows=REGISTER_ADD_ROWS, label=MSG_REGISTER_ADD_LABEL),
    **register_labels(rows=REGISTER_SET_ROWS, label=MSG_REGISTER_SET_LABEL),
    **register_labels(rows=CONDITION_ROWS, label=MSG_CONDITION_LABEL),
}
# The sections of rows under Octave, each a row of the grid: its name after a mark saying whether it's closed (+) or open (-), chosen over triangles, which were hard to tell apart at a distance.
MSG_SECTION_NAMES = {
    RowSection.BASICS: 'Basics', RowSection.CHORD: 'Chord', RowSection.TIMING: 'Timing', RowSection.ADVANCED: 'Advanced', RowSection.CC: 'CCs',
    RowSection.REGISTER_MOD: 'Reg. Mod', RowSection.REGISTER_APPLY: 'Reg. Apply', RowSection.REGISTER_COND: 'Reg. Cond',
}
MSG_SECTION_LABEL = '{mark} {name}'
# What the second line of the header says while the cursor is in a section with something to explain, in place of the scale.
MSG_SECTION_HINTS = {
    RowSection.ADVANCED: "Advanced: Grab plays the Grab track's last note",
    RowSection.CC: "CCs: the track sets each row's CC number",
    RowSection.REGISTER_MOD: 'Reg. Mod: = sets, then += adds, even on an empty step',
    RowSection.REGISTER_APPLY: 'Reg. Apply: +Note and +Vel add (+) or subtract (-) a register',
    RowSection.REGISTER_COND: 'Reg. Cond: the note sounds only if every comparison holds',
}
MSG_SCALE_HEADER = 'Scale {scale}'
MSG_NO_SCALE_NEEDED = 'no scale needed'
MSG_SEVERAL_SCALES = 'Scale varies by scene'
# The first choice of the roll's entry size picker (E), before the step sizes: the pattern takes the song's entry size.
MSG_SONG_ENTRY_SIZE_CHOICE = "(the song's)"
# The piano roll's row labels: the note's name with its octave and the degree, or the octave alone when the scale isn't known.
MSG_ROLL_ROW_LABEL = '{note:<4} {degree}'
MSG_STEP_HEADING = ' Step'
# A CC row's label says the CC number the tracks playing the pattern send on that lane, off for a lane that sends nothing, or ? when the tracks differ.
MSG_CC_ROW_LABEL = '{label} ({number})'
MSG_DOT_NAMES = {GateModifier.DOTTED: ' dotted', GateModifier.TRIPLET: ' triplet'}
MSG_MUNGE_CHOICES = ['reverse after step', 'reverse before step', 'reverse', 'pivot around step', 'randomize']
# The clip page's extra choice, for a clip that follows its pattern's direction.
MSG_PATTERN_DIRECTION_OPTION = '(pattern)'
# What each chord symbol means, as the editor describes it.
MSG_CHORD_NAMES = {
    ChordSymbol.MAJOR: 'major', ChordSymbol.MINOR: 'minor', ChordSymbol.DIMINISHED: 'diminished',
    ChordSymbol.AUGMENTED: 'augmented', ChordSymbol.SUS2: 'suspended second', ChordSymbol.SUS4: 'suspended fourth',
    ChordSymbol.POWER: 'power, root and fifth', ChordSymbol.MAJOR6: 'major sixth', ChordSymbol.MINOR6: 'minor sixth',
    ChordSymbol.DOMINANT7: 'dominant seventh', ChordSymbol.MAJOR7: 'major seventh', ChordSymbol.MINOR7: 'minor seventh',
    ChordSymbol.MINOR_MAJOR7: 'minor-major seventh', ChordSymbol.DIMINISHED7: 'diminished seventh',
    ChordSymbol.HALF_DIMINISHED7: 'half-diminished', ChordSymbol.AUGMENTED7: 'augmented seventh',
    ChordSymbol.AUGMENTED_MAJOR7: 'augmented major seventh', ChordSymbol.DOMINANT7_SUS4: 'seventh, suspended fourth',
    ChordSymbol.ADD9: 'added ninth', ChordSymbol.MINOR_ADD9: 'minor added ninth',
    ChordSymbol.DOMINANT9: 'dominant ninth', ChordSymbol.MAJOR9: 'major ninth', ChordSymbol.MINOR9: 'minor ninth',
    ChordSymbol.DOMINANT11: 'dominant eleventh', ChordSymbol.MAJOR11: 'major eleventh', ChordSymbol.MINOR11: 'minor eleventh',
    ChordSymbol.DOMINANT13: 'dominant thirteenth', ChordSymbol.MAJOR13: 'major thirteenth', ChordSymbol.MINOR13: 'minor thirteenth',
    ChordSymbol.SCALE_FIFTH: 'root and fifth from the scale', ChordSymbol.SCALE_TRIAD: 'triad from the scale',
    ChordSymbol.SCALE_SEVENTH: 'seventh from the scale', ChordSymbol.SCALE_NINTH: 'ninth from the scale',
    ChordSymbol.SCALE_ELEVENTH: 'eleventh from the scale', ChordSymbol.SCALE_THIRTEENTH: 'thirteenth from the scale',
}

# tui/screens/set/registers_page.py
# Each register's settings on the page, labelled like "AX minimum", in the order they're shown.
# The Registers page's columns, in the grid's order.
MSG_REGISTER_COLUMNS = ('Inc max', 'At limit', 'Minimum', 'Default', 'Maximum', 'Reset')
MSG_REGISTER_FIELD_LABEL = '{name} {what}'
MSG_REGISTER_NUMBER_FIELDS = [(RegisterSetting.DEFAULT, 'default'), (RegisterSetting.MINIMUM, 'minimum'), (RegisterSetting.MAXIMUM, 'maximum')]
MSG_REGISTER_AT_LIMIT_FIELD = 'at limit'
MSG_REGISTER_RESET_EACH_SCENE_FIELD = 'reset each scene'
MSG_REGISTER_ALLOWED_INC_MAX_FIELD = 'allowed inc max'
# What the At limit field calls each choice, in the order the choices step.
MSG_AT_LIMIT_NAMES = {
    AtLimit.STOP: 'stop', AtLimit.RESET: 'reset', AtLimit.OVERFLOW: 'overflow', AtLimit.OVERFLOW_RIGHT: 'overflow right',
    AtLimit.OVERFLOW_LEFT: 'overflow left', AtLimit.PICK_RANDOM: 'pick random',
}

# tui/screens/set/groove_editor.py
MSG_CELL_ROW_LABEL = ' Cell'
MSG_AMOUNT_ROW_LABEL = ' Amount'

# tui/screens/arrange/groove_choice.py: the Groove field on the Song, Scene and Track pages
MSG_GROOVE_LABEL = 'Groove'
MSG_GROOVE_OFF_OPTION = '(off: no groove here, whatever else chooses one)'

# tui/screens/set/scale_page.py: the scale picker's two pages, and the headings of the groups of scales on them
# tui/scale_categories.py: the categories of scale type the Chord dialog lists, each opening a flyout.
MSG_SCALE_CATEGORY_COMMON = 'Common'
MSG_SCALE_CATEGORY_MODES = 'Modes'
MSG_SCALE_CATEGORY_HARMONIC_AND_MELODIC = 'Harmonic & Melodic'
MSG_SCALE_CATEGORY_PENTATONIC_AND_BLUES = 'Pentatonic & Blues'
MSG_SCALE_CATEGORY_SYMMETRIC = 'Symmetric'
MSG_SCALE_CATEGORY_JAZZ = 'Jazz'
MSG_SCALE_CATEGORY_MIDDLE_EAST_AND_EUROPE = 'Mid. East & Europe'
MSG_SCALE_CATEGORY_EAST_ASIA = 'East Asia'
MSG_SCALE_CATEGORY_INDIA = 'India'
MSG_SCALE_PAGE_COMMON = 'COMMON'
MSG_SCALE_PAGE_JAZZ_AND_WORLD = 'JAZZ & WORLD'
MSG_SCALE_GROUP_MODES = 'MODES'
MSG_SCALE_GROUP_MINOR_AND_MAJOR = 'MINOR & MAJOR'
MSG_SCALE_GROUP_SYMMETRIC = 'SYMMETRIC'
MSG_SCALE_GROUP_PENTATONIC_AND_BLUES = 'PENTATONIC & BLUES'
MSG_SCALE_GROUP_MELODIC_MINOR = 'MELODIC MINOR'
MSG_SCALE_GROUP_JAZZ = 'JAZZ'
MSG_SCALE_GROUP_MIDDLE_EAST_AND_EUROPE = 'MIDDLE EAST & EUROPE'
MSG_SCALE_GROUP_EAST_ASIA = 'EAST ASIA'
MSG_SCALE_GROUP_INDIA = 'INDIA'

# tui/screens/set/instrument_editor.py: General MIDI's 128 sounds, numbered from 1 in this order, and its 16 families of eight.
MSG_GM_SOUNDS = [
    'Acoustic Grand Piano',
    'Bright Acoustic Piano',
    'Electric Grand Piano',
    'Honky-tonk Piano',
    'Electric Piano 1',
    'Electric Piano 2',
    'Harpsichord',
    'Clavinet',
    'Celesta',
    'Glockenspiel',
    'Music Box',
    'Vibraphone',
    'Marimba',
    'Xylophone',
    'Tubular Bells',
    'Dulcimer',
    'Drawbar Organ',
    'Percussive Organ',
    'Rock Organ',
    'Church Organ',
    'Reed Organ',
    'Accordion',
    'Harmonica',
    'Tango Accordion',
    'Acoustic Guitar (nylon)',
    'Acoustic Guitar (steel)',
    'Electric Guitar (jazz)',
    'Electric Guitar (clean)',
    'Electric Guitar (muted)',
    'Overdriven Guitar',
    'Distortion Guitar',
    'Guitar Harmonics',
    'Acoustic Bass',
    'Electric Bass (finger)',
    'Electric Bass (pick)',
    'Fretless Bass',
    'Slap Bass 1',
    'Slap Bass 2',
    'Synth Bass 1',
    'Synth Bass 2',
    'Violin',
    'Viola',
    'Cello',
    'Contrabass',
    'Tremolo Strings',
    'Pizzicato Strings',
    'Orchestral Harp',
    'Timpani',
    'String Ensemble 1',
    'String Ensemble 2',
    'Synth Strings 1',
    'Synth Strings 2',
    'Choir Aahs',
    'Voice Oohs',
    'Synth Voice',
    'Orchestra Hit',
    'Trumpet',
    'Trombone',
    'Tuba',
    'Muted Trumpet',
    'French Horn',
    'Brass Section',
    'Synth Brass 1',
    'Synth Brass 2',
    'Soprano Sax',
    'Alto Sax',
    'Tenor Sax',
    'Baritone Sax',
    'Oboe',
    'English Horn',
    'Bassoon',
    'Clarinet',
    'Piccolo',
    'Flute',
    'Recorder',
    'Pan Flute',
    'Blown Bottle',
    'Shakuhachi',
    'Whistle',
    'Ocarina',
    'Lead 1 (square)',
    'Lead 2 (sawtooth)',
    'Lead 3 (calliope)',
    'Lead 4 (chiff)',
    'Lead 5 (charang)',
    'Lead 6 (voice)',
    'Lead 7 (fifths)',
    'Lead 8 (bass and lead)',
    'Pad 1 (new age)',
    'Pad 2 (warm)',
    'Pad 3 (polysynth)',
    'Pad 4 (choir)',
    'Pad 5 (bowed)',
    'Pad 6 (metallic)',
    'Pad 7 (halo)',
    'Pad 8 (sweep)',
    'FX 1 (rain)',
    'FX 2 (soundtrack)',
    'FX 3 (crystal)',
    'FX 4 (atmosphere)',
    'FX 5 (brightness)',
    'FX 6 (goblins)',
    'FX 7 (echoes)',
    'FX 8 (sci-fi)',
    'Sitar',
    'Banjo',
    'Shamisen',
    'Koto',
    'Kalimba',
    'Bagpipe',
    'Fiddle',
    'Shanai',
    'Tinkle Bell',
    'Agogo',
    'Steel Drums',
    'Woodblock',
    'Taiko Drum',
    'Melodic Tom',
    'Synth Drum',
    'Reverse Cymbal',
    'Guitar Fret Noise',
    'Breath Noise',
    'Seashore',
    'Bird Tweet',
    'Telephone Ring',
    'Helicopter',
    'Applause',
    'Gunshot',
]
MSG_GM_FAMILIES = [
    'Piano',
    'Chromatic Percussion',
    'Organ',
    'Guitar',
    'Bass',
    'Strings',
    'Ensemble',
    'Brass',
    'Reed',
    'Pipe',
    'Synth Lead',
    'Synth Pad',
    'Synth Effects',
    'Ethnic',
    'Percussive',
    'Sound Effects',
]
MSG_GM_SOUND_LABEL = 'GM sound'
MSG_KEYSWITCH_MAP_LABEL = 'Keyswitch Map'
MSG_KEYSWITCH_LEAD_LABEL = 'Keyswitch lead'
MSG_GM_SOUND_SHOWN = '{number} {name}'

# tui/screens/wizard/wizard_page.py and the branches beside it
MSG_WIZARD_CAPTION = 'NEW SONG WIZARD: {name}'
MSG_WIZARD_REPLACE_CAPTION = 'SONG WIZARD, REPLACING: {name}'
MSG_WIZARD_START_TITLE = 'Song Wizard'
# The four ways a run starts when the current song was made by the wizard, by the constants of tui/screens/wizard/starts.py.
MSG_WIZARD_START_NAMES = {
    'new from last': 'New song, from last settings',
    'new from scratch': 'New song, from scratch',
    'replace from last': 'Replace song, from last settings',
    'replace from scratch': 'Replace song, from scratch',
}
MSG_WIZARD_METER_LABEL = 'Meter'
MSG_WIZARD_BAND_BRANCH = 'Band'
MSG_WIZARD_SOUNDS_LABEL = 'Sounds'
MSG_WIZARD_DRUM_FILLS_LABEL = 'Fills come'
MSG_WIZARD_QUIET_NOTES_LABEL = 'Quiet notes'
MSG_WIZARD_FILLS_COME = ['never', 'each section', 'every 4 bars', 'every 2 bars']
MSG_WIZARD_KIT_PIECE = 'kit: {piece}'
MSG_WIZARD_GUITARISTS_LABEL = 'Guitarists'
# Who has the tune and who answers, the answering player's role, a section's own, and how busy the fills are.
MSG_WIZARD_TUNE_LABEL = 'Tune'
MSG_WIZARD_ANSWERED_BY_LABEL = 'Answered by'
MSG_WIZARD_NOBODY = '(nobody)'
MSG_WIZARD_ROLE_LABEL = 'Role'
MSG_WIZARD_BY_SECTION = 'by section'
MSG_WIZARD_SECTION_ROLE_LABEL = '{player} role'
MSG_WIZARD_FROM_PLAN = '(from plan)'
MSG_WIZARD_FILLS_BUSY_LABEL = 'Fills busy'
MSG_WIZARD_SOUND_LABEL = 'Sound'
MSG_WIZARD_SOUND_TITLE = 'Sound: {player}'
MSG_WIZARD_MORE_SOUNDS = '[ More sounds ]'
MSG_WIZARD_MORE_SOUNDS_TITLE = 'More sounds'
MSG_WIZARD_COMPOSITION_BRANCH = 'Composition'
MSG_WIZARD_CHORDS_BRANCH = 'Chords'
MSG_WIZARD_MELODY_BRANCH = 'Melody'
MSG_WIZARD_HOOKS_BRANCH = 'Hooks'
MSG_WIZARD_HOOK_ON = 'on'
MSG_WIZARD_HOOK_OFF = 'off'
MSG_WIZARD_PROGRESSION_LABEL = 'Progression'
MSG_WIZARD_MELODY_LABEL = 'Melody'
MSG_WIZARD_HOOK_LABEL = 'Hook'
# The song plan's fields on the Form panel, the parts of a hook's kind on the Hooks panel, and a value the wizard picked itself.
MSG_WIZARD_SONG_PLAN_LABEL = 'Song plan'
MSG_WIZARD_CONTRAST_LABEL = 'Contrast'
MSG_WIZARD_PHRASING_LABEL = 'Phrasing'
MSG_WIZARD_HOOK_PART_LABELS = {'contour': 'Contour', 'rhythm': 'Rhythm', 'detail': 'Detail'}
MSG_WIZARD_PICK = "(wizard's pick)"
# What a section of a planned song can be given of its own, and where each comes from until it is.
MSG_WIZARD_SECTION_OWN_LABELS = {'energy': 'Energy', 'leaves': 'Leaves with', 'setup': 'Setup', 'chords': 'Chords', 'tempo': 'Tempo', 'tempo_end': 'Tempo at end', 'root': 'Key', 'type': 'Scale'}
MSG_WIZARD_SECTION_ORIGINS = {'energy': 'from plan', 'leaves': 'from plan', 'setup': 'from plan', 'chords': 'from progression', 'tempo': 'from song', 'tempo_end': 'from song', 'root': 'from song', 'type': 'from song'}
MSG_WIZARD_VALUE_FROM = '{value} ({origin})'
MSG_WIZARD_FROM_ORIGIN = '({origin})'
MSG_WIZARD_PICK_SHOWN = "{value} (wizard's pick)"
MSG_WIZARD_PLAN_LINE = '{number:>2}  {name:<{width}}  {said}'
MSG_WIZARD_FILLS_LABEL = 'Fill pattern'
MSG_WIZARD_USUAL_MELODY = 'from genre'
# The smart melody style's gauges, each by its name in the melody engine: the field's label, then what its two ends mean.
MSG_WIZARD_GAUGE_LABELS = {'moves': 'Moves', 'steps': 'Steps', 'after_leap': 'After leap', 'phrase': 'Phrase', 'leaning': 'Leaning', 'notes': 'Notes', 'surprise': 'Surprise'}
MSG_WIZARD_GAUGE_ENDS = {'moves': ('steps', 'leaps'), 'steps': ('fall', 'rise'), 'after_leap': ('return', 'carry on'), 'phrase': ('flat', 'arched'),
                         'leaning': ('resolved', 'left hanging'), 'notes': ('long', 'short'), 'surprise': ('expected', 'surprising')}
# A melody style's own settings, under the Melody field while the style is in use.
MSG_WIZARD_MELODY_SETTING_LABELS = {'chromatic': 'All 12 notes', 'leaps': 'Leaps', 'rotations': 'Rotations', 'move': 'Moves up', 'rotate': 'Starts later'}
MSG_WIZARD_BREAK_LABEL = 'Break'
# A kit piece's own sound and the note it plays in a General MIDI sound, and the group of the kit's drums in the picker.
MSG_WIZARD_PIECE_SOUND_TITLE = 'Sound of {piece}'
MSG_WIZARD_KIT_DRUMS = 'Kit drums'
MSG_WIZARD_NO_BREAK = '(none)'
MSG_WIZARD_BREAK_CUT_LABEL = 'Cut up'
MSG_WIZARD_ANY_PROGRESSION = 'any'
MSG_WIZARD_KIND_LABEL = 'Kind'
MSG_WIZARD_ADD_SECTION_TITLE = 'Add section'
MSG_WIZARD_INSERT_SECTION_TITLE = 'Insert section'
MSG_WIZARD_SUGGESTED_FORM_BUTTON = 'Use a suggested form'
MSG_WIZARD_NEW_HOOK_BUTTON = 'New hook'
MSG_WIZARD_ROW_LABELS = {'lengths': 'Lengths', 'loudness': 'Loudness', 'articulation': 'Articulation'}
MSG_WIZARD_SUGGESTED_FORM_TITLE = 'Suggested forms'
MSG_WIZARD_REPLACE_SECTIONS_TITLE = 'Replace sections'
MSG_WIZARD_BUSY_LABEL = 'Busy'
# A player's own gauges, under the Busy field, which is a preset of them all.
MSG_WIZARD_PLAYER_GAUGE_LABELS = {'notes': 'Notes', 'variety': 'Variety', 'touch': 'Touch', 'timing': 'Loose timing', 'fills': 'Fill size', 'strumming': 'Strumming', 'range': 'Range'}
MSG_WIZARD_LENGTH_LABEL = 'Length'
# The last row of the dialog that asks how to start.
MSG_WIZARD_START_CANCEL = 'CANCEL'
MSG_WIZARD_GENRE_BRANCH = 'Genre'
MSG_WIZARD_FORM_BRANCH = 'Form'
MSG_WIZARD_CREATE_BRANCH = 'Apply'
MSG_WIZARD_SUBGENRE_LABEL = 'Subgenre'
MSG_WIZARD_KEY_LABEL = 'Key'
MSG_WIZARD_FORM_LABEL = 'Form'
MSG_WIZARD_SONG_LABEL = 'Song'
MSG_WIZARD_BARS_LABEL = 'Bars'
MSG_WIZARD_PLAYS_LABEL = 'Plays'
MSG_WIZARD_CREATE_BUTTON = 'Apply'
MSG_WIZARD_SCALE_TYPE_NAMES = {'major': 'Major', 'minor': 'Minor'}
