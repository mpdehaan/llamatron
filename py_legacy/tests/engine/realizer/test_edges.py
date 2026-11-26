# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Malformed song files, checks on the classes underneath, grab edges, and the ways in."""

from fractions import Fraction
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import yaml

from llamatron.engine.clips.clip import Clip
from llamatron.engine.clips.control import Control
from llamatron.engine.clips.positions import cut_position
from llamatron.engine.generators import arp as arp_plugin, timing as timing_plugin
from llamatron.engine.generators.arp.model import ArpSetting
from llamatron.engine.generators.timing import parts as timing_parts
from llamatron.engine.timing.timing import timed_events
from llamatron.exporters.exports import ExportKind
from llamatron.interface.tracker import app as tui_app
from llamatron.interface.tracker.document import Document
from llamatron.math.length import Length
from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.schema import limits
from llamatron.model.schema.file_format import ClipSlotSetting, PatternSetting, Row, Section, SongSetting, TrackSetting
from llamatron.model.values.chord import Chord
from llamatron.model.values.note import Note, NoteName
from llamatron.model.values.sound import Sound
from llamatron.user_strings import names
from tests.support.rendering import render_data, setlist_from_data

ROOT = Path(__file__).resolve().parents[3]

GOOD = """
tempo: 120
scale: main
scales:
  main: { root: C, type: major }
patterns:
  a: { steps: 2, step_size: 1/4, degree: [1, 3] }
  high: { steps: 1, step_size: 1/2, drum: true, degree: [G], octave: [10] }
tracks:
  lead: {}
  bass: {}
arps:
  up: { step: 1/8 }
chains:
  x:
    - arp: up
scenes:
  - name: one
    tracks:
      lead: { pattern: a }
"""

# Names the tests give to their own things, and other values they use.
X = 'x'
NOT_SETTINGS = 'not settings'
TEMPO_IS_TRUE = 'tempo is true'
TEMPO_IS_WORDS = 'tempo is words'
TEMPO_DIVIDES_BY_ZERO = 'tempo divides by zero'
SCALES_IS_A_LIST = 'scales is a list'
STEP_SIZE_IS_A_DECIMAL = 'step size is a decimal'
STEP_SIZE_IS_TOO_LONG = 'step size is too long'
PATTERN_IS_A_LIST = 'pattern is a list'
DRUM_IS_WORDS = 'drum is words'
TRACK_SETTINGS_ARE_A_LIST = 'track settings are a list'
CHAIN_IS_A_DICT = 'chain is a dict'
SCENES_IS_A_DICT = 'scenes is a dict'
SCENE_IS_A_LIST = 'scene is a list'
SCENE_REPEAT_IS_ZERO = 'scene repeat is zero'
TEMPO_RAMP_BARS_ARE_ZERO = 'tempo ramp bars are zero'
STEPS_ARE_NOT_A_LIST = 'steps are not a list'
UP = 'up'
LEAD = 'lead'
FAST = 'fast'
MAIN = 'main'
YES = 'yes'
BASS = 'bass'
ONE = 'one'
R = 'r'
EIGHTH = '1/8'
A = 'a'
HIGH = 'high'
TIME = 'time'
NUMBER = 'number'
VALUE = 'value'
SONGS = 'songs'
TUNE = 'tune'
LLAMATRON = 'llamatron'
TIE_DEMO = '08_tie'
RUN = 'run'
LLAMATRONAPP = 'LlamatronApp'
# The name of the app's document parameter, which main() passes by keyword.
DOCUMENT_ARGUMENT = 'document'
EXAMPLES = 'examples'


def good():
    return yaml.safe_load(GOOD)


def changed(**changes):
    data = good()
    for path, value in changes.items():
        target = data
        keys = path.split('__')
        for key in keys[:-1]:
            target = target[int(key)] if isinstance(target, list) else target[key]
        if isinstance(target, list):
            target[int(keys[-1])] = value
        else:
            target[keys[-1]] = value
    return data


