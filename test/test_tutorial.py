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

"""The video tutorial: the plan presses keys into the real tracker, headless and with no pace, and what it builds is the target set.

The hello world demo is the first tutorial, and test/sample_sets/tutorial_target.yml holds what
that demo doesn't, so that every way the plan sets a thing is tried: a scale with a name of its
own, a tempo and a time signature, a track that transposes and a muted drum track, a scene that
repeats, a clip that repeats and one that loops, a sharp, a gate, a chord, a negative number, every
kind of row and a drum pattern written as letters. A built set is held to its target two ways: its
data, apart from the title, the notes and the like that a tutorial doesn't write and the two rows the
piano roll writes in its own way (an eighth degree is the first degree an octave up, and an octave
the pattern leaves blank is the default octave written out), and its music, every song's timeline
event for event, as test/test_realtime.py holds the player to the export.
"""

import asyncio
import os
import unittest
from unittest import mock

from llamatron.composition.file_format import Row, SetlistSetting, Section
from llamatron.composition.setlist import Setlist
from llamatron.playback.song_renderer import SongRenderer
from llamatron.realtime.engine import PlaybackEngine, SteppedClock
from llamatron.realtime.outputs import RecordingOutput
from llamatron.realtime.timeline import NOTE_ON, Route, song_timeline
from llamatron.strings.legends import KeyName
from llamatron.strings.labels import PageName
from llamatron.strings.narration import (
    MSG_A_PATTERN, MSG_A_SCENE, MSG_A_SONG, MSG_A_TRACK, MSG_CALL_LETTER, MSG_EXPLAIN_ARROWS, MSG_EXPLAIN_ARROWS_IN_ROWS, MSG_EXPLAIN_ARROWS_ON_ROLL, MSG_EXPLAIN_ESCAPE,
    MSG_EXPLAIN_BACKSPACE_ON_ROLL, MSG_EXPLAIN_ENTER, MSG_EXPLAIN_SPACE_ON_ARRANGE, MSG_EXPLAIN_SPACE_ON_ROLL, MSG_EXPLAIN_SPACE_TOGGLES,
    MSG_NARRATE_COMPLETE, MSG_NARRATE_DONE, MSG_NARRATE_EXPORT_KEY, MSG_NARRATE_GUIDE, MSG_NARRATE_PLAY, MSG_NARRATE_PLAY_LIVE, MSG_NARRATE_REAL_TIME,
    MSG_NARRATE_OPENING, MSG_NARRATE_QUITTING, MSG_NARRATE_RENAMING, MSG_NARRATE_START, MSG_NARRATE_TUTORIAL_COMPLETE, MSG_NARRATE_WOULD_EXPORT, MSG_TUTORIAL_KEYS,
)
from llamatron.tui.app import LlamatronApp
from llamatron.tui.drawing import NOTHING
from llamatron.tui.document import Document
from llamatron.tui.launch import Launch
from llamatron.tui.screens.arrange_page import ArrangePage
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.screens.patterns_page import PatternsPage
from llamatron.tui.screens.pattern_editor import PatternEditor
from llamatron.tui.screens.songs_page import SongsPage
from llamatron.tui.screens.track_editor import TrackEditor
from llamatron.tui.components.pattern_rows import PatternRows
from llamatron.tui.components.piano_roll import PianoRoll
from llamatron.tui.keys import Key, SPACE_CHARACTER
from llamatron.tui import keybindings
from llamatron.tui.key_table import first_key, key_event
from llamatron.tui.screens.main_page import MainPage
from llamatron.tutorial.steps import Press
from llamatron.tui.transport import Transport
from llamatron.tutorial.plan import without_instrument, WORDS, TutorialPlan, TutorialStuck
from llamatron.tutorial.runner import DIALOG_TYPING_SHARE, HUMAN_PACE, LINE_SECONDS, NO_PACE, READING_CHARACTERS_PER_SECOND, SAY_PAUSES, Narrator, TutorialRunner, tutorial
from llamatron.tui.caption_strip import parts
from llamatron.tutorial.steps import Say
from ui_testing import UITest

