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

"""Loading song files: what a file can hold, what it refuses, and the text at its top."""

import copy
import unittest
import yaml

from llamatron.composition.file_format import ClipSlotSetting, GeneratorKind, ScaleSetting, SceneSetting, Section, SetlistSetting, SongSetting
from llamatron.composition.generator_settings import ArpSetting, AutoRatchetSetting, written_name
from llamatron.composition.named_scale import scale_type_name
from llamatron.composition.song_file_error import SongFileError
from llamatron.generators.arp import ChordOrder
from llamatron.music.note import NoteName
from llamatron.music.scale import ScaleType
from llamatron.strings import errors
from tests.support import song_testing
from tests.support.rendering import as_setlist, dump_song_data, render_data, render_file, setlist_from_data, song_from_data
from tests.support.song_testing import pat, with_parts

QUARTER = '1/4'
NOPE = 'nope'
KICK = 'kick'
A = 'a'
WOBBLY = 'wobbly'
C_MAJOR = 'C major'
WOBBLE = 'wobble'
EXPECTED_SETTINGS = 'expected clip settings'
NEEDS_COUNTS = 'needs counts'
UNKNOWN_SCALE_TYPE = 'unknown scale type'
ROOT_NOTE = 'root note'
ROOT_AND_A_TYPE = 'root and a type'
NEEDS_A_PATTERN = 'needs a pattern'
DESCRIPTION_MUST_BE_TEXT = 'description must be text'
NOTES_MUST_BE_TEXT = 'notes must be text'
R = 'r'
COUNT = 'count'
# A name no object of the program knows, put at every level of a set by the test of names passed over.
NOT_KNOWN = 'not_known'
NOT_A_ROOT = 'H'
A_LIST = 'a list'
FROM = 'from'
SOMEONE = 'Someone'
RAIN = 'Rain'


def parts_of(data):
    """Return every part of a set's data that holds settings: the set, each song and its tracks, scenes and clips, each pattern
    and each generator."""
    parts = [data, *data[Section.PATTERNS].values(), *data[Section.AUTO_RATCHETS].values()]
    for song in data[Section.SONGS].values():
        parts += [song, *song[Section.TRACKS].values()]
        for scene in song[Section.SCENES]:
            parts += [scene, *scene[SceneSetting.TRACKS].values()]
    return parts


