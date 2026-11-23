# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The names of things on screen: page names, field labels, column headings, crumbs, row labels and a picker's choices.

Each constant starts with MSG_, and the classes Crumb and Column group the words many pages share.
"""

from llamatron.interface.tracker.keys import RowSection
from llamatron.model.schema.file_format import Approach, ChordColor, ChordSymbol, Direction, DRAW_NOTE_ROWS, DRAW_RESET_ROWS, DRAW_VELOCITY_ROWS, DriftValue, FollowAction, GateModifier, LiveResponsiveness, NamedProgression, OctaveLabels, PatternOrder, RampPart, RampWay, ReadyBar, Restart, Row, ScaleKind, Section, Shape, ShapePart, SingleNotes, STATEMENT_ROWS, Stroke, Tuning


def draw_labels(*, rows, label):
    """Return each draw's row in a group of draw rows with its label, like ad_note with Note+=AD."""
    return {row: label.format(name=name) for name, row in rows.items()}



# interface/tracker/dialogs/quit_dialog.py
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

# interface/pages/statements.py: Bypass When, the table of statements about the draws
MSG_BYPASS_WHEN_LABEL = 'Bypass When'
MSG_STATEMENT_IGNORED = 'ignored'
MSG_STATEMENT_REGISTER_TITLE = 'Draw'
MSG_STATEMENT_OPERATOR_TITLE = 'Operator'
MSG_STATEMENT_VALUE_TITLE = 'Value'
MSG_STATEMENT_COMPARISON_TITLE = 'Comparison'
MSG_STATEMENT_NUMBER_CHOICE = 'number'
# A statement's line has no name of its own: its label is blank, and as long as its place on the page, which tells the lines apart.
MSG_STATEMENT_LINE_LABEL = ' '

# interface/tracker/screens/arrange/arrange_page.py
# A scene's or a clip's field for each draw it can start over, like "Reset AD".
MSG_RESET_LABEL = 'Reset {name}'
MSG_SONG_OPTION = '(song)'
MSG_SCENE_OPTION = 'from scene'
MSG_NAME_LABEL = 'Name'
MSG_SCALE_LABEL = 'Scale'
MSG_TEMPO_LABEL = 'Tempo'
MSG_TIME_SIGNATURE_LABEL = 'Time signature'
# How long a note placed on the piano roll lasts, unless the pattern says otherwise: blank is one step.
MSG_ENTRY_SIZE_LABEL = 'Entry size'
# A ramp's column, on the Velocity tab and the Tempo Ramps tab, which say what ramps, and its fields as the column shows them.
MSG_RAMP_HEADINGS = {RampWay.IN: 'Ramp In', RampWay.OUT: 'Ramp Out'}
MSG_RAMP_PART_LABELS = {RampPart.START: 'Start', RampPart.END: 'End', RampPart.OVER: 'Over'}
MSG_TEMPO_RAMP_LABELS = {
    (RampWay.IN, RampPart.START): 'Tempo in start', (RampWay.IN, RampPart.END): 'Tempo in end', (RampWay.IN, RampPart.OVER): 'Tempo in over',
    (RampWay.OUT, RampPart.START): 'Tempo out start', (RampWay.OUT, RampPart.END): 'Tempo out end', (RampWay.OUT, RampPart.OVER): 'Tempo out over',
}
# How loud a scene or a clip plays, and its ramps in and out, on the Scene page and the clip page (velocity_fields.py).
MSG_VELOCITY_PERCENT_LABEL = 'Velocity'
MSG_VELOCITY_RAMP_LABELS = {
    (RampWay.IN, RampPart.START): 'Velocity in start', (RampWay.IN, RampPart.END): 'Velocity in end', (RampWay.IN, RampPart.OVER): 'Velocity in over',
    (RampWay.OUT, RampPart.START): 'Velocity out start', (RampWay.OUT, RampPart.END): 'Velocity out end', (RampWay.OUT, RampPart.OVER): 'Velocity out over',
}
MSG_REPEAT_LABEL = 'Repeat'
MSG_PATTERNS_LABEL = 'Patterns'
MSG_PATTERN_ORDER_LABEL = 'Pattern order'
MSG_ADD_PATTERN_TITLE = 'Add Pattern'
MSG_ADD_PATTERN_CHOICES = ['Choose an existing pattern', 'New pattern']
# What the clip page calls each order a clip plays its patterns in, in the order of PATTERN_ORDERS.
MSG_PATTERN_ORDER_NAMES = {
    PatternOrder.FORWARD: 'forward',
    PatternOrder.REVERSE_A: 'reverse a',
    PatternOrder.REVERSE_B: 'reverse b',
    PatternOrder.ALTERNATE: 'alternate',
    PatternOrder.PENDULUM: 'pendulum',
    PatternOrder.RANDOM: 'random',
    PatternOrder.FIRST_THEN_RANDOM: 'first, then random',
}
MSG_PATTERN_LABEL = 'Pattern'
MSG_LOOP_LABEL = 'Loop'
MSG_DIRECTION_LABEL = 'Step direction'
MSG_MORPH_TO_LABEL = 'Morph to'
MSG_MORPH_DIRECTION_LABEL = 'Morph direction'
MSG_GRAB_TRACK_LABEL = 'Grab track'

