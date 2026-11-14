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

import unittest

import yaml

from llamatron.composition.setlist import Setlist
from llamatron.composition.setlist_writer import dump_setlist
from rendering import as_setlist, render_data
from llamatron.composition.file_format import ClipSlotSetting, PatternSetting, Row, SceneSetting, Section, SetlistSetting, SongSetting
from llamatron.support.example_sets import example_sets

# One song, laid out the way files were before sets existed, which as_setlist turns into a set of one song.
SONG = {
    'tempo': 120, 'scale': 'main', 'scales': {'main': {'root': 'C', 'type': 'minor'}, 'A Minor': {'root': 'A', 'type': 'minor'}}, 'seed': 3,
    'step_size': '1/8', 'default_octave': 4, 'default_drum_octave': 0,
    'patterns': {
        'a': {
            'steps': 3, 'step_size': '1/4', 'degree': [1, None, 5], 'gate': ['1/4', '1/8', 1], 'dot': ['d', None, 't'], 'accidental': ['#', None, 'b'],
            'octave': [3, None, 2], 'chord': ['M7', None, 3], 'velocity': [100, None, 90],
            'probability': [50, None, 100], 'ratchet': [2, None, None], 'glide': [True, False, False],
        },
        'hit': {'steps': 1, 'drum': True, 'direction': 'pendulum', 'degree': ['C'], 'grab': [True], 'ratchet_offset': [1], 'ax_velocity': [1], 'bx_add': [-3]},
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
SETLIST = as_setlist(SONG)

# Names the tests give to their own things, and other values they use.
T = 'T'
D = 'D'
A = 'A'
ONE_LINE = 'one line'
YES = 'yes'
NULL = 'null'
QUARTER = '1/4'
WALTZ = '3/4'
A_2 = 'a'
UNTITLED = 'untitled'


class TestDumpSetlist(unittest.TestCase):

    def test_reads_back_the_same(self):
        self.assertEqual(yaml.safe_load(dump_setlist(SETLIST)), SETLIST)

    def test_every_example_reads_back_the_same(self):
        for path in example_sets():
            with open(path) as file:
                song = yaml.safe_load(file)
            with self.subTest(path=path):
                self.assertEqual(yaml.safe_load(dump_setlist(song)), song)

    def test_the_notes_are_a_readable_block_after_the_title_author_and_description(self):
        setlist = {SetlistSetting.TITLE: T, SetlistSetting.AUTHOR: A, SetlistSetting.DESCRIPTION: D, SetlistSetting.NOTES: 'First line\n\n  indented: # not a comment\n', PatternSetting.STEP_SIZE: '1/8', Section.SONGS: {}}
        text = dump_setlist(setlist)
        self.assertIn('author: A\ndescription: D\nnotes: |\n  First line\n\n    indented: # not a comment\nstep_size: 1/8\n', text)
        self.assertEqual(yaml.safe_load(text), setlist)

    def test_any_notes_read_back_the_same(self):
        for description in [ONE_LINE, 'ends without\nbreak', ' starts indented\n', '\n\nblank first\n', 'many\n\n\n', '\n', '   ', 'a: b\n- c\n']:
            setlist = {SetlistSetting.NOTES: description, Section.SONGS: {}}
            with self.subTest(description=description):
                self.assertEqual(yaml.safe_load(dump_setlist(setlist)), setlist)

    def test_a_set_with_nothing_in_it_writes(self):
        self.assertEqual(dump_setlist({}), 'songs: {}\n')
        self.assertEqual(yaml.safe_load(dump_setlist({})), {Section.SONGS: {}})

    def test_each_song_is_indented_under_songs_with_its_own_settings_first(self):
        text = dump_setlist(SETLIST)
        self.assertIn('\nsongs:\n  untitled:\n    tempo: 120\n    scale: main\n    seed: 3\n', text)
        self.assertIn('\n    registers:\n      AX: { maximum: 3, wrap: true }\n', text)
        self.assertIn('\n    tracks:\n      lead: { transpose: 2, cc: [74, ~, ~, 1] }\n', text)
        self.assertIn('\n    scenes:\n      - name: one\n        repeat: 3\n', text)

    def test_a_time_signature_follows_the_tempo_on_a_song_and_the_step_size_on_a_pattern(self):
        setlist = as_setlist({
            SongSetting.TEMPO: 120, SongSetting.TIME_SIGNATURE: WALTZ, Section.TRACKS: {}, Section.SCENES: [],
            Section.PATTERNS: {A_2: {PatternSetting.STEPS: 1, PatternSetting.STEP_SIZE: QUARTER, PatternSetting.TIME_SIGNATURE: WALTZ}},
        })
        loaded = yaml.safe_load(dump_setlist(setlist))
        self.assertEqual(loaded, setlist)
        self.assertEqual(list(loaded[Section.SONGS][UNTITLED]), [SongSetting.TEMPO, SongSetting.TIME_SIGNATURE, Section.TRACKS, Section.SCENES])
        self.assertEqual(list(loaded[Section.PATTERNS][A_2]), [PatternSetting.STEPS, PatternSetting.STEP_SIZE, PatternSetting.TIME_SIGNATURE])

    def test_pattern_rows_are_one_list_per_line(self):
        text = dump_setlist(SETLIST)
        self.assertIn('    degree: [1, ~, 5]\n', text)
        self.assertIn('    gate: [1/4, 1/8, 1]\n', text)
        self.assertIn('    dot: [d, ~, t]\n', text)
        self.assertIn('    steps: 3\n    step_size: 1/4\n', text)
        self.assertIn('    accidental: ["#", ~, b]\n', text)
        self.assertIn('    glide: [true, false, false]\n', text)
        self.assertIn('    drum: true\n    direction: pendulum\n', text)
        self.assertIn('    ax_velocity: [1]\n    bx_add: [-3]\n', text)

    def test_follows_the_format_rules(self):
        text = dump_setlist(SETLIST)
        self.assertIn('    tracks:\n      lead: { transpose: 2, cc: [74, ~, ~, 1] }\n      kick: { drum: true }\n      plain: {}\n', text)
        self.assertIn('          lead: { pattern: a, chain: x, loop: true, repeat: 2, morph_to: hit, morph_style: left, grab_track: kick }', text)
        self.assertIn('arps:\n  bells: { step: 1/8, order: up }', text)
        self.assertIn('    registers:\n      AX: { maximum: 3, wrap: true }\n      DX: { minimum: -100, default: -5 }\n\n    tracks:', text)
        self.assertIn("      - name: one\n        repeat: 3\n        reset: [AX, DX]\n", text)
        self.assertIn('auto_ratchets:\n  rolls: { counts: [1, 4] }', text)
        self.assertIn('    - arp: bells', text)
        self.assertIn('    - auto_ratchet: rolls', text)
        self.assertIn('scales:\n  main: { root: C, type: minor }\n  A Minor: { root: A, type: minor }', text)

    def test_awkward_names_survive(self):
        names = ['a, b', 'a: b', '#hash', YES, '123', NULL, '{x}', "it's", 'say "hi"', 'tab\there', ' spaced ']
        for name in names:
            song = {**SONG, Section.TRACKS: {name: {}}, Section.SCENES: [{SceneSetting.NAME: name, SceneSetting.TRACKS: {name: {ClipSlotSetting.PATTERN: A_2}}}]}
            setlist = {**as_setlist(song), Section.SONGS: {name: as_setlist(song)[Section.SONGS][UNTITLED]}}
            with self.subTest(name=name):
                self.assertEqual(yaml.safe_load(dump_setlist(setlist)), setlist)

    def test_empty_sections_are_left_out(self):
        song = {SceneSetting.TEMPO: 120, SceneSetting.SCALE: None, Section.SCALES: {}, Section.PATTERNS: {}, Section.TRACKS: {A_2: {}}, Section.CHAINS: {}, Section.SCENES: [{Section.TRACKS: {}}]}
        text = dump_setlist(as_setlist(song))
        for section in [Section.PATTERNS, Section.SCALES, Section.CHAINS]:
            self.assertNotIn(section, text)
        render_data(yaml.safe_load(text))

    def test_a_new_song_with_nothing_in_it_reads_back(self):
        setlist = as_setlist({SceneSetting.TEMPO: 120, SceneSetting.TRACKS: {}, Section.SCENES: []})
        self.assertEqual(yaml.safe_load(dump_setlist(setlist)), setlist)
        render_data(yaml.safe_load(dump_setlist(setlist)))

    def test_a_fraction_stays_text_and_a_number_stays_a_number(self):
        setlist = yaml.safe_load(dump_setlist(SETLIST))
        self.assertEqual(setlist[Section.PATTERNS][A_2][Row.GATE][0], QUARTER)
        self.assertEqual(setlist[Section.SONGS][UNTITLED][SongSetting.TEMPO], 120)

    def test_a_set_that_was_written_still_builds(self):
        for path in example_sets():
            with open(path) as file:
                setlist = yaml.safe_load(file)
            with self.subTest(path=path):
                Setlist.from_data(data=yaml.safe_load(dump_setlist(setlist)))


if __name__ == '__main__':
    unittest.main()