HELLO_WORLD = os.path.join('examples', 'learning', '01_hello_world.yml')
TARGET = os.path.join('test', 'sample_sets', 'tutorial_target.yml')
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# What a tutorial never writes: the file's attribution and the version, and the set's protection.
# The examples' instruments, which play through FluidSynth with General MIDI sounds, are never built either: when the tutorial plays it makes its own.
# Nor is the Real Time switch, which goes with them, since the first instrument added turns it on.
NOT_BUILT = (
    SetlistSetting.TITLE, SetlistSetting.AUTHOR, SetlistSetting.DESCRIPTION, SetlistSetting.NOTES, SetlistSetting.PROTECTED, SetlistSetting.VERSION, SetlistSetting.REAL_TIME,
    Section.INSTRUMENTS,
)
# The rows the piano roll writes in its own words, compared as music instead.
ROLL_ROWS = (Row.DEGREE, Row.OCTAVE)
PORT = 'Tutorial Port'
PORT_NAMES = 'llamatron.tui.transport.output_port_names'
EDITOR_PORT_NAMES = 'llamatron.tui.screens.instrument_editor.output_port_names'
SEED = 1
EXPORT_CHANNEL = 1
FIRST = 0
KIND_MASK = 0xF0
A_MOMENT = 0.05
FAR_AHEAD = 100000.0
NO_SUCH_PAGE = 'NoSuchPage'
# How wide the narrator box's lines are read.
# A caption a few words long, and how many times longer another is.
SHORT_CAPTION = 20
LONGER = 4
# A name the plan types into a prompt that opened holding an older one.
TYPED_NAME = 'tune'
OLD_NAME = 'old'
# The runner's method that waits after a step, which a test replaces to see the waits.
PAUSE_METHOD = '_pause'
# Where the runner makes each key's event, which a test watches to see which screen each key was pressed on.
KEY_EVENT = 'llamatron.tutorial.runner.key_event'


def comparable_data(setlist):
    """Return a set's data as a tutorial can be held to it: with every default filled in as the tracker fills them, without what it never writes, and without the rows the roll writes its own way."""
    data = {setting: value for setting, value in Document(setlist=setlist, path=None).setlist().to_data().items() if setting not in NOT_BUILT}
    for song in data.get(Section.SONGS, {}).values():
        song[Section.TRACKS] = {name: without_instrument(track) for name, track in song.get(Section.TRACKS, {}).items()}
    data[Section.PATTERNS] = {name: {row: values for row, values in pattern.items() if row not in ROLL_ROWS} for name, pattern in data.get(Section.PATTERNS, {}).items()}
    return data


def comparable_music(setlist):
    """Return every song's timeline as the tuples two timelines are compared by, on one port and channel, as test_realtime compares them."""
    music = {}
    for name in setlist.get_song_names():
        song = setlist.get_song(name)
        routes = {track: Route(PORT, EXPORT_CHANNEL) for track in song.get_track_names()}
        events = song_timeline(grid=SongRenderer(song, seed=SEED).render(), routes=routes)
        music[name] = sorted((round(event.seconds, 6), event.kind, event.number, event.value) for event in events)
    return music


