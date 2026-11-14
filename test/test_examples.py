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

"""Every example song loads, plays and renders to every kind of output."""

import contextlib
import functools
import io
import os
import tempfile
import unittest

import yaml

from llamatron.cli import main
from llamatron.tui.document import Document
from llamatron.exporters.exports import ExportKind
from rendering import PIECES, is_demo, render_file
from llamatron.composition.file_format import Section
from llamatron.composition.setlist import Setlist
from llamatron.composition.generator_settings import GENERATOR_SETTINGS
from llamatron.support.example_sets import BY_GENRE, example_sets, folder_of_example, genre_folder
from song_testing import pitches

SONG = 'song'
# Every song in examples/, including the demos, which test_demos.py checks more closely.
EXAMPLE_PATHS = example_sets()
# How long an example runs, in seconds, give or take the leeway, unless it came before the rule or the user asked for another length.
THREE_MINUTES = 180
GENRE_WITH_A_SPACE = 'TV theme'
FOLDER_OF_GENRE_WITH_A_SPACE = 'tv_theme'
GENRE_WITH_A_HYPHEN = 'Hip-Hop'
FOLDER_OF_GENRE_WITH_A_HYPHEN = 'hip_hop'
GENRE_OF_ONE_WORD = 'Rock'
FOLDER_OF_GENRE_OF_ONE_WORD = 'rock'
LENGTH_LEEWAY = 10
WRITTEN_BEFORE_THE_LENGTH_RULE = {
    '12_sailor_arpeggiator.yml', '20_arrangement_shanty.yml', '17_complex_gifts_chain.yml', '10_mtn_king_direction.yml', 'entertainer.yml', '19_hocket_shanty.yml', '09_groove.yml', '01_hello_world.yml',
    '03_mary_keychange.yml', '02_pachelbel.yml', '11_ode_to_joy_ratchet.yml', '22_registers.yml', '04_scale.yml', '18_techno_morph.yml', '08_tie.yml',
}
# The examples the user asked to run another length, by name, with that length in seconds.
OTHER_LENGTHS = {'incoming_message.yml': 526}
# The songs that are meant to sound good, rather than to teach one feature.
SONG_PATHS = [path for path in EXAMPLE_PATHS if not is_demo(path)]


@functools.cache
def example_grid(path):
    """Return an example's finished clips, rendered once however many tests read them."""
    return render_file(path)


class TestExamples(unittest.TestCase):

    paths = EXAMPLE_PATHS
    songs = SONG_PATHS

    def test_the_pieces_are_the_sets_besides_the_demos(self):
        self.assertEqual([os.path.basename(path) for path in self.songs], sorted(PIECES))

    def test_every_homage_is_in_the_folder_of_its_genre(self):
        for path in self.paths:
            if folder_of_example(path) != BY_GENRE:
                continue
            with self.subTest(path=path):
                genres = Setlist.read_file(path).get_genres()
                self.assertEqual(len(genres), 1)
                self.assertEqual(os.path.basename(os.path.dirname(path)), genre_folder(genres[0]))

    def test_a_genres_folder_is_lower_case_with_underscores_for_spaces_and_hyphens(self):
        self.assertEqual(genre_folder(GENRE_WITH_A_SPACE), FOLDER_OF_GENRE_WITH_A_SPACE)
        self.assertEqual(genre_folder(GENRE_WITH_A_HYPHEN), FOLDER_OF_GENRE_WITH_A_HYPHEN)
        self.assertEqual(genre_folder(GENRE_OF_ONE_WORD), FOLDER_OF_GENRE_OF_ONE_WORD)

    def test_every_generator_is_used(self):
        used = set()
        for path in self.paths:
            with open(path) as file:
                for chain in (yaml.safe_load(file).get(Section.CHAINS) or {}).values():
                    used |= {next(iter(step)) for step in chain}
        self.assertEqual(set(GENERATOR_SETTINGS) - used, set())

    def test_every_example_since_the_rule_lasts_about_three_minutes(self):
        # The user's rule of 2026-11-11: a new example runs about three minutes unless the user asks for another length.
        for path in self.paths:
            name = os.path.basename(path)
            if name in WRITTEN_BEFORE_THE_LENGTH_RULE:
                continue
            with self.subTest(path=path):
                seconds = float(Document.load(path).lengths().song_seconds())
                self.assertAlmostEqual(seconds, OTHER_LENGTHS.get(name, THREE_MINUTES), delta=LENGTH_LEEWAY)

    def test_every_song_lasts_about_three_minutes(self):
        for path in self.songs:
            song = example_grid(path)
            seconds = 0
            for scene in song.get_rows():
                lengths = [song.get_clip(row=scene, column=t).total_length() for t in song.get_columns() if song.get_clip(row=scene, column=t)]
                seconds += float(max(lengths)) * 4 * 60 / (scene.get_tempo() or song.get_tempo())
            with self.subTest(path=path):
                self.assertAlmostEqual(seconds, 180, delta=10)

    def test_every_clip_lasts_as_long_as_its_scene_and_fits_a_piano(self):
        for path in self.paths:
            song = example_grid(path)
            for scene in song.get_rows():
                clips = [song.get_clip(row=scene, column=t) for t in song.get_columns() if song.get_clip(row=scene, column=t)]
                self.assertEqual(len({c.total_length() for c in clips}), 1)
                for each in clips:
                    found = pitches(each)
                    if found:
                        with self.subTest(path=path, scene=scene.get_name()):
                            self.assertGreaterEqual(min(found), 21)
                            self.assertLessEqual(max(found), 108)

    def test_tempo_keeps_rising_through_minimal_techno(self):
        song = example_grid('examples/by_genre/electronic/minimal_techno.yml')
        tempos = [scene.get_tempo() or song.get_tempo() for scene in song.get_rows()]
        self.assertEqual(tempos, sorted(tempos))
        self.assertGreater(tempos[-1], tempos[0])


