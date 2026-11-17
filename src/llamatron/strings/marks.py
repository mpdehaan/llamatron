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
"""What the tracker draws: marks, bars, the text of a cell, and the formats of numbers, times and header lines.

Each constant starts with MSG_.
"""

from llamatron.composition.file_format import Accidental, ChordSymbol, Direction, Quality, Shape, Stroke

# Shared by several pages: a field with no value, and a song or scene with no scale in a sentence.
MSG_NONE_SHOWN = '(none)'
# What a field shows for a genre, subgenre or variant a song doesn't say.
MSG_UNDEFINED_SHOWN = '(undefined)'
MSG_ANY_SCALE_LENGTH = '(any)'
# A cell of a table of settings by section that takes the value above the table.
MSG_SAME_AS_ABOVE = '(same)'

# tui/app.py
MSG_CONFIRM_BUTTON_GAP = '    '

# tui/screens/arrange/arrange_page.py
# A scene's name as a recording announces the scene when it starts.
MSG_SCENE_ANNOUNCED = 'SCENE: {name}'
# A scene's row: its number from 1, then its name.
MSG_SCENE_ROW = '{number:>2} {name}'
# The marks after a clip's pattern on the grid, for anything beyond the pattern itself.
MSG_DIRECTION_MARK = 'd'
MSG_GRAB_MARK = 'g'
MSG_MORPH_MARK = '~'
MSG_LOOP_MARK = '∞'
# After a scene's name on Arrange, when its Launch together is off, so each clip waits for the clip above it.
MSG_LAUNCH_APART_MARK = '┆'
MSG_REPEAT_MARK = '×{repeat}'
MSG_CLIP_WITH_MARKS = '{name} {marks}'

# tui/screens/arrange/arrange_details.py: what Arrange shows in its details view (R): the lines of details under
# each bar, each a word and a colon, a chain's name in parentheses with its generators under it, and a clip's morph and
# direction spelled out, chosen over marks.
MSG_DETAILS_MORPH = 'morph: {pattern}'
MSG_DETAILS_DIRECTION = 'direction: {direction}'
MSG_DETAILS_DIRECTION_NAMES = {
    Direction.REVERSE_A: 'reverse a', Direction.REVERSE_B: 'reverse b', Direction.ALTERNATE: 'alternate', Direction.PENDULUM: 'pendulum',
    Direction.RANDOM: 'random', Direction.BROWNIAN: 'brownian', Direction.EITHERWAY: 'eitherway',
}
MSG_DETAILS_MARKS_SEPARATOR = ' '
MSG_DETAILS_CHAIN = 'chain: {name}'
# The line under a cell's chains that adds one.
MSG_DETAILS_ADD_CHAIN = '+'
MSG_DETAILS_SCALE = 'scale: {name}'
MSG_DETAILS_TEMPO = 'tempo: {tempo}'
MSG_DETAILS_TEMPO_RAMP = 'tempo: {start}→{end}'
MSG_DETAILS_GROOVE = 'groove: {name}'
MSG_DETAILS_NO_GROOVE = 'groove: off'
MSG_DETAILS_RESET = 'reset: {registers}'
MSG_DETAILS_SHAPE = '{shape}: {start}→{end}'
MSG_DETAILS_SHAPE_NAMES = {Shape.DENSITY: 'density', Shape.SWELL: 'swell', Shape.ARTICULATE: 'articulate'}
MSG_DETAILS_GRAB = 'grab: {track}'
MSG_DETAILS_ADVANCE = 'advance: {action}'
MSG_DETAILS_STRUM = 'strum: {direction}'
MSG_DETAILS_INSTRUMENT = 'inst: {name}'
MSG_DETAILS_TRANSPOSE = 'transpose: {amount:+d}'
MSG_DETAILS_EUCLID = 'euclid: {hits}/{steps}'
MSG_DETAILS_MUTED = 'muted'
MSG_DETAILS_LIST_SEPARATOR = ', '
# Around the line of details Tab picked, which ENTER opens, chosen over the triangle, which marks play.
MSG_DETAILS_STOCK = 'stock'

