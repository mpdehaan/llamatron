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

import contextlib
import gzip
import io
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
from fractions import Fraction
from unittest import mock

import demo.blend_base as base
import demo.gifts_to_sun as piece
import demo.tunes as tunes
from llamatron.analyzers.clash_finder import ClashFinder
from llamatron.chord import Chord
from llamatron.note import Note, Rest
from llamatron.renderers.timing import timed_notes

TOTAL_SCENES = 1 + len(piece.PROGRESSION) + 1


def scale_pitches(scale):
    return {(scale.root.midi_number + step) % 12 for step in scale.typ.value}


class TestTunes(unittest.TestCase):

    def test_both_tunes_have_a_pickup_and_sixteen_measures(self):
        self.assertEqual(tunes.SIMPLE_GIFTS.total_length(), 17 * tunes.GIFTS_MEASURE)
        self.assertEqual(tunes.RISING_SUN.total_length(), 17 * tunes.RISING_SUN_MEASURE)

    def test_charts_have_one_chord_per_measure(self):
        for chart, melody in [
            (tunes.SIMPLE_GIFTS_CHORDS, tunes.SIMPLE_GIFTS),
            (tunes.RISING_SUN_CHORDS, tunes.RISING_SUN),
        ]:
            self.assertEqual(len(chart.notes), 17)
            self.assertEqual(chart.total_length(), melody.total_length())

    def test_keys_share_their_notes(self):
        self.assertEqual(scale_pitches(tunes.C_MAJOR), scale_pitches(tunes.A_MINOR))

    def test_melodies_stay_in_their_scales_except_rising_sun_leading_note(self):
        gifts = {note.midi_number % 12 for note in tunes.SIMPLE_GIFTS.notes if not isinstance(note, Rest)}
        self.assertLessEqual(gifts, scale_pitches(tunes.C_MAJOR))
        sun = {note.midi_number % 12 for note in tunes.RISING_SUN.notes if not isinstance(note, Rest)}
        self.assertEqual(sun - scale_pitches(tunes.A_MINOR), {8})

    def test_stretched_rising_sun_lines_up_with_simple_gifts(self):
        self.assertEqual(piece.SUN.total_length(), tunes.SIMPLE_GIFTS.total_length())
        self.assertEqual(piece.SUN_CHORDS.total_length(), tunes.SIMPLE_GIFTS.total_length())