class TestErrors(unittest.TestCase):

    def assert_error(self, expected, **parts):
        with self.assertRaises(SongFileError) as caught:
            render_data(with_parts(**parts))
        self.assertIn(expected, str(caught.exception))

    def test_a_preview_instrument_the_set_does_not_have_is_refused(self):
        # The setting belongs to a song of the set, so the data is a set's, the song's part given the setting.
        data = as_setlist(with_parts())
        song = next(iter(data[Section.SONGS].values()))
        song[SongSetting.PREVIEW_INSTRUMENT] = NOPE
        with self.assertRaises(SongFileError) as caught:
            setlist_from_data(data)
        self.assertIn(errors.ERR_SONG_NO_SUCH_PREVIEW_INSTRUMENT.format(name=NOPE), str(caught.exception))
        # None is no preview instrument, and is read.
        song[SongSetting.PREVIEW_INSTRUMENT] = None
        self.assertIsNone(song_from_data(data).get_preview_instrument_name())

    def test_a_name_the_program_does_not_know_is_passed_over_at_every_level_and_never_written_again(self):
        # The set, a song, a track, a scene, a clip, a pattern and a generator each hold a name no object knows, as a file from
        # another version might, a setting taken away included; the set reads as it would without them and writes none of them.
        scenes = [{Section.TRACKS: {song_testing.LEAD: {ClipSlotSetting.PATTERN: A, ClipSlotSetting.CHAINS: [song_testing.X]}}}]
        plain = as_setlist(with_parts(
            patterns={A: pat([1, QUARTER])}, auto_ratchets={R: {AutoRatchetSetting.COUNTS: [2]}}, chains={song_testing.X: [{GeneratorKind.AUTO_RATCHET: R}]}, scenes=scenes,
        ))
        with_unknown = copy.deepcopy(plain)
        for holder in parts_of(with_unknown):
            holder[NOT_KNOWN] = 1
        written = setlist_from_data(with_unknown).to_data()
        self.assertEqual(written, setlist_from_data(plain).to_data())
        self.assertNotIn(NOT_KNOWN, yaml.safe_dump(written))

    def test_unknown_chain_in_a_clip_slot(self):
        self.assert_error(errors.ERR_NO_GENERATOR_CALLED.format(name='nope'), scenes=[{Section.TRACKS: {song_testing.LEAD: {ClipSlotSetting.PATTERN: A, ClipSlotSetting.CHAINS: [NOPE]}}}])

    def test_unknown_pattern(self):
        self.assert_error('no pattern called (nope)', scenes=[{Section.TRACKS: {song_testing.LEAD: {ClipSlotSetting.PATTERN: NOPE}}}])

    def test_unknown_track(self):
        self.assert_error('no track called (nope)', scenes=[{Section.TRACKS: {NOPE: {ClipSlotSetting.PATTERN: A}}}])

    def test_clip_slots_must_use_the_hash_form(self):
        self.assert_error(EXPECTED_SETTINGS, scenes=[{Section.TRACKS: {song_testing.LEAD: A}}])

    def test_unknown_generator(self):
        self.assert_error('unknown generator (wobble)', chains={song_testing.X: [{WOBBLE: {}}]})

    def test_a_generator_no_chain_uses_is_checked_too(self):
        # A misspelled setting is passed over as unknown, so the generator lacks the setting it needs.
        self.assert_error(NEEDS_COUNTS, auto_ratchets={R: {COUNT: [2]}})
        self.assert_error(NEEDS_COUNTS, auto_ratchets={R: {}})

    def test_missing_generator_setting(self):
        scenes = [{Section.TRACKS: {song_testing.LEAD: {ClipSlotSetting.PATTERN: A, ClipSlotSetting.CHAINS: [song_testing.X]}}}]
        self.assert_error(NEEDS_COUNTS, auto_ratchets={R: {}}, chains={song_testing.X: [{GeneratorKind.AUTO_RATCHET: R}]}, scenes=scenes)

    def test_an_arp_with_no_step_plays_at_the_step_of_the_pattern_its_clip_plays(self):
        # A step left out is "(pattern)", where it was refused before.
        scenes = [{Section.TRACKS: {song_testing.LEAD: {ClipSlotSetting.PATTERN: A, ClipSlotSetting.CHAINS: [song_testing.X]}}}]
        data = with_parts(arps={R: {ArpSetting.ORDER: written_name(ChordOrder.UP)}}, chains={song_testing.X: [{GeneratorKind.ARP: R}]}, scenes=scenes)
        render_data(data)

    def test_bad_scale(self):
        self.assert_error(UNKNOWN_SCALE_TYPE, scales={song_testing.X: {ScaleSetting.ROOT: NoteName.C, ScaleSetting.TYPE: WOBBLY}}, scale=song_testing.X)
        self.assert_error(ROOT_NOTE, scales={song_testing.X: {ScaleSetting.ROOT: NOT_A_ROOT, ScaleSetting.TYPE: scale_type_name(ScaleType.MAJOR)}}, scale=song_testing.X)
        self.assert_error(ROOT_AND_A_TYPE, scales={song_testing.X: {ScaleSetting.ROOT: NoteName.C}}, scale=song_testing.X)

    def test_a_clip_needs_a_pattern(self):
        self.assert_error(NEEDS_A_PATTERN, scenes=[{Section.TRACKS: {song_testing.LEAD: {ClipSlotSetting.LOOP: True}}}])

    def test_a_clip_cannot_come_from_another_track(self):
        # From is no setting of a clip, so it is passed over and the clip has no pattern.
        self.assert_error(NEEDS_A_PATTERN, scenes=[{Section.TRACKS: {song_testing.LEAD: {FROM: KICK}}}])

    def test_every_setting_has_a_default_so_an_empty_file_is_an_empty_song(self):
        for data in [None, {}]:
            song = render_data(data)
            self.assertEqual((song.get_tempo(), song.get_columns(), song.get_rows(), song.get_scale()), (120, [], [], None))

    def test_a_file_without_tempo_tracks_or_scenes_still_loads(self):
        data = {Section.PATTERNS: {A: pat([1, QUARTER])}, SongSetting.SCALE: C_MAJOR, Section.SCALES: {C_MAJOR: {ScaleSetting.ROOT: NoteName.C, ScaleSetting.TYPE: scale_type_name(ScaleType.MAJOR)}}}
        self.assertEqual(render_data(data).get_tempo(), 120)

    def test_the_description_and_the_notes_are_text(self):
        render_data({SetlistSetting.DESCRIPTION: 'A tune', SetlistSetting.NOTES: 'Two lines\nof notes\n'})
        with self.assertRaisesRegex(SongFileError, DESCRIPTION_MUST_BE_TEXT):
            song_from_data({SetlistSetting.DESCRIPTION: [A_LIST]})
        with self.assertRaisesRegex(SongFileError, NOTES_MUST_BE_TEXT):
            song_from_data({SetlistSetting.NOTES: [A_LIST]})

    def test_missing_file(self):
        with self.assertRaises(SongFileError):
            render_file('/no/such/file.yml')


class TestProtected(unittest.TestCase):

    def test_a_set_is_not_protected_unless_the_file_says_so(self):
        self.assertFalse(setlist_from_data(with_parts()).is_protected())
        self.assertTrue(setlist_from_data(with_parts(**{SetlistSetting.PROTECTED: True})).is_protected())

    def test_protected_must_be_true_or_false(self):
        for value in [1, 'yes', None]:
            with self.subTest(value=value), self.assertRaises(SongFileError) as raised:
                setlist_from_data(with_parts(**{SetlistSetting.PROTECTED: value}))
            self.assertIn(errors.ERR_PROTECTED_NOT_TRUE_OR_FALSE.format(value=value), str(raised.exception))


class TestTitleAndAuthor(unittest.TestCase):

    def test_they_are_optional_text(self):
        song_from_data(with_parts(title=RAIN, author=SOMEONE))
        song_from_data(with_parts())
        for key in [SetlistSetting.TITLE, SetlistSetting.AUTHOR]:
            with self.subTest(key=key), self.assertRaises(SongFileError):
                song_from_data(with_parts(**{key: 3}))

    def test_they_are_written_first(self):
        text = dump_song_data({SongSetting.TEMPO: 120, SetlistSetting.AUTHOR: SOMEONE, SetlistSetting.TITLE: 'Rain: Part 2', SceneSetting.TRACKS: {}, Section.SCENES: []})
        self.assertTrue(text.startswith('title: "Rain: Part 2"\nauthor: Someone\n\nsongs:\n'))
        self.assertEqual(yaml.safe_load(text)[SetlistSetting.TITLE], 'Rain: Part 2')