# tui/components/scene_view.py and tui/scene_notes.py: Scene View, an inset window over Arrange showing
# every track's notes in a scene laid over each other, its caption saying which view shows, as written or as played.
MSG_SCENE_VIEW_TITLE = ' SCENE VIEW FOR SCENE: {scene} '
MSG_SCENE_VIEW_CLOSING = ' {key} {what} '
MSG_SCENE_VIEW_TRACK = '{name} ({number})'
MSG_SCENE_VIEW_WRITTEN = 'WRITTEN: the patterns as written, before any generator, groove or register'
MSG_SCENE_VIEW_PLAYED = 'PLAYED: after every generator, groove and register{take}'
MSG_SCENE_VIEW_ONE_TAKE = ', one take of its random parts'
MSG_SCENE_VIEW_EFFECTIVE = 'tempo {tempo} ({tempo_source})  ·  {signature}  ·  scale {scale} ({scale_source})  ·  groove {groove} ({groove_source})'
MSG_SCENE_VIEW_TEMPO_RAMP = '{start}→{end}'
MSG_SCENE_VIEW_SLASH_CHORD = '{chord}/{bass}'
MSG_SCENE_VIEW_FROM_SONG = 'song'
MSG_SCENE_VIEW_FROM_SCENE = 'scene'
MSG_SCENE_VIEW_NO_GROOVE = 'none'
MSG_SCENE_VIEW_SIGNATURE = '{beats}/{unit}'
MSG_SCENE_VIEW_LEGEND_MARK = '■ '
MSG_SCENE_VIEW_CLIP_SCALE = ' [{scale}]'
MSG_SCENE_VIEW_LEGEND_GAP = '  '
MSG_SCENE_VIEW_REGISTERS = '░ reads registers: drawn apart, not as played'
MSG_SCENE_VIEW_CHORD_LABEL = 'chord'
MSG_SCENE_VIEW_NUMERAL_LABEL = 'in key'
MSG_SCENE_VIEW_NOTE = '{track} (track #{number}): {note} for {length}'
MSG_SCENE_VIEW_NOTE_READS = ' (reads registers)'
MSG_SCENE_VIEW_NOTE_SEPARATOR = '  ·  '
MSG_SCENE_VIEW_NOTHING_HERE = 'at {place}: no note'
MSG_SCENE_VIEW_PLACE = 'bar {bar} beat {beat}'
MSG_SCENE_VIEW_CANT_SHOW = 'This scene cannot be shown: {problem}'
MSG_PICKED_OPEN = '['
MSG_PICKED_CLOSE = ']'
# A value a field takes from above, shown with where it comes from.
MSG_SONG_SCALE_SHOWN = '{scale} (from song)'
MSG_SCENE_SCALE_SHOWN = '{scale} (from scene)'
MSG_SONG_TEMPO_SHOWN = '{tempo} BPM (from song)'
MSG_TEMPO_SHOWN = '{tempo} BPM'
MSG_RAMP_OFF_SHOWN = '(off)'
MSG_LOOP_ON_SHOWN = 'on'
MSG_LOOP_OFF_SHOWN = 'off'
MSG_ONE_STEP_SHOWN = '(one step)'
MSG_CLIP_NAMED_FOR_PATTERN = '(pattern: {pattern})'
MSG_PATTERN_DIRECTION_SHOWN = '{direction} (from pattern)'

# tui/screens/shared/page.py and tui/key_table.py: the key names, the labels and the words every page shares
# What a picker shows while something is typed into it, and what a list page's status line shows.
MSG_SEARCH_SHOWN = 'search: {text}'
# The header's first line: the program's name, then the open set and its song, with the save mark at the right.
MSG_UNSAVED_MARK = '● unsaved'
MSG_UNSAVED_CHANGES_MARK = '● unsaved changes'
MSG_SAVED_MARK = '○ saved'
# The header's second line: the pages that led here, with the time at the right.
MSG_CRUMB_SEPARATOR = ' › '