class TutorialTest(UITest):
    """A tracker on a new set, launched with a tutorial that builds TARGET_PATH with no pace, its transport on a stepped clock with recording outputs."""

    TARGET_PATH = HELLO_WORLD
    PLAYS = False

    def make_app(self):
        self.target = Setlist.read_file(os.path.join(HERE, self.TARGET_PATH))
        launch = Launch(driven_by=tutorial(target=self.target, port=PORT if self.PLAYS else None, pace=NO_PACE), quit_when_finished=self.PLAYS, lead_out_seconds=A_MOMENT)
        app = LlamatronApp(document=Document(setlist=Setlist.new(), path=None), launch=launch)
        self.clock = SteppedClock()
        self.outputs = {}

        def make_sender(ports):
            for port in ports:
                self.outputs.setdefault(port, RecordingOutput())
            return PlaybackEngine(clock=self.clock, outputs={port: self.outputs[port] for port in ports})
        app.transport = Transport(document_holder=app, clock=self.clock, make_sender=make_sender, set_timer=app.playback_timer)
        self.exited = False
        quit_for_real = app.exit

        def exit_noted(*arguments, **named):
            self.exited = True
            quit_for_real(*arguments, **named)
        app.exit = exit_noted
        return app

    async def asyncSetUp(self):
        for patched in (PORT_NAMES, EDITOR_PORT_NAMES):
            patcher = mock.patch(patched, return_value=[PORT])
            patcher.start()
            self.addCleanup(patcher.stop)
        # Each key pressed, with the screen it was pressed on.
        self.pressed_on = []

        def noted(key):
            self.pressed_on.append((type(self.app.screen), key))
            return key_event(key)
        patcher = mock.patch(KEY_EVENT, noted)
        patcher.start()
        self.addCleanup(patcher.stop)
        await super().asyncSetUp()

    async def built(self):
        """Wait for the tutorial to finish, fail on what stopped it, and return the set it built."""
        while self.app.driven is None or not self.app.driven.finished:
            await asyncio.sleep(A_MOMENT)
            await self.pilot.pause()
        if self.app.driven.problem is not None:
            raise self.app.driven.problem
        return self.app.get_document().setlist()

    def said(self):
        return [text for _, text in self.app.driven.narrator.said]

    async def playing(self):
        """Wait until the tutorial has started the song, which it waits on before it quits."""
        while self.app.driven is None or MSG_NARRATE_DONE.format(title=self.target.get_title()) not in self.said():
            if self.app.driven is not None and self.app.driven.finished:
                raise self.app.driven.problem or AssertionError(self.said())
            await asyncio.sleep(A_MOMENT)
            await self.pilot.pause()
        return self.app.get_document().setlist()


def opened_before(*, said, text):
    """Return the last "Opening" line said before a line, which names the page the line was said on."""
    openings = [line for line in said[:said.index(text)] if line.startswith(MSG_NARRATE_OPENING.format(cell=NOTHING))]
    return openings[-1]