class TestMalformedFiles(unittest.TestCase):
    """Every way a file can be wrong stops with a SongFileError that says where."""

    def test_each_is_refused(self):
        cases = {
            NOT_SETTINGS: ['tempo: 120'],
            TEMPO_IS_TRUE: changed(tempo=True),
            TEMPO_IS_WORDS: changed(tempo=FAST),
            TEMPO_DIVIDES_BY_ZERO: changed(tempo='1/0'),
            SCALES_IS_A_LIST: changed(scales=[MAIN]),
            STEP_SIZE_IS_A_DECIMAL: changed(step_size='0.25'),
            STEP_SIZE_IS_TOO_LONG: changed(step_size=5),
            PATTERN_IS_A_LIST: changed(patterns__a=[1, 2]),
            DRUM_IS_WORDS: changed(patterns__a={PatternSetting.STEPS: 1, PatternSetting.DRUM: YES}),
            TRACK_SETTINGS_ARE_A_LIST: changed(tracks={LEAD: [1], BASS: {}}),
            CHAIN_IS_A_DICT: changed(chains={X: {arp_plugin.NAME: UP}}),
            'chain step has two generators': changed(chains={X: [{arp_plugin.NAME: UP, timing_plugin.NAME: UP}]}),
            SCENES_IS_A_DICT: changed(scenes={ONE: {}}),
            SCENE_IS_A_LIST: changed(scenes=[[LEAD]]),
            SCENE_REPEAT_IS_ZERO: changed(scenes__0__repeat=0),
            TEMPO_RAMP_BARS_ARE_ZERO: changed(scenes__0__tempo_in_over=0),
            STEPS_ARE_NOT_A_LIST: changed(timings={R: {timing_parts.steps_of(timing_parts.RUSH): 4}}, chains={X: [{timing_plugin.NAME: R}]}),
        }
        for name, data in cases.items():
            if name == STEPS_ARE_NOT_A_LIST:
                data[Section.SCENES][0][Section.TRACKS][LEAD][ClipSlotSetting.CHAINS] = [X]
            with self.subTest(name=name), self.assertRaises(SongFileError):
                render_data(data)

    def test_a_chord_pushed_past_the_top_of_midi_says_which_clip(self):
        data = changed(patterns__a={PatternSetting.STEPS: 1, PatternSetting.STEP_SIZE: 1, Row.DEGREE: [1], Row.OCTAVE: [10], Row.CHORD: ['M']})
        data[arp_plugin.SECTION][UP][ArpSetting.OCTAVE_RANGE] = 4
        data[Section.SCENES][0][Section.TRACKS][LEAD][ClipSlotSetting.CHAINS] = [X]
        with self.assertRaises(SongFileError) as raised:
            render_data(data)
        self.assertIn('scene 1, track (lead)', str(raised.exception))


class TestGrabEdges(unittest.TestCase):

    def lead(self, data):
        song = render_data(data)
        track = next(track for track in song.get_columns() if track.get_name() == LEAD)
        found = song.get_clip(row=song.get_rows()[0], column=track)
        return [pitch for _, _, pitch, _ in sorted(timed_events(clip=found, scale=found.get_scale())[0])]

    def test_a_track_with_no_clip_in_the_scene_leaves_the_notes_alone(self):
        data = good()
        data[Section.PATTERNS][A][Row.GRAB] = [True, True]
        data[Section.SCENES][0][Section.TRACKS][LEAD][ClipSlotSetting.GRAB_TRACK] = BASS
        self.assertEqual(self.lead(data), [60, 64])

    def test_a_grabbed_note_moved_past_the_top_of_midi_stays_where_it_was(self):
        data = good()
        data[Section.PATTERNS][A][Row.GRAB] = [True, False]
        data[Section.TRACKS][LEAD][TrackSetting.TRANSPOSE] = 3
        data[Section.SCENES][0][Section.TRACKS].update(lead={ClipSlotSetting.PATTERN: A, ClipSlotSetting.GRAB_TRACK: BASS}, bass={ClipSlotSetting.PATTERN: HIGH, ClipSlotSetting.LOOP: True})
        self.assertEqual(self.lead(data)[0], 127)


