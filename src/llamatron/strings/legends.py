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
"""What each key is called and what each key does, as the legend at the bottom of a page and the F1 dialog say.

Each constant starts with MSG_, and the class What groups what the keys many pages share are said to do.
"""



class KeyName:
    """What each key, and each group of keys bound together, is called in a legend and in the F1 dialog.

    A key is named here once, and tui/keybindings.py gives each binding its name from these.
    """

    TAB = 'Tab'
    ENTER = 'Enter'
    BACKSPACE = 'Bksp'
    SPACE = 'Space'
    ESCAPE = 'Esc'
    CTRL_S = 'Ctrl+S'
    CTRL_O = 'Ctrl+O'
    CTRL_X = 'Ctrl+X'
    CTRL_T = 'Ctrl+T'
    CTRL_C = 'Ctrl+C'
    CTRL_Z = 'Ctrl+Z'
    CTRL_Y = 'Ctrl+Y'
    F1 = 'F1'
    F2 = 'F2'
    F3 = 'F3'
    N_F2 = 'N/F2'
    # A letter is shown in upper case, though no key needs Shift.
    A = 'A'
    B = 'B'
    C = 'C'
    D = 'D'
    E = 'E'
    F = 'F'
    G = 'G'
    H = 'H'
    I = 'I'
    K = 'K'
    L = 'L'
    M = 'M'
    N = 'N'
    O = 'O'
    P = 'P'
    Q = 'Q'
    R = 'R'
    S = 'S'
    T = 'T'
    V = 'V'
    W = 'W'
    X = 'X'
    Y = 'Y'
    Z = 'Z'
    PERIOD = '.'
    SLASH = '/'
    LEFT_BRACKET = '['
    RIGHT_BRACKET = ']'
    # Groups of keys, where listing each key would be too long.
    ARROWS = '←↑↓→'
    UP_DOWN = '↑↓'
    LEFT_RIGHT = '←→'
    ENTER_ESC_M = 'Enter/Esc/M'
    SPACE_ENTER = 'Space/Enter'
    TAB_SHIFT_TAB = 'Tab/Shift+Tab'
    MINUS_EQUALS = '-/='
    BRACKETS = '[/]'
    HOME_END = 'Home/End'
    PAGE_UP_DOWN = 'PgUp/PgDn'
    TAB_ARROWS = 'Tab/←→'
    ENTER_ESCAPE = 'Enter/Esc'
    # The keys that type into a search, in a picker or on a list page, and the keys that type a number or a note.
    SEARCH_CHARACTERS = 'A-Z 0-9'
    DIGITS = '0-9'
    NOTE_LETTERS = 'A-G'


# tui/screens/arrange_page.py
# What the Arrange page's keys do, on a scene, a track or a clip. C copies everywhere, as the user chose on
# 2026-11-07: a scene or track in place, and a clip to be pasted with V.
MSG_ADD_SCENE_WHAT = 'add scene'
MSG_SCENE_SETTINGS_WHAT = 'scene settings'
MSG_COPY_SCENE_WHAT = 'copy scene'
MSG_INSERT_SCENE_WHAT = 'insert scene'
MSG_MOVE_SCENE_WHAT = 'move scene'
MSG_MOVE_CLIP_WHAT = 'move clip'
MSG_QUIT_WITHOUT_SAVING_WHAT = 'quit without saving'
MSG_SAVE_THEN_QUIT_WHAT = 'save, then quit'
MSG_BLANK_PATTERN_WHAT = 'blank pattern'
MSG_ADD_CHAIN_WHAT = 'add chain'
MSG_REMOVE_CHAIN_WHAT = 'remove chain'
MSG_DELETE_SCENE_WHAT = 'delete scene'
MSG_ADD_TRACK_WHAT = 'add track'
MSG_TRACK_SETTINGS_WHAT = 'track settings'
MSG_COPY_TRACK_WHAT = 'copy track'
MSG_INSERT_TRACK_WHAT = 'insert track'
MSG_MOVE_TRACK_WHAT = 'move track'
MSG_DELETE_TRACK_WHAT = 'delete track'
MSG_ADD_CLIP_WHAT = 'add clip'
MSG_EDIT_CLIP_WHAT = 'edit clip'
# The piano roll's [ and ], which drag a note's end: the user's words, shrink and stretch (2026-11-09), where every other value steps dec and inc.
MSG_SHRINK_WHAT = 'shrink'
MSG_STRETCH_WHAT = 'stretch'
MSG_OPEN_PATTERN_WHAT = 'pattern'
MSG_COPY_CLIP_WHAT = 'copy clip'
MSG_DELETE_CLIP_WHAT = 'delete clip'
MSG_PASTE_CLIP_WHAT = 'paste clip'
MSG_ONE_STEP_WHAT = 'one step'
MSG_USE_SONG_SCALE_WHAT = 'use the song scale'
MSG_USE_SCENE_SCALE_WHAT = 'use the scene scale'
MSG_USE_SONG_TEMPO_WHAT = 'use the song tempo'
MSG_NO_RAMP_WHAT = 'no ramp'
MSG_USE_PATTERN_NAME_WHAT = 'use pattern name'
MSG_NO_CHAIN_WHAT = 'no chain'
MSG_USE_PATTERN_DIRECTION_WHAT = "use the pattern's"
MSG_NO_MORPH_WHAT = 'no morph'
MSG_NO_GRAB_WHAT = 'no grab'

