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

"""Malformed song files, checks on the classes underneath, grab edges, and the ways in."""

import os
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock

import yaml

from llamatron.chord import Chord
from llamatron.note import Note
from llamatron.renderers.timing import timed_events
from llamatron.song import Clip, Control, cut_position
from llamatron.composition.song_file_error import SongFileError
from rendering import render_data
from llamatron.tui import app as tui_app
from llamatron.tui.document import Document

ROOT = Path(__file__).resolve().parents[1]

GOOD = """
tempo: 120
scale: main
scales:
  main: { root: C, type: major }
patterns:
  a: { steps: 2, degree: [1, 3], duration: [1/4, 1/4] }
  high: { steps: 1, drum: true, degree: [G], duration: [1/2], octave: [8] }
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
            'not settings': ['tempo: 120'],
            'tempo is true': changed(tempo=True),
            'tempo is words': changed(tempo='fast'),
            'tempo divides by zero': changed(tempo='1/0'),
            'scales is a list': changed(scales=['main']),
            'granularity': changed(granularity='1/3'),
            'pattern is a list': changed(patterns__a=[1, 2]),
            'drum is words': changed(patterns__a={'steps': 1, 'drum': 'yes'}),
            'track settings are a list': changed(tracks={'lead': [1], 'bass': {}}),
            'chain is a dict': changed(chains={'x': {'arp': 'up'}}),
            'chain step has two generators': changed(chains={'x': [{'arp': 'up', 'auto_ratchet': 'up'}]}),
            'scenes is a dict': changed(scenes={'one': {}}),
            'scene is a list': changed(scenes=[['lead']]),
            'scene repeat is zero': changed(scenes__0__repeat=0),
            'tempo ramp has no end': changed(scenes__0__tempo_start=100),
            'arp seed is words': changed(arps={'up': {'step': '1/8', 'seed': 'lucky'}}),
            'counts is not a list': changed(auto_ratchets={'r': {'counts': 4}}, chains={'x': [{'auto_ratchet': 'r'}]}),
        }
        for name, data in cases.items():
            if name in ('arp seed is words', 'counts is not a list'):
                data['scenes'][0]['tracks']['lead']['chain'] = 'x'
            with self.subTest(name=name), self.assertRaises(SongFileError):
                render_data(data)

    def test_a_chord_pushed_past_the_top_of_midi_says_which_clip(self):
        data = changed(patterns__a={'steps': 1, 'degree': [1], 'duration': [1], 'octave': [8], 'chord': ['M']})
        data['arps']['up']['octave_range'] = 4
        data['scenes'][0]['tracks']['lead']['chain'] = 'x'
        with self.assertRaises(SongFileError) as raised:
            render_data(data)
        self.assertIn("scene 1, track 'lead'", str(raised.exception))


class TestGrabEdges(unittest.TestCase):

    def lead(self, data):
        song = render_data(data)
        track = next(track for track in song.tracks if track.name == 'lead')
        found = song.get_clip(song.scenes[0], track)
        return [pitch for _, _, pitch, _ in sorted(timed_events(found, found.scale)[0])]

    def test_a_track_with_no_clip_in_the_scene_leaves_the_notes_alone(self):
        data = good()
        data['patterns']['a']['grab'] = [True, True]
        data['scenes'][0]['tracks']['lead']['grab_track'] = 'bass'
        self.assertEqual(self.lead(data), [60, 64])

    def test_a_grabbed_note_moved_past_the_top_of_midi_stays_where_it_was(self):
        data = good()
        data['patterns']['a']['grab'] = [True, False]
        data['tracks']['lead']['transpose'] = 3
        data['scenes'][0]['tracks'].update(lead={'pattern': 'a', 'grab_track': 'bass'}, bass={'pattern': 'high', 'loop': True})
        self.assertEqual(self.lead(data)[0], 127)


class TestClassChecks(unittest.TestCase):

    def test_controls_are_checked(self):
        for settings in [
            {'time': Fraction(-1), 'number': 1, 'value': 1}, {'time': 0, 'number': 128, 'value': 1},
            {'time': 0, 'number': 1, 'value': -1}, {'time': 0, 'number': 1, 'value': 1, 'slide': 'yes'},
        ]:
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                Control(**settings)

    def test_a_clips_controls_must_be_controls(self):
        with self.assertRaises(ValueError):
            Clip(controls=[(0, 1, 2)])
        with self.assertRaises(ValueError):
            Clip(loop='yes')

    def test_a_settings_descriptor_on_the_class_is_itself(self):
        self.assertTrue(hasattr(Clip.loop, '__set__'))

    def test_cutting_a_chord_cuts_every_note(self):
        chord = Chord([Note('C', 4, 1), Note('E', 4, Fraction(1, 2))])
        cut = cut_position(chord, Fraction(1, 4))
        self.assertEqual([note.length for note in cut.notes], [Fraction(1, 4), Fraction(1, 4)])


class TestDocumentEdges(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(temporary.name)

    def test_loading_a_missing_file_says_so(self):
        with self.assertRaises(SongFileError) as raised:
            Document.load('nowhere.yml')
        self.assertIn("can't read", str(raised.exception))

    def test_a_clip_tree_renders_into_the_songs_folder(self):
        document = Document(good(), 'songs/tune.yml')
        self.assertEqual(document.render_path('cliptree'), os.path.join('output', 'tune'))

    def test_a_render_that_live_refuses_is_explained(self):
        document = Document(changed(tempo=15), 'tune.yml')
        with self.assertRaises(SongFileError) as raised:
            document.render('ableton')
        self.assertIn('tempo', str(raised.exception))

    def test_a_degree_has_no_name_without_a_scale(self):
        document = Document(changed(scale=None))
        self.assertIsNone(document.note_name('a', 0))

    def test_a_scene_cannot_move_past_the_ends(self):
        document = Document(good())
        self.assertFalse(document.move_scene(0, -1))
        self.assertFalse(document.dirty)

    def test_copying_a_chain_copies_its_steps(self):
        document = Document(good())
        new = document.copy_chain('x')
        self.assertEqual(document.data['chains'][new], [{'arp': 'up'}])
        document.data['chains'][new][0]['arp'] = 'other'
        self.assertEqual(document.data['chains']['x'], [{'arp': 'up'}])


class TestWaysIn(unittest.TestCase):

    def run_module(self, *arguments):
        return subprocess.run([sys.executable, '-m', *arguments], capture_output=True, text=True, cwd=ROOT, timeout=60)

    def test_python_m_llamatron_is_the_command(self):
        result = self.run_module('llamatron', '--help')
        self.assertEqual(result.returncode, 0)
        self.assertIn('usage: llamatron', result.stdout)

    def test_python_m_llamatron_tui_explains_a_bad_song(self):
        result = self.run_module('llamatron.tui', 'nowhere.yml')
        self.assertEqual(result.returncode, 1)
        self.assertIn("error: can't read nowhere.yml", result.stderr)

    def test_the_tracker_opens_on_a_named_song(self):
        with mock.patch.object(tui_app.LlamatronApp, 'run') as run, mock.patch.object(tui_app, 'LlamatronApp', wraps=tui_app.LlamatronApp) as made:
            self.assertEqual(tui_app.main([str(ROOT / 'examples' / 'retro_chill.yml')]), 0)
        run.assert_called_once()
        self.assertEqual(made.call_args.args[0].name, 'retro_chill')

    def test_the_tracker_opens_on_a_new_song_without_one(self):
        with mock.patch.object(tui_app.LlamatronApp, 'run') as run:
            self.assertEqual(tui_app.main([]), 0)
        run.assert_called_once()


if __name__ == '__main__':
    unittest.main()