# AboutDialog: the cowsay cow saying the program's name, then the version, the links, a quote and the license.
# A prompt's cursor line.
MSG_PROMPT_MARK = '› '
MSG_COLUMN_LINE = '{name}  {description}'
# A page tab on a dialog with pages.
MSG_PREVIOUS_PAGE_MARK = '◂ Shift+Tab '
MSG_NEXT_PAGE_MARK = 'Tab ▸'
MSG_PAGE_TAB = ' {name} '

# tui/document.py
MSG_SCALE_NOTES_TEXT = '{root} {kind}'
# How time is shown.
MSG_NO_TIME = '--:--'
MSG_CLOCK = '{minutes}:{seconds:02}'

# tui/screens/set/main_page.py, tui/screens/set/file_page.py and tui/screens/shared/everywhere.py
# The main screen: the set's name and the current song, and the song's summary; the song's length is in the header, and the counts are on the cells.
MSG_NOT_SAVED_YET = '(not saved yet)'
MSG_EXPORTS_BESIDE = '{prefix}.als and the MIDI files beside it'
MSG_EXPORTS_AFTER_SAVING = '(save the set first)'
MSG_NOT_SET = 'not set'

# tui/screens/arrange/track_editor.py
MSG_CURRENT_SONG_MARK = '●'
MSG_PARENT_ROW = '../'
MSG_FOLDER_ROW = '{name}/'
# A step that's off, in a row of steps written out on one line.
MSG_STEP_OFF = '.'
# A Euclidean rhythm drawn a mark a step, and a named rhythm as its picker offers it.
MSG_EUCLID_HIT = 'X'
MSG_EUCLID_MISS = '.'
MSG_RHYTHM_SHOWN = '{name}: {hits} over {steps}, {drawn}'
# A spread with how many milliseconds apart it sounds two strings.
MSG_SPREAD_SHOWN = '{name} ({milliseconds} ms)'
# A voice leading's range on its list page, in the set's octave labels.
# A shape generator's start and end, as its list page shows them.
# A number that isn't set, in a list of numbers like CC numbers or offsets.
MSG_NO_NUMBER_MARK = '-'
MSG_DRUM_TRACK_SHOWN = '(drum track)'
MSG_SIGNED_NUMBER = '{number:+d}'
# The chain editor.
# A step of a chain, the generator's name and then its kind, and a generator listed again in one chain numbered on screen only.
MSG_CHAIN_STEP_SHOWN = '{name} ({kind})'
MSG_CHAIN_STEP_AGAIN = '{name} {number} ({kind})'
# The arp pages: how they show settings a file leaves out, and what they start from.
# A generator's step left as the step size of the pattern each clip plays.
MSG_PATTERN_STEP_SHOWN = '(pattern)'
# A list of chains, as a field shows it.
MSG_CHAIN_JOIN = ', '
MSG_SONG_SEED_SHOWN = '(song)'
# The gauge of offsets (tui/components/signed_gauge.py): a value with its sign and a mark when the gauge is too short to
# reach it, above or below, and the brackets around the cursor's step number and value.
MSG_POSITIVE_VALUE = '+{value}{mark}'
MSG_OTHER_VALUE = '{value}{mark}'
MSG_UNDER_THE_BOTTOM_MARK = '▼'
MSG_CURSOR_STEP_MARKS = '<<{text}>>'
MSG_CURSOR_VALUE_MARKS = '<{text}>'
# The scales page.
MSG_SONG_SCALE_MARK = ' (song)'

# tui/screens/set/scale_page.py
# The keyboard under the scale's fields (tui/components/keyboard.py): a key in the scale, one outside it, and the root's name.
MSG_KEY_IN_SCALE = '███'
MSG_KEY_OUT_OF_SCALE = '░░░'
MSG_KEY_OF_SCALE_OUTLINED = '▒▒▒'
MSG_KEY_IN_CHORD = '███'
MSG_ROOT_KEY_NAME = '[{name}]'