class TestHelloWorldTutorial(TutorialTest):

    async def test_the_keys_build_the_hello_world_demo_and_say_what_they_do_without_saving(self):
        built = await self.built()
        self.assertEqual(comparable_data(built), comparable_data(self.target))
        self.assertEqual(comparable_music(built), comparable_music(self.target))
        self.assertEqual(self.app.driven.plan.left_out, [])
        said = self.said()
        self.assertEqual(said[0], MSG_NARRATE_START.format(title=self.target.get_title()))
        # Without a port to play through, the tutorial shows the finished song, says how it would export, and quits without saving, the user's design of 2026-11-10.
        self.assertEqual(said[-4:], [MSG_NARRATE_COMPLETE, MSG_NARRATE_WOULD_EXPORT, MSG_NARRATE_TUTORIAL_COMPLETE, MSG_NARRATE_QUITTING])
        self.assertTrue(self.exited)
        self.assertNotIn(MSG_NARRATE_PLAY_LIVE, said)
        self.assertNotIn(MSG_NARRATE_DONE.format(title=self.target.get_title()), said)
        self.assertIn(MSG_NARRATE_OPENING.format(cell=PageName.ARRANGE), said)
        # Each rename is said once the list of its kind of thing shows, the user's wish of 2026-11-10.
        self.assertEqual(opened_before(said=said, text=MSG_NARRATE_RENAMING.format(kind=MSG_A_SONG)), MSG_NARRATE_OPENING.format(cell=PageName.SONGS))
        self.assertEqual(opened_before(said=said, text=MSG_NARRATE_RENAMING.format(kind=MSG_A_PATTERN)), MSG_NARRATE_OPENING.format(cell=PageName.PATTERNS))
        for kind in (MSG_A_TRACK, MSG_A_SCENE):
            self.assertEqual(opened_before(said=said, text=MSG_NARRATE_RENAMING.format(kind=kind)), MSG_NARRATE_OPENING.format(cell=PageName.ARRANGE))
        # A page that is open already is gone back to, never opened again, so no two "Opening" lines come together.
        openings = [index for index, line in enumerate(said) if line.startswith(MSG_NARRATE_OPENING.format(cell=NOTHING))]
        self.assertEqual([index for index in openings if index - 1 in openings], [])
        self.assertEqual(said.count(MSG_NARRATE_RENAMING.format(kind=MSG_A_SCENE)), 1)
        self.assertEqual(said.count(MSG_EXPLAIN_ENTER), 1)
        self.assertEqual(said.count(MSG_EXPLAIN_SPACE_ON_ROLL), 1)
        self.assertEqual(said.count(MSG_EXPLAIN_ARROWS_ON_ROLL), 1)
        self.assertEqual(said.count(MSG_EXPLAIN_ARROWS), 1)
        self.assertLess(said.index(MSG_EXPLAIN_ARROWS), said.index(MSG_NARRATE_OPENING.format(cell=PageName.SONGS)))
        self.assertEqual(said.count(MSG_EXPLAIN_ESCAPE), 1)
        # A new set's song, track and scene are there already, and are renamed to the demo's.
        for kind in (MSG_A_SONG, MSG_A_TRACK, MSG_A_SCENE):
            self.assertIn(MSG_NARRATE_RENAMING.format(kind=kind), said)
        self.assertEqual(self.app.caption_strip().text(), parts(text=MSG_NARRATE_QUITTING, width=self.app.size.width)[-1])
        self.assertGreater(self.app.driven.pressed, 0)
        self.assertIsNone(self.app.get_document().get_path())
        self.assertEqual(self.app.driven.report()[-1], MSG_TUTORIAL_KEYS.format(count=self.app.driven.pressed, seconds=self.app.driven.ended_at - self.app.driven.started_at))


class TestEveryKindOfSettingTutorial(TutorialTest):

    TARGET_PATH = TARGET

    async def test_the_keys_build_a_set_with_every_kind_of_row_scene_clip_and_track_setting(self):
        built = await self.built()
        self.assertEqual(comparable_data(built), comparable_data(self.target))
        self.assertEqual(comparable_music(built), comparable_music(self.target))
        self.assertEqual(self.app.driven.plan.left_out, [])
        # On the main screen the tutorial opens each page by moving the cursor's box onto its cell and pressing Enter, never with a letter, the user's wish of 2026-11-10.
        on_main_screen = [key for screen, key in self.pressed_on if screen is MainPage]
        self.assertIn(Key.ENTER, on_main_screen)
        self.assertEqual([key for key in on_main_screen if key not in (Key.UP, Key.DOWN, Key.LEFT, Key.RIGHT, Key.ENTER)], [])


