# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
import yaml

from llamatron.composition.file_format import ClipSlotSetting, PatternSetting, Row, SceneSetting, Section, SetlistSetting, SongSetting
from llamatron.composition.file_layout import as_object_layout
from llamatron.composition.setlist_writer import _text, dump_setlist
from tests.support.rendering import as_setlist, render_data

# One song, laid out the way files were before sets existed, which as_setlist turns into a set of one song.
SONG = {
    'tempo': 120, 'scale': 'main', 'scales': {'main': {'root': 'C', 'type': 'minor'}, 'A Minor': {'root': 'A', 'type': 'minor'}},
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
        {'name': 'one', 'repeat': 3, 'reset': ['AX', 'DX'], 'scale': 'A Minor', 'tempo_in_start': 120, 'tempo_in_end': 130, 'tempo_in_over': 2, 'tracks': {'lead': {'pattern': 'a', 'chain': 'x', 'loop': True, 'repeat': 2, 'morph_to': 'hit', 'morph_style': 'left', 'grab_track': 'kick'}}},
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

# Texts that YAML would read as a number and as true unless they are quoted.
TEXT_OF_A_NUMBER = '1'
TEXT_OF_TRUE = 'true'



def read_back(text):
    """Return what a set file's text holds as the objects read it."""
    return as_object_layout(yaml.safe_load(text))

class TestDumpSetlist(unittest.TestCase):

    def test_values_python_calls_equal_are_each_written_as_their_own_kind(self):
        # 1, 1.0 and true are equal to Python; a text remembered for one must never be handed back for another.
        self.assertEqual([_text(1), _text(1.0), _text(True), _text(1), _text(True), _text(1.0)], ['1', '1.0', 'true', '1', 'true', '1.0'])
        self.assertEqual([_text(0), _text(False), _text(0)], ['0', 'false', '0'])

    def test_a_text_that_would_read_back_as_something_else_is_quoted_every_time(self):
        for _ in range(2):
            self.assertEqual(yaml.safe_load(_text(TEXT_OF_A_NUMBER)), TEXT_OF_A_NUMBER)
            self.assertEqual(yaml.safe_load(_text(TEXT_OF_TRUE)), TEXT_OF_TRUE)

    def test_reads_back_the_same(self):
        self.assertEqual(read_back(dump_setlist(SETLIST)), SETLIST)

    def test_the_notes_are_a_readable_block_after_the_title_author_and_description(self):
        setlist = {SetlistSetting.TITLE: T, SetlistSetting.AUTHOR: A, SetlistSetting.DESCRIPTION: D, SetlistSetting.NOTES: 'First line\n\n  indented: # not a comment\n', PatternSetting.STEP_SIZE: '1/8', Section.SONGS: {}}
        text = dump_setlist(setlist)
        self.assertIn('author: A\ndescription: D\nnotes: |\n  First line\n\n    indented: # not a comment\nstep_size: 1/8\n', text)
        self.assertEqual(read_back(text), setlist)

    def test_any_notes_read_back_the_same(self):
        for description in [ONE_LINE, 'ends without\nbreak', ' starts indented\n', '\n\nblank first\n', 'many\n\n\n', '\n', '   ', 'a: b\n- c\n']:
            setlist = {SetlistSetting.NOTES: description, Section.SONGS: {}}
            with self.subTest(description=description):
                self.assertEqual(read_back(dump_setlist(setlist)), setlist)

    def test_a_set_with_nothing_in_it_writes(self):
        self.assertEqual(dump_setlist({}), 'songs: []\n')
        self.assertEqual(read_back(dump_setlist({})), {Section.SONGS: {}})

    def test_each_song_is_indented_under_songs_with_its_own_settings_first(self):
        text = dump_setlist(SETLIST)
        self.assertIn('\nsongs:\n  - name: untitled\n    tempo: 120\n    scale: main\n', text)
        self.assertIn('\n    registers:\n      AX: { maximum: 3, wrap: true }\n', text)
        self.assertIn('\n    tracks:\n      - { name: lead, transpose: 2, cc: [74, ~, ~, 1] }\n', text)
        self.assertIn('\n    scenes:\n      - name: one\n        repeat: 3\n', text)

    def test_a_time_signature_follows_the_tempo_on_a_song_and_the_step_size_on_a_pattern(self):
        setlist = as_setlist({
            SongSetting.TEMPO: 120, SongSetting.TIME_SIGNATURE: WALTZ, Section.TRACKS: {}, Section.SCENES: [],
            Section.PATTERNS: {A_2: {PatternSetting.STEPS: 1, PatternSetting.STEP_SIZE: QUARTER, PatternSetting.TIME_SIGNATURE: WALTZ}},
        })
        loaded = read_back(dump_setlist(setlist))
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
        self.assertIn('    tracks:\n      - { name: lead, transpose: 2, cc: [74, ~, ~, 1] }\n      - { name: kick, drum: true }\n      - { name: plain }\n', text)
        self.assertIn('          - { track: lead, pattern: a, chain: x, loop: true, repeat: 2, morph_to: hit, morph_style: left, grab_track: kick }', text)
        self.assertIn('generators:\n  - { name: bells, kind: arp, step: 1/8, order: up }', text)
        self.assertIn('    registers:\n      AX: { maximum: 3, wrap: true }\n      DX: { minimum: -100, default: -5 }\n\n    tracks:', text)
        self.assertIn("      - name: one\n        repeat: 3\n        reset: [AX, DX]\n", text)
        self.assertIn('  - { name: rolls, kind: auto_ratchet, counts: [1, 4] }', text)
        self.assertIn('  - { name: x, kind: chain, generators: [{ name: rolls }, { name: bells }] }', text)
        self.assertIn('  - { name: nothing, kind: chain, generators: [] }', text)
        self.assertIn('scales:\n  - { name: main, root: C, type: minor }\n  - { name: A Minor, root: A, type: minor }', text)

    def test_awkward_names_survive(self):
        names = ['a, b', 'a: b', '#hash', YES, '123', NULL, '{x}', "it's", 'say "hi"', 'tab\there', ' spaced ']
        for name in names:
            song = {**SONG, Section.TRACKS: {name: {}}, Section.SCENES: [{SceneSetting.NAME: name, SceneSetting.TRACKS: {name: {ClipSlotSetting.PATTERN: A_2}}}]}
            setlist = {**as_setlist(song), Section.SONGS: {name: as_setlist(song)[Section.SONGS][UNTITLED]}}
            with self.subTest(name=name):
                self.assertEqual(read_back(dump_setlist(setlist)), setlist)

    def test_empty_sections_are_left_out(self):
        song = {SceneSetting.TEMPO: 120, SceneSetting.SCALE: None, Section.SCALES: {}, Section.PATTERNS: {}, Section.TRACKS: {A_2: {}}, Section.CHAINS: {}, Section.SCENES: [{Section.TRACKS: {}}]}
        text = dump_setlist(as_setlist(song))
        for section in [Section.PATTERNS, Section.SCALES, Section.CHAINS]:
            self.assertNotIn(section, text)
        render_data(read_back(text))

    def test_a_new_song_with_nothing_in_it_reads_back(self):
        setlist = as_setlist({SceneSetting.TEMPO: 120, SceneSetting.TRACKS: {}, Section.SCENES: []})
        self.assertEqual(read_back(dump_setlist(setlist)), setlist)
        render_data(read_back(dump_setlist(setlist)))

    def test_a_fraction_stays_text_and_a_number_stays_a_number(self):
        setlist = read_back(dump_setlist(SETLIST))
        self.assertEqual(setlist[Section.PATTERNS][A_2][Row.GATE][0], QUARTER)
        self.assertEqual(setlist[Section.SONGS][UNTITLED][SongSetting.TEMPO], 120)



if __name__ == '__main__':
    unittest.main()