class RendersEveryExample:
    """Renders every example through the command line to one kind of output, set by TO.

    It's mixed into one test class per kind, so that the kinds render in parallel.
    """

    TO = None

    def test_every_example_renders(self):
        for path in EXAMPLE_PATHS:
            with tempfile.TemporaryDirectory() as parent:
                out = os.path.join(parent, SONG)
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(argv=[path, '--to', self.TO, '--out', out]), 0)
                with self.subTest(path=path, to=self.TO):
                    self.assertTrue(os.listdir(out))


class TestExamplesRenderToAbleton(RendersEveryExample, unittest.TestCase):
    TO = ExportKind.ABLETON


class TestExamplesRenderToOneMidiFile(RendersEveryExample, unittest.TestCase):
    TO = ExportKind.MIDI_FILE


class TestExamplesRenderToStems(RendersEveryExample, unittest.TestCase):
    TO = ExportKind.STEMS


class TestExamplesRenderToClipTree(RendersEveryExample, unittest.TestCase):
    TO = ExportKind.CLIP_TREE


class TestExamplesRenderToGeneralMidi(RendersEveryExample, unittest.TestCase):
    TO = ExportKind.GENERAL_MIDI


class TestExamplesHaveSounds(unittest.TestCase):
    """Every example can be heard without a synth through its General MIDI export, the user's design of 2026-11-11."""

    def test_every_melodic_track_that_plays_has_an_instrument_with_a_sound(self):
        for path in EXAMPLE_PATHS:
            setlist = Setlist.read_file(path)
            for song in setlist.get_songs():
                for name in song.get_track_names():
                    track = song.get_track(name)
                    if track.is_drum() or track.is_muted():
                        continue
                    with self.subTest(path=path, track=name):
                        self.assertIsNotNone(track.get_instrument_name())
                        self.assertIsNotNone(setlist.get_instrument(track.get_instrument_name()).get_gm_sound())

    def test_every_example_plays_in_real_time_through_fluidsynth_out_of_the_box(self):
        # The user's design of 2026-11-11: open an example, press Space on Arrange's corner, and hear it, with no synth and no DAW.
        for path in EXAMPLE_PATHS:
            setlist = Setlist.read_file(path)
            with self.subTest(path=path):
                self.assertTrue(setlist.is_real_time())
            for song in setlist.get_songs():
                for name in song.get_track_names():
                    track = song.get_track(name)
                    if track.is_muted():
                        continue
                    with self.subTest(path=path, track=name):
                        self.assertIsNotNone(track.get_instrument_name())
                        self.assertTrue(setlist.get_instrument(track.get_instrument_name()).uses_fluidsynth())

    def test_every_track_that_plays_only_drum_patterns_is_a_drum_track(self):
        # A General MIDI player plays channel 10 as drums, and the export puts drum tracks there, so a drum pattern on another track would play as notes.
        for path in EXAMPLE_PATHS:
            setlist = Setlist.read_file(path)
            for song in setlist.get_songs():
                for name in song.get_track_names():
                    patterns = {scene.get_clip_slot(name).get_pattern_name() for scene in song.get_scenes() if scene.get_clip_slot(name) is not None}
                    if patterns and all(setlist.get_pattern(pattern).is_drum() for pattern in patterns):
                        with self.subTest(path=path, track=name):
                            self.assertTrue(song.get_track(name).is_drum())
