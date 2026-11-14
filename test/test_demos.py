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

"""The demos in examples/ build, export and save, and the generator that wrote them matches its sources.

The demos are the sets in examples/ whose names end in _demo, each holding one song, and docs/DEMOS.md describes
them. TestDemos deliberately doesn't check what they play, so that they can be edited freely.
TestDemoSources instead runs test/demo_sources/make_demos.py into a temporary folder, and checks
what it writes against the source data kept beside it, so nothing here uses the network.
"""

import collections
import contextlib
import glob
import importlib.util
import io
import os
import pathlib
import tempfile
import unittest
from fractions import Fraction

import yaml

from llamatron.composition.file_format import Section, SetlistSetting, TrackSetting
from llamatron.tui.drawing import LINE_BREAK
from llamatron.exporters.ableton_project import AbletonProject
from llamatron.exporters.clip_tree import ClipTree
from llamatron.exporters.timing import timed_events
from rendering import is_demo, render_file
from llamatron.composition.setlist_writer import dump_setlist
from llamatron.tui.document import Document
from llamatron.support.example_sets import example_sets

PATHS = sorted(path for path in example_sets() if is_demo(path))
# Demos written by hand, rather than first written by test/demo_sources/make_demos.py.
HAND_WRITTEN = ['15_acid_articulate.yml', '14_acid_glide.yml', '07_blues_chords.yml', '16_bolero_swell.yml', '06_chord_progression_generator.yml', 'edm_density.yml', 'euclidean.yml', '09_groove.yml', '01_hello_world.yml', '21_look_ma_no_notes.yml', '03_mary_keychange.yml', '22_registers.yml', '13_classic_strum.yml', '08_tie.yml', '05_voice_leading.yml',
                # Written with a composing tool of Claude's (dev_notes/IDEAS.md, "A composing tool"), not by make_demos.py.
                'rick_rolling.yml', 'peanut_buttercup.yml', 'bless_the_rains.yml', 'goodnight_world.yml', 'spot_over_there.yml', 'know_your_slang.yml', 'green_men.yml', 'training_montage.yml', 'secret_chord.yml', 'sax_reindeer.yml', 'spy_hunting.yml', 'phoenix_foundation.yml', 'uphill_cops.yml', 'forgot_your_name.yml', 'tropical_51.yml', 'not_painless.yml', 'mysterious_spooky.yml', 'strange_woodworking.yml', 'get_the_traps_egon.yml', 'sandworm.yml', 'aliens_counting.yml', 'angry_shark.yml', 'very_large_mammals.yml', 'four_wheels_g.yml', 'microwave_snacks.yml', 'nomore_nomore.yml', 'fang_removal.yml', 'not_werewolves.yml', 'annandale.yml', 'volcano.yml', 'incoming_message.yml', 'the_mineral.yml', 'not_star_trek.yml']
SOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'demo_sources')

# Names the tests give to their own things, and other values they use.
WARNING = 'warning'
LIVE = 'live'
CLIPS = 'clips'
SILENT = 'SILENT'
MAKE_DEMOS = 'make_demos'
# The pages that describe the demos, one for each genre.
DEMO_PAGES = os.path.join('docs', 'demos')
DEMO_PAGE_FILES = '*.md'
NOTHING = ''
# Every set the generator writes, in whichever folder of its output.
WRITTEN_SETS = os.path.join('**', '*.yml')
PAD = 'pad'
BASS = 'bass'
VOICE = 'voice'
SILENT_MELODY = 'SILENT melody'


def names():
    return sorted(os.path.basename(path) for path in PATHS)


def without_version(data):
    """Return a set's data without the version it was saved with, which moves with every release of the program."""
    return {key: value for key, value in data.items() if key != SetlistSetting.VERSION}