class TestClassChecks(unittest.TestCase):

    def test_controls_are_checked(self):
        for settings in [
            {TIME: Fraction(-1), NUMBER: 1, VALUE: 1}, {TIME: 0, NUMBER: 128, VALUE: 1},
            {TIME: 0, NUMBER: 1, VALUE: -1}, {TIME: 0, NUMBER: 1, VALUE: 1, Row.SLIDE: YES},
        ]:
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                Control(**settings)

    def test_a_clips_controls_must_be_controls(self):
        with self.assertRaises(ValueError):
            Clip(controls=[(0, 1, 2)])
        with self.assertRaises(ValueError):
            Clip(loop=YES)

    def test_cutting_a_chord_cuts_every_note(self):
        chord = Chord([Note(name=NoteName.C, octave_number=4, length=1), Note(name=NoteName.E, octave_number=4, length=Fraction(1, 2))])
        cut = Sound.position(cut_position(position=Sound.of(chord), length=Length.exact(Fraction(1, 4))))
        self.assertEqual([note.get_length() for note in cut.get_notes()], [Fraction(1, 4), Fraction(1, 4)])


class TestDocumentEdges(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(temporary.name)

    def test_loading_a_missing_file_says_so(self):
        with self.assertRaises(SongFileError) as raised:
            Document.load('nowhere.yml')
        self.assertIn('cannot read', str(raised.exception))

    def test_a_clip_tree_exports_beside_the_file_named_after_the_set_and_the_song(self):
        document = Document(setlist=setlist_from_data(good()), path=os.path.join(SONGS, 'tune.yml'))
        self.assertEqual(document.export_path(ExportKind.CLIP_TREE), os.path.join(SONGS, f'{TUNE}_{names.MSG_DEFAULT_SONG_NAME}_clip_*.mid'))

    def test_an_export_that_live_refuses_is_explained(self):
        document = Document(setlist=setlist_from_data(changed(tempo=limits.MAX_TEMPO + 1)), path='tune.yml')
        with self.assertRaises(SongFileError) as raised:
            document.export(ExportKind.ABLETON)
        self.assertIn(SongSetting.TEMPO, str(raised.exception))

    def test_a_degree_has_no_name_without_a_scale(self):
        document = Document(setlist=setlist_from_data(changed(scale=None)))
        self.assertIsNone(document.note_name(name=A, step=0))

    def test_a_scene_cannot_move_past_the_ends(self):
        document = Document(setlist=setlist_from_data(good()))
        self.assertFalse(document.move_scene(index=0, offset=-1))
        self.assertFalse(document.is_dirty())

    def test_copying_a_chain_copies_its_steps(self):
        document = Document(setlist=setlist_from_data(good()))
        new = document.copy_named(section=Section.CHAINS, name=X)
        self.assertEqual(document.get_setlist().get_chain(new).get_steps(), [(arp_plugin.NAME, UP)])
        document.change_set(document.get_setlist().get_chain(new).remove_step, 0)
        self.assertEqual(document.get_setlist().get_chain(X).get_steps(), [(arp_plugin.NAME, UP)])


class TestWaysIn(unittest.TestCase):

    def run_module(self, *arguments):
        return subprocess.run([sys.executable, '-m', *arguments], capture_output=True, text=True, cwd=ROOT, timeout=60)

    def test_python_m_llamatron_is_the_command(self):
        result = self.run_module(LLAMATRON, '--help')
        self.assertEqual(result.returncode, 0)
        self.assertIn('usage: llamatron', result.stdout)

    def test_python_m_llamatron_tui_explains_a_bad_song(self):
        result = self.run_module('llamatron.interface.tracker', 'nowhere.yml')
        self.assertEqual(result.returncode, 1)
        self.assertIn('error: cannot read nowhere.yml', result.stderr)

    def test_the_tracker_opens_on_a_named_song(self):
        with mock.patch.object(tui_app.LlamatronApp, RUN) as run, mock.patch.object(tui_app, LLAMATRONAPP, wraps=tui_app.LlamatronApp) as made:
            self.assertEqual(tui_app.main(argv=[str(ROOT / EXAMPLES / 'learning' / '08_tie.yml')]), 0)
        run.assert_called_once()
        self.assertEqual(made.call_args.kwargs[DOCUMENT_ARGUMENT].get_name(), TIE_DEMO)

    def test_the_tracker_opens_on_a_new_song_without_one(self):
        with mock.patch.object(tui_app.LlamatronApp, RUN) as run:
            self.assertEqual(tui_app.main(argv=[]), 0)
        run.assert_called_once()


if __name__ == '__main__':
    unittest.main()
