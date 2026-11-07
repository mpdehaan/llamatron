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

import glob
import unittest

import yaml

from rendering import render_data
from llamatron.composition.song import Song
from llamatron.song_writer import dump_song

SONG = {
    'tempo': 120, 'scale': 'main', 'scales': {'main': {'root': 'C', 'type': 'minor'}, 'A Minor': {'root': 'A', 'type': 'minor'}}, 'seed': 3,
    'step_size': '1/8', 'default_octave': 4, 'default_drum_octave': 0,
    'patterns': {
        'a': {
            'steps': 3, 'step_size': '1/4', 'degree': [1, None, 5], 'gate': ['1/4', '1/8', 1], 'dot': ['d', None, 't'], 'accidental': ['#', None, 'b'],
            'octave': [3, None, 2], 'chord': ['M7', None, 3], 'velocity': [100, None, 90],
            'probability': [50, None, 100], 'ratchet': [2, None, None], 'glide': [True, False, False],
        },
        'hit': {'steps': 1, 'drum': True, 'direction': 'pendulum', 'degree': ['C'], 'grab': [True], 'ratchet_offset': [1], 'ax_velocity': [True], 'bx_add': [-3]},
        'rests': {'steps': 2},
    },
    'tracks': {'lead': {'transpose': 2, 'cc': [74, None, None, 1]}, 'kick': {'drum': True}, 'plain': {}},
    'arps': {'bells': {'step': '1/8', 'order': 'up'}},
    'auto_ratchets': {'rolls': {'counts': [1, 4]}},
    'chains': {'x': [{'auto_ratchet': 'rolls'}, {'arp': 'bells'}], 'nothing': [], 'named': [{'arp': 'bells'}]},
    'registers': {'AX': {'maximum': 3, 'wrap': True}, 'DX': {'minimum': -100, 'default': -5}},
    'scenes': [
        {'name': 'one', 'repeat': 3, 'reset': ['AX', 'DX'], 'scale': 'A Minor', 'tempo_start': 120, 'tempo_end': 130, 'tracks': {'lead': {'pattern': 'a', 'chain': 'x', 'loop': True, 'repeat': 2, 'morph_to': 'hit', 'morph_style': 'left', 'grab_track': 'kick'}}},
        {'tracks': {}},
    ],
}


class TestDumpSong(unittest.TestCase):

    def test_reads_back_the_same(self):
        self.assertEqual(yaml.safe_load(dump_song(SONG)), SONG)

    def test_every_example_reads_back_the_same(self):
        for path in glob.glob('examples/*.yml'):
            with open(path) as file:
                song = yaml.safe_load(file)
            with self.subTest(path=path):
                self.assertEqual(yaml.safe_load(dump_song(song)), song)

    def test_a_description_is_a_readable_block_after_the_title_and_author(self):
        song = {'title': 'T', 'author': 'A', 'description': 'First line\n\n  indented: # not a comment\n', 'tempo': 120, 'tracks': {}, 'scenes': []}
        text = dump_song(song)
        self.assertIn('author: A\ndescription: |\n  First line\n\n    indented: # not a comment\ntempo: 120\n', text)
        self.assertEqual(yaml.safe_load(text), song)

    def test_any_description_reads_back_the_same(self):
        for description in ['one line', 'ends without\nbreak', ' starts indented\n', '\n\nblank first\n', 'many\n\n\n', '\n', '   ', 'a: b\n- c\n']:
            song = {'description': description, 'tempo': 120, 'tracks': {}, 'scenes': []}
            with self.subTest(description=description):
                self.assertEqual(yaml.safe_load(dump_song(song)), song)

    def test_a_song_with_nothing_in_it_writes(self):
        self.assertEqual(yaml.safe_load(dump_song({})), {'tracks': {}, 'scenes': []})

    def test_pattern_rows_are_one_list_per_line(self):
        text = dump_song(SONG)
        self.assertIn('    degree: [1, ~, 5]\n', text)
        self.assertIn('    gate: [1/4, 1/8, 1]\n', text)
        self.assertIn('    dot: [d, ~, t]\n', text)
        self.assertIn('    steps: 3\n    step_size: 1/4\n', text)
        self.assertIn('    accidental: ["#", ~, b]\n', text)
        self.assertIn('    glide: [true, false, false]\n', text)
        self.assertIn('    drum: true\n    direction: pendulum\n', text)
        self.assertIn('    ax_velocity: [true]\n    bx_add: [-3]\n', text)

    def test_follows_the_format_rules(self):
        text = dump_song(SONG)
        self.assertIn('tracks:\n  lead: { transpose: 2, cc: [74, ~, ~, 1] }\n  kick: { drum: true }\n  plain: {}\n', text)
        self.assertIn('      lead: { pattern: a, chain: x, loop: true, repeat: 2, morph_to: hit, morph_style: left, grab_track: kick }', text)
        self.assertIn('arps:\n  bells: { step: 1/8, order: up }', text)
        self.assertIn('registers:\n  AX: { maximum: 3, wrap: true }\n  DX: { minimum: -100, default: -5 }\n\nscenes:', text)
        self.assertIn("  - name: one\n    repeat: 3\n    reset: [AX, DX]\n", text)
        self.assertIn('auto_ratchets:\n  rolls: { counts: [1, 4] }', text)
        self.assertIn('    - arp: bells', text)
        self.assertIn('    - auto_ratchet: rolls', text)
        self.assertIn('scales:\n  main: { root: C, type: minor }\n  A Minor: { root: A, type: minor }', text)

    def test_awkward_names_survive(self):
        names = ['a, b', 'a: b', '#hash', 'yes', '123', 'null', '{x}', "it's", 'say "hi"', 'tab\there', ' spaced ']
        for name in names:
            song = {**SONG, 'tracks': {name: {}}, 'scenes': [{'name': name, 'tracks': {name: {'pattern': 'a'}}}]}
            with self.subTest(name=name):
                self.assertEqual(yaml.safe_load(dump_song(song)), song)

    def test_empty_sections_are_left_out(self):
        song = {'tempo': 120, 'scale': None, 'scales': {}, 'patterns': {}, 'tracks': {'a': {}}, 'chains': {}, 'scenes': [{'tracks': {}}]}
        text = dump_song(song)
        for section in ['patterns', 'scales', 'chains']:
            self.assertNotIn(section, text)
        render_data(yaml.safe_load(text))

    def test_a_new_song_with_nothing_in_it_reads_back(self):
        song = {'tempo': 120, 'tracks': {}, 'scenes': []}
        self.assertEqual(yaml.safe_load(dump_song(song)), song)
        render_data(yaml.safe_load(dump_song(song)))

    def test_a_fraction_stays_text_and_a_number_stays_a_number(self):
        song = yaml.safe_load(dump_song(SONG))
        self.assertEqual(song['patterns']['a']['gate'][0], '1/4')
        self.assertEqual(song['tempo'], 120)

    def test_a_song_that_was_written_still_builds(self):
        for path in glob.glob('examples/*.yml'):
            with open(path) as file:
                song = yaml.safe_load(file)
            with self.subTest(path=path):
                Song.from_data(yaml.safe_load(dump_song(song)))


if __name__ == '__main__':
    unittest.main()
