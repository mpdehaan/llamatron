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

"""The plan of a video tutorial: the keys that rebuild a target set from a new one in the running tracker, worked out from the target as the build goes.

The user's design of 2026-11-10: a planner reads the set a demo file holds and presses the keys
a person would, so that any demo becomes a tutorial with nothing written by hand, and a test can
prove that what the keys built is the demo. The plan is a generator of steps, a Press of one key
or a Say of one sentence, and between two steps it reads the tracker's state, the page open and
where its cursor is, so that it never counts keys ahead: it presses an arrow, looks, and presses
again until the cursor is where the next key wants it, as a person does. Narration comes at the
parts worth a sentence, never at every key.

The build goes the way the user asked: the song's own settings, the scales, then one track at a
time, each track's clips scene by scene from the top, every pattern drawn on the piano roll when
the track first needs it and its finer rows set in the rows view after, then the clip put on
Arrange. Whatever the plan can't set yet is reported as left out, so a demo that uses more than
the plan knows still builds the rest.
"""

from llamatron.composition.file_format import Row, SceneSetting, Section, SongSetting, TrackSetting
from llamatron.composition.row_descriptions import ROW_DESCRIPTIONS
from llamatron.composition.limits import MIN_DEGREE
from llamatron.strings.labels import (
    MSG_CHANNEL_LABEL, MSG_DEVICE_LABEL, MSG_DRUM_LABEL, MSG_INSTRUMENT_LABEL, MSG_KIND_LABEL, MSG_LOOP_LABEL, MSG_MUTE_LABEL, MSG_NAME_LABEL,
    MSG_LAUNCH_TOGETHER_LABEL, MSG_PATTERN_LABEL, MSG_REPEAT_LABEL, MSG_ROOT_LABEL, MSG_GENRE_LABEL, MSG_SCALE_LABEL, MSG_TEMPO_LABEL, MSG_TIME_SIGNATURE_LABEL, MSG_TRANSPOSE_LABEL,
)
from llamatron.strings.narration import (
    MSG_A_DRUM_PATTERN, MSG_A_PATTERN, MSG_A_SCALE, MSG_A_SCENE, MSG_A_SONG, MSG_A_TRACK, MSG_AN_INSTRUMENT,
    MSG_CALL_LETTER, MSG_NARRATE_OPENING, MSG_NARRATE_TURNING_ON,
    MSG_EXPLAIN_ARROWS, MSG_EXPLAIN_ARROWS_IN_ROWS, MSG_EXPLAIN_ARROWS_ON_ROLL, MSG_EXPLAIN_ESCAPE, MSG_EXPLAIN_BACKSPACE_ON_ROLL, MSG_EXPLAIN_ENTER, MSG_EXPLAIN_SPACE_ON_ARRANGE,
    MSG_EXPLAIN_SPACE_ON_ROLL, MSG_EXPLAIN_SPACE_TOGGLES,
    MSG_LEFT_OUT_CLIP_SETTING, MSG_LEFT_OUT_PATTERN_SETTING, MSG_LEFT_OUT_ROW, MSG_LEFT_OUT_SCALE, MSG_LEFT_OUT_SCENE_SETTING, MSG_LEFT_OUT_SONG_SETTING,
    MSG_LEFT_OUT_TRACK_SETTING,
    MSG_NARRATE_CLIP, MSG_NARRATE_COMPLETE, MSG_NARRATE_DONE, MSG_NARRATE_EXPORT_KEY, MSG_NARRATE_GUIDE, MSG_NARRATE_MAKING, MSG_NARRATE_PATTERN_ROWS,
    MSG_NARRATE_PLAY, MSG_NARRATE_PLAY_LIVE, MSG_NARRATE_REAL_TIME, MSG_NARRATE_RENAMING, MSG_NARRATE_SONG, MSG_NARRATE_START,
    MSG_NARRATE_QUITTING, MSG_NARRATE_TUTORIAL_COMPLETE, MSG_NARRATE_WOULD_EXPORT,
)
from llamatron.strings.names import MSG_NEW_PATTERN_NAME
from llamatron.tui import keybindings
from llamatron.tui.components.chord_row import CHORD_SYMBOLS, ChordRow, chord_text
from llamatron.tui.components.cycle_row import CycleRow
from llamatron.tui.components.gate_row import GateRow
from llamatron.tui.components.number_row import NumberRow
from llamatron.tui.components.toggle_row import ToggleRow
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.grid_choice_dialog import GridChoiceDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.key_table import first_key
from llamatron.tui.keys import ARROWS, Key, SPACE_CHARACTER
from llamatron.tui.components.pattern_rows import PatternRows
from llamatron.tui.components.piano_roll import PianoRoll
from llamatron.tui.screens.arrange_page import ArrangePage, FIRST_TRACK_COLUMN, HEADER_ROW, SCENE_COLUMN
from llamatron.tui.dialogs.quit_dialog import QuitDialog
from llamatron.tui.screens.instruments_page import InstrumentsPage
from llamatron.tui.screens.main_page import cell_opened_by, MainPage
from llamatron.tui.screens.pattern_editor import PatternEditor, Reconfigure
from llamatron.tui.screens.patterns_page import PatternsPage
from llamatron.tui.screens.scale_page import scale_label
from llamatron.tui.screens.scales_page import ScalesPage
from llamatron.tui.screens.songs_page import SongsPage
from llamatron.tutorial.steps import Gap, Press, Say, Wait

