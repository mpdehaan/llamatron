# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""What each key is called and what each key does, as the legend at the bottom of a page and the F1 dialog say.

Each constant starts with MSG_, and the class What groups what the keys many pages share are said to do.
"""



class KeyName:
    """What each key, and each group of keys bound together, is called in a legend and in the F1 dialog.

    A key is named here once, and interface/tracker/keybindings.py gives each binding its name from these.
    """

    TAB = 'Tab'
    ENTER = 'ENTER'
    BACKSPACE = 'Bksp'
    SPACE = 'Space'
    ESCAPE = 'ESC'
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
    F5 = 'F5'
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
    J = 'J'
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
    TO_THE_RIGHT = '→'
    TO_THE_LEFT = '←'
    ENTER_ESC_M = 'ENTER/ESC/M'
    SPACE_ENTER = 'Space/ENTER'
    TAB_SHIFT_TAB = 'Tab/Shift+Tab'
    MINUS_EQUALS = '-/='
    BRACKETS = '[/]'
    HOME_END = 'Home/End'
    PAGE_UP_DOWN = 'PgUp/PgDn'
    TAB_ARROWS = 'Tab/←→'
    ENTER_ESCAPE = 'ENTER/ESC'
    # The keys that type into a search, in a picker or on a list page, and the keys that type a number or a note.
    SEARCH_CHARACTERS = 'A-Z 0-9'
    DIGITS = '0-9'
    NOTE_LETTERS = 'A-G'


# interface/tracker/screens/arrange/arrange_page.py
# What the Arrange page's keys do, on a scene, a track or a clip. C copies everywhere:
# a scene or track in place, and a clip to be pasted with V.
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
# The piano roll's [ and ], which drag a note's end: Shrink and stretch, where every other value steps dec and inc.
MSG_SHRINK_WHAT = 'shrink'
MSG_STRETCH_WHAT = 'stretch'
MSG_ADD_PATTERN_WHAT = 'add pattern'
MSG_MOVE_PATTERN_WHAT = 'move pattern'
MSG_OPEN_PATTERN_WHAT = 'jump to pattern'
MSG_COPY_CLIP_WHAT = 'copy clip'
MSG_DELETE_CLIP_WHAT = 'delete clip'
MSG_PASTE_CLIP_WHAT = 'paste clip'
MSG_ONE_STEP_WHAT = 'one step'
MSG_USE_SONG_SCALE_WHAT = 'use the song scale'
MSG_USE_SCENE_SCALE_WHAT = 'use the scene scale'
MSG_USE_SONG_TEMPO_WHAT = 'use the song tempo'
MSG_RAMP_BLANK_WHAT = 'leave blank'
MSG_USE_PATTERN_NAME_WHAT = 'use pattern name'
MSG_NO_GENERATOR_WHAT = 'no generator'
MSG_USE_PATTERN_DIRECTION_WHAT = "use the pattern's"
MSG_NO_MORPH_WHAT = 'no morph'
MSG_NO_GRAB_WHAT = 'no grab'

# interface/tracker/key_table.py and interface/tracker/keybindings.py: the key names, and the words every page shares

# AboutDialog: the cowsay cow saying the program's name, then the version, the links, a quote and the license.
# One line of a key legend: how a key's label and what it does are spaced.
MSG_LEGEND_LABEL = ' {label} '
MSG_LEGEND_WHAT = ' {what}  '


class What:
    """What the keys that many pages share are said to do, in their legends."""

    HELP = 'HELP'
    BACK = 'back'
    MOVE = 'move'
    # Move mode: M picks up what the cursor is on, the arrows carry it, and ENTER, ESC or M drops it.
    CARRY = 'carry'
    DROP = 'drop'
    ENDS = 'ends'
    SELECT = 'select'
    SCROLL = 'scroll'
    CHOOSE = 'choose'
    CANCEL = 'CANCEL'
    CLOSE = 'close'
    START = 'start'
    DONE = 'done'
    ERASE = 'erase'
    YES = 'YES'
    NO = 'NO'
    OTHER_PAGE = 'other page'
    OTHER_PANEL = 'other panel'
    ANSWER = 'answer'
    ADD = 'add'
    INSERT = 'insert'
    EDIT = 'edit'
    OPEN = 'open'
    CHANGE = 'change'
    WHEN = 'when'
    COPY = 'copy'
    DELETE = 'delete'
    REMOVE = 'remove'
    RENAME = 'rename'
    SORT = 'sort'
    TOGGLE = 'toggle'
    # [ and ] on every value that steps.
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
    # The keys every page has, in capitals, so that they stand out from a page's own.
    SAVE = 'SAVE'
    OPEN_SET = 'OPEN'
    UNDO = 'UNDO'
    REDO = 'REDO'
    EXPORT = 'EXPORT'
    IMPORT_MIDI = 'LOAD MIDI'
    QUIT = 'QUIT'
    ABOUT = 'ABOUT'
    # Ctrl+T, the emergency stop: note offs, all notes off and all sound off on every channel the instruments use.
    SILENCE = 'SILENCE'
    QUIT_NOW = 'QUIT NOW'
    # F5, the song wizard, which makes a whole song from a few choices.
    WIZARD = 'WIZARD'


# interface/tracker/screens/shared/list_page.py and interface/tracker/screens/shared/field_page.py

# interface/tracker/screens/set/main_page.py, interface/tracker/screens/set/file_page.py and interface/tracker/screens/shared/everywhere.py
# The main screen's footer says help and about in lower case like the rest of a legend, where the F1 dialog's capitals would shout.
MSG_HELP_FOOTER_WHAT = 'help'
MSG_ABOUT_FOOTER_WHAT = 'about'
# What the File/Global page's keys do.
MSG_NEW_WHAT = 'new'
MSG_SAVE_AS_WHAT = 'save as'

# interface/tracker/dialogs/import_dialog.py
MSG_IMPORT_WHAT = 'import'
MSG_PRESS_WHAT = 'press'

# interface/tracker/screens/arrange/arrange_page.py: the visualizer key, and ESC while it shows, which brings the clips back.
MSG_VISUALIZER_WHAT = 'visualizer'
MSG_STEP_VISUALIZER_WHAT = 'mode'
MSG_SHOW_DETAILS_WHAT = 'details'
MSG_FRACTURE_WHAT = 'fracture'
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

# interface/tracker/screens/arrange/track_editor.py
MSG_SONG_WHAT = 'song {name}'
MSG_MAKE_CURRENT_WHAT = 'make current'
# The notes page.
MSG_NEW_LINE_WHAT = 'new line'
MSG_TO_BUTTONS_WHAT = 'Save or CANCEL'
MSG_TO_TEXT_WHAT = 'back to the text'
# How an item is named when deleting it, like "pattern tune".
MSG_PATTERN_WHAT = 'pattern {name}'
MSG_SCALE_WHAT = 'scale {name}'
MSG_GENERATOR_WHAT = '{label} {name}'
MSG_NO_DEFAULT_VELOCITY_WHAT = 'default'
MSG_NO_TRANSPOSE_WHAT = 'no transpose'
MSG_WHOLE_RANGE_WHAT = 'whole range'
MSG_NO_CC_WHAT = 'none'
MSG_UNBIND_WHAT = 'unbind'
# The offsets editor: a one-row grid with a label column this wide, and a margin around it.
MSG_NEXT_ROW_WHAT = 'next row'
# A settings page's tab box: on the row of tabs, the keys that choose a tab, and Tab, which goes to the row of tabs.
MSG_TAB_WHAT = 'tab'
MSG_TO_TABS_WHAT = 'to tabs'
MSG_SILENT_WHAT = 'silent'
MSG_PLAY_WHAT = 'play'

# interface/tracker/screens/arrange/arrange_page.py, interface/tracker/screens/arrange/clip_page.py and interface/tracker/screens/pattern/pattern_editor.py: real-time playback.
MSG_PLAY_SONG_WHAT = 'play song'
MSG_PLAY_SCENE_WHAT = 'play scene'
MSG_PLAY_CLIP_WHAT = 'play clip'
MSG_STOP_WHAT = 'stop'
MSG_STOP_CLIP_WHAT = 'stop clip'
MSG_LISTEN_WHAT = 'listen'
# What Bksp does on a player's loudness level of the song's own.
MSG_FROM_GENRE_WHAT = 'from genre'
MSG_OWN_DRUM_WHAT = 'own drum'
MSG_FROM_PLAN_WHAT = 'from plan'
MSG_TYPE_NOTE_WHAT = 'type a note'
# interface/tracker/keybindings.py: the Patterns page's groups.
MSG_GROUP_WHAT = 'group'
MSG_NEXT_GROUP_WHAT = 'next group'
MSG_NEXT_TYPE_WHAT = 'next type'
MSG_NEW_PATTERN_WHAT = 'new pattern'
MSG_NEW_GROUP_WHAT = 'new group'
MSG_UNGROUP_WHAT = 'ungroup'
# Padded to the width of listen, so that the legend's keys stay where they are while a clip plays.
MSG_STOP_LISTENING_WHAT = 'stop'.ljust(len(MSG_LISTEN_WHAT))

# interface/tracker/screens/pattern/pattern_editor.py, its two drawings and the rows in interface/tracker/components/
# What a section's row does with Space or ENTER, and what Tab does.
MSG_OPEN_SECTION_WHAT = 'open section'
MSG_CLOSE_SECTION_WHAT = 'close section'
MSG_NEXT_SECTION_WHAT = 'next section'
MSG_CHORD_WHAT = 'chord'
MSG_NEXT_LIST_WHAT = 'next list'
# What the piano roll's keys do.
MSG_PLACE_NOTE_WHAT = 'note'
MSG_SPLIT_WHAT = 'split'
MSG_KEYSWITCH_WHAT = 'keyswitch'
MSG_KEYSWITCH_MAP_WHAT = 'keyswitch map'
MSG_KEYSWITCH_NOTE_WHAT = 'note'
MSG_KEYSWITCH_OCTAVE_WHAT = 'octave'
MSG_KEYSWITCH_NAME_WHAT = 'name'
MSG_OK_WHAT = 'OK'
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
MSG_SCALE_LENGTH_WHAT = 'scale length'
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

# interface/tracker/screens/set/registers_page.py
MSG_REGISTER_ENTER_WHAT = 'type'
MSG_REGISTER_CLEAR_WHAT = 'default'

# interface/tracker/screens/set/grooves_page.py
MSG_GROOVE_WHAT = 'groove {name}'
MSG_INSTRUMENT_WHAT = 'instrument {name}'
MSG_NO_INSTRUMENT_WHAT = 'no instrument'
MSG_NO_DEVICE_WHAT = 'no device'
MSG_NO_GM_SOUND_WHAT = 'no sound'
MSG_NO_TRACK_WHAT = 'no track'
MSG_VIEW_WHAT = 'view'

# interface/tracker/screens/set/groove_editor.py
MSG_CELL_LENGTH_WHAT = 'cell length'
MSG_ACCENT_WHAT = 'accent'
MSG_READY_BARS_WHAT = 'ready-made'

# interface/tracker/screens/arrange/groove_choice.py: the Groove field on the Song, Scene and Track pages
MSG_USE_SONG_GROOVE_WHAT = 'use the song groove'
MSG_USE_SCENE_GROOVE_WHAT = 'use the scene or song groove'

# interface/tracker/keybindings.py, the chord editor: H fills it with a named progression.
MSG_PICK_PROGRESSION_WHAT = 'pick progression'

# interface/tracker/keybindings.py, on a mask's Hits field: H fills the hits and steps with a named rhythm.

# interface/tracker/screens/wizard/wizard_page.py
MSG_WIZARD_FOLD_WHAT = 'fold'
MSG_WIZARD_TO_TREE_WHAT = 'to tree'
MSG_WIZARD_CREATE_WHAT = 'apply'
MSG_WIZARD_SUGGESTED_FORM_WHAT = 'choose'
MSG_WIZARD_FORM_QUESTIONS_WHAT = 'answer'
MSG_WIZARD_NEW_HOOK_WHAT = 'new hook'
MSG_USUAL_ROW_WHAT = 'usual row'
MSG_TUNE_USUAL_WHAT = "wizard's notes"
MSG_WIZARD_FROM_GENRE_WHAT = 'from genre'
MSG_WIZARD_EDIT_NOTES_WHAT = 'edit notes'
MSG_REGENERATE_WHAT = 'regenerate'
MSG_WRITE_RIFF_WHAT = 'write riff'