# tui/key_table.py and tui/keybindings.py: the key names, and the words every page shares

# AboutDialog: the cowsay cow saying the program's name, then the version, the links, a quote and the license.
# One line of a key legend: how a key's label and what it does are spaced.
MSG_LEGEND_LABEL = ' {label} '
MSG_LEGEND_WHAT = ' {what}  '


class What:
    """What the keys that many pages share are said to do, in their legends."""

    HELP = 'HELP'
    BACK = 'back'
    MOVE = 'move'
    # Move mode, the user's design: M picks up what the cursor is on, the arrows carry it, and Enter, Esc or M drops it.
    CARRY = 'carry'
    DROP = 'drop'
    ENDS = 'ends'
    SELECT = 'select'
    SCROLL = 'scroll'
    CHOOSE = 'choose'
    CANCEL = 'cancel'
    CLOSE = 'close'
    START = 'start'
    DONE = 'done'
    ERASE = 'erase'
    YES = 'yes'
    NO = 'no'
    OTHER_PAGE = 'other page'
    OTHER_PANEL = 'other panel'
    ANSWER = 'answer'
    ADD = 'add'
    EDIT = 'edit'
    OPEN = 'open'
    CHANGE = 'change'
    COPY = 'copy'
    DELETE = 'delete'
    REMOVE = 'remove'
    RENAME = 'rename'
    SORT = 'sort'
    TOGGLE = 'toggle'
    # [ and ] on every value that steps, the user's words of 2026-11-09.
    MORE = 'inc'
    LESS = 'dec'
    TYPE = 'type'
    SEARCH = 'search'
    COMPLETE = 'complete'
    KEEP = 'keep'
    CLEAR = 'clear'
    DEFAULT = 'default'
    NEXT = 'next'
    SETTINGS = 'settings'
    INSERT_STEP = 'insert step'
    REMOVE_STEP = 'remove step'
    INSERT_CELL = 'insert cell'
    REMOVE_CELL = 'remove cell'
    MUNGE = 'munge'
    # The keys every page has, in capitals as the user asked, so that they stand out from a page's own.
    SAVE = 'SAVE'
    OPEN_SET = 'OPEN'
    UNDO = 'UNDO'
    REDO = 'REDO'
    EXPORT = 'EXPORT'
    IMPORT_MIDI = 'IMPORT MIDI'
    QUIT = 'QUIT'
    ABOUT = 'ABOUT'
    # Ctrl+T, the emergency stop: note offs, all notes off and all sound off on every channel the instruments use.
    SILENCE = 'SILENCE'
    QUIT_NOW = 'QUIT NOW'


# tui/screens/list_page.py and tui/screens/field_page.py

# tui/screens/main_page.py, tui/screens/file_page.py and tui/screens/everywhere.py
# The main screen's footer says help and about in lower case like the rest of a legend, where the F1 dialog's capitals would shout.
MSG_HELP_FOOTER_WHAT = 'help'
MSG_ABOUT_FOOTER_WHAT = 'about'
# What the Set File page's keys do.
MSG_NEW_WHAT = 'new'
MSG_SAVE_AS_WHAT = 'save as'

# tui/dialogs/import_dialog.py
MSG_IMPORT_WHAT = 'import'
MSG_PRESS_WHAT = 'press'

# tui/screens/arrange_page.py: the visualizer key, and Esc while it shows, which brings the clips back.
MSG_VISUALIZER_WHAT = 'visualizer'
MSG_STEP_VISUALIZER_WHAT = 'mode'
MSG_SHOW_DETAILS_WHAT = 'details'
MSG_HIDE_DETAILS_WHAT = 'hide details'
MSG_INTO_DETAILS_WHAT = 'cell details'
MSG_OUT_OF_DETAILS_WHAT = 'leave the cell'
MSG_OPEN_DETAIL_WHAT = 'open'
MSG_CLOSE_DETAILS_WHAT = 'close details'
MSG_SCENE_VIEW_WHAT = 'scene view'
MSG_CLOSE_INSET_WHAT = 'close'
MSG_TO_PLAYED_WHAT = 'played'
MSG_TO_WRITTEN_WHAT = 'written'
MSG_CLOSE_INSET_ESC_WHAT = 'close'
MSG_ZOOM_WHAT = 'zoom'
MSG_JUMP_BAR_WHAT = 'bar'
MSG_SCROLL_SIDEBAR_WHAT = 'scroll tracks'
MSG_LEAVE_CELL_WHAT = 'leave cell'
MSG_TO_CLIPS_WHAT = 'to clips'