# The song's settings the plan can set on the Song page, each by the label of its field, and whether its value is typed into a prompt (True) or chosen from a picker, which the plan tells apart by what Enter opens.
SONG_FIELDS = {
    SongSetting.TEMPO: (MSG_TEMPO_LABEL, True),
    SongSetting.TIME_SIGNATURE: (MSG_TIME_SIGNATURE_LABEL, True),
    SongSetting.SCALE: (MSG_SCALE_LABEL, False),
    SongSetting.GENRE: (MSG_GENRE_LABEL, True),
}
# The parts of a song's data that aren't settings of the Song page.
SONG_SECTIONS_BUILT = (Section.TRACKS, Section.SCENES, Section.REGISTERS)
# What the first Space says on each kind of page that has a sentence of its own, every other kind saying that Space toggles.
SPACE_EXPLAINED = {
    PianoRoll: (MSG_EXPLAIN_SPACE_ON_ROLL, MSG_EXPLAIN_BACKSPACE_ON_ROLL),
    ArrangePage: (MSG_EXPLAIN_SPACE_ON_ARRANGE,),
}
# What the first arrow says on the two kinds of page where the arrows are explained, the piano roll and the rows view.
ARROWS_EXPLAINED = {PianoRoll: MSG_EXPLAIN_ARROWS_ON_ROLL}
# The page each main screen cell the plan opens shows, which the plan goes back to with Esc when it is open already, rather than opening it again.
CELL_PAGES = {
    keybindings.MainPage.SONGS: SongsPage, keybindings.MainPage.SCALES: ScalesPage, keybindings.MainPage.PATTERNS: PatternsPage,
    keybindings.MainPage.ARRANGE: ArrangePage, keybindings.MainPage.INSTRUMENTS: InstrumentsPage,
}
# The seconds the tutorial waits once the song has played, before it goes back to the main screen and quits, the user's choice of 2026-11-10.
AFTER_THE_SONG_SECONDS = 2.0
# The rows the plan sets in the rows view: every row but the two the piano roll writes.
ROWS_SET_IN_THE_ROWS_VIEW = [name for name in ROW_DESCRIPTIONS if name not in (Row.DEGREE, Row.OCTAVE)]
# How many times the plan may press an arrow towards one place before it gives up, since a cursor that never arrives would loop for ever.
MOST_MOVES = 400
# Where a binding keeps the words its legend gives it.
WORDS = 2
# The first instrument's channel, and the number of the first instrument a tutorial adds.
FIRST_CHANNEL = 1
FIRST_INSTRUMENT = 1
# The first song of a new set is the one the tutorial builds.
FIRST = 0
STARTER_PATTERN = MSG_NEW_PATTERN_NAME.format(number=1)


def step_value(*, pattern, row, step):
    """Return a step's value on a row, a row the pattern leaves out reading as its blank, so that a row of all falses equals one not written."""
    value = pattern.get_value(row=row, step=step)
    return ROW_DESCRIPTIONS[row].blank() if value is None else value


def without_clips(scene_data):
    """Return a scene's data without its clips, which are built on their own."""
    return {setting: value for setting, value in scene_data.items() if setting != SceneSetting.TRACKS}


def grid_place(*, dialog, place):
    """Return the page, row and column of an option in a grid picker's pages."""
    for page, cells in enumerate(dialog.page_cells):
        for row in range(len(cells)):
            for column in range(len(cells[row])):
                if dialog.option_at(row=row, column=column, cells=cells) == place:
                    return page, row, column
    raise TutorialStuck(place)


def cell_place(*, rows, binding):
    """Return the row and the place along it of the main screen's cell bound from a binding."""
    for row, cells in enumerate(rows):
        for column, item in enumerate(cells):
            if item.binding == binding:
                return row, column
    raise TutorialStuck(binding)


class TutorialStuck(Exception):
    """The plan pressed arrows towards a place the cursor never reached, or found a page it didn't expect."""


def without_instrument(data):
    """Return a track's data without its instrument, which the tutorial never builds from the target: an example's instruments carry General MIDI sounds for the previews, and when the tutorial plays it makes instruments of its own."""
    return {setting: value for setting, value in data.items() if setting != TrackSetting.INSTRUMENT}


