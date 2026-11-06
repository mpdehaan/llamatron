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

"""The composition objects, each saving itself with to_data() and loading with from_data().

Every class gets the same kinds of test: what it reads comes back the same from to_data(), a
setting the data leaves out gets its default, settings left out aren't written back, and wrong
data is refused with a message that says where it is.
"""

import unittest
from fractions import Fraction

from llamatron.composition.cell import Cell
from llamatron.composition.chain import Chain
from llamatron.composition.generator_settings import ArpSettings, AutoRatchetSettings
from llamatron.composition.named_scale import NamedScale
from llamatron.composition.pattern import Pattern
from llamatron.composition.scene import Scene
from llamatron.composition.song import Song
from llamatron.composition.song_file_error import SongFileError
from llamatron.composition.track import Track
from llamatron.generators.arp import Arp, ChordOrder
from llamatron.generators.auto_ratchet import AutoRatchet
from llamatron.generators.blend import BlendMode


def a_song():
    """Return a small song for objects that check names: a pattern, a track pair, an arp and a chain."""
    return Song.from_data({
        'scales': {'main': {'root': 'C', 'type': 'major'}},
        'patterns': {'a': {'steps': 1, 'degree': [1]}, 'b': {'steps': 1, 'degree': [5]}},
        'tracks': {'lead': {}, 'bass': {}},
        'arps': {'up': {'step': '1/8'}},
        'chains': {'x': [{'arp': 'up'}]},
    })


class RoundTrip(unittest.TestCase):

    def assert_round_trip(self, kind, data, *extra, **named):
        self.assertEqual(kind.from_data(data, 'here', *extra, **named).to_data(), data)

    def assert_refused(self, expected, kind, data, *extra, **named):
        with self.assertRaises(SongFileError) as caught:
            kind.from_data(data, 'here', *extra, **named)
        self.assertIn(expected, str(caught.exception))


class TestNamedScale(RoundTrip):

    def test_round_trip_keeps_the_spelling(self):
        self.assert_round_trip(NamedScale, {'root': 'Bb', 'type': 'natural minor'})

    def test_it_makes_a_scale_in_an_octave(self):
        scale = NamedScale.from_data({'root': 'F', 'type': 'minor'}, 'here').scale_at(5)
        self.assertEqual(scale.root.name, 'F')
        self.assertEqual(scale.root.octave_number, 5)

    def test_refusals(self):
        self.assert_refused('expected a root and a type', NamedScale, {'root': 'C'})
        self.assert_refused('expected a root note like F or Bb', NamedScale, {'root': 'H', 'type': 'major'})
        self.assert_refused("unknown scale type 'wobbly'", NamedScale, {'root': 'C', 'type': 'wobbly'})


class TestTrack(RoundTrip):

    def test_round_trip(self):
        self.assert_round_trip(Track, {'drum': True, 'mute': True, 'cc': [74, None, None, 1]})
        self.assert_round_trip(Track, {'transpose': -7})
        self.assert_round_trip(Track, {})

    def test_defaults(self):
        track = Track.from_data(None, 'here')
        self.assertEqual((track.is_drum(), track.is_muted(), track.get_transpose()), (False, False, 0))
        self.assertEqual(track.get_cc_numbers(), [None] * 4)
        self.assertEqual(track.to_data(), {})

    def test_a_drum_track_never_transposes(self):
        self.assertEqual(Track.from_data({'drum': True, 'transpose': 3}, 'here').get_transpose(), 0)

    def test_refusals(self):
        self.assert_refused('expected settings like', Track, [1])
        self.assert_refused("unknown setting 'octave'", Track, {'octave': 2})
        self.assert_refused('mute must be true or false', Track, {'mute': 'yes'})
        self.assert_refused('transpose must be a whole number from -24 to 24', Track, {'transpose': 25})
        self.assert_refused('cc must be a list of 4 CC numbers', Track, {'cc': [1, 2]})


