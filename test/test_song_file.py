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
import glob
import gzip
import io
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
from fractions import Fraction

import mido
import yaml

from src.analyzers.clash_finder import ClashFinder
from src.chord import Chord
from src.cli import main
from src.note import Note, Rest
from src.renderers.clip_tree import ClipTree
from src.renderers.timing import GLIDE_OVERLAP, timed_events, timed_notes
from src.song_file import GENERATORS, SongBuilder, SongFileError, load_song


def pat(*steps, drum=False, **rows):
    """Return a pattern from [what, duration] steps, with None as what for a rest."""
    pattern = {'steps': len(steps), 'degree': [s[0] for s in steps], 'duration': [s[1] for s in steps]}
    if drum:
        pattern['drum'] = True
    pattern.update(rows)
    return pattern


BASIC = """
tempo: 120
scale: C major
scales:
  C major: { root: C, type: major }
  C minor: { root: C, type: minor }
  C dorian: { root: C, type: dorian }
default_octave: 2
patterns:
  a: { steps: 3, degree: [1, 3, ~], duration: [1/4, 1/4, 1/2] }
  b: { steps: 4, degree: [5, 6, 7, 1], duration: [1/4, 1/4, 1/4, 1/4], octave: [2, 2, 2, 3] }
  hit: { steps: 2, drum: true, degree: [C, ~], duration: [1/16, 3/16] }
tracks: [lead, kick]
scenes:
  - name: one
    tracks:
      lead: { pattern: a }
      kick: { pattern: hit, loop: true }
"""


def build(text):
    return SongBuilder(yaml.safe_load(text)).build()


def with_parts(**parts):
    data = yaml.safe_load(BASIC)
    patterns = {**data['patterns'], **parts.pop('patterns', {})}
    data.update(parts, patterns=patterns)
    return data


def clip(song, scene, track):
    return song.get_clip(song.scenes[scene - 1], [t for t in song.tracks if t.name == track][0])


def pitches(a_clip):
    return [pitch for _, _, pitch in sorted(timed_notes(a_clip, a_clip.scale)[0])]


def lead_song(*steps, cell=None, **parts):
    """Return a song with one clip on the lead track, playing the given steps."""
    rows = parts.pop('rows', {})
    data = with_parts(
        patterns={'x': pat(*steps, **rows), **parts.pop('patterns', {})},
        scenes=[{'tracks': {'lead': {'pattern': 'x', **(cell or {})}}}], **parts,
    )
    return SongBuilder(data).build()


def lead(*steps, **parts):
    return clip(lead_song(*steps, **parts), 1, 'lead')


class TestPatterns(unittest.TestCase):

    def test_degrees_and_rests_and_lengths(self):
        found = clip(build(BASIC), 1, 'lead').notes
        self.assertEqual(found, [Note('C', 4, Fraction(1, 4)), Note('E', 4, Fraction(1, 4)), Rest(Fraction(1, 2))])

    def test_octaves_are_absolute_and_numbered_like_live(self):
        found = lead([1, '1/2'], [1, '1/2'], rows={'octave': [3, 1]})
        self.assertEqual(pitches(found), [60, 36])

    def test_a_note_without_an_octave_uses_the_song_default(self):
        self.assertEqual(pitches(lead([1, '1/2'], default_octave=3)), [60])

    def test_a_default_song_octave_is_live_c3(self):
        data = with_parts(patterns={'x': pat([1, '1/2'])}, scenes=[{'tracks': {'lead': {'pattern': 'x'}}}])
        del data['default_octave']
        self.assertEqual(pitches(clip(SongBuilder(data).build(), 1, 'lead')), [60])

    def test_a_degree_past_the_scale_wraps_up_an_octave(self):
        self.assertEqual(pitches(lead([8, '1/2'])), [60])

    def test_accidentals(self):
        found = lead([3, '1/4'], [3, '1/4'], [3, '1/4'], rows={'accidental': [None, 'b', '#']})
        self.assertEqual(pitches(found), [52, 51, 53])

    def test_a_step_with_nothing_set_is_a_rest_of_the_default_length(self):
        found = lead([1, '1/4'], [None, None], [3, '1/4'])
        self.assertEqual(found.total_length(), Fraction(9, 16))
        self.assertEqual(pitches(found), [48, 52])

    def test_a_step_with_only_a_duration_is_a_rest(self):
        found = lead([1, '1/4'], [None, '1/4'], [3, '1/4'])
        self.assertEqual(found.total_length(), Fraction(3, 4))

    def test_a_note_without_a_duration_uses_the_song_default(self):
        self.assertEqual(lead([1, None], default_length='1/8').total_length(), Fraction(1, 8))

    def test_a_pattern_needs_at_least_one_step(self):
        with self.assertRaises(SongFileError):
            lead()

    def test_rows_must_match_the_step_count(self):
        with self.assertRaises(SongFileError):
            lead([1, '1/4'], rows={'velocity': [1, 2]})

    def test_values_are_checked(self):
        for row, value in [
            ('duration', 0), ('accidental', 'x'), ('octave', 9), ('chord', 'nope'), ('velocity', 0),
            ('velocity', 128), ('probability', 101), ('ratchet', 0), ('glide', 'yes'),
        ]:
            with self.subTest(row=row, value=value), self.assertRaises(SongFileError):
                lead([1, '1/4'], rows={row: [value]})


class TestChordRow(unittest.TestCase):

    def chord(self, symbol, degree=1, **rows):
        return lead([degree, 1], rows={'chord': [symbol], **rows}).notes[0]

    def test_fixed_chords(self):
        expected = {'M': [48, 52, 55], 'm': [48, 51, 55], 'M7': [48, 52, 55, 59], 'm7': [48, 51, 55, 58], 'dim': [48, 51, 54], 'sus4': [48, 53, 55]}
        for symbol, notes in expected.items():
            with self.subTest(symbol=symbol):
                self.assertEqual(sorted(n.midi_number for n in self.chord(symbol).notes), notes)

    def test_a_fixed_chord_stays_the_same_in_any_scale(self):
        found = lead([1, 1], scale='C minor', rows={'chord': ['M']}).notes[0]
        self.assertEqual(sorted(n.midi_number for n in found.notes), [48, 52, 55])

    def test_chords_from_the_scale_follow_the_scale(self):
        major = lead([1, 1], rows={'chord': [3]}).notes[0]
        minor = lead([1, 1], scale='C minor', rows={'chord': [3]}).notes[0]
        self.assertEqual(sorted(n.midi_number for n in major.notes), [48, 52, 55])
        self.assertEqual(sorted(n.midi_number for n in minor.notes), [48, 51, 55])

    def test_a_seventh_from_the_scale_has_four_notes(self):
        self.assertEqual(sorted(n.midi_number for n in self.chord(7).notes), [48, 52, 55, 59])

    def test_a_chord_uses_the_octave_and_accidental(self):
        found = self.chord('M', octave=[3], accidental=['#'])
        self.assertEqual(sorted(n.midi_number for n in found.notes), [61, 65, 68])


class TestDrumPatterns(unittest.TestCase):

    def test_letters_ignore_the_scale_and_use_the_drum_octave(self):
        self.assertEqual(set(pitches(clip(build(BASIC), 1, 'kick'))), {36})

    def test_a_drum_step_can_have_an_accidental_and_octave(self):
        found = lead(['F', '1/4'], rows={'drum': True, 'accidental': ['#'], 'octave': [2]})
        self.assertEqual(pitches(found), [54])

    def test_a_drum_pattern_needs_no_scale(self):
        found = lead(['C', '1/4'], rows={'drum': True}, scale=None)
        self.assertEqual(pitches(found), [36])

    def test_a_drum_pattern_only_takes_letters(self):
        with self.assertRaises(SongFileError):
            lead([1, '1/4'], rows={'drum': True})

    def test_a_scale_pattern_only_takes_numbers(self):
        with self.assertRaises(SongFileError):
            lead(['C', '1/4'])

    def test_a_drum_pattern_has_no_chords(self):
        with self.assertRaises(SongFileError):
            lead(['C', '1/4'], rows={'drum': True, 'chord': ['M']})


