# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The plan of a video tutorial: the keys that rebuild a target set from a new one in the running tracker, worked out from the target as the build goes.

A planner reads the set a demo file holds and presses the keys
a person would, so that any demo becomes a tutorial with nothing written by hand, and a test can
prove that what the keys built is the demo. The plan is a generator of steps, a Press of one key
or a Say of one sentence, and between two steps it reads the tracker's state, the page open and
where its cursor is, so that it never counts keys ahead: it presses an arrow, looks, and presses
again until the cursor is where the next key wants it, as a person does. Narration comes at the
parts worth a sentence, never at every key.

The build goes in this order: the song's own settings, the scales, then one track at a
time, each track's clips scene by scene from the top, every pattern drawn on the piano roll when
the track first needs it and its finer rows set in the rows view after, then the clip put on
Arrange. Whatever the plan can't set yet is reported as left out, so a demo that uses more than
the plan knows still builds the rest.
"""

from llamatron.interface.pages import pattern_list
from llamatron.interface.pages.pattern_list import Listed, PatternTab
from llamatron.interface.pages.scale import scale_label
from llamatron.interface.tracker import keybindings, keys as keys_values
from llamatron.interface.tracker.components.chord_row import chord_text, ChordRow
from llamatron.interface.tracker.components.cycle_row import CycleRow
from llamatron.interface.tracker.components.gate_row import GateRow
from llamatron.interface.tracker.components.number_row import NumberRow
from llamatron.interface.tracker.components.pattern_rows import PatternRows
from llamatron.interface.tracker.components.piano_roll import PianoRoll
from llamatron.interface.tracker.components.toggle_row import ToggleRow
from llamatron.interface.tracker.dialogs import new_pattern_dialog
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.dialogs.confirm_dialog import ConfirmDialog
from llamatron.interface.tracker.dialogs.prompt_dialog import PromptDialog
from llamatron.interface.tracker.dialogs.quit_dialog import QuitDialog
from llamatron.interface.tracker.key_table import first_key
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.arrange import arrange_page
from llamatron.interface.tracker.screens.arrange.arrange_page import ArrangePage
from llamatron.interface.tracker.screens.pattern.pattern_editor import PatternEditor, Reconfigure
from llamatron.interface.tracker.screens.pattern.patterns_page import PatternsPage
from llamatron.interface.tracker.screens.set.instruments_page import InstrumentsPage
from llamatron.interface.tracker.screens.set.main_page import cell_opened_by, MainPage
from llamatron.interface.tracker.screens.set.scales_page import ScalesPage
from llamatron.interface.tracker.screens.set.songs_page import SongsPage
from llamatron.interface.tutorial.steps import Gap, Press, Say, Wait
from llamatron.model.objects.naming import new_name
from llamatron.model.schema import file_format, limits, row_descriptions
from llamatron.model.schema.file_format import Row, SceneSetting, Section, SongSetting, TrackSetting
from llamatron.user_strings import labels as labels_text, names as names_text, narration

# The song's settings the plan can set on the Song page, each by the label of its field, and whether its value is typed into a prompt (True) or chosen from a picker, which the plan tells apart by what Enter opens.
SONG_FIELDS = {
    SongSetting.TEMPO: (labels_text.MSG_TEMPO_LABEL, True),
    SongSetting.TIME_SIGNATURE: (labels_text.MSG_TIME_SIGNATURE_LABEL, True),
    SongSetting.SCALE: (labels_text.MSG_SCALE_LABEL, False),
    SongSetting.GENRE: (labels_text.MSG_GENRE_LABEL, False),
}
# The parts of a song's data that aren't settings of the Song page.
SONG_SECTIONS_BUILT = (Section.TRACKS, Section.SCENES, Section.DRAWS)
# What the first Space says on each kind of page that has a sentence of its own, every other kind saying that Space toggles.
SPACE_EXPLAINED = {
    PianoRoll: (narration.MSG_EXPLAIN_SPACE_ON_ROLL, narration.MSG_EXPLAIN_BACKSPACE_ON_ROLL),
    ArrangePage: (narration.MSG_EXPLAIN_SPACE_ON_ARRANGE,),
}
# What the first arrow says on the two kinds of page where the arrows are explained, the piano roll and the rows view.
ARROWS_EXPLAINED = {PianoRoll: narration.MSG_EXPLAIN_ARROWS_ON_ROLL}
# The page each main screen cell the plan opens shows, which the plan goes back to with Esc when it is open already, rather than opening it again.
CELL_PAGES = {
    keybindings.MainPage.SONGS: SongsPage, keybindings.MainPage.SCALES: ScalesPage, keybindings.MainPage.PATTERNS: PatternsPage,
    keybindings.MainPage.ARRANGE: ArrangePage, keybindings.MainPage.INSTRUMENTS: InstrumentsPage,
}
# The seconds the tutorial waits once the song has played, before it goes back to the main screen and quits.
AFTER_THE_SONG_SECONDS = 2.0
# The rows the plan sets in the rows view: every row but the two the piano roll writes.
ROWS_SET_IN_THE_ROWS_VIEW = [name for name in row_descriptions.ROW_DESCRIPTIONS if name not in (Row.DEGREE, Row.OCTAVE)]
# How many times the plan may press an arrow towards one place before it gives up, since a cursor that never arrives would loop for ever.
MOST_MOVES = 400
# Where a binding keeps the words its legend gives it.
WORDS = 2
# The first instrument's channel.
FIRST_CHANNEL = 1
# The first song of a new set is the one the tutorial builds.
FIRST = 0
STARTER_PATTERN = names_text.MSG_NEW_PATTERN_NAME.format(number=1)


def step_value(*, pattern, row, step):
    """Return a step's value on a row, a row the pattern leaves out reading as its blank, so that a row of all falses equals one not written."""
    value = pattern.get_value(row=row, step=step)
    return row_descriptions.ROW_DESCRIPTIONS[row].blank() if value is None else value