class TutorialPlan:
    """The steps that build a target set in a running tracker, read from the tracker's state as they go."""

    __slots__ = ('app', 'target', 'driver', 'left_out', 'instruments', 'explained', 'letters_called')

    def __init__(self, *, app, target, driver=None):
        """app is the running tracker, target the Setlist to build, and driver the name of the MIDI port to play through at the end, or None to build without playing."""
        self.app = app
        self.target = target
        self.driver = driver
        # What the plan found in the target and couldn't set, in the words of the report.
        self.left_out = []
        # The instrument made for each track, when there is a driver.
        self.instruments = {}
        # What has been explained once: each kind of page whose arrows or Space were, and Enter.
        self.explained = set()
        # The letters called out on each kind of page, which are called only the first time there.
        self.letters_called = set()

    def document(self):
        return self.app.get_document()

    def screen(self):
        return self.app.screen

    def target_song(self):
        return self.target.get_song(self.target.get_song_names()[FIRST])

    # The whole build.

    def steps(self):
        song = self.target_song()
        title = self.target.get_title() or self.target.get_song_names()[FIRST]
        yield Say(MSG_NARRATE_START.format(title=title))
        yield from self.build_scales()
        yield from self.set_up_song(song)
        yield from self.drop_spare_scales()
        for place, track in enumerate(song.get_track_names()):
            yield from self.build_track(song=song, track=track, place=place)
        yield from self.drop_starter_pattern()
        yield from self.show_the_finished_song()
        if self.driver is not None:
            yield Say(MSG_NARRATE_PLAY_LIVE)
            yield Say(MSG_NARRATE_EXPORT_KEY)
            yield Say(MSG_NARRATE_REAL_TIME)
            yield Say(MSG_NARRATE_GUIDE)
            yield from self.connect_instruments(song)
            yield from self.play()
            yield Say(MSG_NARRATE_DONE.format(title=title))
            yield Wait(until=self.song_has_ended, seconds=AFTER_THE_SONG_SECONDS)
        else:
            yield Say(MSG_NARRATE_WOULD_EXPORT)
            yield Say(MSG_NARRATE_TUTORIAL_COMPLETE)
        yield from self.quit()

    def song_has_ended(self):
        return not self.app.transport.is_playing()

    def quit(self):
        """Go back to the main screen and quit through the Quit cell, without saving, the user's design of 2026-11-10."""
        yield from self.go_home()
        yield Say(MSG_NARRATE_QUITTING)
        yield from self.open_page(keybindings.MainPage.QUIT, said=False)
        if isinstance(self.screen(), QuitDialog):
            yield from self.press(keybindings.QuitDialog.PRESS)

    def show_the_finished_song(self):
        """Show the finished song on Arrange for a sentence, then go back to the main screen."""
        yield from self.open_page(keybindings.MainPage.ARRANGE)
        yield Say(MSG_NARRATE_COMPLETE)
        yield from self.go_home()

    # Pressing keys and reading the screen.

    def press(self, *bindings):
        """Press each binding's first key, with what its legend says it does, or a key named as tui/keys.py names it."""
        for binding in bindings:
            if isinstance(binding, str):
                yield from self.pressing(binding)
            else:
                yield from self.pressing(first_key(binding), what=binding[WORDS])

    def type_text(self, text, *, in_dialog=False):
        """Type the text a key at a time, into a dialog when in_dialog says so, and never called out, since what is typed shows where it goes."""
        for character in text:
            yield from self.pressing(Key.SPACE if character == SPACE_CHARACTER else character, in_dialog=in_dialog, typed=True)

    def pressing(self, key, *, in_dialog=False, what=None, typed=False):
        """Return the steps of a key's press: what it says first, the user's design of 2026-11-10, and the press. The arrows, Enter and Space are explained once where they matter, a letter is called the first time on each kind of page with its legend's words, and what is typed is never called."""
        if in_dialog or typed:
            yield Press(key, in_dialog)
            return
        yield from self.explaining(key)
        yield Press(key, in_dialog, None if what is None else self.letter_call(key=key, what=what))

    def page_kind(self):
        """Return the kind of page open, which the pattern editor's two views each are on their own."""
        screen = self.screen()
        return type(screen.view()) if isinstance(screen, PatternEditor) else type(screen)

    def explaining(self, key):
        """Return the sentences that explain a key the first time it matters: the arrows the first time anywhere and again on the piano roll and in the rows view, Enter and Esc the first time anywhere, and Space once on each kind of page."""
        kind = self.page_kind()
        if key in ARROWS:
            if ARROWS not in self.explained:
                self.explained.add(ARROWS)
                yield Say(MSG_EXPLAIN_ARROWS)
            if kind in (PianoRoll, PatternRows) and (ARROWS, kind) not in self.explained:
                self.explained.add((ARROWS, kind))
                yield Say(ARROWS_EXPLAINED.get(kind, MSG_EXPLAIN_ARROWS_IN_ROWS))
        elif key == Key.ESCAPE and Key.ESCAPE not in self.explained:
            self.explained.add(Key.ESCAPE)
            yield Say(MSG_EXPLAIN_ESCAPE)
        elif key == Key.ENTER and Key.ENTER not in self.explained:
            self.explained.add(Key.ENTER)
            yield Say(MSG_EXPLAIN_ENTER)
        elif key == Key.SPACE and (Key.SPACE, kind) not in self.explained:
            self.explained.add((Key.SPACE, kind))
            for sentence in SPACE_EXPLAINED.get(kind, (MSG_EXPLAIN_SPACE_TOGGLES,)):
                yield Say(sentence)

    def letter_call(self, *, key, what):
        """Return what a letter key is called the first time on a kind of page, or None: no other key is called, and a letter only once there."""
        if not (len(key) == 1 and key.isalpha()) or (key, self.page_kind()) in self.letters_called:
            return None
        self.letters_called.add((key, self.page_kind()))
        return MSG_CALL_LETTER.format(key=key.upper(), what=what)

    def go_home(self):
        """Press Esc until the main screen shows."""
        for _ in range(MOST_MOVES):
            if isinstance(self.screen(), MainPage):
                return
            yield from self.press(keybindings.Page.BACK)
        raise TutorialStuck(type(self.screen()).__name__)

    def open_page(self, binding, *, said=True):
        """Open a main screen cell the way the user asked on 2026-11-10: go to the main screen, move the cursor's box onto the cell with the arrows, say which cell after a blank line unless said is False, and press Enter, so that a viewer sees where the tutorial is going. A page that is open already, under what is on top, is gone back to with Esc instead, saying nothing, so that it is never opened twice."""
        page_class = CELL_PAGES.get(binding)
        if page_class is not None and any(isinstance(page, page_class) for page in self.app.pages()):
            yield from self.go_back_to(page_class)
            return
        yield from self.go_home()
        yield from self.select_cell(binding)
        if said:
            cell = cell_opened_by(first_key(binding))
            yield Gap()
            yield Say((MSG_NARRATE_TURNING_ON if binding == keybindings.MainPage.REAL_TIME else MSG_NARRATE_OPENING).format(cell=cell))
        yield from self.press(keybindings.MainPage.OPEN)

    def go_back_to(self, page_class):
        """Press Esc until a page of the class is on top."""
        for _ in range(MOST_MOVES):
            if isinstance(self.screen(), page_class):
                return
            yield from self.press(keybindings.Page.BACK)
        raise TutorialStuck(page_class.__name__)

    def select_cell(self, binding):
        """Move the main screen's cursor onto a cell: Up and Down to its row, then Left and Right along it."""
        page = self.screen()
        self.expect(MainPage)
        row, column = cell_place(rows=page.rows(), binding=binding)
        for _ in range(MOST_MOVES):
            now_row, now_column = page.row_and_column()
            if (now_row, now_column) == (row, column):
                return
            if now_row != row:
                yield from self.press(Key.UP if row < now_row else Key.DOWN)
            else:
                yield from self.press(Key.LEFT if column < now_column else Key.RIGHT)
        raise TutorialStuck(binding)

    def expect(self, screen_class):
        if not isinstance(self.screen(), screen_class):
            raise TutorialStuck(type(self.screen()).__name__)

    def answer_prompt(self, text):
        """Erase what a prompt opened with, type the text and press Enter."""
        self.expect(PromptDialog)
        for _ in range(len(self.screen().value)):
            yield from self.pressing(first_key(keybindings.PromptDialog.ERASE), in_dialog=True, typed=True)
        yield from self.type_text(str(text), in_dialog=True)
        yield from self.press(keybindings.PromptDialog.DONE)

    def choose(self, option):
        """Move a picker's cursor to an option, by its text, and press Enter."""
        self.expect(ChoiceDialog)
        yield from self.choose_place(self.screen().options.index(option))

    def choose_place(self, place):
        """Move a picker's cursor to the option at a place in its whole list, and press Enter: Up and Down through a list, and the arrows and Tab through a grid."""
        dialog = self.screen()
        for _ in range(MOST_MOVES):
            if dialog.place == place:
                yield from self.press(keybindings.ChoiceDialog.CHOOSE)
                return
            yield from self.press(self.towards_option(dialog=dialog, place=place))
        raise TutorialStuck(dialog.title)

    def towards_option(self, *, dialog, place):
        """Return the key that brings a picker's cursor nearer an option."""
        if not isinstance(dialog, GridChoiceDialog):
            return Key.UP if place < dialog.place else Key.DOWN
        page, target_row, target_column = grid_place(dialog=dialog, place=place)
        if page != dialog.page:
            return Key.TAB
        row, column = dialog.where()
        if target_row != row:
            return Key.UP if target_row < row else Key.DOWN
        return Key.LEFT if target_column < column else Key.RIGHT

    def select_field(self, label):
        """Move a settings page's cursor to the field with a label."""
        page = self.screen()
        for _ in range(MOST_MOVES):
            labels = [field.label for field in page.fields()]
            if labels[page.place] == label:
                return
            yield from self.press(Key.UP if labels.index(label) < page.place else Key.DOWN)
        raise TutorialStuck(label)

    def set_field(self, *, label, answer):
        """Press Enter on a field and answer what opens: the text typed into a prompt, or the option chosen from a picker."""
        yield from self.select_field(label)
        yield from self.press(keybindings.FieldPage.ENTER)
        if isinstance(self.screen(), PromptDialog):
            yield from self.answer_prompt(answer)
        else:
            yield from self.choose(answer)

    def toggle_field(self, label):
        yield from self.select_field(label)
        yield from self.press(keybindings.FieldPage.TOGGLE)

    def confirm(self):
        self.expect(ConfirmDialog)
        yield from self.press(keybindings.ConfirmDialog.YES)

    def go_to_list_row(self, key):
        """Move a list page's cursor to the row keyed by a name."""
        page = self.screen()
        for _ in range(MOST_MOVES):
            if page.current() == key:
                return
            keys = [row[0] for row in page.rows()]
            yield from self.press(Key.UP if keys.index(key) < page.place else Key.DOWN)
        raise TutorialStuck(key)

    # The song and the scales.

    def build_scales(self):
        """Add each scale of the target the set doesn't have: a new scale on the Scales page, its root and kind picked, and its name set when the kind's own name isn't the one wanted."""
        for name in self.target.get_scale_names():
            if name in self.document().setlist().get_scale_names():
                continue
            scale = self.target.get_named_scale(name)
            yield Say(MSG_NARRATE_MAKING.format(kind=MSG_A_SCALE, name=name))
            yield from self.open_page(keybindings.MainPage.SCALES)
            yield from self.press(keybindings.ListPage.ADD)
            yield from self.set_field(label=MSG_ROOT_LABEL, answer=scale.get_root())
            yield from self.set_field(label=MSG_KIND_LABEL, answer=scale_label(scale.get_kind()))
            if name not in self.document().setlist().get_scale_names():
                yield from self.set_field(label=MSG_NAME_LABEL, answer=name)

    def drop_spare_scales(self):
        """Delete the new set's scales that the target doesn't have, once the song no longer uses them."""
        for name in list(self.document().setlist().get_scale_names()):
            if name in self.target.get_scale_names():
                continue
            if self.document().uses(section=Section.SCALES, name=name):
                self.left_out.append(MSG_LEFT_OUT_SCALE.format(name=name))
                continue
            yield from self.open_page(keybindings.MainPage.SCALES)
            yield from self.go_to_list_row(name)
            yield from self.press(keybindings.ListPage.DELETE)
            yield from self.confirm()

    def set_up_song(self, song):
        """Rename the new set's one song and set the settings that differ, on the Song page."""
        name = self.target.get_song_names()[FIRST]
        yield Say(MSG_NARRATE_SONG)
        yield from self.open_page(keybindings.MainPage.SONGS)
        # A rename is said on the list of the things renamed, where the thing already there shows, the user's wish of 2026-11-10.
        if self.document().current_song_name() != name:
            yield Say(MSG_NARRATE_RENAMING.format(kind=MSG_A_SONG))
        yield from self.press(keybindings.SongsPage.SETTINGS)
        if self.document().current_song_name() != name:
            yield from self.set_field(label=MSG_NAME_LABEL, answer=name)
        wanted = song.to_data()
        for setting, (label, _) in SONG_FIELDS.items():
            # A setting the target leaves out is its default, which a new song has too.
            if wanted.get(setting) is not None and wanted[setting] != self.document().song().to_data().get(setting):
                yield from self.set_field(label=label, answer=wanted[setting])
        for setting in wanted:
            if setting not in SONG_FIELDS and setting not in SONG_SECTIONS_BUILT and wanted[setting] != self.document().song().to_data().get(setting):
                self.left_out.append(MSG_LEFT_OUT_SONG_SETTING.format(setting=setting))

    # Tracks, scenes, patterns and clips.

    def build_track(self, *, song, track, place):
        """Make a track, its settings and then its clips scene by scene, drawing each pattern the first time a clip needs it."""
        current = self.document().song()
        was_there = place < len(current.get_track_names())
        if not was_there:
            yield Say(MSG_NARRATE_MAKING.format(kind=MSG_A_TRACK, name=track))
            yield from self.open_arrange()
            yield from self.go_to_cell(row=HEADER_ROW, column=len(current.get_track_names()) + FIRST_TRACK_COLUMN)
            yield from self.press(keybindings.ArrangePage.ADD_TRACK_HERE)
        old = self.document().song().get_track_names()[place]
        yield from self.open_arrange()
        if was_there and old != track:
            yield Say(MSG_NARRATE_RENAMING.format(kind=MSG_A_TRACK))
        yield from self.go_to_cell(row=HEADER_ROW, column=place + FIRST_TRACK_COLUMN)
        yield from self.press(keybindings.ArrangePage.TRACK_SETTINGS)
        if old != track:
            yield from self.set_field(label=MSG_NAME_LABEL, answer=track)
        wanted = song.get_track(track)
        if wanted.is_drum() != self.document().song().get_track(track).is_drum():
            yield from self.toggle_field(MSG_DRUM_LABEL)
        if wanted.is_muted() != self.document().song().get_track(track).is_muted():
            yield from self.toggle_field(MSG_MUTE_LABEL)
        if not wanted.is_drum() and wanted.get_transpose() != self.document().song().get_track(track).get_transpose():
            yield from self.set_field(label=MSG_TRANSPOSE_LABEL, answer=wanted.get_transpose())
        self.note_left_out(wanted=without_instrument(wanted.to_data()), built=self.document().song().get_track(track).to_data(), message=MSG_LEFT_OUT_TRACK_SETTING, name=track)
        for index, scene in enumerate(song.get_scenes()):
            yield from self.build_scene(song=song, index=index)
            if scene.has_clip_slot(track):
                yield from self.build_clip(song=song, index=index, track=track)
            elif self.document().song().get_scene(index).has_clip_slot(track):
                yield from self.delete_clip(index=index, track=track)

    def build_scene(self, *, song, index):
        """Add the scene at an index when the set doesn't have it yet, and name it."""
        current = self.document().song()
        wanted = song.get_scene(index)
        was_there = index < len(current.get_scenes())
        if not was_there:
            yield Say(MSG_NARRATE_MAKING.format(kind=MSG_A_SCENE, name=wanted.get_name()))
            yield from self.open_arrange()
            yield from self.go_to_cell(row=len(current.get_scenes()), column=SCENE_COLUMN)
            yield from self.press(keybindings.ArrangePage.ADD_SCENE_HERE)
        built = self.document().song().get_scene(index)
        if (built.get_name(), built.get_repeat(), built.launches_together()) != (wanted.get_name(), wanted.get_repeat(), wanted.launches_together()):
            yield from self.open_arrange()
            if was_there and built.get_name() != wanted.get_name():
                yield Say(MSG_NARRATE_RENAMING.format(kind=MSG_A_SCENE))
            yield from self.go_to_cell(row=index, column=SCENE_COLUMN)
            yield from self.press(keybindings.ArrangePage.SCENE_SETTINGS)
            if built.get_name() != wanted.get_name():
                yield from self.set_field(label=MSG_NAME_LABEL, answer=wanted.get_name())
            if built.get_repeat() != wanted.get_repeat():
                yield from self.set_field(label=MSG_REPEAT_LABEL, answer=wanted.get_repeat())
            if built.launches_together() != wanted.launches_together():
                yield from self.toggle_field(MSG_LAUNCH_TOGETHER_LABEL)
        self.note_left_out(wanted=without_clips(wanted.to_data()), built=without_clips(self.document().song().get_scene(index).to_data()), message=MSG_LEFT_OUT_SCENE_SETTING, name=wanted.get_name())

    def note_left_out(self, *, wanted, built, message, name):
        """Report each setting of a thing that the target holds and the built thing doesn't, once the plan has set what it can."""
        for setting in wanted:
            if wanted[setting] != built.get(setting):
                self.left_out.append(message.format(setting=setting, name=name))

    def build_clip(self, *, song, index, track):
        wanted = song.get_scene(index).get_clip_slot(track)
        pattern = wanted.get_pattern_name()
        if pattern not in self.document().setlist().get_pattern_names():
            yield from self.build_pattern(song=song, name=pattern)
        yield Say(MSG_NARRATE_CLIP.format(pattern=pattern, track=track, scene=song.get_scene(index).get_name()))
        yield from self.open_arrange()
        yield from self.go_to_cell(row=index, column=song.get_track_names().index(track) + FIRST_TRACK_COLUMN)
        scene = self.document().song().get_scene(index)
        if scene.has_clip_slot(track):
            yield from self.press(keybindings.ArrangePage.EDIT_CLIP)
            if scene.get_clip_slot(track).get_pattern_name() != pattern:
                yield from self.set_field(label=MSG_PATTERN_LABEL, answer=pattern)
        else:
            yield from self.press(keybindings.ArrangePage.ADD_CLIP)
            yield from self.choose(pattern)
            # Adding a clip stays on Arrange, so Enter on it again opens the clip page for its settings.
            yield from self.press(keybindings.ArrangePage.EDIT_CLIP)
        current = self.document().song().get_scene(index).get_clip_slot(track)
        if wanted.get_repeat() != current.get_repeat():
            yield from self.set_field(label=MSG_REPEAT_LABEL, answer=wanted.get_repeat())
        if wanted.loops() != current.loops():
            yield from self.toggle_field(MSG_LOOP_LABEL)
        for setting in wanted.to_data():
            if wanted.to_data()[setting] != self.document().song().get_scene(index).get_clip_slot(track).to_data().get(setting):
                self.left_out.append(MSG_LEFT_OUT_CLIP_SETTING.format(setting=setting, track=track, scene=song.get_scene(index).get_name()))

    def delete_clip(self, *, index, track):
        yield from self.open_arrange()
        yield from self.go_to_cell(row=index, column=self.document().song().get_track_names().index(track) + FIRST_TRACK_COLUMN)
        yield from self.press(keybindings.ArrangePage.DELETE_CLIP)
        yield from self.confirm()

    def build_pattern(self, *, song, name):
        """Make a pattern on the Patterns page and fill it in the editor: its steps, its notes on the piano roll and then its other rows."""
        wanted = self.target.get_pattern(name)
        kind = MSG_A_DRUM_PATTERN if wanted.is_drum() else MSG_A_PATTERN
        if not self.starter_pattern_is_spare():
            yield Say(MSG_NARRATE_MAKING.format(kind=kind, name=name))
        yield from self.open_page(keybindings.MainPage.PATTERNS)
        if self.starter_pattern_is_spare():
            yield Say(MSG_NARRATE_RENAMING.format(kind=kind))
            yield from self.go_to_list_row(STARTER_PATTERN)
            yield from self.press(keybindings.ListPage.RENAME)
            yield from self.answer_prompt(name)
            yield from self.press(keybindings.ListPage.EDIT)
        else:
            yield from self.press(keybindings.ListPage.ADD)
            yield from self.answer_prompt(name)
        self.expect(PatternEditor)
        if wanted.get_steps() != self.editor().steps():
            yield from self.press(keybindings.PatternEditor.RESIZE)
            yield from self.answer_prompt(wanted.get_steps())
            # Cutting steps that hold something asks first.
            if isinstance(self.screen(), ConfirmDialog):
                yield from self.confirm()
        if wanted.is_drum() != self.editor().is_drum():
            yield from self.reconfigure(Reconfigure.DRUM)
            yield from self.confirm()
        if wanted.is_drum():
            yield from self.write_drum_notes(wanted)
        else:
            yield from self.draw_notes(wanted)
        yield Say(MSG_NARRATE_PATTERN_ROWS.format(name=name))
        yield from self.set_rows(wanted)
        for setting in wanted.to_data():
            if setting not in ROW_DESCRIPTIONS and setting not in self.document().setlist().get_pattern(name).to_data():
                self.left_out.append(MSG_LEFT_OUT_PATTERN_SETTING.format(setting=setting, name=name))

    def starter_pattern_is_spare(self):
        """Return whether the new set's starter pattern is still there and the target has no pattern of that name, so that it becomes the first pattern built."""
        return STARTER_PATTERN in self.document().setlist().get_pattern_names() and STARTER_PATTERN not in self.target.get_pattern_names()

    def drop_starter_pattern(self):
        """Delete the starter pattern when no pattern was built over it, since the target doesn't have it."""
        if not self.starter_pattern_is_spare():
            return
        yield from self.open_page(keybindings.MainPage.PATTERNS)
        yield from self.go_to_list_row(STARTER_PATTERN)
        yield from self.press(keybindings.ListPage.DELETE)
        yield from self.confirm()

    def reconfigure(self, choice):
        yield from self.press(keybindings.PatternEditor.RECONFIGURE)
        yield from self.choose_place(choice)

    def editor(self):
        self.expect(PatternEditor)
        return self.screen()

    def draw_notes(self, wanted):
        """On the piano roll, erase the notes the target doesn't have and place the ones it has, step by step."""
        if not self.editor().on_roll():
            yield from self.press(keybindings.PatternEditor.TO_ROLL)
        roll = self.editor().roll
        default_octave = self.editor().default_octave()
        for step in range(wanted.get_steps()):
            degree = wanted.get_value(row=Row.DEGREE, step=step)
            here = self.editor().value(row=Row.DEGREE, step=step)
            if degree is None:
                if here is not None:
                    yield from self.go_to_step(step)
                    yield from self.go_to_pitch(roll.pitch_of(step))
                    yield from self.press(keybindings.PianoRoll.ERASE)
                continue
            octave = wanted.get_value(row=Row.OCTAVE, step=step)
            pitch = self.pitch_for(degree=degree, octave=default_octave if octave is None else octave)
            if here == degree and roll.pitch_of(step) == pitch:
                continue
            yield from self.go_to_step(step)
            yield from self.go_to_pitch(pitch)
            yield from self.press(keybindings.PianoRoll.PLACE)

    def pitch_for(self, *, degree, octave):
        """Return the roll's row for a degree in an octave, a degree past the scale's size carried into the next octave, as the roll works it out."""
        roll = self.editor().roll
        octaves_up, place = divmod(degree - MIN_DEGREE, roll.size())
        return roll.clamped((octave + octaves_up) * roll.per_octave() + roll.scale_steps()[place])

    def go_to_step(self, step):
        for _ in range(MOST_MOVES):
            if self.editor().step == step:
                return
            yield from self.press(Key.LEFT if step < self.editor().step else Key.RIGHT)
        raise TutorialStuck(step)

    def go_to_pitch(self, pitch):
        roll = self.editor().roll
        for _ in range(MOST_MOVES):
            rows = roll.rows()
            if roll.pitch == pitch:
                return
            yield from self.press(Key.UP if rows.index(pitch) < rows.index(roll.pitch) else Key.DOWN)
        raise TutorialStuck(pitch)

    def write_drum_notes(self, wanted):
        """In the rows view, type each drum note's letter on the Note row and its octave on the Octave row, in the set's octave labels."""
        if self.editor().on_roll():
            yield from self.press(keybindings.PatternEditor.TO_EDITOR)
        for step in range(wanted.get_steps()):
            letter = wanted.get_value(row=Row.DEGREE, step=step)
            if letter == self.editor().value(row=Row.DEGREE, step=step):
                continue
            yield from self.go_to_row(Row.DEGREE)
            yield from self.go_to_step(step)
            if letter is None:
                yield from self.press(keybindings.DegreeRow.CLEAR)
            else:
                yield from self.type_text(letter.lower())
        for step in range(wanted.get_steps()):
            octave = wanted.get_value(row=Row.OCTAVE, step=step)
            if octave == self.editor().value(row=Row.OCTAVE, step=step):
                continue
            yield from self.go_to_row(Row.OCTAVE)
            yield from self.go_to_step(step)
            if octave is None:
                yield from self.press(keybindings.OctaveRow.DEFAULT)
                continue
            shown = self.document().song().shown_octave(octave)
            if shown >= 0:
                yield from self.type_text(str(shown))
            else:
                # A negative label can't be typed, so step down to it from the default.
                for _ in range(MOST_MOVES):
                    now = self.editor().value(row=Row.OCTAVE, step=step)
                    if now == octave:
                        break
                    yield from self.press(keybindings.PatternRow.LESS if octave < (self.editor().default_octave() if now is None else now) else keybindings.PatternRow.MORE)

    def set_rows(self, wanted):
        """In the rows view, set every row but Degree and Octave where the target's step differs from the pattern's."""
        for row in ROWS_SET_IN_THE_ROWS_VIEW:
            if wanted.is_drum() and not ROW_DESCRIPTIONS[row].is_in_drum_patterns():
                continue
            for step in range(wanted.get_steps()):
                value = step_value(pattern=wanted, row=row, step=step)
                if value == step_value(pattern=self.editor().pattern(), row=row, step=step):
                    continue
                if self.editor().on_roll():
                    yield from self.press(keybindings.PatternEditor.TO_EDITOR)
                yield from self.go_to_row(row)
                yield from self.go_to_step(step)
                yield from self.set_cell(row=row, value=value)

    def go_to_row(self, name):
        """Move the rows view's cursor to a row, opening its section when the section is closed."""
        rows_view = self.editor().rows_view
        section = rows_view.section_of(name)
        if section is not None and not rows_view.section_is_open(section):
            yield from self.go_to_reachable_row(section)
            yield from self.press(keybindings.SectionRow.OPEN)
        yield from self.go_to_reachable_row(name)

    def go_to_reachable_row(self, name):
        rows_view = self.editor().rows_view
        for _ in range(MOST_MOVES):
            names = [row.name for row in rows_view.reachable()]
            if names[rows_view.row] == name:
                return
            yield from self.press(Key.UP if names.index(name) < rows_view.row else Key.DOWN)
        raise TutorialStuck(name)

    def set_cell(self, *, row, value):
        """Set the cell under the cursor to a value the way its row takes one: a toggle's Space, a cycle's Spaces, a chord's Spaces, a typed gate or a typed number."""
        component = self.editor().rows_view.row_for(row)
        if isinstance(component, ToggleRow):
            yield from self.press(keybindings.ToggleRow.TOGGLE)
        elif isinstance(component, ChordRow):
            options = [None, *CHORD_SYMBOLS]
            presses = (options.index(chord_text(value)) - options.index(chord_text(component.value()))) % len(options)
            for _ in range(presses):
                yield from self.press(keybindings.ChordRow.NEXT)
        elif isinstance(component, CycleRow):
            choices = component.choices()
            current = component.value()
            presses = (choices.index(value) - choices.index(choices[0] if current is None else current)) % len(choices)
            for _ in range(presses):
                yield from self.press(keybindings.CycleRow.NEXT)
        elif isinstance(component, GateRow):
            if value is None:
                yield from self.press(keybindings.GateRow.ONE_STEP)
            else:
                yield from self.press(keybindings.GateRow.TYPE)
                yield from self.answer_prompt(value)
        elif isinstance(component, NumberRow):
            if value is None:
                yield from self.press(keybindings.NumberRow.DEFAULT)
            elif value >= 0:
                yield from self.type_text(str(value))
            else:
                yield from self.press(keybindings.NumberRow.ASK)
                yield from self.answer_prompt(value)
        else:
            self.left_out.append(MSG_LEFT_OUT_ROW.format(row=row, name=self.editor().item))

    # Arrange.

    def open_arrange(self):
        yield from self.open_page(keybindings.MainPage.ARRANGE)

    def go_to_cell(self, *, row, column):
        """Move Arrange's cursor to a row and column: the header row for the track names, the scene rows, and the row after the last scene for the scene +."""
        page = self.screen()
        self.expect(ArrangePage)
        for _ in range(MOST_MOVES):
            if (page.row, page.column) == (row, column):
                return
            if page.row != row:
                yield from self.press(Key.UP if row < page.row else Key.DOWN)
            else:
                yield from self.press(Key.LEFT if column < page.column else Key.RIGHT)
        raise TutorialStuck((row, column))

    # Playing at the end, through a driver.

    def connect_instruments(self, song):
        """Add an instrument on the driver for each track, one channel each, and give each track its instrument."""
        for number, track in enumerate(song.get_track_names()):
            yield from self.open_page(keybindings.MainPage.INSTRUMENTS)
            yield from self.press(keybindings.ListPage.ADD)
            self.instruments[track] = self.document().setlist().get_instrument_names()[-1]
            yield Say(MSG_NARRATE_MAKING.format(kind=MSG_AN_INSTRUMENT, name=self.instruments[track]))
            yield from self.set_field(label=MSG_DEVICE_LABEL, answer=self.driver)
            yield from self.set_field(label=MSG_CHANNEL_LABEL, answer=FIRST_CHANNEL + number)
        for place, track in enumerate(song.get_track_names()):
            yield from self.open_arrange()
            yield from self.go_to_cell(row=HEADER_ROW, column=place + FIRST_TRACK_COLUMN)
            yield from self.press(keybindings.ArrangePage.TRACK_SETTINGS)
            yield from self.set_field(label=MSG_INSTRUMENT_LABEL, answer=self.instruments[track])
        if not self.document().setlist().is_real_time():
            yield from self.open_page(keybindings.MainPage.REAL_TIME)

    def play(self):
        """Say so, go into Arrange, and play the song from the corner."""
        yield Say(MSG_NARRATE_PLAY)
        yield from self.open_page(keybindings.MainPage.ARRANGE)
        yield from self.go_to_cell(row=HEADER_ROW, column=SCENE_COLUMN)
        yield from self.press(keybindings.ArrangePage.PLAY_SONG)