class TestStepRows(unittest.TestCase):

    def test_velocity_defaults_to_127(self):
        events, _ = timed_events(lead([1, '1/4']), None)
        self.assertEqual(events[0][3], 127)

    def test_velocity_reaches_the_note(self):
        events, _ = timed_events(lead([1, '1/4'], rows={'velocity': [40]}), None)
        self.assertEqual(events[0][3], 40)

    def test_velocity_reaches_every_chord_note(self):
        events, _ = timed_events(lead([1, '1/4'], rows={'velocity': [40], 'chord': ['M']}), None)
        self.assertEqual({event[3] for event in events}, {40})

    def test_velocity_reaches_a_midi_file(self):
        with tempfile.TemporaryDirectory() as directory:
            ClipTree(directory, lead_song([1, '1/4'], rows={'velocity': [40]})).render()
            played = mido.MidiFile(os.path.join(directory, os.listdir(directory)[0]))
        self.assertEqual([m.velocity for m in played.tracks[0] if m.type == 'note_on'], [40])

    def test_ratchet_slices_a_note_in_the_same_time(self):
        found = lead([1, '1/16'], rows={'ratchet': [2]})
        self.assertEqual(found.notes, [Note('C', 4, Fraction(1, 32))] * 2)

    def test_ratchet_slices_a_chord(self):
        found = lead([1, '1/4'], rows={'ratchet': [3], 'chord': ['M']})
        self.assertEqual(len(found.notes), 3)
        self.assertIsInstance(found.notes[0], Chord)
        self.assertEqual(found.total_length(), Fraction(1, 4))

    def test_probability_of_zero_is_always_silent_but_keeps_the_time(self):
        found = lead([1, '1/4'], rows={'probability': [0]})
        self.assertEqual(found.notes, [Rest(Fraction(1, 4))])

    def many(self, **parts):
        steps = [[1, '1/16']] * 200
        return lead(*steps, rows={'probability': [50] * 200}, **parts)

    def test_probability_is_rolled_once_at_render_from_the_seed(self):
        self.assertEqual(self.many(seed=5).notes, self.many(seed=5).notes)

    def test_probability_changes_with_the_seed(self):
        self.assertNotEqual(self.many(seed=5).notes, self.many(seed=6).notes)

    def test_probability_drops_about_the_right_share(self):
        sounding = [n for n in self.many(seed=5).notes if isinstance(n, Note)]
        self.assertTrue(70 < len(sounding) < 130)

    def test_each_repeat_rolls_again(self):
        found = lead(*[[1, '1/16']] * 100, cell={'repeat': 2}, rows={'probability': [50] * 100})
        self.assertNotEqual(found.notes[:100], found.notes[100:])

    def test_each_ratchet_slice_rolls_again(self):
        found = lead(*[[1, '1/16']] * 50, rows={'probability': [50] * 50, 'ratchet': [2] * 50})
        pairs = zip(found.notes[::2], found.notes[1::2])
        self.assertTrue(any(isinstance(a, Note) != isinstance(b, Note) for a, b in pairs))

    def test_glide_runs_into_the_next_note(self):
        events, _ = timed_events(lead([1, '1/4'], [3, '1/4'], rows={'glide': [True, False]}), None)
        self.assertEqual(events[0][1], Fraction(1, 4) + GLIDE_OVERLAP)
        self.assertEqual(events[1][1], Fraction(1, 2))

    def test_glide_to_a_rest_or_the_same_pitch_or_the_end_does_nothing(self):
        for steps, glide in [
            ([[1, '1/4'], [None, '1/4']], [True, None]),
            ([[1, '1/4'], [1, '1/4']], [True, None]),
            ([[1, '1/4']], [True]),
        ]:
            with self.subTest(steps=steps):
                events, _ = timed_events(lead(*steps, rows={'glide': glide}), None)
                self.assertEqual(events[0][1], Fraction(1, 4))

    def test_only_the_last_ratchet_slice_glides(self):
        events, _ = timed_events(lead([1, '1/4'], [3, '1/4'], rows={'ratchet': [2, None], 'glide': [True, None]}), None)
        self.assertEqual(events[0][1], Fraction(1, 8))
        self.assertEqual(events[1][1], Fraction(1, 4) + GLIDE_OVERLAP)


class TestClipsInAScene(unittest.TestCase):

    def scene(self, **cells):
        return SongBuilder(with_parts(scenes=[{'tracks': cells}])).build()

    def test_a_clip_plays_its_pattern_once_and_ends(self):
        song = self.scene(lead={'pattern': 'a'}, kick={'pattern': 'hit'})
        self.assertEqual(clip(song, 1, 'kick').total_length(), Fraction(1, 4))
        self.assertEqual(clip(song, 1, 'lead').total_length(), 1)

    def test_repeat_plays_a_pattern_more_times(self):
        song = self.scene(kick={'pattern': 'hit', 'repeat': 3})
        self.assertEqual(clip(song, 1, 'kick').total_length(), Fraction(3, 4))
        self.assertEqual(len(pitches(clip(song, 1, 'kick'))), 3)

    def test_loop_plays_until_the_longest_other_clip_ends(self):
        song = self.scene(lead={'pattern': 'a', 'repeat': 2}, kick={'pattern': 'hit', 'loop': True})
        self.assertEqual(clip(song, 1, 'kick').total_length(), 2)
        self.assertEqual(len(pitches(clip(song, 1, 'kick'))), 8)

    def test_a_loop_is_cut_at_the_end_of_the_scene(self):
        song = self.scene(lead={'pattern': 'hit'}, kick={'pattern': 'a', 'loop': True})
        self.assertEqual(clip(song, 1, 'kick').total_length(), Fraction(1, 4))

    def test_every_clip_looping_is_an_error(self):
        data = with_parts(scenes=[{'name': 'big', 'tracks': {'lead': {'pattern': 'a', 'loop': True}, 'kick': {'pattern': 'hit', 'loop': True}}}])
        with self.assertRaises(SongFileError) as caught:
            SongBuilder(data).build()
        self.assertIn('every clip is set to loop', str(caught.exception))
        self.assertIn('big', str(caught.exception))

    def test_loop_must_be_true_or_false(self):
        with self.assertRaises(SongFileError):
            self.scene(kick={'pattern': 'hit', 'loop': 'yes'})

    def test_repeat_must_be_positive(self):
        for repeat in [0, 'two', True]:
            with self.subTest(repeat=repeat), self.assertRaises(SongFileError):
                self.scene(kick={'pattern': 'hit', 'repeat': repeat})

    def test_clips_say_whether_live_should_loop_them(self):
        song = self.scene(lead={'pattern': 'a'}, kick={'pattern': 'hit', 'loop': True})
        self.assertFalse(clip(song, 1, 'lead').loop)
        self.assertTrue(clip(song, 1, 'kick').loop)

    def test_estimate_gives_seconds_for_scenes_and_clips(self):
        builder = SongBuilder(with_parts(scenes=[{'tracks': {'lead': {'pattern': 'a', 'repeat': 2}, 'kick': {'pattern': 'hit'}}}]))
        number, seconds, clips, problem = builder.estimate()[0]
        self.assertEqual((number, seconds, problem), (1, 4, None))
        self.assertEqual(clips, {'lead': 4, 'kick': Fraction(1, 2)})

    def test_estimate_uses_the_scene_tempo(self):
        builder = SongBuilder(with_parts(scenes=[{'tempo': 60, 'tracks': {'lead': {'pattern': 'a'}}}]))
        self.assertEqual(builder.estimate()[0][1], 4)

    def test_estimate_reports_a_problem_in_only_that_scene(self):
        builder = SongBuilder(with_parts(scenes=[
            {'tracks': {'lead': {'pattern': 'a', 'loop': True}}},
            {'tracks': {'lead': {'pattern': 'a'}}},
        ]))
        first, second = builder.estimate()
        self.assertIn('every clip', first[3])
        self.assertIsNone(first[1])
        self.assertEqual(second[1], 2)


