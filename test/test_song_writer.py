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

import glob
import unittest

import yaml

from src.song_file import SongBuilder
from src.song_writer import dump_song

SONG = {
    'tempo': 120, 'scale': 'main', 'scales': {'main': {'root': 'C', 'type': 'minor'}, 'A Minor': {'root': 'A', 'type': 'minor'}}, 'seed': 3,
    'default_length': '1/8', 'granularity': '1/32', 'default_octave': 4, 'default_drum_octave': 0,
    'patterns': {
        'a': {
            'steps': 3, 'degree': [1, None, 5], 'duration': ['1/4', '1/8', 1], 'accidental': ['#', None, 'b'],
            'octave': [3, None, 2], 'chord': ['M7', None, 3], 'velocity': [100, None, 90],
            'probability': [50, None, 100], 'ratchet': [2, None, None], 'glide': [True, None, False],
        },
        'hit': {'steps': 1, 'drum': True, 'direction': 'pendulum', 'source_pattern': 'a', 'accumulator_limit': 5, 'degree': ['C'], 'duration': ['1/16'], 'grab': [True], 'ratchet_offset': [1], 'note_add': [-1], 'velocity_add': [3]},
        'rests': {'steps': 2},
    },
    'tracks': ['lead', 'kick', 'plain'],
    'arps': {'bells': {'step': '1/8', 'order': 'up'}},
    'auto_ratchets': {'rolls': {'counts': [1, 4]}},
    'chains': {'x': [{'mix_up': {'probabilities': [0.5, 0.25]}}, {'reverse': {}}], 'nothing': [], 'named': [{'arp': 'bells'}]},
    'scenes': [
        {'name': 'one', 'repeat': 3, 'scale': 'A Minor', 'tempo_start': 120, 'tempo_end': 130, 'tracks': {'lead': {'pattern': 'a', 'chain': 'x', 'loop': True, 'repeat': 2, 'morph_to': 'hit', 'morph_style': 'left', 'rhythm_from': 'hit', 'notes_from': 'rests'}}},
        {'tracks': {}},
    ],
    'paint': [{'chain': 'x', 'tracks': ['lead', 'kick'], 'scenes': [1, 2]}],
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

    def test_pattern_rows_are_one_list_per_line(self):
        text = dump_song(SONG)
        self.assertIn('    degree: [1, ~, 5]\n', text)
        self.assertIn('    duration: [1/4, 1/8, 1]\n', text)
        self.assertIn('    accidental: ["#", ~, b]\n', text)
        self.assertIn('    glide: [true, ~, false]\n', text)
        self.assertIn('    drum: true\n    direction: pendulum\n    source_pattern: a\n    accumulator_limit: 5\n', text)

    def test_follows_the_format_rules(self):
        text = dump_song(SONG)
        self.assertIn('tracks: [lead, kick, plain]', text)
        self.assertIn('      lead: { pattern: a, chain: x, loop: true, repeat: 2, morph_to: hit, morph_style: left, rhythm_from: hit, notes_from: rests }', text)
        self.assertIn('arps:\n  bells: { step: 1/8, order: up }', text)
        self.assertIn('auto_ratchets:\n  rolls: { counts: [1, 4] }', text)
        self.assertIn('    - arp: bells', text)
        self.assertIn('    - mix_up: { probabilities: [0.5, 0.25] }', text)
        self.assertIn('  - { chain: x, tracks: [lead, kick], scenes: [1, 2] }', text)
        self.assertIn('scales:\n  main: { root: C, type: minor }\n  A Minor: { root: A, type: minor }', text)

    def test_awkward_names_survive(self):
        names = ['a, b', 'a: b', '#hash', 'yes', '123', 'null', '{x}', "it's", 'say "hi"', 'tab\there', ' spaced ']
        for name in names:
            song = {**SONG, 'tracks': [name], 'scenes': [{'name': name, 'tracks': {name: {'pattern': 'a'}}}]}
            del song['paint']
            with self.subTest(name=name):
                self.assertEqual(yaml.safe_load(dump_song(song)), song)

    def test_empty_sections_are_left_out(self):
        song = {'tempo': 120, 'scale': None, 'scales': {}, 'patterns': {}, 'tracks': ['a'], 'chains': {}, 'scenes': [{'tracks': {}}], 'paint': []}
        text = dump_song(song)
        for section in ['patterns', 'scales', 'chains', 'paint']:
            self.assertNotIn(section, text)
        SongBuilder(yaml.safe_load(text)).build()

    def test_a_new_song_with_nothing_in_it_reads_back(self):
        song = {'tempo': 120, 'tracks': [], 'scenes': []}
        self.assertEqual(yaml.safe_load(dump_song(song)), song)
        SongBuilder(yaml.safe_load(dump_song(song))).build()

    def test_a_fraction_stays_text_and_a_number_stays_a_number(self):
        song = yaml.safe_load(dump_song(SONG))
        self.assertEqual(song['patterns']['a']['duration'][0], '1/4')
        self.assertEqual(song['tempo'], 120)

    def test_a_song_that_was_written_still_builds(self):
        for path in glob.glob('examples/*.yml'):
            with open(path) as file:
                song = yaml.safe_load(file)
            with self.subTest(path=path):
                SongBuilder(yaml.safe_load(dump_song(song)))


if __name__ == '__main__':
    unittest.main()