# tui/screens/pattern/pattern_editor.py, its two drawings and the rows in tui/components/
MSG_SECTION_CLOSED_MARK = '+'
MSG_SECTION_OPEN_MARK = '-'
# tui/dialogs/grouped_choice_dialog.py: a heading of choices, and a choice under one.
MSG_GROUP_OF_CHOICES = '{mark} {name}'
MSG_GROUPED_CHOICE = '    {name}'
# What a settings page's section heading says when a field inside it holds a value, so that a closed one never hides it.
MSG_SECTION_SET = '(set)'
# The header's two lines are cells laid out in columns, each column as wide as its wider cell, so that the second line's cells start under the
# first's: Steps over Time, Step size over Scale, Drum over Entry, then Direction. The rows view's section hint takes the whole second line after Time.
MSG_HEADER_INDENT = '  '
MSG_HEADER_CELL_GAP = '   '
MSG_STEPS_HEADER = 'Steps {steps}'
MSG_DRUM_HEADER = 'Drum {drum}'
MSG_DIRECTION_HEADER = 'Direction {direction}'
# Which steps are on screen when the pattern is wider than the window, at the right of the second header line, with a mark on each side that has more.
MSG_STEPS_SHOWN = '{before}steps {first}-{last}{after}'
# The same for a groove, whose steps are called cells.
MSG_CELLS_SHOWN = '{before}cells {first}-{last}{after}'
MSG_MORE_BEFORE = '‹ '
MSG_MORE_AFTER = ' ›'
MSG_TIME_SIGNATURE_SHOWN = 'Time {signature}{whose}'
# The scale the gauge is drawn in, by name and notes, and the note when the pattern's uses play it under more than one.
MSG_SCALE_SHOWN = '{name}: {notes}'
# The piano roll's header's second line ends with the entry size, how long Space draws a note, the pattern's own or the song's.
MSG_ENTRY_SIZE_SHOWN = 'Entry {size}{whose}'
MSG_ROLL_OCTAVE_ONLY = 'oct{octave}'
# The piano roll's cells: a note fills its cell and runs through the dividers it crosses, with a mark inside on its first step,
# its sharp or flat or G for a step that grabs, drawn in reverse video so that it reads against the bar;
# the cursor is shaded on a note, since reverse video on a solid block is blank; a row outside the track's range is marked off.
# A note whose gate ends inside a step fills only part of its last cell, built from the single blocks, so the bar ends where the sound does.
MSG_NOTE_CELL = '█████'
MSG_NOTE_CELL_WITH_MARK = '██{mark}██'
MSG_NOTE_EDGE = '█'
MSG_NOTE_UNDER_CURSOR = '▓▓▓▓▓'
MSG_NOTE_UNDER_CURSOR_WITH_MARK = '▓▓{mark}▓▓'
MSG_CURSOR_BLOCK = '▓'
MSG_GRAB_NOTE_MARK = 'G'
# A note whose chord's inversion lifts its root an octave doesn't sound where it is written, so its bar is drawn hollow: light where a note's bar is
# solid, and medium under the cursor.
MSG_NOTE_HOLLOW = '░'
MSG_NOTE_HOLLOW_UNDER_CURSOR = '▒'
MSG_OUT_OF_RANGE_CELL = '·····'
# A chord's other notes on the piano roll: thin dim lines, chosen over hollow boxes, which can't be edited on their own.
MSG_GHOST_LINE = '─'
# The piano roll's read head, a thin line down the roll at the left edge of the step that sounds.
MSG_READ_HEAD = '│'
# The light on a step that has keyswitches, in the middle of the step's cell on the roll's top row, over a note's bar when one is there.
MSG_KEYSWITCH_LIGHT = '◆'
MSG_DRUM_ON = '[x]'
MSG_DRUM_OFF = '[ ]'
# A toggle that's on shows a dot, from the few characters every terminal has.
MSG_TOGGLE_ON = '●'
# The Degree gauge: the bar in each step's column, and the mark after a number the gauge is too short to reach.
MSG_GAUGE_BAR = '███'
# tui/screens/generators/chords_editor.py: the lower half of a gauge's cell, for the odd degree of a line that holds two, and a numeral's marks.
MSG_GAUGE_HALF_BAR = '▄▄▄'
MSG_DIMINISHED_NUMERAL_MARK = '°'
MSG_AUGMENTED_NUMERAL_MARK = '+'
MSG_OVER_THE_TOP_MARK = '▲'
# The Tie row's bar, drawn like a piano roll's note: where a note starts, where it starts and is tied on, a tied step, and the
# piece that takes the divider's place where the bar runs through it; the Glide row's bar runs from its step into the next.
MSG_CC_LANE_OFF = 'off'
MSG_CC_LANE_VARIES = '?'
MSG_TOGGLE_OFF = ' '
# After the value of a settings field whose ENTER opens a list of choices (tui/screens/shared/field_page.py).
MSG_PICKER_MARK = '▾'
# tui/dialogs/chord_dialog.py: a row that opens a flyout, drawn as a button, alone and with the choice made inside it, with and without room for its own name, and the
# flyout's heading.
MSG_FLYOUT_CHOSEN = '[ {name} ▸ {chosen} ]'
MSG_FLYOUT_CHOSEN_ALONE = '[ ▸ {chosen} ]'
MSG_FLYOUT_CLOSED = '[ {name} ]'
# A sound a search found, with the group that holds it.
MSG_SOUND_FOUND = '{sound}  ({group})'
MSG_FLYOUT_TITLE = 'Scale: {name}'
# The marks either side of a row's name while Move mode carries it, in place of the spaces beside it so that nothing shifts.
MSG_MOVING_OPEN = '<'
MSG_MOVING_CLOSE = '>'
# A settings page's toggle that is off, an empty circle, so that a toggle shows itself either way.
MSG_FIELD_TOGGLE_OFF = '○'
# What a register's +Note or +Vel cell shows when the step adds the register or subtracts it (RegisterRow).
MSG_REGISTER_ADDS = '+'
MSG_REGISTER_SUBTRACTS = '-'
# A number row with nothing set shows a dot where its default means nothing happens.
MSG_UNSET_MARK = '.'
# A cell that can't take a value, which the render ignores, like Velocity on an empty step or Tie on a note's own step, drawn dim; A light slash in place of the (X) tried first.
MSG_BLOCKED_CELL = '/'
MSG_DRUM_LETTER_ROW = 'Note'
MSG_STEP_SIZE_SHOWN = 'Step size {size}{whose}'
MSG_FROM_SONG_SHOWN = " (song's)"