class TestScenes(unittest.TestCase):

    def test_a_scene_scale_overrides_only_that_scene(self):
        data = with_parts(scenes=[
            {'scale': 'C minor', 'tracks': {'lead': {'pattern': 'a'}}},
            {'tracks': {'lead': {'pattern': 'a'}}},
        ])
        song = SongBuilder(data).build()
        self.assertEqual(pitches(clip(song, 1, 'lead')), [48, 51])
        self.assertEqual(pitches(clip(song, 2, 'lead')), [48, 52])

    def test_degrees_with_no_scale_anywhere_name_the_problem(self):
        data = with_parts(scale=None, scenes=[{'tracks': {'lead': {'pattern': 'a'}}}])
        with self.assertRaises(SongFileError) as caught:
            SongBuilder(data).build()
        self.assertIn('no scale', str(caught.exception))

    def test_a_scene_scale_works_when_the_song_has_none(self):
        data = with_parts(scale=None, scenes=[{'scale': 'C minor', 'tracks': {'lead': {'pattern': 'a'}}}])
        self.assertEqual(pitches(clip(SongBuilder(data).build(), 1, 'lead')), [48, 51])

    def test_a_scale_can_have_any_name(self):
        data = with_parts(scales={'main': {'root': 'D', 'type': 'minor'}}, scale='main')
        self.assertEqual(pitches(clip(SongBuilder(data).build(), 1, 'lead')), [50, 53])

    def test_a_generator_can_use_a_scale_by_name(self):
        data = with_parts(
            scales={'main': {'root': 'D', 'type': 'minor'}}, scale='main',
            chains={'x': [{'force_scale': {'scale': 'main'}}]},
            scenes=[{'tracks': {'lead': {'pattern': 'a', 'chain': 'x'}}}],
        )
        self.assertEqual(pitches(clip(SongBuilder(data).build(), 1, 'lead')), [50, 53])

    def test_scales_must_be_in_the_list(self):
        for parts in [{'scale': 'D major'}, {'scenes': [{'scale': 'D major', 'tracks': {}}]}]:
            with self.subTest(parts=parts), self.assertRaises(SongFileError):
                SongBuilder(with_parts(**parts))

    def test_scale_list_is_checked(self):
        with self.assertRaises(SongFileError):
            SongBuilder(with_parts(scales={'bad': {'root': 'C', 'type': 'wobbly'}}))

    def test_repeat_writes_numbered_scenes(self):
        data = with_parts(scenes=[{'name': 'x', 'repeat': 3, 'tracks': {}}])
        self.assertEqual([s.name for s in SongBuilder(data).build().scenes], ['x 1', 'x 2', 'x 3'])

    def test_tempo_ramps_across_a_repeat(self):
        data = with_parts(scenes=[{'repeat': 3, 'tempo_start': 120, 'tempo_end': 124, 'tracks': {}}])
        self.assertEqual([s.tempo for s in SongBuilder(data).build().scenes], [120, 122, 124])

    def test_a_scene_can_set_a_tempo(self):
        data = with_parts(scenes=[{'tempo': 90, 'tracks': {}}])
        self.assertEqual(SongBuilder(data).build().scenes[0].tempo, 90)

    def test_no_tempo_uses_the_song_tempo(self):
        self.assertIsNone(build(BASIC).scenes[0].tempo)
        self.assertEqual(build(BASIC).tempo, 120)

    def test_any_number_of_tracks(self):
        tracks = [f't{n}' for n in range(9)]
        data = with_parts(tracks=tracks, scenes=[{'tracks': {name: {'pattern': 'a'} for name in tracks}}])
        self.assertEqual(len(SongBuilder(data).build().tracks), 9)

    def test_a_cell_can_be_empty(self):
        self.assertIsNone(clip(SongBuilder(with_parts(scenes=[{'tracks': {}}])).build(), 1, 'lead'))

    def test_a_song_can_start_with_nothing(self):
        song = SongBuilder({'tempo': 120, 'tracks': [], 'scenes': []}).build()
        self.assertEqual(song.scenes, [])

    def test_track_names_must_differ(self):
        with self.assertRaises(SongFileError):
            SongBuilder(with_parts(tracks=['a', 'a']))

    def test_song_settings_are_checked(self):
        for parts in [{'granularity': '1/3'}, {'default_length': 0}, {'default_octave': 20}, {'default_drum_octave': 'x'}]:
            with self.subTest(parts=parts), self.assertRaises(SongFileError):
                SongBuilder(with_parts(**parts))


class TestChainsAndPaint(unittest.TestCase):

    def song(self, chains, scenes=None, paint=None):
        parts = {'chains': chains}
        if scenes:
            parts['scenes'] = scenes
        if paint:
            parts['paint'] = paint
        return SongBuilder(with_parts(**parts)).build()

    def test_a_cell_can_use_a_chain(self):
        song = self.song(
            {'up': [{'transpose': {'octaves': 1}}]},
            [{'tracks': {'lead': {'pattern': 'a', 'chain': 'up'}}}],
        )
        self.assertEqual(pitches(clip(song, 1, 'lead')), [60, 64])

    def test_a_chain_applies_its_steps_in_order(self):
        song = self.song(
            {'both': [{'transpose': {'octaves': 1}}, {'reverse': {}}]},
            [{'tracks': {'lead': {'pattern': 'a', 'chain': 'both'}}}],
        )
        self.assertEqual(pitches(clip(song, 1, 'lead')), [64, 60])

    def test_paint_applies_only_to_its_scenes(self):
        scene = {'tracks': {'lead': {'pattern': 'a'}}}
        song = self.song(
            {'up': [{'transpose': {'octaves': 1}}]}, [scene, scene, scene],
            [{'chain': 'up', 'tracks': ['lead'], 'scenes': [2]}],
        )
        self.assertEqual([pitches(clip(song, n, 'lead'))[0] for n in (1, 2, 3)], [48, 60, 48])

    def test_paint_only_touches_its_tracks(self):
        song = self.song(
            {'up': [{'transpose': {'octaves': 1}}]}, None,
            [{'chain': 'up', 'tracks': ['lead'], 'scenes': [1]}],
        )
        self.assertEqual(set(pitches(clip(song, 1, 'kick'))), {36})

    def test_paint_goes_on_top_of_a_cell_chain(self):
        song = self.song(
            {'up': [{'transpose': {'scale_notes': 1}}], 'flip': [{'reverse': {}}]},
            [{'tracks': {'lead': {'pattern': 'a', 'chain': 'flip'}}}],
            [{'chain': 'up', 'tracks': ['lead'], 'scenes': [1]}],
        )
        self.assertEqual(pitches(clip(song, 1, 'lead')), [53, 50])

    def test_gradients_run_across_painted_scenes(self):
        scene = {'tracks': {'lead': {'pattern': 'a'}}}
        song = self.song(
            {'climb': [{'transpose': {'half_steps_start': 0, 'half_steps_end': 4}}]}, [scene] * 3,
            [{'chain': 'climb', 'tracks': ['lead'], 'scenes': [1, 2, 3]}],
        )
        self.assertEqual([pitches(clip(song, n, 'lead'))[0] for n in (1, 2, 3)], [48, 50, 52])

    def test_gradients_run_across_a_repeated_scene(self):
        song = self.song(
            {'climb': [{'transpose': {'half_steps_start': 0, 'half_steps_end': 4}}]},
            [{'repeat': 3, 'tracks': {'lead': {'pattern': 'a', 'chain': 'climb'}}}],
        )
        self.assertEqual([pitches(clip(song, n, 'lead'))[0] for n in (1, 2, 3)], [48, 50, 52])

    def test_blend_runs_from_all_of_one_pattern_to_all_of_the_other(self):
        scene = {'tracks': {'lead': {'pattern': 'a'}}}
        song = self.song(
            {'morph': [{'blend': {'to': 'b', 'style': 'left'}}]}, [scene] * 3,
            [{'chain': 'morph', 'tracks': ['lead'], 'scenes': [1, 2, 3]}],
        )
        self.assertEqual(pitches(clip(song, 1, 'lead')), [48, 52])
        self.assertEqual(pitches(clip(song, 3, 'lead')), [55, 57, 59, 60])

    def test_same_file_gives_the_same_song(self):
        chains = {'mix': [{'mix_up': {'probabilities': [0.5]}}]}
        scenes = [{'tracks': {'lead': {'pattern': 'b', 'chain': 'mix'}}}]
        self.assertEqual(
            clip(self.song(chains, scenes), 1, 'lead').notes,
            clip(self.song(chains, scenes), 1, 'lead').notes,
        )

    def test_order_in_a_paint_list_does_not_matter(self):
        scene = {'tracks': {'lead': {'pattern': 'a'}}}
        song = self.song(
            {'up': [{'transpose': {'half_steps_start': 0, 'half_steps_end': 4}}]}, [scene] * 5,
            [{'chain': 'up', 'tracks': ['lead'], 'scenes': [5, 1, 3]}],
        )
        self.assertEqual([pitches(clip(song, n, 'lead'))[0] for n in range(1, 6)], [48, 48, 50, 48, 52])

    def test_empty_paint_lists_do_nothing(self):
        scene = {'tracks': {'lead': {'pattern': 'a'}}}
        for paint in [{'tracks': ['lead'], 'scenes': []}, {'tracks': [], 'scenes': [1]}]:
            song = self.song({'up': [{'transpose': {'octaves': 1}}]}, [scene], [{'chain': 'up', **paint}])
            with self.subTest(paint=paint):
                self.assertEqual(pitches(clip(song, 1, 'lead'))[0], 48)


