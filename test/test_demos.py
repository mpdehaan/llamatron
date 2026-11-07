# llamatron: a Python language and framework for producing MIDI clips.
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

"""The demos in examples/ build, render and save, and the generator that wrote them matches its sources.

The demos are the songs in examples/ whose names end in _demo, and examples/DEMOS.md describes
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
import tempfile
import unittest
from fractions import Fraction

import yaml

from llamatron.renderers.ableton_project import AbletonProject
from llamatron.renderers.clip_tree import ClipTree
from llamatron.renderers.timing import timed_events
from rendering import is_demo, render_file
from llamatron.song_writer import dump_song
from llamatron.tui.document import Document

PATHS = sorted(path for path in glob.glob('examples/*.yml') if is_demo(path))
# Demos written by hand, rather than first written by test/demo_sources/make_demos.py.
HAND_WRITTEN = ['demo_registers.yml']
# Song files' names end like this.
YAML_ENDING = '.yml'
SOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'demo_sources')


def names():
    return [os.path.basename(path) for path in PATHS]


class TestDemos(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = temporary.name

    def test_there_are_demos(self):
        self.assertGreaterEqual(len(PATHS), 10)

    def test_every_demo_renders_both_ways(self):
        for path in PATHS:
            name = os.path.splitext(os.path.basename(path))[0]
            with self.subTest(path=path):
                song = render_file(path)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    ClipTree(os.path.join(self.folder, 'clips', name), song).render()
                    AbletonProject(os.path.join(self.folder, 'live', name), song).render()
                self.assertNotIn('warning', output.getvalue())
                self.assertTrue(os.path.exists(os.path.join(self.folder, 'live', name, f'{name}.als')))

    def test_every_demo_reads_back_the_same_after_writing(self):
        for path in PATHS:
            with open(path) as file:
                data = yaml.safe_load(file)
            with self.subTest(path=path):
                self.assertEqual(yaml.safe_load(dump_song(data)), data)

    def test_every_demo_saves_and_loads_the_same_in_the_tracker(self):
        for path in PATHS:
            target = os.path.join(self.folder, os.path.basename(path))
            Document.load(path).save(target)
            with open(path) as first, open(target) as second:
                original, saved = yaml.safe_load(first), yaml.safe_load(second)
            with self.subTest(path=path):
                self.assertEqual({key: saved[key] for key in original}, original)

    def test_every_demo_has_a_title_and_a_description_of_what_it_shows(self):
        for path in PATHS:
            with open(path) as file:
                data = yaml.safe_load(file)
            with self.subTest(path=path):
                self.assertTrue(data.get('title'))
                self.assertIn('When changing this demo:', data.get('description', ''))

    def test_every_demo_is_described_in_demos_md_and_nothing_else_is(self):
        with open('examples/DEMOS.md') as file:
            text = file.read()
        for name in names():
            with self.subTest(name=name):
                self.assertIn(f'`{name}`', text)
        words = [word.strip('`.,') for word in text.split() if word.startswith('`')]
        mentioned = {word for word in words if word.endswith(YAML_ENDING) and is_demo(word)}
        self.assertEqual(mentioned - set(names()), set())

    def test_muted_tracks_and_only_those_are_named_silent(self):
        for path in PATHS:
            with open(path) as file:
                tracks = yaml.safe_load(file)['tracks']
            for name, settings in tracks.items():
                with self.subTest(path=path, track=name):
                    self.assertEqual(bool(settings.get('mute')), 'SILENT' in name)


def load_generator():
    """Import make_demos.py from test/demo_sources, which isn't a package."""
    spec = importlib.util.spec_from_file_location('make_demos', os.path.join(SOURCES, 'make_demos.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def onsets(song, scene, track_name):
    """Return (start, MIDI number) for each note a track plays in a scene, in whole notes."""
    track = next(track for track in song.tracks if track.name == track_name)
    clip = song.get_clip(scene, track)
    if clip is None:
        return []
    return [(Fraction(event[0]), event[2]) for event in timed_events(clip, clip.scale)[0]]


class TestDemoSources(unittest.TestCase):
    """The generator writes demos that build, and that play what its sources say."""

    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.folder = temporary.name
        cls.generator = load_generator()
        cls.generator.main(cls.folder)

    def made(self, name):
        return render_file(os.path.join(self.folder, name))

    def test_it_writes_every_demo_and_each_one_builds(self):
        written = sorted(os.listdir(self.folder))
        self.assertEqual(sorted(written + HAND_WRITTEN), names())
        for name in written:
            with self.subTest(name=name):
                self.made(name)

    def test_the_entertainer_plays_the_notes_of_its_midi_file(self):
        song = self.made('entertainer_demo.yml')
        played = collections.Counter()
        start = Fraction(0)
        for scene in song.scenes:
            for track in song.tracks:
                for time, number in onsets(song, scene, track.name):
                    played[(start + time, number)] += 1
            start += self.generator.PHRASE
        source = collections.Counter(
            (time, number) for hand in (1, 2) for time, number, _, _ in self.generator.entertainer_notes(hand)
        )
        self.assertEqual(sum((played - source).values()), 0)
        # A fourth note sounding at once in one hand has no voice to go to, and that happens 19 times.
        self.assertEqual(sum((source - played).values()), 19)

    def test_the_hocketing_voices_add_up_to_the_melody(self):
        song = self.made('grab_demo.yml')
        for scene in song.scenes:
            voices = [track.name for track in song.tracks if track.name.startswith('voice')]
            playing = [name for name in voices if onsets(song, scene, name)]
            if len(playing) < len(voices):
                continue
            with self.subTest(scene=scene.name):
                together = sorted(note for name in voices for note in onsets(song, scene, name))
                self.assertEqual(together, sorted(onsets(song, scene, 'SILENT melody')))

    def test_the_arrangement_bass_plays_the_pad_roots_an_octave_down(self):
        song = self.made('arrangement_demo.yml')
        scene = song.scenes[2]
        pad = onsets(song, scene, 'pad')
        roots = {time: min(number for start, number in pad if start == time) for time, _ in pad}
        for time, number in onsets(song, scene, 'bass'):
            latest = max(start for start in roots if start <= time)
            self.assertEqual(number, roots[latest] - 12)


if __name__ == '__main__':
    unittest.main()