# tui/screens/set/grooves_page.py
MSG_FACTORY_GROOVE_SHOWN = 'factory'

# tui/screens/set/main_page.py and tui/screens/set/instruments_page.py
MSG_REAL_TIME_ON_MARK = '●'
MSG_REAL_TIME_OFF_MARK = '○'

# tui/screens/arrange/arrange_drawing.py: the lights of real-time playback, the one place the tracker draws in colour.
# The play button before each scene's and clip's bar, and the corner's, which turns into the stop mark while it plays.
MSG_PLAY_MARK = '▶'
MSG_STOP_MARK = '■'
# After a track's name while a note sounds on it.
MSG_SOUNDING_MARK = '●'
# The corner over the scene names, where Space plays the song from the top.
MSG_SONG_BUTTON = '{mark} song'
# The time at the right of the crumbs while the song plays: where it is, and how long it is.
MSG_PLAYING_CLOCK = '▶ {at} / {total}'
MSG_NO_DEVICE_SHOWN = '(none)'
# An instrument's Channel while its Device is FluidSynth, which gives each track a channel of its own.
MSG_AUTO_CHANNEL_SHOWN = '(auto)'
MSG_OWN_GROOVE_SHOWN = 'yours'

# tui/screens/set/groove_editor.py
MSG_GROOVE_NAME_SHOWN = '  {label}: {name}'

# tui/screens/arrange/groove_choice.py: the Groove field on the Song, Scene and Track pages
MSG_GROOVE_OFF_SHOWN = 'off'
MSG_SONG_GROOVE_SHOWN = '{groove} (from song)'
MSG_FROM_TRACK_SHOWN = '{value} (from track)'
MSG_FROM_SET_SHOWN = '{value} (from set)'
MSG_SCENE_OR_SONG_GROOVE_SHOWN = '(scene or song)'