class TestGeneratorSettings(unittest.TestCase):

    def song(self, chain, patterns=None):
        return SongBuilder(with_parts(
            patterns=patterns or {}, chains={'x': chain},
            scenes=[{'tracks': {'lead': {'pattern': 'a', 'chain': 'x'}}}],
        )).build()

    def test_every_blend_style_works(self):
        for style in ['left', 'right', 'middle', 'slices', 'strong_beats', 'contour']:
            with self.subTest(style=style):
                self.assertEqual(clip(self.song([{'blend': {'to': 'b', 'style': style}}]), 1, 'lead').total_length(), 1)

    def test_blend_can_set_its_slices(self):
        chain = [{'blend': {'to': 'b', 'style': 'slices', 'slice_length': '1/4', 'seed': 2}}]
        self.assertEqual(clip(self.song(chain), 1, 'lead').total_length(), 1)

    def test_harmonize_takes_several_charts(self):
        patterns = {'one': pat([1, 1], chord=[3]), 'two': pat([4, 1], chord=[3])}
        result = self.song([{'harmonize': {'charts': ['one', 'two']}}], patterns)
        self.assertIsInstance(clip(result, 1, 'lead').notes[0], Chord)

    def test_generators_can_be_given_a_scale(self):
        for step in [
            {'accompany': {'scale': 'C major'}},
            {'backfill': {'probabilities': [1], 'scale': 'C major'}},
            {'transpose': {'scale_notes': 1, 'scale': 'C major'}},
            {'harmonize': {'charts': ['b'], 'scale': 'C major'}},
            {'counterpoint': {'chords': 'b', 'scale': 'C major'}},
            {'blend': {'to': 'b', 'style': 'contour', 'scale': 'C major'}},
        ]:
            with self.subTest(step=step):
                self.assertEqual(clip(self.song([step]), 1, 'lead').total_length(), 1)

    def test_a_pattern_setting_after_stretch_fills_the_longer_clip(self):
        for step in [
            {'take_rhythm': {'rhythm': 'hit'}},
            {'blend': {'to': 'b', 'style': 'left'}},
            {'smoother': {'chords': 'b'}},
        ]:
            with self.subTest(step=step):
                found = self.song([{'stretch': {'factor': 2}}, step])
                self.assertEqual(clip(found, 1, 'lead').total_length(), 2)


class TestClipMorph(unittest.TestCase):

    C_NOTES = [48, 50, 52, 53]
    D_NOTES = [55, 57, 59, 60]

    def morph(self, repeat=3, style='left', **cell):
        settings = {'pattern': 'c', 'repeat': repeat, 'morph_to': 'd', 'morph_style': style, **cell}
        fourths = ['1/4'] * 4
        data = with_parts(
            patterns={
                'c': pat(*zip([1, 2, 3, 4], fourths)),
                'd': pat(*zip([5, 6, 7, 1], fourths), octave=[2, 2, 2, 3]),
            },
            scenes=[{'tracks': {'lead': settings}}],
        )
        return clip(SongBuilder(data).build(), 1, 'lead')

    def test_runs_across_the_repeats_of_the_clip(self):
        found = self.morph(repeat=2)
        self.assertEqual(found.total_length(), 2)
        self.assertEqual(pitches(found), self.C_NOTES + self.D_NOTES)

    def test_left_replaces_notes_from_the_left(self):
        found = pitches(self.morph(repeat=5))
        self.assertEqual(found[4:8], self.D_NOTES[:1] + self.C_NOTES[1:])

    def test_right_replaces_notes_from_the_right(self):
        found = pitches(self.morph(repeat=5, style='right'))
        self.assertEqual(found[4:8], self.C_NOTES[:3] + self.D_NOTES[3:])

    def test_middle_works(self):
        self.assertEqual(self.morph(style='middle').total_length(), 3)

    def test_a_longer_target_is_cut_and_a_shorter_one_is_looped(self):
        data = with_parts(
            patterns={'long': pat([1, 2]), 'short': pat([3, '1/2'])},
            scenes=[{'tracks': {'lead': {'pattern': 'a', 'repeat': 2, 'morph_to': 'long', 'morph_style': 'left'}, 'kick': {'pattern': 'a', 'repeat': 2, 'morph_to': 'short', 'morph_style': 'left'}}}],
        )
        song = SongBuilder(data).build()
        self.assertEqual(clip(song, 1, 'lead').total_length(), 2)
        self.assertEqual(clip(song, 1, 'kick').total_length(), 2)

    def test_needs_a_repeat_above_one(self):
        with self.assertRaises(SongFileError) as caught:
            self.morph(repeat=1)
        self.assertIn('repeat of 2', str(caught.exception))

    def test_needs_both_settings_and_real_values(self):
        good = {'pattern': 'a', 'repeat': 2, 'morph_to': 'b', 'morph_style': 'left'}
        bad = [{**good, 'morph_to': 'nope'}, {**good, 'morph_style': 'nope'}]
        bad += [{k: v for k, v in good.items() if k != missing} for missing in ['morph_to', 'morph_style']]
        for cell in bad:
            with self.subTest(cell=cell), self.assertRaises(SongFileError):
                SongBuilder(with_parts(scenes=[{'tracks': {'lead': cell}}]))

    def test_a_cell_cannot_set_a_scale(self):
        with self.assertRaises(SongFileError):
            SongBuilder(with_parts(scenes=[{'tracks': {'lead': {'pattern': 'a', 'scale': 'C major'}}}]))