class TestPattern(RoundTrip):

    DATA = {
        'steps': 3, 'drum': False, 'direction': 'pendulum', 'accumulator_limit': 5,
        'degree': [1, None, 5], 'gate': ['1/4', None, 1], 'dot': ['d', None, None], 'glide': [True, False, False],
    }

    def test_round_trip(self):
        self.assert_round_trip(Pattern, self.DATA)
        self.assert_round_trip(Pattern, {'steps': 1})

    def test_values_and_defaults(self):
        pattern = Pattern.from_data(self.DATA, 'here')
        self.assertEqual((pattern.get_steps(), pattern.get_direction(), pattern.get_accumulator_limit()), (3, 'pendulum', 5))
        self.assertEqual([pattern.get_value('degree', step) for step in range(3)], [1, None, 5])
        self.assertIsNone(pattern.get_value('velocity', 0))
        self.assertEqual(pattern.get_note_steps(), [0, 2])
        self.assertIsNone(pattern.get_first_octave())
        plain = Pattern.from_data({'steps': 2, 'octave': [None, 4]}, 'here')
        self.assertEqual((plain.get_direction(), plain.get_accumulator_limit(), plain.is_drum()), ('forward', 36, False))
        self.assertEqual(plain.get_first_octave(), 4)

    def test_its_lists_are_its_own(self):
        data = {'steps': 1, 'degree': [1]}
        pattern = Pattern.from_data(data, 'here')
        data['degree'][0] = 9
        pattern.to_data()['degree'][0] = 9
        self.assertEqual(pattern.get_value('degree', 0), 1)

    def test_refusals(self):
        self.assert_refused('expected settings like steps', Pattern, [])
        self.assert_refused("unknown setting 'notes'", Pattern, {'steps': 1, 'notes': []})
        self.assert_refused('steps must be a whole number of 1 or more', Pattern, {'steps': 0})
        self.assert_refused('degree must be a list of 2 values', Pattern, {'steps': 2, 'degree': [1]})
        self.assert_refused('glide must be true or false, got null', Pattern, {'steps': 1, 'glide': [None]})
        self.assert_refused('direction must be one of', Pattern, {'steps': 1, 'direction': 'sideways'})
        self.assert_refused('velocity must be a whole number from 1 to 127', Pattern, {'steps': 1, 'velocity': [0]})
        self.assert_refused('must be a note letter', Pattern, {'steps': 1, 'drum': True, 'degree': [1]})


class TestGeneratorSettings(RoundTrip):

    def test_round_trip_keeps_settings_as_written(self):
        self.assert_round_trip(ArpSettings, {'step': '1/16', 'order': 'up_down', 'offsets': [0, None, 7]})
        self.assert_round_trip(AutoRatchetSettings, {'counts': [1, 4]})
        self.assertEqual(ArpSettings.from_data(None, 'here').to_data(), {})

    def test_it_makes_its_generator(self):
        arp = ArpSettings.from_data({'step': '1/8', 'order': 'down'}, 'here').make_generator('chain x, arp', 7)
        self.assertIsInstance(arp, Arp)
        self.assertEqual((arp.step, arp.order, arp.seed), (Fraction(1, 8), ChordOrder.DOWN, 7))
        self.assertIsInstance(AutoRatchetSettings.from_data({'counts': [2]}, 'here').make_generator('chain x', 7), AutoRatchet)

    def test_a_seed_of_its_own_beats_the_default(self):
        arp = ArpSettings.from_data({'step': '1/8', 'seed': 3}, 'here').make_generator('chain x', 7)
        self.assertEqual(arp.seed, 3)

    def test_wrong_settings_are_only_refused_when_used_and_name_the_chain(self):
        settings = AutoRatchetSettings.from_data({'count': [2]}, 'here')
        with self.assertRaisesRegex(SongFileError, "chain 'x', auto_ratchet: unknown setting 'count'"):
            settings.make_generator("chain 'x', auto_ratchet", 1)
        with self.assertRaisesRegex(SongFileError, 'needs step'):
            ArpSettings.from_data({}, 'here').make_generator('chain x', 1)


class TestChain(RoundTrip):

    def test_round_trip(self):
        self.assert_round_trip(Chain, [{'arp': 'up'}, {'arp': 'up'}], a_song())

    def test_steps(self):
        self.assertEqual(Chain.from_data([{'arp': 'up'}], 'here', a_song()).get_steps(), [('arp', 'up')])

    def test_refusals(self):
        self.assert_refused('expected a list of generators', Chain, {}, a_song())
        self.assert_refused('each step must be one generator', Chain, [{'arp': 'up', 'auto_ratchet': 'r'}], a_song())
        self.assert_refused("unknown generator 'wobble'", Chain, [{'wobble': 'up'}], a_song())
        self.assert_refused("no arp called 'down'", Chain, [{'arp': 'down'}], a_song())


class TestCell(RoundTrip):

    def test_round_trip(self):
        data = {'pattern': 'a', 'chain': 'x', 'repeat': 2, 'morph_to': 'b', 'morph_style': 'left', 'grab_track': 'bass'}
        self.assert_round_trip(Cell, data, a_song(), track='lead')
        self.assert_round_trip(Cell, {'pattern': 'a', 'loop': False}, a_song(), track='lead')

    def test_values_and_defaults(self):
        cell = Cell.from_data({'pattern': 'a', 'rhythm_from': 'b', 'morph_to': 'b', 'morph_style': 'middle', 'repeat': 3}, 'here', a_song(), track='lead')
        self.assertEqual((cell.get_pattern_name(), cell.get_rhythm_pattern_name(), cell.get_repeat()), ('a', 'b', 3))
        self.assertEqual((cell.get_morph_target(), cell.get_morph_style()), ('b', BlendMode.MIDDLE))
        plain = Cell.from_data({'pattern': 'a'}, 'here', a_song(), track='lead')
        self.assertEqual((plain.get_rhythm_pattern_name(), plain.get_repeat(), plain.loops()), ('a', 1, False))
        self.assertIsNone(plain.get_chain_name())
        self.assertIsNone(plain.get_direction())
        self.assertIsNone(plain.get_morph_style())
        self.assertIsNone(plain.get_grab_track())

    def test_refusals_name_the_track(self):
        song = a_song()
        self.assert_refused("here, track 'lead': needs a pattern", Cell, {}, song, track='lead')
        self.assert_refused("no pattern called 'zz'", Cell, {'pattern': 'zz'}, song, track='lead')
        self.assert_refused("no chain called 'y'", Cell, {'pattern': 'a', 'chain': 'y'}, song, track='lead')
        self.assert_refused("can't grab from its own track", Cell, {'pattern': 'a', 'grab_track': 'lead'}, song, track='lead')
        self.assert_refused('a morph needs both', Cell, {'pattern': 'a', 'morph_to': 'b', 'repeat': 2}, song, track='lead')
        self.assert_refused('a morph needs a repeat of 2', Cell, {'pattern': 'a', 'morph_to': 'b', 'morph_style': 'left'}, song, track='lead')
        self.assert_refused('loop must be true or false', Cell, {'pattern': 'a', 'loop': 'yes'}, song, track='lead')


