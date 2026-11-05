# noose6: a Python language and framework for producing MIDI clips.
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

import contextlib
import gzip
import importlib
import inspect
import io
import os
import pkgutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from fractions import Fraction
from unittest import mock

import mido

import demo.mary_jazz as jazz
import src.generators
from src.generators.arp import Arp
from src.generators.base import ClipGenerator
from src.generators.blend import Blend
from src.legacy.generators.counterpoint import Counterpoint
from src.legacy.generators.delay import Delay
from src.legacy.generators.force_scale import ForceScale
from src.legacy.generators.hold import Hold
from src.legacy.generators.harmonize import Harmonize
from src.legacy.generators.register import Register
from src.legacy.generators.smoother import Smoother
from src.legacy.generators.stretch import Stretch
from src.generators.take_rhythm import TakeRhythm
from src.note import Degree, Note, Rest
from src.renderers.clip_tree import ClipTree

STACK_SIZE = len(jazz.STACK)
TOTAL_SCENES = 3 + STACK_SIZE + STACK_SIZE + 1


def every_generator_class():
    classes = set()
    for module_info in pkgutil.iter_modules(src.generators.__path__):
        module = importlib.import_module(f'src.generators.{module_info.name}')
        for _, value in inspect.getmembers(module, inspect.isclass):
            if issubclass(value, ClipGenerator) and value is not ClipGenerator:
                classes.add(value)
    return classes


def versions():
    """Return the stack of melody versions, starting with plain Mary."""
    result = [jazz.MARY]
    for step in jazz.STACK:
        result.append(step.generate(result[-1]))
    return result


def sounds(clip):
    """Return (MIDI number or None for a rest, start, length) for everything in a clip."""
    result = []
    now = Fraction(0)
    for position in clip.resolved_notes():
        length = Fraction(position.length).limit_denominator(1_000_000)
        if isinstance(position, Degree):
            position = position.to_note(clip.scale)
        pitch = position.midi_number if isinstance(position, Note) else None
        if not isinstance(position, Rest):
            result.append((pitch, now, length))
        now += length
    return result