class TestRhythmAndNotesFrom(unittest.TestCase):

    PATTERNS = {
        'groove': pat([1, '1/8'], [None, '1/8'], [1, '1/16'], [1, '1/16'], [1, '1/4'], velocity=[40, None, 50, 60, 70], ratchet=[None, None, None, None, 2]),
        'line': pat([1, '1/4'], [None, '1/4'], [3, '1/4'], [5, '1/4'], octave=[3, None, 2, 2]),
        'plain': pat([6, '1/2'], [7, '1/2']),
        'hits': pat(['C', '1/4'], [None, '1/4'], ['D', '1/4'], drum=True),
        'restful': pat([None, '1/4'], [None, '1/4']),
        'colored': pat([1, '1/4'], chord=['M'], accidental=['#'], octave=[3]),
    }

    def clip(self, **cell):
        data = with_parts(patterns=self.PATTERNS, scenes=[{'tracks': {'lead': {'pattern': 'plain', **cell}}}])
        return clip(SongBuilder(data).build(), 1, 'lead')

    def timed(self, found):
        return [(str(start), pitch) for start, _, pitch in sorted(timed_notes(found, found.scale)[0])]

    def test_rhythm_from_plays_the_clips_notes_in_another_rhythm(self):
        found = self.clip(rhythm_from='groove')
        self.assertEqual(found.total_length(), Fraction(5, 8))
        self.assertEqual(self.timed(found)[:3], [('0', 57), ('1/4', 59), ('5/16', 57)])

    def test_notes_from_plays_other_notes_in_the_clips_rhythm(self):
        found = self.clip(notes_from='line')
        self.assertEqual(found.total_length(), 1)
        self.assertEqual(self.timed(found), [('0', 60), ('1/2', 52)])

    def test_rests_in_the_notes_are_skipped(self):
        found = self.clip(rhythm_from='line', notes_from='line')
        self.assertEqual(self.timed(found), [('0', 60), ('1/2', 52), ('3/4', 55)])

    def test_rests_come_from_the_rhythm_even_if_the_notes_have_none_there(self):
        self.assertNotIn('1/8', [start for start, _ in self.timed(self.clip(rhythm_from='groove'))])

    def test_the_notes_carry_on_across_repeats_and_drift(self):
        found = self.clip(rhythm_from='groove', notes_from='line', repeat=2)
        self.assertEqual(found.total_length(), Fraction(5, 4))
        pitches_played = [pitch for _, pitch in self.timed(found)]
        # Each step: 1 3 5 1 1, then 3 5 1 3 3, with the last step of each repeat ratcheted.
        self.assertEqual(pitches_played, [60, 52, 55, 60, 60, 52, 55, 60, 52, 52])

    def test_a_looped_clip_carries_on_too(self):
        data = with_parts(
            patterns=self.PATTERNS,
            scenes=[{'tracks': {
                'lead': {'pattern': 'plain', 'rhythm_from': 'hits', 'notes_from': 'line', 'loop': True},
                'kick': {'pattern': 'plain', 'repeat': 3},
            }}],
        )
        found = clip(SongBuilder(data).build(), 1, 'lead')
        self.assertEqual(found.total_length(), 3)
        self.assertEqual([pitch for _, pitch in self.timed(found)][:5], [60, 52, 55, 60, 52])

    def test_the_rhythm_side_owns_velocity_ratchet_and_duration(self):
        found = self.clip(rhythm_from='groove')
        events, _ = timed_events(found, None)
        self.assertEqual([event[3] for event in sorted(events)][:4], [40, 50, 60, 70])
        self.assertEqual(sorted(events)[-1][1] - sorted(events)[-1][0], Fraction(1, 8))

    def test_the_notes_side_owns_octave_chord_and_accidental(self):
        found = self.clip(notes_from='colored')
        self.assertIsInstance(found.notes[0], Chord)
        self.assertEqual(sorted(n.midi_number for n in found.notes[0].notes), [61, 65, 68])
        self.assertEqual(found.notes[0].length, Fraction(1, 2))

    def test_both_replace_the_clips_pattern(self):
        both = self.clip(rhythm_from='groove', notes_from='line')
        data = with_parts(patterns=self.PATTERNS, scenes=[{'tracks': {'lead': {'pattern': 'hits', 'rhythm_from': 'groove', 'notes_from': 'line'}}}])
        other = clip(SongBuilder(data).build(), 1, 'lead')
        self.assertEqual(both.notes, other.notes)

    def test_a_melody_in_the_rhythm_of_a_drum_pattern(self):
        found = self.clip(rhythm_from='hits')
        self.assertEqual(self.timed(found), [('0', 57), ('1/2', 59)])

    def test_notes_from_a_drum_pattern_use_its_fixed_notes(self):
        found = self.clip(notes_from='hits')
        self.assertEqual([pitch for _, pitch in self.timed(found)], [36, 38])

    def test_notes_with_nothing_to_play_are_rests(self):
        found = self.clip(notes_from='restful')
        self.assertEqual(pitches(found), [])
        self.assertEqual(found.total_length(), 1)

    def test_a_morph_target_plays_as_written(self):
        data = with_parts(
            patterns=self.PATTERNS,
            scenes=[{'tracks': {'lead': {'pattern': 'plain', 'notes_from': 'line', 'repeat': 2, 'morph_to': 'plain', 'morph_style': 'left'}}}],
        )
        found = clip(SongBuilder(data).build(), 1, 'lead')
        self.assertEqual([pitch for _, pitch in self.timed(found)], [60, 52, 57, 59])

    def test_probability_comes_from_the_rhythm(self):
        patterns = {**self.PATTERNS, 'silent': pat([1, '1/2'], [1, '1/2'], probability=[0, 0])}
        data = with_parts(patterns=patterns, scenes=[{'tracks': {'lead': {'pattern': 'plain', 'rhythm_from': 'silent'}}}])
        self.assertEqual(pitches(clip(SongBuilder(data).build(), 1, 'lead')), [])

    def test_the_same_every_time(self):
        self.assertEqual(self.clip(rhythm_from='groove', notes_from='line').notes, self.clip(rhythm_from='groove', notes_from='line').notes)

    def test_names_must_be_real_patterns(self):
        for setting in ['rhythm_from', 'notes_from']:
            with self.subTest(setting=setting), self.assertRaises(SongFileError):
                self.clip(**{setting: 'nope'})

    def test_estimate_uses_the_rhythm(self):
        data = with_parts(patterns=self.PATTERNS, scenes=[{'tracks': {'lead': {'pattern': 'plain', 'rhythm_from': 'groove'}}}])
        self.assertEqual(SongBuilder(data).estimate()[0][2]['lead'], Fraction(5, 4))


class TestPlayDirections(unittest.TestCase):

    NOTES = pat([1, '1/4'], [2, '1/4'], [3, '1/4'])
    C, D, E = 48, 50, 52

    def played(self, repeat=2, pattern_direction=None, clip_direction=None, pattern=None, **parts):
        pattern = dict(pattern or self.NOTES)
        if pattern_direction:
            pattern['direction'] = pattern_direction
        cell = {'pattern': 'x', 'repeat': repeat}
        if clip_direction:
            cell['direction'] = clip_direction
        data = with_parts(patterns={'x': pattern}, scenes=[{'tracks': {'lead': cell}}], **parts)
        return clip(SongBuilder(data).build(), 1, 'lead')

    def order(self, *arguments, **parts):
        return pitches(self.played(*arguments, **parts))

    def test_forward_is_the_default(self):
        self.assertEqual(self.order(), [self.C, self.D, self.E] * 2)

    def test_reverse_a_starts_on_the_first_step(self):
        self.assertEqual(self.order(pattern_direction='reverse_a'), [self.C, self.E, self.D] * 2)

    def test_reverse_b_starts_on_the_last_step(self):
        self.assertEqual(self.order(pattern_direction='reverse_b'), [self.E, self.D, self.C] * 2)

    def test_alternate_goes_forward_then_reverse(self):
        self.assertEqual(self.order(pattern_direction='alternate'), [self.C, self.D, self.E, self.E, self.D, self.C])

    def test_pendulum_does_not_repeat_the_ends(self):
        self.assertEqual(self.order(pattern_direction='pendulum'), [self.C, self.D, self.E, self.D, self.C, self.D])

    def test_a_clip_overrides_the_pattern(self):
        self.assertEqual(self.order(pattern_direction='reverse_b', clip_direction='forward'), [self.C, self.D, self.E] * 2)
        self.assertEqual(self.order(pattern_direction='alternate', clip_direction='reverse_b'), [self.E, self.D, self.C] * 2)

    def test_chosen_directions_are_the_same_every_render(self):
        for direction in ['random', 'brownian', 'eitherway']:
            with self.subTest(direction=direction):
                self.assertEqual(self.order(8, direction), self.order(8, direction))

    def test_chosen_directions_change_with_the_seed(self):
        for direction in ['random', 'brownian', 'eitherway']:
            with self.subTest(direction=direction):
                self.assertNotEqual(self.order(20, direction, seed=1), self.order(20, direction, seed=2))

    def test_chosen_directions_do_not_change_what_probability_rolls(self):
        rows = {'probability': [50] * 40}
        steps = pat(*[[1, '1/16']] * 40, **rows)
        plain = [isinstance(n, Note) for n in self.played(1, pattern=steps).notes]
        moved = [isinstance(n, Note) for n in self.played(1, 'random', pattern=steps).notes]
        self.assertEqual(plain, moved)

    def test_brownian_only_moves_one_step_at_a_time(self):
        found = self.order(40, 'brownian')
        places = [[self.C, self.D, self.E].index(pitch) for pitch in found]
        for before, after in zip(places, places[1:]):
            self.assertIn((after - before) % 3, (0, 1, 2))
        self.assertEqual(places[0], 0)

    def test_eitherway_always_moves(self):
        found = self.order(20, 'eitherway')
        for before, after in zip(found, found[1:]):
            self.assertNotEqual(before, after)

    def test_a_pass_always_lasts_as_long_as_the_pattern(self):
        uneven = pat([1, '1/2'], [2, '1/16'], [3, '3/16'])
        for direction in ['forward', 'reverse_a', 'reverse_b', 'alternate', 'pendulum', 'random', 'brownian', 'eitherway']:
            with self.subTest(direction=direction):
                self.assertEqual(self.played(5, direction, pattern=uneven).total_length(), Fraction(15, 4))

    def test_a_looping_clip_carries_on_in_its_direction(self):
        data = with_parts(
            patterns={'x': {**self.NOTES, 'direction': 'alternate'}, 'long': pat([1, 2])},
            scenes=[{'tracks': {'lead': {'pattern': 'x', 'loop': True}, 'kick': {'pattern': 'long'}}}],
        )
        found = clip(SongBuilder(data).build(), 1, 'lead')
        self.assertEqual(pitches(found)[:6], [self.C, self.D, self.E, self.E, self.D, self.C])

    def test_rests_play_in_order_too(self):
        steps = pat([1, '1/4'], [None, '1/4'], [3, '1/4'])
        found = self.played(1, 'reverse_b', pattern=steps)
        self.assertEqual(found.notes, [Note('E', 4, Fraction(1, 4)), Rest(Fraction(1, 4)), Note('C', 4, Fraction(1, 4))])

    def test_a_generator_reads_a_pattern_as_written(self):
        data = with_parts(
            patterns={'x': pat([1, '1/2'], [3, '1/2']), 'y': {**pat([5, '1/2'], [6, '1/2']), 'direction': 'reverse_b'}},
            chains={'c': [{'blend': {'to': 'y', 'style': 'left'}}]},
            scenes=[{'tracks': {'lead': {'pattern': 'x', 'chain': 'c'}}}],
        )
        self.assertEqual(pitches(clip(SongBuilder(data).build(), 1, 'lead')), [55, 57])

    def test_a_morph_target_uses_its_own_direction_and_not_the_clips(self):
        data = with_parts(
            patterns={'x': pat([1, '1/2'], [3, '1/2']), 'y': {**pat([5, '1/2'], [6, '1/2']), 'direction': 'reverse_b'}},
            scenes=[{'tracks': {'lead': {'pattern': 'x', 'repeat': 2, 'direction': 'reverse_b', 'morph_to': 'y', 'morph_style': 'left'}}}],
        )
        self.assertEqual(pitches(clip(SongBuilder(data).build(), 1, 'lead')), [52, 48, 57, 55])

    def test_rhythm_and_notes_each_use_their_own_direction(self):
        data = with_parts(
            patterns={'r': pat([1, '1/4'], [None, '1/2'], [1, '1/8'], direction='reverse_b'), 'n': pat([1, 1], [3, 1], direction='reverse_b')},
            scenes=[{'tracks': {'lead': {'pattern': 'r', 'notes_from': 'n'}}}],
        )
        found = clip(SongBuilder(data).build(), 1, 'lead')
        self.assertEqual(found.notes, [Note('E', 4, Fraction(1, 8)), Rest(Fraction(1, 2)), Note('C', 4, Fraction(1, 4))])

    def test_a_clip_direction_overrides_both_rhythm_and_notes(self):
        data = with_parts(
            patterns={'r': pat([1, '1/4'], [None, '1/2'], [1, '1/8']), 'n': pat([1, 1], [3, 1])},
            scenes=[{'tracks': {'lead': {'pattern': 'r', 'notes_from': 'n', 'direction': 'reverse_b'}}}],
        )
        found = clip(SongBuilder(data).build(), 1, 'lead')
        self.assertEqual(found.notes[0], Note('E', 4, Fraction(1, 8)))

    def test_bad_directions_are_refused(self):
        with self.assertRaises(SongFileError):
            self.played(pattern_direction='sideways')
        with self.assertRaises(SongFileError):
            self.played(clip_direction='sideways')