class TestTutorialPlays(TutorialTest):
    """With a driver, the tutorial ends by giving each track an instrument on it, turning Real Time on and playing the song on Arrange, and once the song has ended it goes back to the main screen and quits without saving."""

    PLAYS = True

    async def test_it_connects_each_track_to_a_channel_of_the_driver_plays_the_song_and_quits_at_its_end(self):
        built = await self.playing()
        self.assertEqual(comparable_music(built), comparable_music(self.target))
        song = built.get_song(built.get_song_names()[FIRST])
        self.assertTrue(built.is_real_time())
        channels = []
        for track in song.get_track_names():
            instrument = built.get_instrument(song.get_track(track).get_instrument_name())
            self.assertEqual(instrument.get_device(), PORT)
            channels.append(instrument.get_channel())
        self.assertEqual(channels, list(range(1, len(song.get_track_names()) + 1)))
        said = self.said()
        ending = [MSG_NARRATE_COMPLETE, MSG_NARRATE_PLAY_LIVE, MSG_NARRATE_EXPORT_KEY, MSG_NARRATE_REAL_TIME, MSG_NARRATE_GUIDE, MSG_NARRATE_PLAY, MSG_NARRATE_DONE.format(title=self.target.get_title())]
        self.assertEqual([text for text in said if text in ending], ending)
        self.assertLess(said.index(MSG_NARRATE_PLAY), said.index(MSG_EXPLAIN_SPACE_ON_ARRANGE))
        self.assertNotIn(MSG_NARRATE_TUTORIAL_COMPLETE, said)
        self.assertIsInstance(self.app.screen, ArrangePage)
        self.assertTrue(self.app.transport.is_playing())
        self.assertFalse(self.exited)
        self.clock.advance(FAR_AHEAD)
        self.app.transport.tick()
        self.app.transport.player().sender().send_due()
        self.assertFalse(self.app.transport.is_playing())
        note_ons = [data for _, data in self.outputs[PORT].sent if data[0] & KIND_MASK == NOTE_ON]
        self.assertGreater(len(note_ons), 0)
        await self.built()
        self.assertEqual(self.said()[-1], MSG_NARRATE_QUITTING)
        self.assertTrue(self.exited)


class TestTutorialStuck(unittest.TestCase):

    def test_a_plan_that_finds_the_wrong_screen_stops_with_the_screens_name(self):
        class ScreenOnly:
            screen = type(NO_SUCH_PAGE, (), {})()

            def get_document(self):
                return None
        plan = TutorialPlan(app=ScreenOnly(), target=Setlist.new())
        with self.assertRaises(TutorialStuck) as caught:
            plan.expect(MainPage)
        self.assertEqual(str(caught.exception), NO_SUCH_PAGE)


class ScreenShown:
    """A tracker that shows only a screen, which a test changes, for a plan that reads nothing else."""

    __slots__ = ('screen',)

    def __init__(self, screen):
        self.screen = screen

    def get_document(self):
        return None


def page_of(page_class):
    """Return a page of the class without starting a tracker, for a plan that asks only which page is open."""
    return page_class.__new__(page_class)


class TestTutorialPace(unittest.TestCase):
    """Typing into a dialog goes twice as fast as every other key, the user's choice of 2026-11-10, and typing into a pattern's cells doesn't."""

    def test_the_letters_typed_into_a_prompt_go_at_the_dialog_pace_uncalled_and_its_enter_at_the_pace(self):
        plan = TutorialPlan(app=ScreenShown(mock.Mock(spec=PromptDialog, value=OLD_NAME)), target=Setlist.new())
        steps = list(plan.answer_prompt(TYPED_NAME))
        erase = first_key(keybindings.PromptDialog.ERASE)
        done = first_key(keybindings.PromptDialog.DONE)
        self.assertEqual(steps, [Press(erase, True)] * len(OLD_NAME) + [Press(letter, True) for letter in TYPED_NAME] + [Say(MSG_EXPLAIN_ENTER), Press(done)])
        runner = TutorialRunner(app=None, plan=plan, pace=HUMAN_PACE)
        self.assertEqual(runner.key_seconds(steps[-1]), HUMAN_PACE)
        self.assertEqual(runner.key_seconds(steps[len(OLD_NAME)]), HUMAN_PACE * DIALOG_TYPING_SHARE)

    def test_text_typed_outside_a_dialog_goes_at_the_pace_and_is_never_called_or_explained(self):
        plan = TutorialPlan(app=ScreenShown(page_of(PatternsPage)), target=Setlist.new())
        typed = list(plan.type_text(SPACE_CHARACTER.join(TYPED_NAME)))
        self.assertEqual([press.key for press in typed][:2], [TYPED_NAME[0], Key.SPACE])
        self.assertEqual(typed, [Press(key) for key in [press.key for press in typed]])


def pattern_editor_on(view_class):
    """Return a pattern editor showing a view of the class, for a plan that asks only which view is open."""
    editor = mock.Mock(spec=PatternEditor)
    editor.view.return_value = page_of(view_class)
    return editor