class TestSongStructure(unittest.TestCase):

    def setUp(self):
        self.song = jazz.build_song()
        self.melody_track, self.chord_track = self.song.tracks

    def melody(self, scene):
        return self.song.get_clip(scene, self.melody_track)

    def chords(self, scene):
        return self.song.get_clip(scene, self.chord_track)

    def test_has_one_melody_track_and_one_accompaniment_track(self):
        self.assertEqual([track.name for track in self.song.tracks], ['Melody', 'Chords'])

    def test_scenes_follow_the_sections_in_order(self):
        names = [scene.name for scene in self.song.scenes]
        expected = ['Tune Alone', 'Tune With Chords', 'Tune With Arp']
        expected += [f'Going Out {number}' for number in range(1, STACK_SIZE + 1)]
        expected += [f'Coming Back {number}' for number in range(STACK_SIZE - 1, -1, -1)]
        expected += ['Tune Again']
        self.assertEqual(names, expected)
        self.assertEqual(len(names), TOTAL_SCENES)

    def test_tune_starts_alone(self):
        self.assertIsNone(self.chords(self.song.scenes[0]))

    def test_every_other_scene_has_an_accompaniment(self):
        for scene in self.song.scenes[1:]:
            with self.subTest(scene=scene.name):
                self.assertIsNotNone(self.chords(scene))

    def test_third_scene_arpeggiates_the_second_scene_chords(self):
        chords = self.chords(self.song.scenes[1])
        arpeggiated = self.chords(self.song.scenes[2])
        self.assertEqual(arpeggiated.notes, jazz.ARPEGGIATE.generate(chords).notes)
        self.assertNotEqual(arpeggiated.notes, chords.notes)

    def test_opening_scenes_all_play_plain_mary(self):
        for scene in self.song.scenes[:3]:
            with self.subTest(scene=scene.name):
                self.assertEqual(self.melody(scene).notes, jazz.MARY.notes)

    def test_going_out_plays_each_stacked_version(self):
        going_out = self.song.scenes[3:3 + STACK_SIZE]
        for scene, version in zip(going_out, versions()[1:]):
            with self.subTest(scene=scene.name):
                self.assertEqual(self.melody(scene).notes, version.notes)

    def test_ends_on_plain_mary_in_the_minor_key(self):
        last = self.song.scenes[-1]
        minor_mary = jazz.TO_MINOR.generate(jazz.MARY)
        self.assertEqual(self.melody(last).notes, minor_mary.notes)
        self.assertEqual(self.chords(last).notes, jazz.ACCOMPANY.generate(minor_mary).notes)
        self.assertEqual(
            [pitch for pitch, _, _ in sounds(self.melody(last))][:4],
            [48, 47, 45, 47],
        )

    def test_front_half_is_in_the_major_key(self):
        front_half = self.song.scenes[:len(self.song.scenes) // 2]
        for scene in front_half:
            with self.subTest(scene=scene.name):
                self.assertIs(self.melody(scene).scale, jazz.C_MAJOR)

    def test_back_half_is_in_the_minor_key(self):
        back_half = self.song.scenes[len(self.song.scenes) // 2:]
        self.assertEqual(back_half[0].name, f'Going Out {STACK_SIZE}')
        for scene in back_half:
            with self.subTest(scene=scene.name):
                self.assertIs(self.melody(scene).scale, jazz.A_MINOR)
                self.assertIs(self.chords(scene).scale, jazz.A_MINOR)

    def test_back_half_only_plays_notes_and_chords_from_the_minor_key(self):
        minor_pitches = {
            (jazz.A_MINOR.root.midi_number + step) % 12 for step in jazz.A_MINOR.typ.value
        }
        for scene in self.song.scenes[len(self.song.scenes) // 2:]:
            for chord in self.chords(scene).notes:
                with self.subTest(scene=scene.name):
                    self.assertLessEqual(
                        {note.midi_number % 12 for note in chord.notes}, minor_pitches,
                    )

    def test_every_scene_is_eight_measures_long(self):
        for scene in self.song.scenes:
            for clip in [self.melody(scene), self.chords(scene)]:
                if clip is not None:
                    with self.subTest(scene=scene.name):
                        total = sum(
                            Fraction(position.length).limit_denominator(1_000_000)
                            for position in clip.resolved_notes()
                        )
                        self.assertEqual(total, 8)

    def test_chords_are_chosen_from_each_scene_melody(self):
        for scene in self.song.scenes[3:-1]:
            with self.subTest(scene=scene.name):
                self.assertEqual(
                    self.chords(scene).notes,
                    jazz.ACCOMPANY.generate(self.melody(scene)).notes,
                )

    def test_chords_follow_the_change_of_key(self):
        minor = self.song.scenes[-2]
        lowest = {
            min(note.midi_number for note in chord.notes) % 12
            for chord in self.chords(minor).notes
        }
        self.assertLessEqual(lowest, {9, 11, 0, 2, 4, 5, 7})
        self.assertIn(9, lowest)


class TestEveryGeneratorIsUsed(unittest.TestCase):

    def test_every_generator_in_the_project_appears(self):
        used = {type(step) for step in jazz.STACK + jazz.SMALL_MUTATIONS}
        used |= {type(jazz.ACCOMPANY), type(jazz.ARPEGGIATE)}
        # These came later, and need a second song, so demo/gifts_to_sun.py shows them.
        used |= {Blend, Counterpoint, Delay, ForceScale, Harmonize, Hold, Register, Smoother, Stretch, TakeRhythm}
        self.assertEqual(every_generator_class() - used, set())

    def test_arp_is_used_on_the_accompaniment(self):
        self.assertIsInstance(jazz.ARPEGGIATE, Arp)

    def test_every_step_in_the_stack_changes_the_melody(self):
        stacked = versions()
        for step, before, after in zip(jazz.STACK, stacked, stacked[1:]):
            with self.subTest(step=type(step).__name__):
                self.assertNotEqual(sounds(after), sounds(before))


class TestComingBack(unittest.TestCase):

    def setUp(self):
        song = jazz.build_song()
        self.melody_track = song.tracks[0]
        self.song = song
        self.coming_back = song.scenes[3 + STACK_SIZE:-1]

    def test_every_mutation_changes_its_version(self):
        stacked = versions()
        for scene in self.coming_back:
            number = int(scene.name.split()[-1])
            with self.subTest(scene=scene.name):
                self.assertNotEqual(
                    sounds(self.song.get_clip(scene, self.melody_track)),
                    sounds(jazz.TO_MINOR.generate(stacked[number])),
                )

    def test_every_mutation_is_different(self):
        melodies = {
            tuple(sounds(self.song.get_clip(scene, self.melody_track)))
            for scene in self.coming_back
        }
        self.assertEqual(len(melodies), STACK_SIZE)

    def test_more_than_one_kind_of_mutation_is_used(self):
        self.assertGreater(len({type(step) for step in jazz.SMALL_MUTATIONS}), 1)


class TestRendering(unittest.TestCase):

    def render(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        ClipTree(temporary.name, jazz.build_song()).render()
        return temporary.name

    def test_writes_every_clip_with_names_that_sort_in_order(self):
        names = sorted(os.listdir(self.render()))
        self.assertEqual(len(names), TOTAL_SCENES * 2 - 1)
        self.assertEqual(names[0], '001-001-Tune_Alone.mid')
        self.assertEqual(names[1], '002-001-Tune_With_Chords.mid')
        self.assertEqual(names[2], '002-002-Tune_With_Chords.mid')
        self.assertEqual(names[-1], '022-002-Tune_Again.mid')
        self.assertEqual([name[:3] for name in names], sorted(name[:3] for name in names))

    def test_every_file_lasts_sixteen_seconds(self):
        directory = self.render()
        for name in os.listdir(directory):
            with self.subTest(name=name):
                self.assertAlmostEqual(mido.MidiFile(os.path.join(directory, name)).length, 16)

    def test_every_run_gives_the_same_song(self):
        first, second = self.render(), self.render()
        self.assertEqual(sorted(os.listdir(first)), sorted(os.listdir(second)))
        for name in os.listdir(first):
            with self.subTest(name=name):
                with open(os.path.join(first, name), 'rb') as one:
                    with open(os.path.join(second, name), 'rb') as two:
                        self.assertEqual(one.read(), two.read())


class TestChoosingARenderer(unittest.TestCase):

    def run_demo(self, use_ableton):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        directory = os.path.join(temporary.name, 'mary_jazz')
        with mock.patch.object(jazz, 'USE_ABLETON', use_ableton):
            with mock.patch.object(jazz, 'OUTPUT_DIRECTORY', directory):
                with contextlib.redirect_stdout(io.StringIO()):
                    jazz.main()
        return directory

    def test_ableton_is_the_default(self):
        self.assertIs(jazz.USE_ABLETON, True)

    def test_ableton_writes_a_set_into_the_output_directory(self):
        directory = self.run_demo(True)
        self.assertEqual(os.listdir(directory), ['mary_jazz.als'])
        with open(os.path.join(directory, 'mary_jazz.als'), 'rb') as file:
            live_set = ET.fromstring(gzip.decompress(file.read())).find('LiveSet')
        self.assertEqual(len(live_set.find('Scenes')), TOTAL_SCENES)
        self.assertEqual(
            [track.find('Name/EffectiveName').get('Value')
             for track in live_set.find('Tracks').findall('MidiTrack')],
            ['Melody', 'Chords'],
        )
        names = [scene.find('Name').get('Value') for scene in live_set.find('Scenes')]
        self.assertEqual(names[0], 'Tune Alone')
        self.assertEqual(names[-1], 'Tune Again')
        clips = list(live_set.find('Tracks').iter('MidiClip'))
        self.assertEqual(len(clips), (TOTAL_SCENES * 2 - 1) * 2)
        self.assertEqual({clip.find('Loop/LoopEnd').get('Value') for clip in clips}, {'32'})

    def test_clip_tree_writes_midi_files_into_the_output_directory(self):
        directory = self.run_demo(False)
        names = os.listdir(directory)
        self.assertEqual(len(names), TOTAL_SCENES * 2 - 1)
        self.assertTrue(all(name.endswith('.mid') for name in names))


if __name__ == '__main__':
    unittest.main()