class TestGrab(unittest.TestCase):

    def lead(self, riff=None, source=None, **cell):
        riff = riff or pat(*[[1, '1/4']] * 4, grab=[True, None, True, None], source_pattern='src')
        source = source or pat([1, '1/4'], [2, '1/4'], [3, '1/4'], octave=[3, 3, 3])
        data = with_parts(patterns={'riff': riff, 'src': source}, scenes=[{'tracks': {'lead': {'pattern': 'riff', **cell}}}])
        return clip(SongBuilder(data).build(), 1, 'lead')

    def test_marked_steps_play_the_source_note_at_that_moment(self):
        self.assertEqual(pitches(self.lead()), [60, 48, 64, 48])

    def test_a_shorter_source_drifts_across_repeats(self):
        self.assertEqual(pitches(self.lead(repeat=2)), [60, 48, 64, 48, 62, 48, 60, 48])

    def test_the_source_owns_octave_accidental_and_chord(self):
        source = pat([1, 1], octave=[4], accidental=['#'], chord=['M'])
        found = self.lead(source=source).notes[0]
        self.assertEqual(sorted(n.midi_number for n in found.notes), [73, 77, 80])

    def test_the_pattern_keeps_its_rhythm_velocity_and_other_settings(self):
        riff = pat([1, '1/8'], grab=[True], source_pattern='src', velocity=[33], ratchet=[2])
        found = self.lead(riff=riff)
        self.assertEqual(found.total_length(), Fraction(1, 8))
        events, _ = timed_events(found, None)
        self.assertEqual([event[2:] for event in events], [(60, 33), (60, 33)])

    def test_a_rest_in_the_source_leaves_the_note_alone(self):
        source = pat([None, '1/4'], [1, '1/4'], octave=[None, 3])
        self.assertEqual(pitches(self.lead(source=source)), [48, 48, 48, 48])

    def test_a_marked_rest_stays_a_rest(self):
        riff = pat([None, '1/4'], [1, '1/4'], grab=[True, None], source_pattern='src')
        self.assertEqual(pitches(self.lead(riff=riff)), [48])

    def test_marks_without_a_source_do_nothing(self):
        riff = pat([1, '1/4'], grab=[True])
        self.assertEqual(pitches(self.lead(riff=riff)), [48])

    def test_can_grab_from_a_drum_pattern(self):
        source = pat(['F', '1/4'], drum=True, accidental=['#'], octave=[2])
        self.assertEqual(pitches(self.lead(source=source))[:2], [54, 48])

    def test_the_source_follows_its_own_direction(self):
        source = pat([1, '1/4'], [2, '1/4'], [3, '1/4'], octave=[3, 3, 3], direction='reverse_b')
        self.assertEqual(pitches(self.lead(source=source))[0], 64)

    def test_a_clip_direction_applies_to_the_source_too(self):
        # Backward through both: the riff's marks land on its second and last plays.
        self.assertEqual(pitches(self.lead(direction='reverse_b')), [48, 62, 48, 64])

    def test_works_with_notes_from(self):
        patterns = {
            'r': pat([1, '1/2'], [1, '1/2']),
            'n': pat([1, '1/4'], [3, '1/4'], grab=[True, None], source_pattern='s'),
            's': pat([5, '1/4'], octave=[3]),
        }
        data = with_parts(patterns=patterns, scenes=[{'tracks': {'lead': {'pattern': 'r', 'notes_from': 'n'}}}])
        self.assertEqual(pitches(clip(SongBuilder(data).build(), 1, 'lead')), [67, 52])

    def test_a_generator_reading_a_pattern_ignores_grab(self):
        patterns = {
            'x': pat([1, '1/2']),
            'y': pat([3, '1/2'], grab=[True], source_pattern='s'),
            's': pat([5, '1/2']),
        }
        data = with_parts(patterns=patterns, chains={'c': [{'blend': {'to': 'y', 'style': 'left'}}]}, scenes=[{'tracks': {'lead': {'pattern': 'x', 'chain': 'c'}}}])
        self.assertEqual(pitches(clip(SongBuilder(data).build(), 1, 'lead')), [52])

    def test_the_source_must_be_a_real_pattern(self):
        with self.assertRaises(SongFileError):
            SongBuilder(with_parts(patterns={'x': pat([1, 1], source_pattern='nope')}))

    def test_grab_must_be_true_or_false(self):
        with self.assertRaises(SongFileError):
            SongBuilder(with_parts(patterns={'x': pat([1, 1], grab=['yes'])}))


class TestRatchetOffset(unittest.TestCase):

    def test_moves_each_slice_along_the_scale(self):
        found = lead([1, '1/4'], rows={'ratchet': [4], 'ratchet_offset': [1]})
        self.assertEqual(pitches(found), [48, 50, 52, 53])
        self.assertEqual(found.total_length(), Fraction(1, 4))

    def test_stays_in_the_scale_it_plays_in(self):
        found = lead([1, '1/4'], scale='C minor', rows={'ratchet': [4], 'ratchet_offset': [1]})
        self.assertEqual(pitches(found), [48, 50, 51, 53])

    def test_can_go_down(self):
        found = lead([1, '1/4'], rows={'ratchet': [3], 'ratchet_offset': [-1]})
        self.assertEqual(sorted(pitches(found)), [45, 47, 48])
        self.assertEqual(found.notes[1], Note('B', 3, Fraction(1, 12)))

    def test_zero_or_no_ratchet_changes_nothing(self):
        self.assertEqual(pitches(lead([1, '1/4'], rows={'ratchet': [2], 'ratchet_offset': [0]})), [48, 48])
        self.assertEqual(pitches(lead([1, '1/4'], rows={'ratchet_offset': [5]})), [48])

    def test_a_chord_moves_as_a_whole(self):
        found = lead([1, '1/4'], rows={'ratchet': [2], 'ratchet_offset': [1], 'chord': [3]})
        self.assertEqual(sorted(n.midi_number for n in found.notes[0].notes), [48, 52, 55])
        self.assertEqual(sorted(n.midi_number for n in found.notes[1].notes), [50, 53, 57])

    def test_a_drum_moves_by_half_steps(self):
        found = lead(['C', '1/4'], rows={'drum': True, 'ratchet': [3], 'ratchet_offset': [1]})
        self.assertEqual(pitches(found), [36, 37, 38])

    def test_every_slice_keeps_its_velocity_and_only_the_last_glides(self):
        found = lead([1, '1/4'], [5, '1/4'], rows={'ratchet': [2, None], 'ratchet_offset': [1, None], 'velocity': [40, None], 'glide': [True, None]})
        events, _ = timed_events(found, None)
        self.assertEqual([event[3] for event in sorted(events)[:2]], [40, 40])
        self.assertEqual(sorted(events)[1][1], Fraction(1, 4) + GLIDE_OVERLAP)

    def test_is_a_whole_number(self):
        with self.assertRaises(SongFileError):
            lead([1, '1/4'], rows={'ratchet_offset': ['x']})