# interface/tracker/screens/set/instrument_editor.py and interface/tracker/screens/arrange/track_editor.py
MSG_DEVICE_LABEL = 'Device'
MSG_CHANNEL_LABEL = 'Channel'
MSG_INSTRUMENT_LABEL = 'Instrument'
# The Listen button of the clip page and the song wizard's panels, and what the clip page's says while the clip plays.
MSG_LISTEN_LABEL = 'Listen'
MSG_STOP_LISTENING_LABEL = 'Stop'
# What a clip does in real-time playback when its scene is done, which no export reads, and the set's default for it.
MSG_FOLLOW_ACTION_LABEL = 'Follow action'
MSG_DEFAULT_FOLLOW_ACTION_LABEL = 'Default follow action'
MSG_FOLLOW_ACTION_NAMES = {FollowAction.WITH_SCENE: 'With Scene', FollowAction.NEXT: 'Next', FollowAction.OFF: 'Off'}
MSG_LAUNCH_TOGETHER_LABEL = 'Launch together'
MSG_SCENE_SECTION_LABEL = 'Section'

# interface/tracker/screens/shared/page.py and interface/tracker/key_table.py: the key names, the labels and the words every page shares
# The file crumb, right after the title on every page: the file's name, or this before the set is saved.
MSG_NO_FILE_CRUMB = '(unsaved)'
# The file crumb carries the current song too: minimal_techno.yml, song: minimal techno.
# The theme's stripe on a page that edits one thing: what it edits and its name.
MSG_EDITING_CAPTION = 'EDITING {what}: {name}'
MSG_CAPTION_WORDS = {
    Section.SONGS: 'song', Section.PATTERNS: 'pattern', Section.CHAINS: 'chain', Section.SCALES: 'scale', Section.GROOVES: 'groove',
    Section.INSTRUMENTS: 'instrument', Section.TRACKS: 'track',
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
    WIZARD = 'Wizard'
    PATTERNS = 'Patterns'
    GENERATORS = 'Generators'
    SCALES = 'Scales'
    GROOVES = 'Grooves'
    INSTRUMENTS = 'Instruments'
    DRAWS = 'Draws'
    ARRANGE = 'Arrange'
    # What the main screen's Arrange cell is called while the set's Real Time switch is on, since Arrange then plays the song too.
    # The main screen's switch for real-time playback, beside the pages: a cell with a mark in place of a count.
    REAL_TIME = 'Real Time'
    SAVE = 'Save'
    OPEN = 'Open'
    EXPORT = 'Export'
    IMPORT = 'Load MIDI'
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
    GENERATORS = 'GENERATORS'
    CHORDS = 'CHORDS'
    VOICE_LEADING = 'VOICE LEADING'
    STEPS = 'STEPS'
    STROKES = 'STROKES'
    OFFSETS = 'OFFSETS'
    STATEMENTS = 'BYPASS WHEN'
    SCALES = 'SCALES'
    GROOVES = 'GROOVES'
    INSTRUMENTS = 'INSTRUMENTS'
    DRAWS = 'DRAWS'
    ARRANGE = 'ARRANGE'


# interface/tracker/document.py
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
    # interface/tracker/dialogs/keyswitch_map_dialog.py: the note each slot sends.
    NOTE = 'NOTE'
    TYPE = 'TYPE'
    # interface/tracker/dialogs/chord_dialog.py: the Chord dialog's four lists.
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
    SELECT_FILE = 'SELECT FILE'
    # A generator page's first column, with the kind's name, like SELECT ARPEGGIATOR.


# interface/tracker/screens/set/file_page.py and interface/tracker/screens/set/song_page.py
# The File and Song pages' fields, and how they show what has no value.
MSG_GENRE_LABEL = 'Genre'
MSG_SUBGENRE_LABEL = 'Subgenre'
MSG_VARIANT_LABEL = 'Variant'
# When an edit made while the song plays is heard, the Song page's field and its choices.
MSG_LIVE_RESPONSIVENESS_LABEL = 'Live response'
MSG_PREVIEW_INSTRUMENT_LABEL = 'Preview instrument'
# What the Preview instrument field shows when the song names none: Listen plays a pattern through General MIDI's piano in FluidSynth.
MSG_PREVIEW_INSTRUMENT_UNSET = '(General MIDI piano)'
MSG_LIVE_RESPONSIVENESS_NAMES = {LiveResponsiveness.NEXT_BAR: 'next bar', LiveResponsiveness.CLIP_RESTART: 'clip restart', LiveResponsiveness.ASAP: 'ASAP'}
MSG_TITLE_LABEL = 'Title'
MSG_AUTHOR_LABEL = 'Author'
MSG_STEP_SIZE_LABEL = 'Step size'
MSG_DEFAULT_OCTAVE_LABEL = 'Default octave'
MSG_DEFAULT_DRUM_OCTAVE_LABEL = 'Default drum octave'
MSG_OCTAVE_LABELS_LABEL = 'Octave labels'
# interface/tracker/screens/set/visualizer_fields.py: the visualizer mode Arrange shows first, what none of a song's own is called, and the section that hides modes.
MSG_VISUALIZER_LABEL = 'Visualizer'
MSG_SETS_VISUALIZER_CHOICE = 'from set'
# The File/Global page's tabs, after its first, MSG_SETTINGS_TAB, and its buttons beside Save and Open.
MSG_NEW_SET_BUTTON = 'New'
MSG_SAVE_AS_BUTTON = 'Save As'
MSG_NOTES_AND_OCTAVES_TAB = 'Notes & Octaves'
MSG_VISUALIZERS_TAB = 'Visualizers'
MSG_HIDE_VISUALIZERS_LABEL = 'Hide Visualizers'
MSG_PROTECTED_LABEL = 'Protected'
# How each choice of octave labels is shown, saying where middle C, MIDI note 60, falls in it.
MSG_OCTAVE_LABEL_NAMES = {OctaveLabels.LIVE: 'Live (middle C is C3)', OctaveLabels.LLAMATRON: 'llamatron (middle C is C5)'}
# The Description field is one line saying what the set is, like the tune it plays, typed in a prompt. The Notes field shows
# the notes' first line, or that there are none; ENTER opens the Notes page editing.
MSG_DESCRIPTION_LABEL = 'Description'
MSG_NOTES_LABEL = 'Notes'
MSG_EXPORT_CHOICES = ['Ableton Live set', 'MIDI (Stems)', 'MIDI (Multitrack)', 'MIDI (Clips)', 'MIDI (General MIDI)', 'WAV (FluidSynth)']

# interface/tracker/screens/arrange/track_editor.py
# The two buttons under the text while editing, which Tab reaches and Left and Right move between.
MSG_NOTES_BUTTONS = ('Save', 'CANCEL')
# The lists of named things.
MSG_DRUM_KIND = 'drum'
# interface/tracker/screens/generators/generators_page.py: a type's heading.
MSG_GROUP_HEADING = '{mark} {name} ({count})'
# interface/tracker/screens/pattern/patterns_page.py: the tab of the patterns in no group, the last tab, which makes a group, its
# button, also the entry of the Group picker that makes a group, and the prompt for a copied group's name.
MSG_UNGROUPED = 'Ungrouped'
MSG_NEW_GROUP_TAB = '+ New'
# interface/tracker/dialogs/new_pattern_dialog.py: its two rows and its buttons; the Scale length is also a choice of the pattern editor's Reconfigure.
MSG_SCALE_LENGTH_LABEL = 'Scale length'
MSG_DRUM_PATTERN_LABEL = 'Drum pattern'
MSG_NEW_PATTERN_BUTTONS = ('OK', 'CANCEL')
MSG_NEW_GROUP_BUTTON = '[ New Pattern Group ]'
MSG_NOTES_KIND = 'notes'
# interface/tracker/screens/generators/generator_pages.py: a chain, as the Generators page lists it beside the kinds of generator.
MSG_CHAIN_LABEL = 'Chain'
# interface/pages/drift_values.py and the Drift's view: its own fields, then each value's two versions, A and B side by side.
MSG_EVERY_LABEL = 'Every'
MSG_STEPS_TO_B_LABEL = 'Steps to B'
MSG_DRIFT_DIRECTION_LABEL = 'Direction'
MSG_DRIFT_VALUE_LABELS = {
    DriftValue.VELOCITY: 'Vel+=',
    DriftValue.PROBABILITY: 'Prob \u00b1', DriftValue.DEGREE: 'Degree +', DriftValue.DEGREE_RANDOM: 'Degree random', DriftValue.SCALE: 'Scale',
    DriftValue.SCALE_PROBABILITY: 'Scale prob', DriftValue.ROOT: 'Root', DriftValue.ROOT_PROBABILITY: 'Root prob',
}
# A version row's two values, the one the cursor is on marked like the offsets editor's cursor.
# interface/pages/shape_fields.py: each shape's name, which heads its section, and its parts' labels, the shape's name in front on the Scene and clip pages.
MSG_SHAPE_NAMES = {Shape.DENSITY: 'Density', Shape.SWELL: 'Swell', Shape.ARTICULATE: 'Articulate'}
MSG_SHAPE_FIELD_LABELS = {ShapePart.START: '{shape} start', ShapePart.END: '{shape} end', ShapePart.OVER: '{shape} over', ShapePart.THEN: '{shape} then'}
MSG_SHAPE_PART_LABELS = {ShapePart.START: 'Start', ShapePart.END: 'End', ShapePart.OVER: 'Over', ShapePart.THEN: 'Then'}
MSG_WHOLE_SPAN = '(whole)'
MSG_CHORDS_FROM_LABEL = 'Chords from'
MSG_MUSICIAN_INSTRUMENT_LABEL = 'Instrument'
MSG_TUNE_FROM_LABEL = 'Tune from'
MSG_MUSICIAN_ACTIVITY_LABEL = 'Activity'
MSG_MUSICIAN_LOUDNESS_LABEL = 'Loudness'
MSG_MUSICIAN_LOOSENESS_LABEL = 'Looseness'
MSG_MUSICIAN_GIVES_WAY_LABEL = 'Gives way'
MSG_MUSICIAN_ACCENTS_LABEL = 'Accents'
MSG_MUSICIAN_NOTES_LABEL = 'Notes'
MSG_MUSICIAN_RANGE_LABEL = 'Range'
MSG_MUSICIAN_PLAYS_LABEL = 'Plays'
MSG_MUSICIAN_PLAYED_LABEL = 'Played'
MSG_MUSICIAN_INSTRUMENT_CHOICE = '(instrument)'
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
# interface/forms/tab_box.py: the row of tabs, as the cursor finds it.
MSG_TABS_LABEL = 'Tabs'
# interface/tracker/screens/arrange/clip_page.py, the track's and scene's pages and the File/Global page: their tabs, and the Settings tab's columns.
MSG_SETTINGS_TAB = 'Settings'
MSG_USER_TAB = 'More Generators'
MSG_SHAPES_TAB = 'Shapes'
MSG_VELOCITY_TAB = 'Velocity'
MSG_BYPASS_WHEN_TAB = 'Bypass When'
MSG_ORDER_HEADING = 'Order'
MSG_NOTES_HEADING = 'Notes'
MSG_PLAYING_HEADING = 'Playing'
MSG_RESET_DRAWS_TAB = 'Reset Draws'
# interface/pages/built_in_tab.py: the button that opens a built-in generator's statements, with how many it holds.
MSG_BYPASS_WHEN_BUTTON = 'Bypass When ({count})'
# What the Reset Draws tab says while no draw of the song holds a value.
MSG_NO_DRAWS_CONFIGURED = 'No draws configured'
MSG_CC_LANES_TAB = 'MIDI CCs'
MSG_TEMPO_RAMPS_TAB = 'Tempo Ramps'
MSG_ROUTING_HEADING = 'Routing'
# interface/pages/built_in_tab.py: what the crumbs call a page opened on a part of a built-in generator.
MSG_BUILT_IN_WORD = 'built-in'
# interface/tracker/screens/shared/plugin_editor.py: every generator's switch, first after its name.
MSG_ENABLED_LABEL = 'Enabled'
# interface/pages/restart_field.py: when a generator starts over, as its editor names the choices.
MSG_RESTART_LABEL = 'Restart'
MSG_STEP_NUMBER_ROW_LABEL = 'Step'
MSG_RESTART_NAMES = {Restart.EVERY_CLIP: 'every clip', Restart.ON_NEW_SCENE: 'on new scene', Restart.WHOLE_SONG: 'whole song'}
MSG_CHORDS_LABEL = 'Chords'
MSG_CHORD_ROW_LABEL = 'Chord'
MSG_NUMERAL_ROW_LABEL = 'Degree'
MSG_CHORD_NAME_ROW_LABEL = 'Name'
MSG_PROGRESSION_ACCIDENTAL_ROW_LABEL = '#/b'
MSG_INVERSION_ROW_LABEL = 'Inv.'
MSG_PROGRESSION_SCALE_ROW_LABEL = 'Scale'
MSG_PROGRESSION_QUALITY_ROW_LABEL = 'Quality'
MSG_PROGRESSION_TENSIONS_ROW_LABEL = 'Tens.'
# The named progressions H offers, by the key model/values/progressions.py names each with, in two groups.
MSG_PROGRESSION_GROUPS = ['Pop and rock', 'Blues, jazz, folk and more']
MSG_PROGRESSION_NAMES = {
    NamedProgression.POP: 'Pop', NamedProgression.FIFTIES: 'Fifties', NamedProgression.SAD_POP: 'Sad pop', NamedProgression.EPIC: 'Epic', NamedProgression.HOPEFUL: 'Hopeful', NamedProgression.ROCK: 'Rock',
    NamedProgression.MIXOLYDIAN_ROCK: 'Mixolydian rock', NamedProgression.POWER_BALLAD: 'Power ballad', NamedProgression.GRUNGE: 'Grunge', NamedProgression.PUNK: 'Punk',
    NamedProgression.ROYAL_ROAD: 'Royal road', NamedProgression.HIP_HOP_LOOP: 'Hip hop loop', NamedProgression.TWELVE_BAR_BLUES: 'Twelve-bar blues',
    NamedProgression.QUICK_CHANGE_BLUES: 'Quick-change blues', NamedProgression.EIGHT_BAR_BLUES: 'Eight-bar blues', NamedProgression.JAZZ_TURNAROUND: 'Jazz turnaround',
    NamedProgression.LONG_TURNAROUND: 'Long turnaround', NamedProgression.CIRCLE_OF_FIFTHS: 'Circle of fifths', NamedProgression.RHYTHM_CHANGES: 'Rhythm changes',
    NamedProgression.FOLK: 'Folk, country', NamedProgression.GOSPEL: 'Gospel', NamedProgression.PACHELBEL: 'Pachelbel', NamedProgression.ANDALUSIAN: 'Andalusian', NamedProgression.MINOR: 'Minor',
}
# interface/pages/time_field.py: what the list of times calls a dotted or triplet length, where its written fraction says nothing to a musician.
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
MSG_STEP_LABEL = 'Step'
MSG_ORDER_LABEL = 'Order'
MSG_OCTAVE_RANGE_LABEL = 'Octave range'
MSG_OCTAVE_JUMP_LABEL = 'Octave jump'
MSG_OFFSETS_LABEL = 'Offsets'
MSG_STEP_ROW_LABEL = ' Step'
MSG_OFFSET_ROW_LABEL = ' Offset'

# interface/tracker/screens/set/scale_page.py
MSG_ROOT_LABEL = 'Root'
MSG_KIND_LABEL = 'Kind'
# Names to show where the full ones are too long to fit.
MSG_SHORT_SCALE_NAMES = {
    ScaleKind.WHOLE_HALF_DIMINISHED: 'whole half dim', ScaleKind.HALF_WHOLE_DIMINISHED: 'half whole dim',
    ScaleKind.LYDIAN_DOMINANT: 'lydian dom', ScaleKind.BEBOP_DOMINANT: 'bebop dom', ScaleKind.PHRYGIAN_DOMINANT: 'phrygian dom',
}

# interface/tracker/screens/pattern/pattern_editor.py, its two drawings and the rows in interface/tracker/components/
# The Use Draws section's rows, by the draw they use.
MSG_DRAW_NOTE_LABEL = 'Note+={name}'
MSG_DRAW_VELOCITY_LABEL = 'Vel+={name}'
MSG_DRAW_RESET_LABEL = 'Reset {name}'
# interface/tracker/screens/arrange/arrange_page.py: what a copied scene's or track's clips play, as the copy's picker offers it.
MSG_COPY_PATTERNS_CHOICES = ['the same patterns', 'copies of the patterns']
# interface/tracker/screens/set/draws_page.py
MSG_DRAW_DIRECTION_LABEL = 'Direction'
MSG_DRAW_SLOTS_LABEL = 'Slots'
MSG_DRAW_VALUE_MIN_LABEL = 'Value Min'
MSG_DRAW_VALUE_MAX_LABEL = 'Value Max'
MSG_DRAW_CONDITIONS_REDRAW_LABEL = 'Conditions redraw'
MSG_DRAW_STRIP_LABEL = 'Strip'
# interface/forms/grouped_choices.py: the headings of a statement's pickers.
MSG_PICKER_CONSTANT_HEADING = '--Constant--'
MSG_PICKER_DRAWS_HEADING = '--Draws--'
# The strip's two rows, as a grid's label column shows them.
MSG_DRAW_STRIP_SLOT_ROW = 'slot'
MSG_DRAW_STRIP_VALUE_ROW = 'value'
# A row of a step's statement is labelled by its place among the statement's five parts, c for condition.
MSG_STATEMENT_ROW_LABEL = 'c{place}'
# The rows on screen. Degree always shows, and the rest depend on the set of rows showing.
MSG_ROW_LABELS = {
    Row.DEGREE: 'Degree', Row.GATE: 'Gate', Row.DOT: 'Dot', Row.ACCIDENTAL: '#/b', Row.OCTAVE: 'Octave', Row.CHORD: 'Chord', Row.INVERSION: 'Inversion',
    Row.TENSION: 'Tension', Row.CHORD_SCALE: 'Scale',
    Row.VELOCITY: 'Velocity', Row.ACCENT: 'Accent', Row.PROBABILITY: 'Probability', Row.GLIDE: 'Glide', Row.TIE: 'Tie', Row.RATCHET: 'Ratchet',
    Row.RATCHET_OFFSET: 'Ratchet Offset', Row.GRAB: 'Grab', Row.KEYSWITCH: 'Keyswitch',
    Row.CC1: 'CC 1', Row.CC2: 'CC 2', Row.CC3: 'CC 3', Row.CC4: 'CC 4', Row.SLIDE: 'Slide',
    **draw_labels(rows=DRAW_NOTE_ROWS, label=MSG_DRAW_NOTE_LABEL),
    **draw_labels(rows=DRAW_VELOCITY_ROWS, label=MSG_DRAW_VELOCITY_LABEL),
    **draw_labels(rows=DRAW_RESET_ROWS, label=MSG_DRAW_RESET_LABEL),
    **{row: MSG_STATEMENT_ROW_LABEL.format(place=place) for rows in STATEMENT_ROWS.values() for place, row in enumerate(rows, start=1)},
}
# The sections of rows under Octave, each a row of the grid: its name after a mark saying whether it's closed (+) or open (-), chosen over triangles, which were hard to tell apart at a distance.
MSG_SECTION_NAMES = {
    RowSection.BASICS: 'Basics', RowSection.CHORD: 'Chord', RowSection.TIMING: 'Timing', RowSection.KEYSWITCH: 'Keyswitch', RowSection.ADVANCED: 'Advanced', RowSection.CC: 'CCs',
    RowSection.DRAW_APPLY: 'Use Draws', RowSection.STOP_WHEN: 'Stop When',
    RowSection.RESTART_WHEN: 'Restart When', RowSection.MUTE_WHEN: 'Mute When',
}
MSG_SECTION_LABEL = '{mark} {name}'
# What the second line of the header says while the cursor is in a section with something to explain, in place of the scale.
MSG_SECTION_HINTS = {
    RowSection.ADVANCED: "Advanced: Grab plays the Grab track's last note",
    RowSection.CC: "CCs: the track sets each row's CC number",
    RowSection.DRAW_APPLY: "Use Draws: Note+= and Vel+= add (+) or subtract (-) a draw's next value",
    RowSection.STOP_WHEN: 'Stop When: the clip is done at a step whose statement is true',
    RowSection.RESTART_WHEN: 'Restart When: the pattern starts over at a step whose statement is true',
    RowSection.MUTE_WHEN: 'Mute When: a step whose statement is true does not sound',
}
MSG_SCALE_HEADER = 'Scale {scale}'
MSG_NO_SCALE_NEEDED = 'no scale needed'
MSG_SEVERAL_SCALES = 'Scale varies by scene'
# What follows the scale where the pattern was written for a scale of another number of notes than one it plays under.
MSG_WRITTEN_FOR = '{scale}, written for {length}'
# The first choice of the roll's entry size picker (E), before the step sizes: the pattern takes the song's entry size.
MSG_SONG_ENTRY_SIZE_CHOICE = "(the song's)"
# The piano roll's row labels: the note's name with its octave and the degree, or the octave alone when the scale isn't known.
MSG_ROLL_ROW_LABEL = '{note:<4} {degree}'
MSG_STEP_HEADING = ' Step'
# A CC row's label says the CC number the tracks playing the pattern send on that lane, off for a lane that sends nothing, or ? when the tracks differ.
MSG_CC_ROW_LABEL = '{label} ({number})'
MSG_DOT_NAMES = {GateModifier.DOTTED: ' dotted', GateModifier.TRIPLET: ' triplet'}
# The headings the munge dialog lists its choices under.
class MungeGroup:
    """The names of the groups the Munge picker lists the munges under."""

    CLEAR = 'Clear'
    COPY = 'Copy'
    OTHER_PATTERNS = 'Other Patterns'
    PITCH = 'Pitch'
    REORDER = 'Reorder'
    RHYTHM = 'Rhythm'
    ROLL = 'Roll'
    VELOCITY_AND_CCS = 'Velocity and CCs'


MSG_MUNGE_CHOICES = [
    'reverse after (cursor)', 'reverse before (cursor)', 'reverse all', 'pivot (cursor)', 'randomize all',
    'copy before to end (cursor)', 'copy after to end (cursor)', 'copy before to start (cursor)',
    'copy after to start (cursor)', 'randomize after (cursor)', 'randomize before (cursor)', 'clear all except pitch',
    'clear conditions', 'roll left (N)', 'roll right (N)', 'clear chords', 'mirror', 'interleave (pattern)', 'smooth CCs',
    'smooth velocity', 'splice after (pattern)', 'splice before (pattern)', 'split into new patterns (N)',
    'splice (pattern, cursor)', 'roll left (cursor)', 'roll right (cursor)', 'join repeated notes', 'divide long notes',
    'randomize rhythm', 'randomize pitches', 'reverse pitches', 'clear every Nth step (N)', 'crop (cursor)',
    'humanize velocity (N)', 'invert melody (cursor)', 'apply voice leading (no octave shift)',
    'apply voice leading (octave shift)',
]
# The clip page's extra choice, for a clip that follows its pattern's direction.
MSG_PATTERN_DIRECTION_OPTION = 'from pattern'
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

# interface/tracker/screens/set/groove_editor.py
MSG_CELL_ROW_LABEL = ' Cell'
MSG_AMOUNT_ROW_LABEL = ' Amount'

# interface/pages/groove_choice.py: the Groove field on the Song, Scene and Track pages
MSG_GROOVE_LABEL = 'Groove'
MSG_GROOVE_OFF_OPTION = '(off: no groove here, whatever else chooses one)'

# interface/tracker/screens/set/scale_page.py: the scale picker's two pages, and the headings of the groups of scales on them
# interface/tracker/scale_categories.py: the categories of scale type the Chord dialog lists, each opening a flyout.
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

# interface/tracker/screens/set/instrument_editor.py: General MIDI's 128 sounds, numbered from 1 in this order, and its 16 families of eight.
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
# What a step with no velocity typed plays at, on an instrument and on a track.
MSG_DEFAULT_VELOCITY_LABEL = 'Default velocity'
MSG_GM_SOUND_SHOWN = '{number} {name}'

# interface/tracker/screens/wizard/wizard_page.py and the branches of interface/pages/wizard/
MSG_WIZARD_CAPTION = 'NEW SONG WIZARD: {name}'
MSG_WIZARD_REPLACE_CAPTION = 'SONG WIZARD, REPLACING: {name}'
MSG_WIZARD_START_TITLE = 'Song Wizard'
# The four ways a run starts when the current song was made by the wizard, by the constants of interface/pages/wizard/starts.py.
MSG_WIZARD_START_NAMES = {
    'new from last': 'New song, from last settings',
    'new from scratch': 'New song, from scratch',
    'replace from last': 'Replace song, from last settings',
    'replace from scratch': 'Replace song, from scratch',
}
MSG_WIZARD_METER_LABEL = 'Meter'
MSG_WIZARD_SWING_LABEL = 'Swing'
MSG_WIZARD_VARIANT_LABEL = 'Variant'
# A kind of song in the Variant picker, with the line that says what it is.
MSG_WIZARD_VARIANT_NAMED = '{name}: {says}'
MSG_WIZARD_BAND_BRANCH = 'Band'
MSG_WIZARD_SOUNDS_LABEL = 'Sounds'
MSG_WIZARD_DRUM_FILLS_LABEL = 'Fills come'
MSG_WIZARD_QUIET_NOTES_LABEL = 'Quiet notes'
MSG_WIZARD_FILLS_COME = ['never', 'each section', 'every 4 bars', 'every 2 bars']
MSG_WIZARD_KIT_PIECE = 'kit: {piece}'
MSG_WIZARD_GUITARISTS_LABEL = 'Guitarists'
# Who has the tune and who answers, the answering player's role, a section's own, and how busy the fills are.
MSG_WIZARD_TUNE_LABEL = 'Melody played by'
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
# interface/pages/wizard/melody_branch.py, interface/pages/wizard/section_melody_branch.py: the whole song's melodies, and one kind of section's.
MSG_WIZARD_MELODY_WAY_LABELS = {'busy': 'Busy', 'range': 'Range', 'repeats': 'Repeats'}
MSG_WIZARD_CHARACTER_LABEL = 'Character'
MSG_WIZARD_HEIGHT_LABEL = 'Height'
MSG_WIZARD_SECTION_BUSY_LABEL = 'Busy'
MSG_WIZARD_FROM_SONG = 'from song'
MSG_WIZARD_NOTES_EDITED = 'edited'
MSG_WIZARD_EDIT_NOTES_BUTTON = 'Edit Notes'
# interface/pages/wizard/solo_melody_branch.py: one solo's notes.
MSG_WIZARD_SOLO_NUMBERED = '{kind} {number}'
MSG_WIZARD_SOLO_PLAYED_BY_LABEL = 'Played by'
MSG_WIZARD_SOLO_SECTION_LABEL = 'Section'
MSG_WIZARD_REGENERATE_BUTTON = 'Regenerate'
# interface/pages/wizard/riffs_branch.py, interface/pages/wizard/riff_assign_branch.py, interface/pages/wizard/section_players_branch.py, interface/tracker/dialogs/new_riff_dialog.py: the riffs.
MSG_WIZARD_RIFFS_BRANCH = 'Riffs'
MSG_WIZARD_RIFF_ASSIGN_BRANCH = 'Riff Assign'
MSG_WIZARD_SECTION_PLAYERS_BRANCH = 'Section Players'
MSG_WIZARD_RIFF_COLUMNS = 'BARS  USED IN'
MSG_WIZARD_RIFF_FOR_COLUMN = 'FOR'
MSG_WIZARD_RIFF_PLAYED_IN_COLUMN = 'PLAYED IN'
MSG_WIZARD_COPY_RIFF_TITLE = 'Copy {riff} for'
MSG_WIZARD_GIVE_RIFF_TITLE = 'Add Riff for {player}'
MSG_NEW_RIFF_TITLE = 'New Riff for {player}'
MSG_NEW_RIFF_LABELS = {'bars': 'Bars', 'notes': 'Made of', 'with chords': 'Follows chords', 'between': 'Gaps'}
MSG_NEW_RIFF_VALUES = {1: '1', 2: '2', 'single notes': 'notes', 'chords on the accents': 'notes and chords', 'muted roots': 'muted roots', 'rests': 'silence'}
MSG_NEW_RIFF_BUTTONS = ('Write Riff', 'CANCEL')
# interface/pages/wizard/section_melody_branch.py: a kind of section's melody.
MSG_WIZARD_LISTEN_BAND_BUTTON = 'Listen With Band'
MSG_WIZARD_BODY_GAUGE_LABELS = {'sameness': 'Sameness', 'space': 'Space', 'lift': 'Lift', 'resolve': 'Resolve', 'call_and_answer': 'Call and answer'}
# interface/pages/wizard/hooks_branch.py: the song's hooks.
MSG_WIZARD_HOOKS_BRANCH = 'Hook'
MSG_WIZARD_BEHAVIOR_LABEL = 'Behavior'
MSG_WIZARD_HOOK_GAUGE_LABELS = {'catchiness': 'Catchiness', 'simplicity': 'Simplicity', 'leap': 'Leap', 'height': 'Height', 'hold': 'Hold', 'bounce': 'Bounce'}
# interface/pages/wizard/melodies_branch.py: the group of the song's melodies.
MSG_WIZARD_MELODIES_BRANCH = 'Melodies'
MSG_WIZARD_MAIN_HOOK_HEADING = 'Main Hook'
MSG_WIZARD_HOOK_HEADING = 'Hook'
MSG_WIZARD_HOOK_BARS_LABEL = 'Hook bars'
MSG_WIZARD_HOOK_BARS = '{first} to {last}'
MSG_WIZARD_EDIT_KIND_NOTES_BUTTON = 'Edit {kind} Notes'
MSG_WIZARD_SECOND_HOOK_HEADING = 'Second Hook'
MSG_WIZARD_MAIN_HOOK_LABEL = 'Main hook'
MSG_WIZARD_SECOND_HOOK_LABEL = 'Second hook'
MSG_WIZARD_SUNG_IN_LABEL = 'Sung in'
MSG_WIZARD_SECOND_SUNG_IN_LABEL = 'Tag sung in'
MSG_WIZARD_PLACEMENT_LABEL = 'Placement'
MSG_WIZARD_NEW_SECOND_HOOK_BUTTON = 'New Second Hook'
MSG_WIZARD_PROGRESSION_LABEL = 'Progression'
MSG_WIZARD_HOOK_NOTES_LABEL = 'Hook notes'
MSG_WIZARD_HOOK_NOTES_OWN = 'edited'
# The Lines dialog, a section's lines one by one, and the section panel's field that opens it.
MSG_WIZARD_LINES_LABEL = 'Lines'
# The groups of a section's panel, each a heading that opens and closes.
MSG_WIZARD_GROUP_TUNE = 'Tune'
# The groups of the Hooks panel, and the riff's fields.
# Made of, since Notes is the hook's field on the same panel.
# The kick's row above the riff's picture.
MSG_WIZARD_GROUP_HARMONY = 'Harmony'
MSG_WIZARD_GROUP_SHAPE = 'Shape'
MSG_WIZARD_GROUP_JOINS = 'Joins'
MSG_WIZARD_GROUP_PLAYERS = 'Who plays'
# The song plan's fields on the Form panel, the parts of a hook's kind on the Hooks panel, and a value the wizard picked itself.
MSG_WIZARD_SONG_PLAN_LABEL = 'Song plan'
MSG_WIZARD_CONTRAST_LABEL = 'Contrast'
# A player as a person: where the player comes in and lays out, and how strongly the player answers to Energy, by the gauge's place.
MSG_WIZARD_COMES_IN_LABEL = 'Comes in'
MSG_WIZARD_LAYS_OUT_LABEL = 'Lays out'
MSG_WIZARD_REACTS_LABEL = 'Reacts'
# How far a player's loud and soft notes lie from the player's normal ones, and the player's four levels under a heading.
MSG_WIZARD_DYNAMICS_LABEL = 'Dynamics'
MSG_WIZARD_DYNAMICS_SAID = {0: 'flat', 1: 'narrow', 2: 'narrow', 3: 'gentle', 4: 'gentle', 5: 'as written', 6: 'lively', 7: 'lively', 8: 'wide', 9: 'wide', 10: 'widest'}
# Not Loudness alone, which is a row of the serial style on the same panel.
MSG_WIZARD_GROUP_LOUDNESS = 'Loudness levels'
MSG_WIZARD_LEVEL_LABELS = {'ghost': 'Ghost note', 'soft': 'Soft', 'normal': 'Normal', 'accent': 'Accent'}
MSG_WIZARD_REACTS_SAID = {1: 'even', 2: 'even', 3: 'steady', 4: 'steady', 5: 'as the band', 6: 'lively', 7: 'lively', 8: 'dramatic', 9: 'dramatic', 10: 'dramatic'}
MSG_WIZARD_STARTS_LABEL = 'Starts with'
MSG_WIZARD_FIRST_PLAYER_LABEL = 'First player'
MSG_WIZARD_SETUP_BARS_LABEL = 'Setup bars'
MSG_WIZARD_ENDS_LABEL = 'Ends with'
MSG_WIZARD_OWN_START = 'your own'
MSG_WIZARD_PHRASING_LABEL = 'Phrasing'
MSG_WIZARD_EDIT_PHRASING_BUTTON = 'Edit Phrasing'
MSG_WIZARD_EDIT_PLAYER_BUTTON = 'Edit Player'
MSG_WIZARD_EDIT_OWN_PLAYER_BUTTON = 'Edit Player (your own)'
# What a section of a planned song can be given of its own, and where each comes from until it is.
MSG_WIZARD_INTRO_HOOK_LABEL = 'Intro hook'
MSG_WIZARD_SECTION_OWN_LABELS = {'shape': 'Shape', 'rises': 'Rises', 'energy': 'Energy', 'leaves': 'Leaves with', 'setup': 'Setup', 'chords': 'Chords', 'tempo': 'Tempo', 'tempo_end': 'Tempo at end', 'root': 'Key', 'type': 'Scale', 'fades': 'Fades'}
MSG_WIZARD_SECTION_ORIGINS = {'shape': 'from genre', 'rises': 'from plan', 'energy': 'from plan', 'leaves': 'from plan', 'setup': 'from plan', 'chords': 'from progression', 'tempo': 'from song', 'tempo_end': 'from song', 'root': 'from song', 'type': 'from song', 'fades': 'from genre'}
MSG_WIZARD_VALUE_FROM = '{value} ({origin})'
# A fade's fields, named for its way: a section that opens the song fades in, and one that closes the song fades out.
MSG_WIZARD_FADE_LABELS = {'in': {'fades': 'Fade in', 'fade_level': 'Fade from', 'fade_over': 'Fade over'}, 'out': {'fades': 'Fade out', 'fade_level': 'Fade to', 'fade_over': 'Fade over'}}
MSG_WIZARD_FADE_VELOCITY = '{value}%'
# interface/pages/wizard/intro_melody_branch.py: the intro's parts.
MSG_WIZARD_INTRO_PART = 'Part {number}'
MSG_WIZARD_PART_MELODY_LABEL = 'Melody'
MSG_WIZARD_ADD_PART_BUTTON = 'Add Part'
MSG_WIZARD_FADE_BARS = '{value} bars'
MSG_WIZARD_FADE_ONE_BAR = '1 bar'
MSG_WIZARD_FROM_ORIGIN = '({origin})'
MSG_WIZARD_PLAN_LINE = '{number:>2}  {name:<{width}}  {said}'
MSG_WIZARD_FILLS_LABEL = 'Fill pattern'
MSG_WIZARD_USUAL_MELODY = 'from genre'
# The smart melody style's gauges, each by its name in the melody engine: the field's label, then what its two ends mean.
# A melody style's own settings, under the Melody field while the style is in use.
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
# The questions a form is made from, each a dialog's title, by the question's name.
MSG_WIZARD_FORM_QUESTIONS_BUTTON = 'Form questions'
MSG_WIZARD_FORM_QUESTION_TITLES = {
    'verses first': 'Verses before the first chorus', 'pre-choruses': 'Pre-chorus', 'bridge': 'Bridge', 'solos': 'Solos', 'drum solo': 'Drum solo',
    'last choruses': 'Choruses at the end',
}
MSG_WIZARD_ROW_LABELS = {'lengths': 'Lengths', 'loudness': 'Loudness', 'articulation': 'Articulation'}
MSG_WIZARD_SUGGESTED_FORM_TITLE = 'Suggested forms'
MSG_WIZARD_BUSY_LABEL = 'Busy'
# A player's own gauges, under the Busy field, which is a preset of them all.
MSG_WIZARD_PLAYER_GAUGE_LABELS = {'notes': 'Notes', 'variety': 'Variety', 'touch': 'Touch', 'timing': 'Loose timing', 'fills': 'Fill size', 'strumming': 'Strumming', 'range': 'Range'}
MSG_WIZARD_LENGTH_LABEL = 'Length'
# The last row of the dialog that asks how to start.
MSG_WIZARD_START_CANCEL = 'CANCEL'
MSG_WIZARD_GENRE_BRANCH = 'Genre'
MSG_WIZARD_SUBGENRE_BRANCH = 'Subgenre'
MSG_WIZARD_FORM_BRANCH = 'Form'
MSG_WIZARD_CREATE_BRANCH = 'Apply'
# A tab's own row in its list, at its head, before its parts, by the tab's name: the band's members, the summary of the
# composition, and the shape of the form.
MSG_WIZARD_MEMBERS_ROW = 'Members'
MSG_WIZARD_SUMMARY_ROW = 'Summary'
MSG_WIZARD_SHAPE_ROW = 'Shape'
MSG_WIZARD_TAB_OWN_ROWS = {MSG_WIZARD_BAND_BRANCH: MSG_WIZARD_MEMBERS_ROW, MSG_WIZARD_COMPOSITION_BRANCH: MSG_WIZARD_SUMMARY_ROW, MSG_WIZARD_FORM_BRANCH: MSG_WIZARD_SHAPE_ROW}
MSG_WIZARD_SUBGENRE_LABEL = 'Subgenre'
MSG_WIZARD_KEY_LABEL = 'Key'
MSG_WIZARD_FORM_LABEL = 'Form'
MSG_WIZARD_SONG_LABEL = 'Song'
MSG_WIZARD_BARS_LABEL = 'Bars'
MSG_WIZARD_PLAYS_LABEL = 'Plays'
MSG_WIZARD_CREATE_BUTTON = 'Apply'
# The buttons under the wizard's tab box, which open the tab before or after.
MSG_WIZARD_BACK_BUTTON = '< Back'
MSG_WIZARD_NEXT_BUTTON = 'Next >'
MSG_WIZARD_SCALE_TYPE_NAMES = {'major': 'Major', 'minor': 'Minor'}

MSG_LISTED_GENERATOR = '{kind} ({name})'
MSG_GENERATORS_FIELD_LABEL = 'Generators'