# tui/screens/shared/list_page.py and tui/screens/arrange/arrange_page.py
# The row at the bottom of a list that adds to it, and the cell on Arrange that adds a scene or a track.
MSG_ADD_ROW_MARK = '+'


# composition/progressions.py: the marks of a chord's Roman numeral: a sharp or flat in front, and after it what its quality adds.
MSG_ACCIDENTAL_MARKS = {Accidental.SHARP: '♯', Accidental.FLAT: '♭'}
MSG_QUALITY_MARKS = {Quality.MAJOR: '', Quality.MINOR: '', Quality.DIMINISHED: '°', Quality.AUGMENTED: '+'}
# composition/chords.py: what follows a chord's root in its short name, by its symbol, and how its tensions are shown after that.
MSG_CHORD_SUFFIXES = {
    ChordSymbol.MAJOR: '', ChordSymbol.MINOR: 'm', ChordSymbol.DIMINISHED: '°', ChordSymbol.AUGMENTED: '+', ChordSymbol.SUS2: 'sus2',
    ChordSymbol.SUS4: 'sus4', ChordSymbol.POWER: '5', ChordSymbol.MAJOR6: '6', ChordSymbol.MINOR6: 'm6', ChordSymbol.DOMINANT7: '7',
    ChordSymbol.MAJOR7: 'M7', ChordSymbol.MINOR7: 'm7', ChordSymbol.MINOR_MAJOR7: 'mM7', ChordSymbol.DIMINISHED7: '°7',
    ChordSymbol.HALF_DIMINISHED7: 'm7b5', ChordSymbol.AUGMENTED7: '+7', ChordSymbol.AUGMENTED_MAJOR7: '+M7', ChordSymbol.DOMINANT7_SUS4: '7sus4',
    ChordSymbol.ADD9: 'add9', ChordSymbol.MINOR_ADD9: 'madd9', ChordSymbol.DOMINANT9: '9', ChordSymbol.MAJOR9: 'M9', ChordSymbol.MINOR9: 'm9',
    ChordSymbol.DOMINANT11: '11', ChordSymbol.MAJOR11: 'M11', ChordSymbol.MINOR11: 'm11',
    ChordSymbol.DOMINANT13: '13', ChordSymbol.MAJOR13: 'M13', ChordSymbol.MINOR13: 'm13',
}
MSG_UNNAMED_CHORD_SUFFIX = '?'
# tui/keyswitch_text.py, tui/components/keyswitch_row.py and tui/dialogs/keyswitch_dialog.py: a keyswitch's note with its MIDI number, a slot with no name,
# a step's keyswitches joined in words, and a slot's row in the dialog that picks a step's: its number, its toggle, its name and its note.
MSG_KEYSWITCH_NOTE = '{name} ({number})'
MSG_KEYSWITCH_SLOT_NAMED = 'slot {slot}'
MSG_KEYSWITCH_SEPARATOR = ', '
MSG_KEYSWITCH_SLOT_ROW = '{slot:>2}   {toggle}   '
# tui/dialogs/keyswitch_map_dialog.py: a slot's row in an instrument's Keyswitch Map, its number before its name and note.
MSG_KEYSWITCH_MAP_ROW = ' {slot:>2}  '
# tui/screens/set/instrument_editor.py: how many of an instrument's keyswitch slots hold anything, and its keyswitch lead.
MSG_KEYSWITCH_LEAD_SHOWN = '{milliseconds} ms'