class TestAccumulators(unittest.TestCase):

    def test_note_add_applies_from_its_step_on(self):
        found = lead([1, '1/4'], [1, '1/4'], [1, '1/4'], rows={'note_add': [None, 1, None]})
        self.assertEqual(pitches(found), [48, 50, 50])

    def test_the_total_builds_up_across_repeats(self):
        found = lead([1, '1/4'], cell={'repeat': 4}, rows={'note_add': [1]})
        self.assertEqual(pitches(found), [50, 52, 53, 55])

    def test_moves_along_the_scale_the_clip_plays_in(self):
        found = lead([1, '1/4'], cell={'repeat': 3}, scale='C minor', rows={'note_add': [1]})
        self.assertEqual(pitches(found), [50, 51, 53])

    def test_can_go_negative(self):
        found = lead([1, '1/4'], cell={'repeat': 2}, rows={'note_add': [-1]})
        self.assertEqual(pitches(found), [47, 45])

    def test_a_drum_moves_by_half_steps(self):
        found = lead(['C', '1/4'], cell={'repeat': 3}, rows={'drum': True, 'note_add': [1]})
        self.assertEqual(pitches(found), [37, 38, 39])

    def test_velocity_add_builds_up_and_stays_in_range(self):
        found = lead([1, '1/4'], cell={'repeat': 3}, rows={'velocity': [100], 'velocity_add': [20], 'accumulator_limit': 99})
        events, _ = timed_events(found, None)
        self.assertEqual([event[3] for event in sorted(events)], [120, 127, 127])

    def test_velocity_add_going_down_stops_at_one(self):
        found = lead([1, '1/4'], cell={'repeat': 2}, rows={'velocity': [10], 'velocity_add': [-20], 'accumulator_limit': 99})
        events, _ = timed_events(found, None)
        self.assertEqual({event[3] for event in events}, {1})

    def test_the_total_clears_past_the_limit(self):
        rows = {'note_add': [1], 'accumulator_limit': 2}
        found = lead([1, '1/4'], cell={'repeat': 4}, rows=rows)
        self.assertEqual(pitches(found), [50, 52, 48, 50])

    def test_a_limit_applies_going_down_too(self):
        rows = {'note_add': [-1], 'accumulator_limit': 1}
        found = lead([1, '1/4'], cell={'repeat': 3}, rows=rows)
        self.assertEqual(pitches(found), [47, 48, 47])

    def test_starts_again_in_each_clip(self):
        data = with_parts(
            patterns={'x': pat([1, '1/4'], note_add=[1])},
            scenes=[{'repeat': 2, 'tracks': {'lead': {'pattern': 'x'}}}],
        )
        song = SongBuilder(data).build()
        self.assertEqual(pitches(clip(song, 1, 'lead')), pitches(clip(song, 2, 'lead')))

    def test_a_note_past_the_midi_range_moves_by_octaves_to_fit(self):
        found = lead([1, '1/4'], cell={'repeat': 2}, rows={'octave': [8], 'note_add': [12], 'accumulator_limit': 99})
        self.assertTrue(all(0 <= pitch <= 127 for pitch in pitches(found)))
        self.assertEqual(len(pitches(found)), 2)

    def test_a_note_written_past_the_range_is_still_an_error(self):
        with self.assertRaises(SongFileError):
            lead([1, '1/4'], [8, '1/4'], rows={'octave': [8, 8], 'accidental': [None, None], 'degree': [80, 90]})

    def test_a_rest_adds_nothing(self):
        found = lead([None, '1/4'], [1, '1/4'], rows={'note_add': [5, None]})
        self.assertEqual(pitches(found), [48])

    def test_note_add_belongs_to_the_notes_and_velocity_add_to_the_rhythm(self):
        patterns = {
            'r': pat([1, '1/4'], velocity_add=[10], note_add=[5], velocity=[50]),
            'n': pat([1, '1/4'], note_add=[1], velocity_add=[99], velocity=[99]),
        }
        data = with_parts(patterns=patterns, scenes=[{'tracks': {'lead': {'pattern': 'r', 'notes_from': 'n', 'repeat': 2}}}])
        found = clip(SongBuilder(data).build(), 1, 'lead')
        events, _ = timed_events(found, None)
        self.assertEqual([event[2:] for event in sorted(events)], [(50, 60), (52, 70)])

    def test_a_generator_reading_a_pattern_ignores_them(self):
        data = with_parts(
            patterns={'x': pat([1, '1/2']), 'y': pat([3, '1/2'], note_add=[3])},
            chains={'c': [{'blend': {'to': 'y', 'style': 'left'}}]},
            scenes=[{'tracks': {'lead': {'pattern': 'x', 'chain': 'c'}}}],
        )
        self.assertEqual(pitches(clip(SongBuilder(data).build(), 1, 'lead')), [52])

    def test_settings_are_checked(self):
        for rows in [{'note_add': ['x']}, {'velocity_add': [1.5]}, {'accumulator_limit': 0}]:
            with self.subTest(rows=rows), self.assertRaises(SongFileError):
                lead([1, '1/4'], rows=rows)


class TestArps(unittest.TestCase):

    def lead(self, chain='x', **parts):
        scene = {'tracks': {'lead': {'pattern': 'c', 'chain': chain}}}
        data = with_parts(patterns={'c': pat([1, 1], chord=[3]), 'd': pat([1, '1/2'], [3, '1/2'])}, scenes=[scene], **parts)
        return clip(SongBuilder(data).build(), 1, 'lead')

    def test_a_chain_can_use_a_named_arp(self):
        found = self.lead(arps={'bells': {'step': '1/4', 'order': 'up'}}, chains={'x': [{'arp': 'bells'}]})
        self.assertEqual(pitches(found), [48, 52, 55, 48])

    def test_an_arp_keeps_the_velocity(self):
        data = with_parts(
            patterns={'c': pat([1, 1], chord=[3], velocity=[40])}, arps={'bells': {'step': '1/4'}},
            chains={'x': [{'arp': 'bells'}]}, scenes=[{'tracks': {'lead': {'pattern': 'c', 'chain': 'x'}}}],
        )
        events, _ = timed_events(clip(SongBuilder(data).build(), 1, 'lead'), None)
        self.assertEqual({event[3] for event in events}, {40})

    def test_a_chain_can_use_a_named_auto_ratchet(self):
        scene = {'tracks': {'lead': {'pattern': 'd', 'chain': 'x'}}}
        data = with_parts(patterns={'d': pat([1, '1/2'], [3, '1/2'])}, scenes=[scene], auto_ratchets={'rolls': {'counts': [2]}}, chains={'x': [{'auto_ratchet': 'rolls'}]})
        self.assertEqual(pitches(clip(SongBuilder(data).build(), 1, 'lead')), [48, 48, 52, 52])

    def test_named_generators_run_in_chain_order(self):
        found = self.lead(
            arps={'bells': {'step': '1/2'}}, auto_ratchets={'rolls': {'counts': [2]}},
            chains={'x': [{'arp': 'bells'}, {'auto_ratchet': 'rolls'}]},
        )
        self.assertEqual(pitches(found), [48, 48, 52, 52])

    def test_settings_in_a_chain_still_work(self):
        self.assertEqual(pitches(self.lead(chains={'x': [{'arp': {'step': '1/2'}}]})), [48, 52])

    def test_unknown_names_and_types_are_refused(self):
        for parts in [
            {'chains': {'x': [{'arp': 'nope'}]}},
            {'chains': {'x': [{'auto_ratchet': 'nope'}]}},
            {'chains': {'x': [{'reverse': 'nope'}]}},
        ]:
            with self.subTest(parts=parts), self.assertRaises(SongFileError):
                self.lead(**parts)

    def test_a_bad_setting_names_the_problem(self):
        with self.assertRaises(SongFileError):
            self.lead(arps={'a': {'wobble': 1}}, chains={'x': [{'arp': 'a'}]})