class TestTutorialCallsKeys(unittest.TestCase):
    """What the tutorial says as it presses keys, the user's design of 2026-11-10: a letter once on each kind of page with its legend's words; the arrows explained once on the piano roll and once in the rows view, Enter once, and Space once on each kind of page; and nothing else."""

    def setUp(self):
        self.app = ScreenShown(page_of(MainPage))
        self.plan = TutorialPlan(app=self.app, target=Setlist.new())

    def pressed(self, binding):
        return list(self.plan.press(binding))

    def said(self, binding):
        """Return what a press says: its sentences and its call-out."""
        return [step.text if isinstance(step, Say) else step.called for step in self.pressed(binding) if isinstance(step, Say) or step.called is not None]

    def test_a_letter_elsewhere_is_called_with_its_legends_words_once_on_each_kind_of_page(self):
        self.app.screen = page_of(PatternsPage)
        self.assertEqual(self.pressed(keybindings.ListPage.ADD), [Press(Key.A, False, MSG_CALL_LETTER.format(key=KeyName.A, what=keybindings.ListPage.ADD[WORDS]))])
        self.assertEqual(self.pressed(keybindings.ListPage.ADD), [Press(Key.A)])
        self.assertEqual(self.said(keybindings.ListPage.RENAME), [MSG_CALL_LETTER.format(key=KeyName.N, what=keybindings.ListPage.RENAME[WORDS])])
        self.app.screen = page_of(SongsPage)
        self.assertEqual(self.said(keybindings.ListPage.ADD), [MSG_CALL_LETTER.format(key=KeyName.A, what=keybindings.ListPage.ADD[WORDS])])
        self.app.screen = mock.Mock(spec=ConfirmDialog)
        self.assertEqual(self.said(keybindings.ConfirmDialog.YES), [MSG_CALL_LETTER.format(key=KeyName.Y, what=keybindings.ConfirmDialog.YES[WORDS])])

    def test_other_keys_with_words_are_never_called(self):
        self.app.screen = page_of(PatternsPage)
        self.assertEqual(self.said(keybindings.ListPage.DELETE), [])

    def test_esc_is_explained_the_first_time_anywhere_and_never_again(self):
        self.app.screen = page_of(PatternsPage)
        self.assertEqual(self.pressed(keybindings.Page.BACK), [Say(MSG_EXPLAIN_ESCAPE), Press(Key.ESCAPE)])
        self.app.screen = page_of(SongsPage)
        self.assertEqual(self.pressed(keybindings.Page.BACK), [Press(Key.ESCAPE)])

    def test_enter_is_explained_the_first_time_anywhere_and_never_again(self):
        self.app.screen = page_of(PatternsPage)
        self.assertEqual(self.pressed(keybindings.ListPage.EDIT), [Say(MSG_EXPLAIN_ENTER), Press(Key.ENTER)])
        self.app.screen = page_of(SongsPage)
        self.assertEqual(self.pressed(keybindings.SongsPage.SETTINGS), [Press(Key.ENTER)])

    def test_the_arrows_are_explained_the_first_time_anywhere_and_again_once_on_the_piano_roll_and_once_in_the_rows_view(self):
        self.app.screen = page_of(PatternsPage)
        self.assertEqual(self.pressed(Key.DOWN), [Say(MSG_EXPLAIN_ARROWS), Press(Key.DOWN)])
        self.assertEqual(self.pressed(Key.DOWN), [Press(Key.DOWN)])
        self.app.screen = pattern_editor_on(PianoRoll)
        self.assertEqual(self.pressed(Key.RIGHT), [Say(MSG_EXPLAIN_ARROWS_ON_ROLL), Press(Key.RIGHT)])
        self.assertEqual(self.pressed(Key.UP), [Press(Key.UP)])
        self.app.screen = pattern_editor_on(PatternRows)
        self.assertEqual(self.pressed(Key.DOWN), [Say(MSG_EXPLAIN_ARROWS_IN_ROWS), Press(Key.DOWN)])
        self.assertEqual(self.pressed(Key.LEFT), [Press(Key.LEFT)])

    def test_space_is_explained_once_on_each_kind_of_page_in_that_pages_words(self):
        explained = {
            pattern_editor_on(PianoRoll): [MSG_EXPLAIN_SPACE_ON_ROLL, MSG_EXPLAIN_BACKSPACE_ON_ROLL],
            page_of(ArrangePage): [MSG_EXPLAIN_SPACE_ON_ARRANGE],
            pattern_editor_on(PatternRows): [MSG_EXPLAIN_SPACE_TOGGLES],
            page_of(TrackEditor): [MSG_EXPLAIN_SPACE_TOGGLES],
        }
        for screen, sentences in explained.items():
            self.app.screen = screen
            self.assertEqual(self.pressed(Key.SPACE), [*[Say(sentence) for sentence in sentences], Press(Key.SPACE)])
            self.assertEqual(self.pressed(Key.SPACE), [Press(Key.SPACE)])

    def test_typing_explains_nothing(self):
        self.app.screen = pattern_editor_on(PianoRoll)
        self.assertEqual(list(self.plan.type_text(SPACE_CHARACTER)), [Press(Key.SPACE)])