class TemporaryFolderTest(unittest.TestCase):
    """A test with an empty folder of its own, removed when it's done."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = temporary.name


class TestDemosRender(TemporaryFolderTest):
    """Renders every demo both ways, in a class of its own so that it runs alongside the other checks."""

    def test_every_demo_renders_both_ways(self):
        for path in PATHS:
            name = os.path.splitext(os.path.basename(path))[0]
            with self.subTest(path=path):
                song = render_file(path)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    ClipTree(directory=os.path.join(self.folder, CLIPS, name), grid=song).export()
                    AbletonProject(directory=os.path.join(self.folder, LIVE, name), grid=song).export()
                self.assertNotIn(WARNING, output.getvalue())
                self.assertTrue(os.path.exists(os.path.join(self.folder, LIVE, name, f'{name}.als')))


class TestDemos(TemporaryFolderTest):

    def test_there_are_demos(self):
        self.assertGreaterEqual(len(PATHS), 10)

    def test_every_demo_reads_back_the_same_after_writing(self):
        for path in PATHS:
            with open(path) as file:
                data = yaml.safe_load(file)
            with self.subTest(path=path):
                self.assertEqual(yaml.safe_load(dump_setlist(data)), data)

    def test_every_demo_saves_and_loads_the_same_in_the_tracker(self):
        for path in PATHS:
            target = os.path.join(self.folder, os.path.basename(path))
            Document.load(path).save(path=target)
            with open(path) as first, open(target) as second:
                original = yaml.safe_load(first)
                saved = yaml.safe_load(second)
            with self.subTest(path=path):
                self.assertEqual(without_version({key: saved[key] for key in original}), without_version(original))

    def test_every_demo_has_a_title_a_description_of_what_it_plays_and_notes_on_what_it_shows(self):
        for path in PATHS:
            with open(path) as file:
                data = yaml.safe_load(file)
            with self.subTest(path=path):
                self.assertTrue(data.get(SetlistSetting.TITLE))
                self.assertTrue(data.get(SetlistSetting.DESCRIPTION))
                self.assertNotIn(LINE_BREAK, data.get(SetlistSetting.DESCRIPTION).strip())
                self.assertIn('When changing this demo:', data.get(SetlistSetting.NOTES, ''))

    def test_every_demo_is_described_on_a_genre_page_and_nothing_else_is(self):
        # Each demo has a section on its genre's page in docs/demos/, the user's layout, where its description lives.
        text = NOTHING.join(path.read_text() for path in sorted(pathlib.Path(DEMO_PAGES).glob(DEMO_PAGE_FILES)))
        for name in names():
            with self.subTest(name=name):
                self.assertIn(f'`{name}`', text)
        words = [os.path.basename(word.strip('`.,')) for word in text.split() if word.startswith('`')]
        mentioned = {word for word in words if is_demo(word)}
        self.assertEqual(mentioned - set(names()), set())

    def test_muted_tracks_and_only_those_are_named_silent(self):
        for path in PATHS:
            with open(path) as file:
                songs = yaml.safe_load(file)[Section.SONGS]
            for song in songs.values():
                for name, settings in song[Section.TRACKS].items():
                    with self.subTest(path=path, track=name):
                        self.assertEqual(bool(settings.get(TrackSetting.MUTE)), SILENT in name)


def load_generator():
    """Import make_demos.py from test/demo_sources, which isn't a package."""
    spec = importlib.util.spec_from_file_location(MAKE_DEMOS, os.path.join(SOURCES, 'make_demos.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def onsets(*, song, scene, track_name):
    """Return (start, MIDI number) for each note a track plays in a scene, in whole notes."""
    track = next(track for track in song.get_columns() if track.get_name() == track_name)
    clip = song.get_clip(row=scene, column=track)
    if clip is None:
        return []
    return [(Fraction(event[0]), event[2]) for event in timed_events(clip=clip, scale=clip.get_scale())[0]]


class TestDemoSources(unittest.TestCase):
    """The generator writes demos that build, and that play what its sources say."""

    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.folder = temporary.name
        cls.generator = load_generator()
        cls.generator.main(output=cls.folder)

    def written(self):
        """Return each demo the generator wrote, by its file name, with where it went."""
        return {os.path.basename(path): path for path in glob.glob(os.path.join(self.folder, WRITTEN_SETS), recursive=True)}

    def made(self, name):
        return render_file(self.written()[name])

    def test_it_writes_every_demo_and_each_one_builds(self):
        written = sorted(self.written())
        self.assertEqual(sorted(written + HAND_WRITTEN), names())
        for name in written:
            with self.subTest(name=name):
                self.made(name)

    def test_the_entertainer_plays_the_notes_of_its_midi_file(self):
        song = self.made('entertainer.yml')
        played = collections.Counter()
        # The scenes are laid end to end, eight bars each but for the four-bar Intro and Bridge.
        for scene, start in zip(song.get_rows(), song.row_starts()):
            for track in song.get_columns():
                for time, number in onsets(song=song, scene=scene, track_name=track.get_name()):
                    played[(start + time, number)] += 1
        source = collections.Counter(
            (time, number) for hand in (1, 2) for time, number, _, _ in self.generator.entertainer_notes(hand)
        )
        self.assertEqual(sum((played - source).values()), 0)
        # A fourth note sounding at once in one hand has no voice to go to, and that happens 19 times.
        self.assertEqual(sum((source - played).values()), 19)

    def test_the_hocketing_voices_add_up_to_the_melody(self):
        song = self.made('19_hocket_shanty.yml')
        for scene in song.get_rows():
            voices = [track.get_name() for track in song.get_columns() if track.get_name().startswith(VOICE)]
            playing = [name for name in voices if onsets(song=song, scene=scene, track_name=name)]
            if len(playing) < len(voices):
                continue
            with self.subTest(scene=scene.get_name()):
                together = sorted(note for name in voices for note in onsets(song=song, scene=scene, track_name=name))
                self.assertEqual(together, sorted(onsets(song=song, scene=scene, track_name=SILENT_MELODY)))

    def test_the_arrangement_bass_plays_the_pad_roots_an_octave_down(self):
        song = self.made('20_arrangement_shanty.yml')
        scene = song.get_rows()[2]
        pad = onsets(song=song, scene=scene, track_name=PAD)
        roots = {time: min(number for start, number in pad if start == time) for time, _ in pad}
        for time, number in onsets(song=song, scene=scene, track_name=BASS):
            latest = max(start for start in roots if start <= time)
            self.assertEqual(number, roots[latest] - 12)


if __name__ == '__main__':
    unittest.main()