# tui/components/tension_row.py: a step's tensions in a cell, and how many when they don't fit.
MSG_TENSIONS_IN_CELL_SEPARATOR = ' '
MSG_TENSIONS_COUNTED = '{count} set'
MSG_CHORD_SYMBOL_NAMED = '{symbol:<6}{name}'
MSG_NOTES_SEPARATOR = ' '
MSG_SCALE_NAMED = '{root} {kind}'
MSG_CHORD_TENSIONS_SHOWN = '({tensions})'
MSG_TENSION_SEPARATOR = ','
MSG_SHARP_SPELLED = '#'
MSG_FLAT_SPELLED = 'b'
# How a progression's chords are listed, by their numerals, and the numerals of a named progression in its picker.
MSG_NUMERALS_SEPARATOR = ' '
MSG_PRESET_NUMERALS_SEPARATOR = '–'

# tui/screens/generators/generators_page.py: a generator's kind beside its name on the Generators page.
MSG_GENERATOR_KIND_SHOWN = '({kind})'

# tui/screens/generators/guitarify_editor.py, tui/screens/generators/guitar_bar_editor.py: a Guitarify's values, and what each stroke is drawn as in its cell.
MSG_GUITAR_OPEN_POSITION = 'open'
MSG_GUITAR_FRET = 'fret {fret}'
MSG_GUITAR_NO_CAPO = '(none)'
MSG_GUITAR_MILLISECONDS = '{milliseconds} ms'
MSG_GUITAR_EVERY_STRING = 'all'
MSG_GUITAR_BAR_SHOWN = '{name}, {count} cells of {cell}'
MSG_STROKE_MARKS = {
    Stroke.NOTHING: '—', Stroke.DOWN: '↓', Stroke.UP: '↑', Stroke.MUTE: 'x', Stroke.STAB: '!', Stroke.BASS: 'B', Stroke.MUTED_BASS: 'b', Stroke.ALT_BASS: 'A', Stroke.SQUEAL: '^',
    Stroke.STRING_1: '1', Stroke.STRING_2: '2', Stroke.STRING_3: '3', Stroke.STRING_4: '4',
}