def without_clips(scene_data):
    """Return a scene's data without its clips, which are built on their own."""
    return {setting: value for setting, value in scene_data.items() if setting != SceneSetting.TRACKS}


class TutorialStuck(Exception):
    """The plan pressed arrows towards a place the cursor never reached, or found a page it didn't expect."""


def without_instrument(data):
    """Return a track's data without its instrument, which the tutorial never builds from the target: an example's instruments carry General MIDI sounds for the previews, and when the tutorial plays it makes instruments of its own."""
    return {setting: value for setting, value in data.items() if setting != TrackSetting.INSTRUMENT}


def _toward(*, here, there, back, forward):
    """Return the key that moves from one place toward another: back where the other comes before, forward otherwise."""
    if there < here:
        return back
    return forward


def _presses_round(*, options, now, wanted):
    """Return how many presses of a key that goes round a list of options bring it from one option to another."""
    return (options.index(wanted) - options.index(now)) % len(options)


def _track_column(*, song, track):
    """Return the column of Arrange a track of a song is in."""
    names = song.get_track_names()
    return names.index(track) + arrange_page.FIRST_TRACK_COLUMN


def _scene_settings(scene):
    """Return the settings of a scene the tutorial sets on the Scene page: its name, its repeats and whether it launches
    together."""
    return (scene.get_name(), scene.get_repeat(), scene.launches_together())


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
        yield Say(narration.MSG_NARRATE_START.format(title=title))
        yield from self.build_scales()
        yield from self.set_up_song(song)
        yield from self.drop_spare_scales()
        for place, track in enumerate(song.get_track_names()):
            yield from self.build_track(song=song, track=track, place=place)
        yield from self.drop_starter_pattern()
        yield from self.show_the_finished_song()
        if self.driver is not None:
            yield Say(narration.MSG_NARRATE_PLAY_LIVE)
            yield Say(narration.MSG_NARRATE_EXPORT_KEY)
            yield Say(narration.MSG_NARRATE_REAL_TIME)
            yield Say(narration.MSG_NARRATE_GUIDE)
            yield from self.connect_instruments(song)
            yield from self.play()
            yield Say(narration.MSG_NARRATE_DONE.format(title=title))
            yield Wait(until=self.song_has_ended, seconds=AFTER_THE_SONG_SECONDS)
        else:
            yield Say(narration.MSG_NARRATE_WOULD_EXPORT)
            yield Say(narration.MSG_NARRATE_TUTORIAL_COMPLETE)
        yield from self.quit()

    def song_has_ended(self):
        return not self.app.transport.is_playing()

    def quit(self):
        """Go back to the main screen and quit through the Quit cell, without saving."""
        yield from self.go_home()
        yield Say(narration.MSG_NARRATE_QUITTING)
        yield from self.open_page(keybindings.MainPage.QUIT, said=False)
        if isinstance(self.screen(), QuitDialog):
            yield from self.press(keybindings.QuitDialog.PRESS)

    def show_the_finished_song(self):
        """Show the finished song on Arrange for a sentence, then go back to the main screen."""
        yield from self.open_page(keybindings.MainPage.ARRANGE)
        yield Say(narration.MSG_NARRATE_COMPLETE)
        yield from self.go_home()

    # Pressing keys and reading the screen.

    def press(self, *bindings):
        """Press each binding's first key, with what its legend says it does, or a key named as interface/tracker/keys.py names it."""
        for binding in bindings:
            if isinstance(binding, str):
                yield from self.pressing(binding)
            else:
                yield from self.pressing(first_key(binding), what=binding[WORDS])

    def type_text(self, text, *, in_dialog=False):
        """Type the text a key at a time, into a dialog when in_dialog says so, and never called out, since what is typed shows
        where it goes."""
        for character in text:
            key = character
            if character == keys_values.SPACE_CHARACTER:
                key = Key.SPACE
            yield from self.pressing(key, in_dialog=in_dialog, typed=True)

    def pressing(self, key, *, in_dialog=False, what=None, typed=False):
        """Return the steps of a key's press: what it says first, and the press. The arrows, ENTER and Space are explained once
        where they matter, a letter is called the first time on each kind of page with its legend's words, and what is typed is
        never called."""
        if in_dialog or typed:
            yield Press(key, in_dialog)
            return
        yield from self.explaining(key)
        called = None
        if what is not None:
            called = self.letter_call(key=key, what=what)
        yield Press(key, in_dialog, called)

    def page_kind(self):
        """Return the kind of page open, which the pattern editor's two views each are on their own."""
        screen = self.screen()
        return type(screen.view()) if isinstance(screen, PatternEditor) else type(screen)

    def explaining(self, key):
        """Return the sentences that explain a key the first time it matters: the arrows the first time anywhere and again on the piano roll and in the rows view, Enter and Esc the first time anywhere, and Space once on each kind of page."""
        kind = self.page_kind()
        if key in keys_values.ARROWS:
            if keys_values.ARROWS not in self.explained:
                self.explained.add(keys_values.ARROWS)
                yield Say(narration.MSG_EXPLAIN_ARROWS)
            if kind in (PianoRoll, PatternRows) and (keys_values.ARROWS, kind) not in self.explained:
                self.explained.add((keys_values.ARROWS, kind))
                yield Say(ARROWS_EXPLAINED.get(kind, narration.MSG_EXPLAIN_ARROWS_IN_ROWS))
        elif key == Key.ESCAPE and Key.ESCAPE not in self.explained:
            self.explained.add(Key.ESCAPE)
            yield Say(narration.MSG_EXPLAIN_ESCAPE)
        elif key == Key.ENTER and Key.ENTER not in self.explained:
            self.explained.add(Key.ENTER)
            yield Say(narration.MSG_EXPLAIN_ENTER)
        elif key == Key.SPACE and (Key.SPACE, kind) not in self.explained:
            self.explained.add((Key.SPACE, kind))
            for sentence in SPACE_EXPLAINED.get(kind, (narration.MSG_EXPLAIN_SPACE_TOGGLES,)):
                yield Say(sentence)

    def letter_call(self, *, key, what):
        """Return what a letter key is called the first time on a kind of page, or None: no other key is called, and a letter only once there."""
        if not (len(key) == 1 and key.isalpha()) or (key, self.page_kind()) in self.letters_called:
            return None
        self.letters_called.add((key, self.page_kind()))
        return narration.MSG_CALL_LETTER.format(key=key.upper(), what=what)

    def go_home(self):
        """Press Esc until the main screen shows."""
        for _ in range(MOST_MOVES):
            if isinstance(self.screen(), MainPage):
                return
            yield from self.press(keybindings.Page.BACK)
        raise TutorialStuck(type(self.screen()).__name__)

    def open_page(self, binding, *, said=True):
        """Open a main screen cell: go to the main screen, move the cursor's box onto the cell with the arrows, say which cell
        after a blank line unless said is False, and press ENTER, so that a viewer sees where the tutorial is going. A page that
        is open already, under what is on top, is gone back to with ESC instead, saying nothing, so that it is never opened
        twice."""
        page_class = CELL_PAGES.get(binding)
        if page_class is not None and self._has_page_open(page_class):
            yield from self.go_back_to(page_class)
            return
        yield from self.go_home()
        yield from self.select_cell(binding)
        if said:
            cell = cell_opened_by(first_key(binding))
            saying = narration.MSG_NARRATE_OPENING
            if binding == keybindings.MainPage.REAL_TIME:
                saying = narration.MSG_NARRATE_TURNING_ON
            yield Gap()
            yield Say(saying.format(cell=cell))
        yield from self.press(keybindings.MainPage.OPEN)

    def _has_page_open(self, page_class):
        """Return whether a page of a class is open, on top or under what is."""
        for page in self.app.pages():
            if isinstance(page, page_class):
                return True
        return False

    def go_back_to(self, page_class):
        """Press Esc until a page of the class is on top."""
        for _ in range(MOST_MOVES):
            if isinstance(self.screen(), page_class):
                return
            yield from self.press(keybindings.Page.BACK)
        raise TutorialStuck(page_class.__name__)

    def select_cell(self, binding):
        """Move the main screen's cursor onto a cell, with the fewest arrows over the layout the screen draws."""
        self.expect(MainPage)
        arrows = self.screen().arrows_to(binding)
        if arrows is None:
            raise TutorialStuck(binding)
        for arrow in arrows:
            yield from self.press(arrow)

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
            key = dialog.key_toward_place(place)
            if key is None:
                yield from self.press(keybindings.ChoiceDialog.CHOOSE)
                return
            yield from self.press(key)
        raise TutorialStuck(dialog.title)

    def go_to(self, target):
        """Move the screen's cursor to what is named, a field by its label or a row by what it lists, pressing the keys the screen says lead there."""
        screen = self.screen()
        for _ in range(MOST_MOVES):
            key = screen.key_toward(target)
            if key is None:
                return
            yield from self.press(key)
        raise TutorialStuck(target)

    def select_field(self, label):
        """Move a settings page's cursor to the field with a label."""
        yield from self.go_to(label)

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
        yield from self.go_to(key)

    # The song and the scales.

    def build_scales(self):
        """Add each scale of the target the set doesn't have: a new scale on the Scales page, its root and kind picked, and its
        name set when the kind's own name isn't the one wanted."""
        for name in self.target.get_scale_names():
            if name in self.built_setlist().get_scale_names():
                continue
            scale = self.target.get_named_scale(name)
            yield Say(narration.MSG_NARRATE_MAKING.format(kind=narration.MSG_A_SCALE, name=name))
            yield from self.open_page(keybindings.MainPage.SCALES)
            yield from self.press(keybindings.ListPage.ADD)
            yield from self.set_field(label=labels_text.MSG_ROOT_LABEL, answer=scale.get_root())
            yield from self.set_field(label=labels_text.MSG_KIND_LABEL, answer=scale_label(scale.get_kind()))
            if name not in self.built_setlist().get_scale_names():
                yield from self.set_field(label=labels_text.MSG_NAME_LABEL, answer=name)

    def drop_spare_scales(self):
        """Delete the new set's scales that the target doesn't have, once the song no longer uses them."""
        built = self.built_setlist()
        for name in list(built.get_scale_names()):
            if name in self.target.get_scale_names():
                continue
            if self.document().uses(section=Section.SCALES, name=name):
                self.left_out.append(narration.MSG_LEFT_OUT_SCALE.format(name=name))
                continue
            yield from self.open_page(keybindings.MainPage.SCALES)
            yield from self.go_to_list_row(name)
            yield from self.press(keybindings.ListPage.DELETE)
            yield from self.confirm()

    def set_up_song(self, song):
        """Rename the new set's one song and set the settings that differ, on the Song page."""
        name = self.target.get_song_names()[FIRST]
        renamed = self.document().get_current_song_name() != name
        yield Say(narration.MSG_NARRATE_SONG)
        yield from self.open_page(keybindings.MainPage.SONGS)
        # A rename is said on the list of the things renamed, where the thing already there shows.
        if renamed:
            yield Say(narration.MSG_NARRATE_RENAMING.format(kind=narration.MSG_A_SONG))
        yield from self.press(keybindings.SongsPage.SETTINGS)
        if renamed:
            yield from self.set_field(label=labels_text.MSG_NAME_LABEL, answer=name)
        wanted = song.to_data()
        for setting, (label, _) in SONG_FIELDS.items():
            # A setting the target leaves out is its default, which a new song has too.
            built = self.built_song().to_data()
            if wanted.get(setting) is not None and wanted[setting] != built.get(setting):
                yield from self.set_field(label=label, answer=wanted[setting])
        built = self.built_song().to_data()
        for setting in wanted:
            is_built_here = setting in SONG_FIELDS or setting in SONG_SECTIONS_BUILT
            if not is_built_here and wanted[setting] != built.get(setting):
                self.left_out.append(narration.MSG_LEFT_OUT_SONG_SETTING.format(setting=setting))

    # Tracks, scenes, patterns and clips.

    def build_track(self, *, song, track, place):
        """Make a track, its settings and then its clips scene by scene, drawing each pattern the first time a clip needs it."""
        was_there = place < len(self.built_song().get_track_names())
        if not was_there:
            yield from self._add_track(track)
        old = self.built_song().get_track_names()[place]
        yield from self.open_arrange()
        if was_there and old != track:
            yield Say(narration.MSG_NARRATE_RENAMING.format(kind=narration.MSG_A_TRACK))
        yield from self.go_to_cell(row=arrange_page.HEADER_ROW, column=place + arrange_page.FIRST_TRACK_COLUMN)
        yield from self.press(keybindings.ArrangePage.TRACK_SETTINGS)
        if old != track:
            yield from self.set_field(label=labels_text.MSG_NAME_LABEL, answer=track)
        yield from self._set_track_settings(wanted=song.get_track(track), track=track)
        for index, scene in enumerate(song.get_scenes()):
            yield from self.build_scene(song=song, index=index)
            built_scene = self.built_song().get_scene(index)
            if scene.has_clip_slot(track):
                yield from self.build_clip(song=song, index=index, track=track)
            elif built_scene.has_clip_slot(track):
                yield from self.delete_clip(index=index, track=track)

    def _add_track(self, track):
        """Add a track at the end of Arrange's tracks."""
        yield Say(narration.MSG_NARRATE_MAKING.format(kind=narration.MSG_A_TRACK, name=track))
        yield from self.open_arrange()
        column = len(self.built_song().get_track_names()) + arrange_page.FIRST_TRACK_COLUMN
        yield from self.go_to_cell(row=arrange_page.HEADER_ROW, column=column)
        yield from self.press(keybindings.ArrangePage.ADD_TRACK_HERE)

    def _built_track(self, track):
        """Return a track as the tutorial has built it so far."""
        song = self.built_song()
        return song.get_track(track)

    def _set_track_settings(self, *, wanted, track):
        """Set the track's settings that differ from the target's on the Track page: drum, mute and transpose."""
        if wanted.is_drum() != self._built_track(track).is_drum():
            yield from self.toggle_field(labels_text.MSG_DRUM_LABEL)
        if wanted.is_muted() != self._built_track(track).is_muted():
            yield from self.toggle_field(labels_text.MSG_MUTE_LABEL)
        if not wanted.is_drum() and wanted.get_transpose() != self._built_track(track).get_transpose():
            yield from self.set_field(label=labels_text.MSG_TRANSPOSE_LABEL, answer=wanted.get_transpose())
        built = self._built_track(track)
        self.note_left_out(wanted=without_instrument(wanted.to_data()), built=built.to_data(), message=narration.MSG_LEFT_OUT_TRACK_SETTING, name=track)

    def build_scene(self, *, song, index):
        """Add the scene at an index when the set doesn't have it yet, and name it."""
        wanted = song.get_scene(index)
        was_there = index < len(self.built_song().get_scenes())
        if not was_there:
            yield Say(narration.MSG_NARRATE_MAKING.format(kind=narration.MSG_A_SCENE, name=wanted.get_name()))
            yield from self.open_arrange()
            yield from self.go_to_cell(row=len(self.built_song().get_scenes()), column=arrange_page.SCENE_COLUMN)
            yield from self.press(keybindings.ArrangePage.ADD_SCENE_HERE)
        built = self.built_song().get_scene(index)
        if _scene_settings(built) != _scene_settings(wanted):
            yield from self._set_scene_settings(wanted=wanted, index=index, was_there=was_there)
        built = self.built_song().get_scene(index)
        wanted_data = without_clips(wanted.to_data())
        built_data = without_clips(built.to_data())
        self.note_left_out(wanted=wanted_data, built=built_data, message=narration.MSG_LEFT_OUT_SCENE_SETTING, name=wanted.get_name())

    def _set_scene_settings(self, *, wanted, index, was_there):
        """Set the scene's name, repeats and launching together on the Scene page where they differ from the target's."""
        built = self.built_song().get_scene(index)
        yield from self.open_arrange()
        if was_there and built.get_name() != wanted.get_name():
            yield Say(narration.MSG_NARRATE_RENAMING.format(kind=narration.MSG_A_SCENE))
        yield from self.go_to_cell(row=index, column=arrange_page.SCENE_COLUMN)
        yield from self.press(keybindings.ArrangePage.SCENE_SETTINGS)
        if built.get_name() != wanted.get_name():
            yield from self.set_field(label=labels_text.MSG_NAME_LABEL, answer=wanted.get_name())
        if built.get_repeat() != wanted.get_repeat():
            yield from self.set_field(label=labels_text.MSG_REPEAT_LABEL, answer=wanted.get_repeat())
        if built.launches_together() != wanted.launches_together():
            yield from self.toggle_field(labels_text.MSG_LAUNCH_TOGETHER_LABEL)

    def note_left_out(self, *, wanted, built, message, name):
        """Report each setting of a thing that the target holds and the built thing doesn't, once the plan has set what it can."""
        for setting in wanted:
            if wanted[setting] != built.get(setting):
                self.left_out.append(message.format(setting=setting, name=name))

    def build_clip(self, *, song, index, track):
        target_scene = song.get_scene(index)
        wanted = target_scene.get_clip_slot(track)
        pattern = wanted.get_pattern_name()
        if pattern not in self.built_setlist().get_pattern_names():
            yield from self.build_pattern(song=song, name=pattern)
        yield Say(narration.MSG_NARRATE_CLIP.format(pattern=pattern, track=track, scene=target_scene.get_name()))
        yield from self.open_arrange()
        column = _track_column(song=song, track=track)
        yield from self.go_to_cell(row=index, column=column)
        scene = self.built_song().get_scene(index)
        if scene.has_clip_slot(track):
            yield from self.press(keybindings.ArrangePage.EDIT_CLIP)
            clip_slot = scene.get_clip_slot(track)
            if clip_slot.get_pattern_name() != pattern:
                yield from self.set_field(label=labels_text.MSG_PATTERN_LABEL, answer=pattern)
        else:
            yield from self.press(keybindings.ArrangePage.ADD_CLIP)
            yield from self.choose(pattern)
            # Adding a clip stays on Arrange, so ENTER on it again opens the clip page for its settings.
            yield from self.press(keybindings.ArrangePage.EDIT_CLIP)
        yield from self._set_clip_settings(wanted=wanted, index=index, track=track)
        built = self._built_clip(index=index, track=track)
        built_data = built.to_data()
        wanted_data = wanted.to_data()
        for setting in wanted_data:
            if wanted_data[setting] != built_data.get(setting):
                self.left_out.append(narration.MSG_LEFT_OUT_CLIP_SETTING.format(setting=setting, track=track, scene=target_scene.get_name()))

    def _built_clip(self, *, index, track):
        """Return the clip built so far on a track in the scene at an index."""
        scene = self.built_song().get_scene(index)
        return scene.get_clip_slot(track)

    def _set_clip_settings(self, *, wanted, index, track):
        """Set the clip's repeats and loop on the clip page where they differ from the target's."""
        current = self._built_clip(index=index, track=track)
        if wanted.get_repeat() != current.get_repeat():
            yield from self.set_field(label=labels_text.MSG_REPEAT_LABEL, answer=wanted.get_repeat())
        if wanted.loops() != current.loops():
            yield from self.toggle_field(labels_text.MSG_LOOP_LABEL)

    def delete_clip(self, *, index, track):
        yield from self.open_arrange()
        column = _track_column(song=self.built_song(), track=track)
        yield from self.go_to_cell(row=index, column=column)
        yield from self.press(keybindings.ArrangePage.DELETE_CLIP)
        yield from self.confirm()

    def build_pattern(self, *, song, name):
        """Make a pattern on the Patterns page and fill it in the editor: its steps, its notes on the piano roll and then its
        other rows."""
        wanted = self.target.get_pattern(name)
        yield from self._make_pattern(wanted=wanted, name=name)
        self.expect(PatternEditor)
        if wanted.get_steps() != self.editor().step_count():
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
        yield Say(narration.MSG_NARRATE_PATTERN_ROWS.format(name=name))
        yield from self.set_rows(wanted)
        pattern = self.built_setlist().get_pattern(name)
        built = pattern.to_data()
        for setting in wanted.to_data():
            if setting not in row_descriptions.ROW_DESCRIPTIONS and setting not in built:
                self.left_out.append(narration.MSG_LEFT_OUT_PATTERN_SETTING.format(setting=setting, name=name))

    def _make_pattern(self, *, wanted, name):
        """Make the pattern on the Patterns page and open it: the starter pattern renamed where it is spare, else a new one in
        its group."""
        kind = narration.MSG_A_PATTERN
        if wanted.is_drum():
            kind = narration.MSG_A_DRUM_PATTERN
        if not self.starter_pattern_is_spare():
            yield Say(narration.MSG_NARRATE_MAKING.format(kind=kind, name=name))
        yield from self.open_page(keybindings.MainPage.PATTERNS)
        if self.starter_pattern_is_spare():
            yield Say(narration.MSG_NARRATE_RENAMING.format(kind=kind))
            yield from self.go_to_list_row(STARTER_PATTERN)
            yield from self.press(keybindings.ListPage.RENAME)
            yield from self.answer_prompt(name)
            yield from self.move_to_group(name=name, group=self.group_wanted(name))
            yield from self.press(keybindings.ListPage.EDIT)
            return
        # A drum pattern is made one later, which clears its scale length, so the dialog's number is left as it opens.
        scale_length = wanted.get_scale_length()
        if wanted.is_drum():
            scale_length = limits.NEW_PATTERN_SCALE_LENGTH
        yield from self.add_to_group(name=name, group=self.group_wanted(name), scale_length=scale_length)

    def group_wanted(self, name):
        """Return the group a pattern is built in: the target's for it, or else the one named after the first track of the target that plays it,
        as the tracker groups a pattern made anywhere but the Patterns page, or after a new group for a pattern nothing plays."""
        group = self.target.get_pattern(name).get_group()
        if group is None:
            group = self.target.first_track_playing(name)
        return group if group is not None else new_name(word=names_text.MSG_NEW_GROUP_WORD, taken=[])

    def go_to_patterns_row(self, listed):
        """Move the Patterns page's cursor to a row of the chosen tab by what the row is: a pattern or a button."""
        page = self.screen()
        for _ in range(MOST_MOVES):
            if page.listed() == listed:
                return
            rows = []
            for what, _ in page.remembered_rows():
                rows.append(what)
            yield from self.press(_toward(here=page.cursor.get_place(), there=rows.index(listed), back=Key.UP, forward=Key.DOWN))
        raise TutorialStuck(listed.name)

    def go_to_pattern_tab(self, tab):
        """Choose a tab of the Patterns page from its row of tabs, going there first."""
        page = self.screen()
        if not page.on_tabs:
            yield from self.press(keybindings.PatternsPage.TO_TABS)
        for _ in range(MOST_MOVES):
            tabs = page.tabs()
            if page.chosen() == tab:
                return
            yield from self.press(_toward(here=tabs.index(page.chosen()), there=tabs.index(tab), back=Key.LEFT, forward=Key.RIGHT))
        raise TutorialStuck(page.tab_label(tab))

    def add_to_group(self, *, name, group, scale_length):
        """Add a pattern written for a scale of so many notes to a group on the Patterns page: on the + (New) row of the group's tab
        when the set has the group, and after making the group with the button of the last tab when it doesn't."""
        if group in self.screen().groups():
            yield from self.go_to_pattern_tab(PatternTab(pattern_list.GROUP_TAB, group))
            yield from self.press(keybindings.PatternsPage.INTO_TAB)
        else:
            yield from self.go_to_pattern_tab(PatternTab(pattern_list.NEW_TAB))
            yield from self.press(keybindings.PatternsPage.NEW_GROUP)
            yield from self.answer_prompt(group)
        yield from self.go_to_patterns_row(Listed(pattern_list.NEW_PATTERN, group))
        yield from self.press(keybindings.PatternsPage.NEW_PATTERN)
        # The New Pattern dialog's first row is stepped to the scale length wanted and takes OK; the pattern is made a drum
        # pattern later where the set says so.
        dialog = self.screen()
        for _ in range(len(new_pattern_dialog.SCALE_LENGTHS)):
            if dialog.scale_length == scale_length:
                break
            higher = dialog.scale_length is None or (scale_length is not None and scale_length > dialog.scale_length)
            step = keybindings.NewPatternDialog.LESS
            if higher:
                step = keybindings.NewPatternDialog.MORE
            yield from self.press(step)
        yield from self.press(keybindings.NewPatternDialog.OK)
        yield from self.answer_prompt(name)

    def move_to_group(self, *, name, group):
        """Move the pattern under the Patterns page's cursor to a group, making the group when the set doesn't have it."""
        if self.document().pattern_group(name) == group:
            return
        made = group in self.screen().groups()
        yield from self.press(keybindings.PatternsPage.GROUP)
        if made:
            yield from self.choose(group)
        else:
            yield from self.choose(labels_text.MSG_NEW_GROUP_BUTTON)
            yield from self.answer_prompt(group)

    def starter_pattern_is_spare(self):
        """Return whether the new set's starter pattern is still there and the target has no pattern of that name, so that it
        becomes the first pattern built."""
        built = self.built_setlist()
        return STARTER_PATTERN in built.get_pattern_names() and STARTER_PATTERN not in self.target.get_pattern_names()

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
            if octave is None:
                octave = default_octave
            pitch = self.pitch_for(degree=degree, octave=octave)
            if here == degree and roll.pitch_of(step) == pitch:
                continue
            yield from self.go_to_step(step)
            yield from self.go_to_pitch(pitch)
            yield from self.press(keybindings.PianoRoll.PLACE)

    def pitch_for(self, *, degree, octave):
        """Return the roll's row for a degree in an octave, a degree past the scale's size carried into the next octave, as the roll works it out."""
        roll = self.editor().roll
        octaves_up, place = divmod(degree - limits.MIN_DEGREE, roll.size())
        return roll.clamped((octave + octaves_up) * roll.per_octave() + roll.scale_steps()[place])

    def go_to_step(self, step):
        for _ in range(MOST_MOVES):
            here = self.editor().step
            if here == step:
                return
            yield from self.press(_toward(here=here, there=step, back=Key.LEFT, forward=Key.RIGHT))
        raise TutorialStuck(step)

    def go_to_pitch(self, pitch):
        roll = self.editor().roll
        for _ in range(MOST_MOVES):
            rows = roll.rows()
            if roll.pitch == pitch:
                return
            yield from self.press(_toward(here=rows.index(roll.pitch), there=rows.index(pitch), back=Key.UP, forward=Key.DOWN))
        raise TutorialStuck(pitch)

    def write_drum_notes(self, wanted):
        """In the rows view, type each drum note's letter on the Note row and its octave on the Octave row, in the set's octave
        labels."""
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
            if octave != self.editor().value(row=Row.OCTAVE, step=step):
                yield from self._write_drum_octave(step=step, octave=octave)

    def _write_drum_octave(self, *, step, octave):
        """Set a drum note's octave on the Octave row: back to the default, typed as its label, or stepped down to a label below
        zero, which cannot be typed."""
        yield from self.go_to_row(Row.OCTAVE)
        yield from self.go_to_step(step)
        if octave is None:
            yield from self.press(keybindings.OctaveRow.DEFAULT)
            return
        shown = self.built_setlist().shown_octave(octave)
        if shown >= 0:
            yield from self.type_text(str(shown))
            return
        for _ in range(MOST_MOVES):
            now = self.editor().value(row=Row.OCTAVE, step=step)
            if now == octave:
                return
            if now is None:
                now = self.editor().default_octave()
            yield from self.press(_toward(here=now, there=octave, back=keybindings.PatternRow.LESS, forward=keybindings.PatternRow.MORE))

    def set_rows(self, wanted):
        """In the rows view, set every row but Degree and Octave where the target's step differs from the pattern's."""
        for row in ROWS_SET_IN_THE_ROWS_VIEW:
            description = row_descriptions.ROW_DESCRIPTIONS[row]
            if wanted.is_drum() and not description.is_in_drum_patterns():
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
            names = []
            for row in rows_view.reachable():
                names.append(row.name)
            if names[rows_view.row] == name:
                return
            yield from self.press(_toward(here=rows_view.row, there=names.index(name), back=Key.UP, forward=Key.DOWN))
        raise TutorialStuck(name)

    def set_cell(self, *, row, value):
        """Set the cell under the cursor to a value the way its row takes one: a toggle's Space, a cycle's Spaces, a chord's
        Spaces, a typed gate or a typed number."""
        component = self.editor().rows_view.row_for(row)
        if isinstance(component, ToggleRow):
            yield from self.press(keybindings.ToggleRow.TOGGLE)
        elif isinstance(component, ChordRow):
            options = [None, *file_format.CHORD_SYMBOLS]
            presses = _presses_round(options=options, now=chord_text(component.value()), wanted=chord_text(value))
            yield from self._press_times(binding=keybindings.ChordRow.NEXT, times=presses)
        elif isinstance(component, CycleRow):
            choices = component.choices()
            now = component.value()
            if now is None:
                now = choices[0]
            yield from self._press_times(binding=keybindings.CycleRow.NEXT, times=_presses_round(options=choices, now=now, wanted=value))
        elif isinstance(component, GateRow):
            yield from self._set_gate(value)
        elif isinstance(component, NumberRow):
            yield from self._set_number(value)
        else:
            self.left_out.append(narration.MSG_LEFT_OUT_ROW.format(row=row, name=self.editor().item))

    def _press_times(self, *, binding, times):
        for _ in range(times):
            yield from self.press(binding)

    def _set_gate(self, value):
        """Set a gate: one step with none, else typed."""
        if value is None:
            yield from self.press(keybindings.GateRow.ONE_STEP)
            return
        yield from self.press(keybindings.GateRow.TYPE)
        yield from self.answer_prompt(value)

    def _set_number(self, value):
        """Set a number: the default with none, typed where it is zero or more, and asked for where it is below zero."""
        if value is None:
            yield from self.press(keybindings.NumberRow.DEFAULT)
        elif value >= 0:
            yield from self.type_text(str(value))
        else:
            yield from self.press(keybindings.NumberRow.ASK)
            yield from self.answer_prompt(value)

    # Arrange.

    def open_arrange(self):
        yield from self.open_page(keybindings.MainPage.ARRANGE)

    def go_to_cell(self, *, row, column):
        """Move Arrange's cursor to a row and column: the header row for the track names, the scene rows, and the row after the
        last scene for the scene +."""
        page = self.screen()
        self.expect(ArrangePage)
        for _ in range(MOST_MOVES):
            if (page.row, page.column) == (row, column):
                return
            if page.row != row:
                yield from self.press(_toward(here=page.row, there=row, back=Key.UP, forward=Key.DOWN))
            else:
                yield from self.press(_toward(here=page.column, there=column, back=Key.LEFT, forward=Key.RIGHT))
        raise TutorialStuck((row, column))

    # Playing at the end, through a driver.

    def connect_instruments(self, song):
        """Add an instrument on the driver for each track, one channel each, and give each track its instrument."""
        for number, track in enumerate(song.get_track_names()):
            yield from self.open_page(keybindings.MainPage.INSTRUMENTS)
            yield from self.press(keybindings.ListPage.ADD)
            self.instruments[track] = self.built_setlist().get_instrument_names()[-1]
            yield Say(narration.MSG_NARRATE_MAKING.format(kind=narration.MSG_AN_INSTRUMENT, name=self.instruments[track]))
            yield from self.set_field(label=labels_text.MSG_DEVICE_LABEL, answer=self.driver)
            yield from self.set_field(label=labels_text.MSG_CHANNEL_LABEL, answer=FIRST_CHANNEL + number)
        for place, track in enumerate(song.get_track_names()):
            yield from self.open_arrange()
            yield from self.go_to_cell(row=arrange_page.HEADER_ROW, column=place + arrange_page.FIRST_TRACK_COLUMN)
            yield from self.press(keybindings.ArrangePage.TRACK_SETTINGS)
            yield from self.set_field(label=labels_text.MSG_INSTRUMENT_LABEL, answer=self.instruments[track])
        if not self.built_setlist().is_real_time():
            yield from self.open_page(keybindings.MainPage.REAL_TIME)

    def play(self):
        """Say so, go into Arrange, and play the song from the corner."""
        yield Say(narration.MSG_NARRATE_PLAY)
        yield from self.open_page(keybindings.MainPage.ARRANGE)
        yield from self.go_to_cell(row=arrange_page.HEADER_ROW, column=arrange_page.SCENE_COLUMN)
        yield from self.press(keybindings.ArrangePage.PLAY_SONG)

    def built_song(self):
        """Return the song as the tutorial has built it so far."""
        document = self.document()
        return document.song()

    def built_setlist(self):
        """Return the set as the tutorial has built it so far."""
        document = self.document()
        return document.get_setlist()