# tui/screens/track_editor.py
MSG_SONG_WHAT = 'song {name}'
MSG_MAKE_CURRENT_WHAT = 'make current'
# The notes page.
MSG_NEW_LINE_WHAT = 'new line'
MSG_TO_BUTTONS_WHAT = 'Save or Cancel'
MSG_TO_TEXT_WHAT = 'back to the text'
# How an item is named when deleting it, like "pattern tune".
MSG_PATTERN_WHAT = 'pattern {name}'
MSG_SCALE_WHAT = 'scale {name}'
MSG_CHAIN_WHAT = 'chain {name}'
MSG_GENERATOR_WHAT = '{label} {name}'
MSG_NO_TRANSPOSE_WHAT = 'no transpose'
MSG_WHOLE_RANGE_WHAT = 'whole range'
MSG_NO_CC_WHAT = 'none'
MSG_UNBIND_WHAT = 'unbind'
MSG_USE_SONG_SEED_WHAT = 'use the song seed'
# The offsets editor: a one-row grid with a label column this wide, and a margin around it.
MSG_NEXT_ROW_WHAT = 'next row'
MSG_A_OR_B_WHAT = 'A or B'
MSG_SILENT_WHAT = 'silent'
MSG_PLAY_WHAT = 'play'

# tui/screens/arrange_page.py, tui/screens/clip_page.py and tui/screens/pattern_editor.py: real-time playback.
MSG_PLAY_SONG_WHAT = 'play song'
MSG_PLAY_SCENE_WHAT = 'play scene'
MSG_PLAY_CLIP_WHAT = 'play clip'
MSG_STOP_WHAT = 'stop'
MSG_STOP_CLIP_WHAT = 'stop clip'
MSG_LISTEN_WHAT = 'listen'
# Padded to the width of listen, so that the legend's keys stay where they are while a clip plays.
MSG_STOP_LISTENING_WHAT = 'stop'.ljust(len(MSG_LISTEN_WHAT))

# tui/screens/pattern_editor.py, its two drawings and the rows in tui/components/
# What a section's row does with Space or Enter, and what Tab does.
MSG_OPEN_SECTION_WHAT = 'open section'
MSG_CLOSE_SECTION_WHAT = 'close section'
MSG_NEXT_SECTION_WHAT = 'next section'
MSG_CHORD_WHAT = 'chord'
MSG_NEXT_LIST_WHAT = 'next list'
# What the piano roll's keys do.
MSG_PLACE_NOTE_WHAT = 'note'
MSG_SPLIT_WHAT = 'split'
MSG_ACCIDENTAL_WHAT = '#/b'
MSG_GRAB_WHAT = 'grab'
MSG_ENTRY_SIZE_WHAT = 'entry size'
# How groups of typing keys are labelled, like 0-9 or 1-7.
MSG_DIGITS_RANGE_LABEL = '{low}-{high}'
MSG_LOAD_OVER_WHAT = 'load over'
MSG_SIZE_WHAT = 'size'
MSG_STEP_SIZE_WHAT = 'step size'
MSG_TIME_SIGNATURE_WHAT = 'time signature'
MSG_DRUM_ON_WHAT = 'drum on'
MSG_DRUM_OFF_WHAT = 'drum off'
MSG_DIRECTION_WHAT = 'direction'
# The roll's [ and ] drag a note's end shorter or longer.
# P opens the piano roll over the rows and closes it again.
MSG_TO_ROLL_WHAT = 'to piano roll'
MSG_TO_EDITOR_WHAT = 'to editor'
# The Reconfigure dialog (R) gathers the whole-pattern actions, so that the legend stays short; its choices are built from the words above.
MSG_RECONFIGURE_WHAT = 'reconfigure'
MSG_TYPE_OCTAVE_WHAT = 'type octave'
MSG_NOTE_WHAT = 'note'
MSG_DEGREE_WHAT = 'degree'
MSG_PATTERN_DIRECTION_WHAT = "use each pattern's direction"
MSG_LETTERS_WHAT = 'letters'
MSG_DEGREES_WHAT = 'scale degrees'

# tui/screens/registers_page.py
MSG_REGISTER_ENTER_WHAT = 'type'
MSG_REGISTER_CLEAR_WHAT = 'default'

# tui/screens/grooves_page.py
MSG_GROOVE_WHAT = 'groove {name}'
MSG_INSTRUMENT_WHAT = 'instrument {name}'
MSG_NO_INSTRUMENT_WHAT = 'no instrument'
MSG_NO_DEVICE_WHAT = 'no device'
MSG_NO_GM_SOUND_WHAT = 'no sound'
MSG_NO_SOURCE_WHAT = 'no source'
MSG_VIEW_WHAT = 'view'

# tui/screens/groove_editor.py
MSG_CELL_LENGTH_WHAT = 'cell length'

# tui/screens/groove_choice.py: the Groove field on the Song, Scene and Track pages
MSG_USE_SONG_GROOVE_WHAT = 'use the song groove'
MSG_USE_SCENE_GROOVE_WHAT = 'use the scene or song groove'

# tui/keybindings.py, the chord editor: H fills it with a named progression.
MSG_PICK_PROGRESSION_WHAT = 'pick progression'

# tui/keybindings.py, on a mask's Hits field: H fills the hits and steps with a named rhythm.
MSG_PICK_RHYTHM_WHAT = 'pick rhythm'