# tui/screens/wizard/wizard_page.py and the branches beside it
MSG_WIZARD_CHOOSE = '(choose)'
MSG_WIZARD_NEEDS_GENRE = '(genre?)'
MSG_WIZARD_BRANCH_OPEN = '▾'
MSG_WIZARD_BRANCH_CLOSED = '▸'
MSG_WIZARD_EDITED_BRANCH = '◀'
MSG_WIZARD_TEMPO_SHOWN = '{tempo}  (usual {low} to {high})'
MSG_WIZARD_KEY_SHOWN = '{root} {scale}'
MSG_WIZARD_GENRE_SHOWN = '{genre}, {subgenre}'
MSG_WIZARD_SECTION_VARIANT = '{kind} {letter}'
MSG_WIZARD_SECTION_NUMBERED = '{kind}-{number}'
MSG_WIZARD_OWN_FORM = 'your own'
MSG_WIZARD_BAND_SOUND_SHOWN = '{sound} (from band)'
MSG_WIZARD_ROLE_FROM_PLAN = '{way} (from plan)'
MSG_WIZARD_FROM_BAND = 'from band ({sound})'
MSG_WIZARD_SUGGESTED_FORM = '{form}: {count} sections, {length}'
MSG_WIZARD_CARRIED = '<{name}>'
MSG_WIZARD_FILLS_SHOWN = '{gauge}  {often}'
MSG_WIZARD_BUSY_SHOWN = '{gauge}  {level} of {most}'
# The Busy field of a player whose own gauges were moved from the preset, and one of those gauges.
MSG_WIZARD_BUSY_CUSTOM_SHOWN = '{gauge}  {level} of {most} (custom)'
MSG_WIZARD_PLAYER_GAUGE_SHOWN = '{gauge}  {place}'
# A player's loudness level the genre gives, where the song has not chosen its own.
MSG_WIZARD_LEVEL_FROM_GENRE = '{number} (from genre)'
# A kit piece that plays its own drum or another of the kit, and a note by its name and octave.
MSG_WIZARD_OWN_DRUM_SHOWN = '{piece}'
MSG_WIZARD_KIT_DRUM_SHOWN = '{drum} (kit)'
MSG_NOTE_NAME_SHOWN = '{name}{octave}'
# A kit piece in a General MIDI sound, with its note, the Sound dialog's Note row, and a note being typed there.
MSG_WIZARD_SOUND_ON_NOTE = '{sound}  {note}'
MSG_SOUND_NOTE_ROW = 'Note   {note}'
MSG_SOUND_NOTE_TYPED = 'Note   {text}_'
MSG_WIZARD_MELODY_GAUGE_SHOWN = '{gauge}  {low} to {high}'
MSG_WIZARD_GAUGE_FULL = '█'
MSG_WIZARD_GAUGE_EMPTY = '░'
MSG_WIZARD_LENGTH_SHOWN = '{length}  ({form})'
MSG_WIZARD_FORM_SHOWN = '{form}: {count} sections'
# The Chords panel: a progression with its numerals, the key its chords are spelled in, a kind of section's chords, and what follows a chord's root.
MSG_WIZARD_PROGRESSION_SHOWN = '{name} ({numerals})'
# The Row dialog: a level's number at the left of its line, a cell's bar and the zero line of a row that goes under zero.
MSG_ROW_DIALOG_LEVEL = '{level:>4} '
MSG_ROW_DIALOG_BAR = '█'
MSG_ROW_DIALOG_ZERO = '─'
# A player's row of numbers on the wizard's panel, the genre's own marked so.
MSG_WIZARD_ROW_SHOWN = '{row}'
MSG_WIZARD_GENRE_ROW_SHOWN = '{row}  (from genre)'
MSG_WIZARD_ROW_SEPARATOR = ' '
MSG_WIZARD_PROGRESSION_FOR = '{progression} for {scale}'
MSG_WIZARD_GENRE_MELODY_SHOWN = '{style} (from genre)'
MSG_WIZARD_CHORDS_KEY = 'in {root} {scale}'
MSG_WIZARD_CHORDS_LINE = '{kind:<{width}}  {chords}'
MSG_WIZARD_CHORD_SEPARATOR = '  '
MSG_WIZARD_CHORD_SUFFIXES = {Quality.MAJOR: '', Quality.MINOR: 'm', Quality.DIMINISHED: '°', Quality.AUGMENTED: '+'}
# The Hooks panel's picture of the hook: a row for each note the hook plays, the highest first, a bar line between bars, and under the rows the beats of each bar.
MSG_WIZARD_HOOK_ROW = '{name:<{width}} {cells}'
MSG_WIZARD_HOOK_CELL = '▓'
MSG_WIZARD_HOOK_GAP = ' '
MSG_WIZARD_HOOK_BAR_LINE = '│'
MSG_WIZARD_HOOK_FLOOR = '─'
MSG_WIZARD_HOOK_FLOOR_BAR = '┴'
# The Tune dialog: the mark under the cursor's step, the shading of the note under the cursor, and what the cursor is on.
MSG_TUNE_CURSOR = '▲'
# The Lines dialog: a line's row, what the cursor's line is, and its values.
MSG_LINES_ROW = '{number:>2}  {cells}  {player}'
MSG_LINES_SILENT = 'nobody plays this line'
MSG_LINES_LINE_SAID = 'Line {number}: {player}'
MSG_LINES_HOOK_SAID = 'Line {number}: {player}, the hook'
MSG_LINES_BREATH_OWN = '{eighths} eighths'
MSG_LINES_FROM_MELODY = '(from melody)'
MSG_LINES_SAME_IDEA = '(as the line the idea came from)'
MSG_LINES_COUNT = '{count}'
MSG_LINES_COUNT_OWN = '{count} ({own} your own)'
MSG_LINES_FIELD = '{label:<12} {value}'
MSG_TUNE_CURSOR_NOTE = '▒'
MSG_TUNE_NOTE_SAID = 'step {step} of {steps}: {note}, {length} long'
MSG_TUNE_REST_SAID = 'step {step} of {steps}: silent'
MSG_WIZARD_COMPOSITION_LINE = '{name:<{width}}  {value}'
MSG_WIZARD_SECTION_LINE = '{number:>2}  {name:<{width}}  {bars:>3} bars'