class TestSong(unittest.TestCase):

    def setUp(self):
        self.song = piece.build_song()
        self.melody_track, self.chord_track, self.bass_track, self.kick_track, self.snare_track = self.song.tracks
        self.parts = list(zip(self.song.scenes[1:-1], piece.PROGRESSION))

    def melody(self, scene):
        return self.song.get_clip(scene, self.melody_track)

    def chords(self, scene):
        return self.song.get_clip(scene, self.chord_track)

    def bass(self, scene):
        return self.song.get_clip(scene, self.bass_track)

    def leader(self, part):
        """Return the melody, chords and scale of the tune ahead in a part."""
        if part.amount <= 50:
            return tunes.SIMPLE_GIFTS, tunes.SIMPLE_GIFTS_CHORDS, piece.GIFTS_SCALE
        return piece.SUN, piece.SUN_CHORDS, piece.SUN_SCALE

    def test_plays_simple_gifts_then_morphs_then_rising_sun(self):
        names = [scene.name for scene in self.song.scenes]
        self.assertEqual(names, [
            'Simple Gifts', 'Morph at 30', 'Morph at 60', 'Morph at 90', 'Rising Sun',
        ])

    def test_lasts_under_two_minutes(self):
        whole_notes = sum(self.melody(scene).total_length() for scene in self.song.scenes)
        self.assertEqual(whole_notes * 2, 100)

    def test_starts_with_half_of_simple_gifts_and_ends_with_all_of_rising_sun(self):
        opening = tunes.SIMPLE_GIFTS.measures(1, piece.OPENING_LAST_MEASURE)
        self.assertEqual(self.melody(self.song.scenes[0]).notes, opening.notes)
        self.assertEqual(self.melody(self.song.scenes[-1]).notes, piece.SUN.notes)

    def test_the_blend_only_ever_moves_towards_rising_sun(self):
        amounts = [part.amount for part in piece.PROGRESSION]
        self.assertEqual(amounts, sorted(amounts))
        self.assertEqual(len(amounts), len(set(amounts)))

    def test_rising_sun_leads_most_of_the_morphs(self):
        led = sum(part.amount > 50 for part in piece.PROGRESSION)
        self.assertGreater(led, len(piece.PROGRESSION) / 2)

    def test_melody_and_chords_last_the_same_in_every_scene(self):
        for scene in self.song.scenes:
            with self.subTest(scene=scene.name):
                self.assertEqual(self.melody(scene).total_length(), self.chords(scene).total_length())

    def test_morphs_last_eight_measures(self):
        for scene, _ in self.parts:
            with self.subTest(scene=scene.name):
                self.assertEqual(self.melody(scene).total_length(), 8)

    def test_every_morph_has_some_of_both_tunes(self):
        for scene, part in self.parts:
            gifts = tunes.SIMPLE_GIFTS.measures(part.first, part.last).played_notes()
            sun = piece.SUN.measures(part.first, part.last).played_notes()
            with self.subTest(scene=scene.name):
                self.assertNotEqual(self.melody(scene).played_notes(), gifts)
                self.assertNotEqual(self.melody(scene).played_notes(), sun)

    def test_the_amount_sets_the_share_of_slices_from_rising_sun(self):
        for _, part in self.parts:
            gifts = tunes.SIMPLE_GIFTS.measures(part.first, part.last)
            chart = tunes.SIMPLE_GIFTS_CHORDS.measures(part.first, part.last)
            target = piece.SUN.measures(part.first, part.last)
            blend = base.Blend(target, part.amount, points=base.slice_points(gifts, chart), seed=piece.SEED)
            owners = blend.takes_target(target.total_length())
            with self.subTest(amount=part.amount):
                self.assertAlmostEqual(sum(owners) / len(owners), part.amount / 100, delta=0.1)

    def test_decorations_are_slight(self):
        for part in piece.PROGRESSION:
            plain = tunes.SIMPLE_GIFTS.measures(part.first, part.last)
            decorated = base.decorate(plain, plain, piece.GIFTS_SCALE)
            count = lambda clip: sum(not isinstance(p, Rest) for p in clip.notes)
            with self.subTest(amount=part.amount):
                self.assertLessEqual(count(decorated) - count(plain), count(plain) / 3)

    def test_the_tune_that_is_ahead_sets_the_scale(self):
        for scene, part in self.parts:
            _, _, scale = self.leader(part)
            with self.subTest(scene=scene.name):
                self.assertEqual(self.melody(scene).scale, scale)
                self.assertEqual(self.chords(scene).scale, scale)

    def test_every_morph_note_and_chord_note_is_in_the_scale_of_the_tune_ahead(self):
        for scene, part in self.parts:
            _, _, scale = self.leader(part)
            melody, _ = timed_notes(self.melody(scene), scale)
            chords, _ = timed_notes(self.chords(scene), scale)
            with self.subTest(scene=scene.name):
                self.assertLessEqual({pitch % 12 for _, _, pitch in melody + chords}, scale_pitches(scale))

    def test_the_tune_that_is_ahead_sets_the_rhythm(self):
        def starts(clip):
            now, result = 0, []
            for position in clip.played_notes():
                if not isinstance(position, Rest):
                    result.append(now)
                now += position.length
            return set(result)

        for scene, part in self.parts:
            tune, _, _ = self.leader(part)
            # Decorations can add a few notes, but the tune's own rhythm must all be there.
            with self.subTest(scene=scene.name):
                self.assertLessEqual(starts(tune.measures(part.first, part.last)), starts(self.melody(scene)))

    def test_the_tune_that_is_ahead_sets_the_chords(self):
        for scene, part in self.parts:
            _, chart, scale = self.leader(part)
            forced = base.ForceScale(scale).generate(chart.measures(part.first, part.last)).notes
            sounding, _ = timed_notes(self.chords(scene), scale)
            matching = 0
            for measure, chord in enumerate(forced):
                in_measure = {pitch % 12 for start, _, pitch in sounding if measure <= start < measure + 1}
                matching += in_measure <= {note.midi_number % 12 for note in chord.notes}
            with self.subTest(scene=scene.name):
                self.assertGreaterEqual(matching, len(forced) - 2)

    def test_chords_get_busier_as_rising_sun_takes_over(self):
        counts = []
        for scene in self.song.scenes[1:]:
            notes, _ = timed_notes(self.chords(scene), self.chords(scene).scale)
            attacks = {start for start, _, _ in notes}
            counts.append(len(attacks) / self.chords(scene).total_length())
        self.assertEqual(counts, [1, 3, 6, 6])

    def test_arpeggios_play_every_note_of_the_chord(self):
        for scene, part in self.parts:
            if part.arp_step is not None:
                sounding, _ = timed_notes(self.chords(scene), self.chords(scene).scale)
                first_measure = {pitch for start, _, pitch in sounding if start < 1}
                with self.subTest(scene=scene.name):
                    self.assertEqual(len(first_measure), 3)

    def test_gifts_led_chords_are_held_and_sun_led_chords_are_arpeggiated(self):
        for scene, part in self.parts:
            positions = self.chords(scene).notes
            with self.subTest(scene=scene.name):
                if part.arp_step is None:
                    self.assertTrue(all(isinstance(p, Chord) for p in positions))
                else:
                    self.assertTrue(all(isinstance(p, Note) for p in positions))
                    self.assertEqual({p.length for p in positions}, {part.arp_step})

    def test_arpeggios_line_up_with_the_rising_sun_rhythm(self):
        self.assertEqual(piece.SUN_EIGHTH * 6, 1)
        self.assertEqual(piece.SUN.notes[1].length, piece.SUN_EIGHTH)

    def test_whole_rising_sun_arpeggiates_its_real_chords(self):
        sounding, _ = timed_notes(self.chords(self.song.scenes[-1]), piece.SUN_SCALE)
        for measure, chord in enumerate(piece.SUN_CHORDS.resolved_notes()):
            in_measure = {pitch % 12 for start, _, pitch in sounding if measure <= start < measure + 1}
            with self.subTest(measure=measure):
                self.assertEqual(in_measure, {note.midi_number % 12 for note in chord.notes})

    def test_smoother_can_be_turned_off(self):
        with mock.patch.object(base, 'Smoother', wraps=base.Smoother) as smoother:
            piece.build_song()
            self.assertEqual(smoother.call_count, len(piece.PROGRESSION))
            smoother.reset_mock()
            with mock.patch.object(piece, 'USE_SMOOTHER', False):
                piece.build_song()
            self.assertEqual(smoother.call_count, 0)

    def test_no_morph_jumps_more_than_an_octave(self):
        # Smoother can't leave the melody's range, so it can't shrink every jump to max_leap.
        for scene, _ in self.parts:
            pitches = [p.midi_number for p in self.melody(scene).notes if not isinstance(p, Rest)]
            with self.subTest(scene=scene.name):
                self.assertLessEqual(max(abs(a - b) for a, b in zip(pitches, pitches[1:])), 12)

    def test_chords_never_clash_with_the_melody(self):
        for scene in self.song.scenes:
            with self.subTest(scene=scene.name):
                self.assertEqual(ClashFinder().analyze(self.melody(scene), self.chords(scene)), [])

    def test_opening_mostly_uses_the_real_chords(self):
        chords = self.chords(self.song.scenes[0]).notes
        real = base.Register(base.CHORDS_LOW, base.CHORDS_HIGH).generate(
            tunes.SIMPLE_GIFTS_CHORDS.measures(1, piece.OPENING_LAST_MEASURE)
        ).notes
        self.assertGreaterEqual(sum(a == b for a, b in zip(chords, real)), len(real) - 2)

    def pitches(self, clip):
        return [pitch for _, _, pitch in timed_notes(clip, clip.scale)[0]]

    def test_every_part_stays_in_its_own_space(self):
        for scene in self.song.scenes:
            melody, chords = self.pitches(self.melody(scene)), self.pitches(self.chords(scene))
            with self.subTest(scene=scene.name):
                self.assertLess(max(chords), min(melody))
                if self.bass(scene) is not None:
                    self.assertLess(max(self.pitches(self.bass(scene))), min(chords))

    def drum_times(self, clip):
        return [(start, end - start, pitch) for start, end, pitch in timed_notes(clip, clip.scale)[0]]

    def test_kick_plays_a_short_c3_at_the_start_of_every_measure(self):
        for scene in self.song.scenes:
            clip = self.song.get_clip(scene, self.kick_track)
            measures = int(self.melody(scene).total_length())
            expected = [(measure, Fraction(1, 16), Note('C', 3).midi_number) for measure in range(measures)]
            with self.subTest(scene=scene.name):
                self.assertEqual(self.drum_times(clip), expected)
                self.assertEqual(clip.total_length(), measures)

    def test_snare_plays_a_short_d3_on_beats_two_three_and_four(self):
        for scene in self.song.scenes:
            clip = self.song.get_clip(scene, self.snare_track)
            measures = int(self.melody(scene).total_length())
            expected = [
                (measure + Fraction(beat, 4), Fraction(1, 16), Note('D', 3).midi_number)
                for measure in range(measures) for beat in (1, 2, 3)
            ]
            with self.subTest(scene=scene.name):
                self.assertEqual(self.drum_times(clip), expected)
                self.assertEqual(clip.total_length(), measures)

    def test_track_names(self):
        self.assertEqual(
            [track.name for track in self.song.tracks],
            ['Melody', 'Chords', 'Bass', 'kick', 'snare'],
        )

    def test_every_note_is_on_a_piano(self):
        for scene in self.song.scenes:
            for clip in [self.melody(scene), self.chords(scene), self.bass(scene)]:
                if clip is not None:
                    pitches = [pitch for _, _, pitch in timed_notes(clip, clip.scale)[0]]
                    with self.subTest(scene=scene.name):
                        self.assertGreaterEqual(min(pitches), 21)
                        self.assertLessEqual(max(pitches), 108)

    def test_the_bass_enters_after_the_opening(self):
        self.assertIsNone(self.bass(self.song.scenes[0]))
        for scene in self.song.scenes[1:]:
            with self.subTest(scene=scene.name):
                self.assertEqual(self.bass(scene).total_length(), self.melody(scene).total_length())

    def test_the_bass_moves_through_every_style(self):
        styles = {part.bass_style for part in piece.PROGRESSION}
        self.assertEqual(styles, set(base.CounterpointStyle))
        self.assertEqual(
            [part.bass_style.name for part in piece.PROGRESSION],
            ['NOTE_AGAINST_NOTE', 'FLOWING', 'CANON'],
        )

    def test_the_bass_is_low(self):
        for scene in self.song.scenes[1:]:
            pitches = [pitch for _, _, pitch in timed_notes(self.bass(scene), self.bass(scene).scale)[0]]
            with self.subTest(scene=scene.name):
                self.assertLessEqual(max(pitches), base.BASS_HIGH.midi_number)

    def test_the_bass_never_clashes_with_the_chords(self):
        for scene in self.song.scenes[1:]:
            with self.subTest(scene=scene.name):
                self.assertEqual(ClashFinder().analyze(self.bass(scene), self.chords(scene)), [])

    def test_every_run_gives_the_same_song(self):
        again = piece.build_song()
        for first, second in zip(self.song.scenes, again.scenes):
            with self.subTest(scene=first.name):
                self.assertEqual(
                    self.melody(first).played_notes(),
                    again.get_clip(second, again.tracks[0]).played_notes(),
                )