class TestErrors(unittest.TestCase):

    def assert_error(self, expected, **parts):
        with self.assertRaises(SongFileError) as caught:
            SongBuilder(with_parts(**parts)).build()
        self.assertIn(expected, str(caught.exception))

    def test_unknown_top_level_setting(self):
        self.assert_error("unknown setting 'themes'", themes={})

    def test_unknown_chain_in_a_cell(self):
        self.assert_error("no chain called 'nope'", scenes=[{'tracks': {'lead': {'pattern': 'a', 'chain': 'nope'}}}])

    def test_unknown_pattern(self):
        self.assert_error("no pattern called 'nope'", scenes=[{'tracks': {'lead': {'pattern': 'nope'}}}])

    def test_unknown_track(self):
        self.assert_error("no track called 'nope'", scenes=[{'tracks': {'nope': {'pattern': 'a'}}}])

    def test_cells_must_use_the_hash_form(self):
        self.assert_error('expected settings like', scenes=[{'tracks': {'lead': 'a'}}])

    def test_unknown_generator(self):
        self.assert_error("unknown generator 'wobble'", chains={'x': [{'wobble': {}}]})

    def test_unknown_generator_setting_names_the_chain(self):
        scenes = [{'tracks': {'lead': {'pattern': 'a', 'chain': 'x'}}}]
        self.assert_error("chain 'x', auto_ratchet: unknown setting 'count'", chains={'x': [{'auto_ratchet': {'count': [2]}}]}, scenes=scenes)

    def test_missing_generator_setting(self):
        scenes = [{'tracks': {'lead': {'pattern': 'a', 'chain': 'x'}}}]
        self.assert_error('needs to', chains={'x': [{'blend': {'style': 'left'}}]}, scenes=scenes)

    def test_paint_outside_the_song(self):
        self.assert_error('scene numbers from 1 to 1', chains={'x': [{'reverse': {}}]},
                          paint=[{'chain': 'x', 'tracks': ['lead'], 'scenes': [1, 9]}])

    def test_bad_scale(self):
        self.assert_error('unknown scale type', scales={'x': {'root': 'C', 'type': 'wobbly'}}, scale='x')
        self.assert_error('root note', scales={'x': {'root': 'H', 'type': 'major'}}, scale='x')
        self.assert_error('root and a type', scales={'x': {'root': 'C'}}, scale='x')

    def test_a_generator_cannot_read_another_track(self):
        scenes = [{'tracks': {'lead': {'pattern': 'a', 'chain': 'x'}}}]
        self.assert_error("unknown setting 'rhythm_from'", chains={'x': [{'take_rhythm': {'rhythm_from': 'kick'}}]}, scenes=scenes)

    def test_a_clip_needs_a_pattern(self):
        self.assert_error('needs a pattern', scenes=[{'tracks': {'lead': {'loop': True}}}])

    def test_a_clip_cannot_come_from_another_track(self):
        self.assert_error("unknown setting 'from'", scenes=[{'tracks': {'lead': {'from': 'kick'}}}])

    def test_missing_file(self):
        with self.assertRaises(SongFileError):
            load_song('/no/such/file.yml')


class TestExamples(unittest.TestCase):

    paths = sorted(glob.glob('examples/*.yml'))

    def test_there_are_three_songs(self):
        self.assertEqual(
            [os.path.basename(path) for path in self.paths],
            ['acid_techno.yml', 'minimal_techno.yml', 'retro_chill.yml'],
        )

    def test_every_generator_outside_legacy_is_used(self):
        used = set()
        for path in self.paths:
            with open(path) as file:
                for chain in yaml.safe_load(file)['chains'].values():
                    used |= {next(iter(step)) for step in chain}
        current = {name for name, details in GENERATORS.items() if '.legacy.' not in details[0].__module__}
        self.assertEqual(current - used, set())

    def test_every_song_lasts_about_three_minutes(self):
        for path in self.paths:
            song = load_song(path)
            seconds = 0
            for scene in song.scenes:
                lengths = [song.get_clip(scene, t).total_length() for t in song.tracks if song.get_clip(scene, t)]
                seconds += float(max(lengths)) * 4 * 60 / (scene.tempo or song.tempo)
            with self.subTest(path=path):
                self.assertAlmostEqual(seconds, 180, delta=10)

    def test_every_clip_lasts_as_long_as_its_scene_and_fits_a_piano(self):
        for path in self.paths:
            song = load_song(path)
            for scene in song.scenes:
                clips = [song.get_clip(scene, t) for t in song.tracks if song.get_clip(scene, t)]
                self.assertEqual(len({c.total_length() for c in clips}), 1)
                for each in clips:
                    found = pitches(each)
                    if found:
                        with self.subTest(path=path, scene=scene.name):
                            self.assertGreaterEqual(min(found), 21)
                            self.assertLessEqual(max(found), 108)

    def test_tempo_keeps_rising_through_minimal_techno(self):
        song = load_song('examples/minimal_techno.yml')
        tempos = [scene.tempo or song.tempo for scene in song.scenes]
        self.assertEqual(tempos, sorted(tempos))
        self.assertGreater(tempos[-1], tempos[0])

    def test_acid_bass_stays_low(self):
        song = load_song('examples/acid_techno.yml')
        for scene in song.scenes[1:]:
            acid = clip(song, scene.id + 1, 'acid')
            if acid is not None:
                with self.subTest(scene=scene.name):
                    self.assertLessEqual(max(pitches(acid)), 72)

    def test_acid_chords_never_clash_with_the_bass(self):
        song = load_song('examples/acid_techno.yml')
        for number in range(3, 11):
            with self.subTest(scene=number):
                self.assertEqual(ClashFinder().analyze(clip(song, number, 'acid'), clip(song, number, 'chords')), [])

    def test_every_example_renders_both_ways(self):
        for path in self.paths:
            for to in ['ableton', 'cliptree']:
                with tempfile.TemporaryDirectory() as parent:
                    out = os.path.join(parent, 'song')
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(main([path, '--to', to, '--out', out]), 0)
                    with self.subTest(path=path, to=to):
                        self.assertTrue(os.listdir(out))


class TestCli(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.parent = temporary.name
        self.song = os.path.join(self.parent, 'tune.yml')
        with open(self.song, 'w') as file:
            file.write(BASIC)
        self.out = os.path.join(self.parent, 'out')

    def run_cli(self, *arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main([self.song, '--out', self.out, *arguments])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_writes_an_ableton_set_by_default(self):
        self.assertEqual(self.run_cli()[0], 0)
        self.assertEqual(os.listdir(self.out), ['out.als'])
        with gzip.open(os.path.join(self.out, 'out.als')) as file:
            live_set = ET.fromstring(file.read()).find('LiveSet')
        self.assertEqual(
            [t.find('Name/EffectiveName').get('Value') for t in live_set.find('Tracks').findall('MidiTrack')],
            ['lead', 'kick'],
        )

    def test_writes_midi_files_numbered_from_1(self):
        self.run_cli('--to', 'cliptree')
        self.assertEqual(sorted(os.listdir(self.out)), ['001-001-one.mid', '001-002-one.mid'])
        played = mido.MidiFile(os.path.join(self.out, '001-001-one.mid'))
        self.assertEqual(played.tracks[0].name, '001-001-one')

    def test_stops_with_a_warning_if_the_output_exists(self):
        self.run_cli()
        code, stdout, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn('warning: stopping', stdout)

    def test_replace_regenerates_a_set(self):
        self.run_cli()
        with open(os.path.join(self.out, 'out.als'), 'wb') as file:
            file.write(b'old')
        self.assertEqual(self.run_cli('--replace')[0], 0)
        with open(os.path.join(self.out, 'out.als'), 'rb') as file:
            self.assertNotEqual(file.read(), b'old')

    def test_replace_keeps_everything_else(self):
        os.makedirs(self.out)
        keep = os.path.join(self.out, 'notes.txt')
        with open(keep, 'w') as file:
            file.write('keep me')
        self.run_cli('--to', 'cliptree', '--replace')
        self.run_cli('--to', 'cliptree', '--replace')
        self.assertTrue(os.path.exists(keep))
        self.assertEqual(sorted(os.listdir(self.out)), ['001-001-one.mid', '001-002-one.mid', 'notes.txt'])

    def test_errors_are_explained_without_a_traceback(self):
        with open(self.song, 'w') as file:
            file.write('tempo: 120\n')
        code, _, stderr = self.run_cli()
        self.assertEqual(code, 1)
        self.assertIn('error:', stderr)

    def test_bad_yaml_is_explained(self):
        with open(self.song, 'w') as file:
            file.write('tempo: [\n')
        code, _, stderr = self.run_cli()
        self.assertEqual(code, 1)
        self.assertIn('valid YAML', stderr)


if __name__ == '__main__':
    unittest.main()