class TestScene(RoundTrip):

    def test_round_trip(self):
        data = {'name': 'verse', 'repeat': 2, 'scale': 'main', 'tempo_start': 100, 'tempo_end': 120, 'tracks': {'lead': {'pattern': 'a'}}}
        self.assert_round_trip(Scene, data, a_song())
        self.assert_round_trip(Scene, {}, a_song())

    def test_values_and_defaults(self):
        scene = Scene.from_data({'repeat': 3, 'tempo_start': 100, 'tempo_end': 120, 'tracks': {'lead': {'pattern': 'a'}}}, 'here', a_song())
        self.assertEqual([scene.get_tempo(place) for place in range(3)], [100, 110, 120])
        self.assertEqual(scene.get_track_names(), ['lead'])
        self.assertEqual(scene.get_cell('lead').get_pattern_name(), 'a')
        self.assertIsNone(scene.get_cell('bass'))
        plain = Scene.from_data({}, 'here', a_song())
        self.assertEqual((plain.get_name(), plain.get_repeat(), plain.get_scale_name(), plain.get_tempo(0)), (None, 1, None, None))

    def test_refusals(self):
        song = a_song()
        self.assert_refused('expected settings like name and tracks', Scene, [], song)
        self.assert_refused('repeat must be a positive whole number', Scene, {'repeat': 0}, song)
        self.assert_refused("no track called 'drums'", Scene, {'tracks': {'drums': {'pattern': 'a'}}}, song)
        self.assert_refused("no scale called 'other'", Scene, {'scale': 'other'}, song)
        self.assert_refused('needs both tempo_start and tempo_end', Scene, {'tempo_start': 90}, song)


class TestSong(RoundTrip):

    def test_round_trip(self):
        self.assertEqual(a_song().to_data(), Song.from_data(a_song().to_data()).to_data())
        self.assert_round_trip(Song, {'title': 'T', 'tempo': 90, 'tracks': {}, 'scenes': []})

    def test_an_empty_file_is_an_empty_song_with_defaults(self):
        for data in [None, {}]:
            song = Song.from_data(data)
            self.assertEqual(song.to_data(), {})
            self.assertEqual((song.get_tempo(), song.get_seed(), song.get_step_size()), (120, 1, Fraction(1, 16)))
            self.assertEqual((song.get_default_octave(), song.get_default_drum_octave(), song.get_scale_name()), (3, 1, None))
            self.assertEqual((song.get_track_names(), song.get_scenes()), ([], []))

    def test_it_looks_up_its_named_objects(self):
        song = a_song()
        self.assertTrue(song.has_pattern('a') and song.has_track('lead') and song.has_chain('x') and song.has_scale('main'))
        self.assertTrue(song.has_generator('arp', 'up'))
        self.assertFalse(song.has_generator('auto_ratchet', 'up'))
        self.assertEqual(song.get_track_names(), ['lead', 'bass'])
        self.assertEqual(song.get_pattern('b').get_value('degree', 0), 5)

    def test_refusals(self):
        self.assert_refused('a song file must have settings', Song, [1])
        self.assert_refused("unknown setting 'themes'", Song, {'themes': {}})
        self.assert_refused('title must be text', Song, {'title': 3})
        self.assert_refused("scale: no scale called 'main'", Song, {'scale': 'main'})
        self.assert_refused('step_size: expected a whole number or a fraction', Song, {'step_size': '0.25'})
        self.assert_refused('step_size: a length can be at most 4', Song, {'step_size': 8})
        self.assert_refused("pattern 'a': steps must be", Song, {'patterns': {'a': {'steps': 0}}})
        self.assert_refused('tracks: expected named tracks', Song, {'tracks': ['lead']})
        self.assert_refused('arps: expected named settings', Song, {'arps': ['up']})
        self.assert_refused('scenes: expected a list of scenes', Song, {'scenes': {'verse': {}}})


if __name__ == '__main__':
    unittest.main()