class TestRendering(unittest.TestCase):

    def run_demo(self, use_ableton):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        directory = os.path.join(temporary.name, 'gifts_to_sun')
        with mock.patch.object(piece, 'USE_ABLETON', use_ableton):
            with mock.patch.object(piece, 'OUTPUT_DIRECTORY', directory):
                with contextlib.redirect_stdout(io.StringIO()):
                    piece.main()
        return directory

    def test_ableton_set_has_both_views(self):
        directory = self.run_demo(True)
        self.assertEqual(os.listdir(directory), ['gifts_to_sun.als'])
        with open(os.path.join(directory, 'gifts_to_sun.als'), 'rb') as file:
            live_set = ET.fromstring(gzip.decompress(file.read())).find('LiveSet')
        self.assertEqual(len(live_set.find('Scenes')), TOTAL_SCENES)
        for track in live_set.find('Tracks').findall('MidiTrack'):
            expected = TOTAL_SCENES - 1 if track.find('Name/EffectiveName').get('Value') == 'Bass' else TOTAL_SCENES
            sequencer = track.find('DeviceChain/MainSequencer')
            self.assertEqual(len(sequencer.find('ClipSlotList').findall('.//MidiClip')), expected)
            arrangement = sequencer.find('ClipTimeable/ArrangerAutomation/Events')
            self.assertEqual(len(arrangement), expected)
            ends = [float(clip.find('CurrentEnd').get('Value')) for clip in arrangement]
            self.assertEqual(ends[-1], (9 + 8 * len(piece.PROGRESSION) + 17) * 4)

    def test_clip_tree_writes_midi_files(self):
        names = os.listdir(self.run_demo(False))
        self.assertEqual(len(names), TOTAL_SCENES * 5 - 1)
        self.assertTrue(all(name.endswith('.mid') for name in names))


if __name__ == '__main__':
    unittest.main()