class StepsOnly:
    """A plan of steps given, for a runner that reads nothing else of a plan."""

    __slots__ = ('given', 'left_out')

    def __init__(self, given):
        self.given = given
        self.left_out = []

    def steps(self):
        yield from self.given


class TestTutorialRunnerPauses(unittest.IsolatedAsyncioTestCase):
    """A sentence waits a sentence's pause and a key called waits only the extra second every line of the narrator box gets."""

    async def test_a_sentence_waits_a_sentences_pause_and_a_called_key_a_line_s_second(self):
        happened = []
        app = mock.Mock()
        app.screen.on_key.side_effect = lambda event: happened.append(event.key)
        narrator = mock.Mock(spec=Narrator)
        narrator.say.side_effect = lambda *, text, seconds: happened.append(text)
        narrator.parts.side_effect = lambda text: [text]
        called = MSG_CALL_LETTER.format(key=KeyName.A, what=keybindings.ListPage.ADD[WORDS])
        plan = StepsOnly([Say(MSG_NARRATE_START), Press(Key.S), Press(Key.A, False, called), Press(Key.B)])
        runner = TutorialRunner(app=app, plan=plan, pace=HUMAN_PACE, narrator=narrator)

        async def paused(runner, *, pilot, seconds):
            happened.append(seconds)
        with mock.patch.object(TutorialRunner, PAUSE_METHOD, paused):
            await runner.start()
        self.assertIsNone(runner.problem)
        # Every caption shows long enough to read, and a second more, the user's choice of 2026-11-10.
        say_pause = max(HUMAN_PACE * SAY_PAUSES, len(MSG_NARRATE_START) / READING_CHARACTERS_PER_SECOND) + LINE_SECONDS
        called_pause = len(called) / READING_CHARACTERS_PER_SECOND + LINE_SECONDS
        self.assertEqual(happened, [MSG_NARRATE_START, say_pause, Key.S, HUMAN_PACE, called, called_pause, Key.A, HUMAN_PACE, Key.B, HUMAN_PACE])
        self.assertEqual(runner.pressed, 3)

    def test_at_no_pace_a_caption_waits_nothing_and_a_long_one_waits_longer(self):
        short = MSG_NARRATE_START[:SHORT_CAPTION]
        self.assertEqual(TutorialRunner(app=None, plan=StepsOnly([]), pace=NO_PACE).caption_seconds(part=short, least=NO_PACE), NO_PACE)
        paced = TutorialRunner(app=None, plan=StepsOnly([]), pace=HUMAN_PACE)
        self.assertLess(paced.caption_seconds(part=short, least=NO_PACE), paced.caption_seconds(part=short * LONGER, least=NO_PACE))
