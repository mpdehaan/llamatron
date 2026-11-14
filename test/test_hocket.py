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
"""The Hocket, the user's design of 2026-11-11: the tracks whose clips name it take turns at its source track's notes, one note each, left to right, the source playing its own pattern as ever."""

import unittest

from llamatron.composition.file_format import ClipSlotSetting, GeneratorKind, Restart, Row, SceneSetting, Section, TrackSetting
from llamatron.composition.generator_settings import HocketSetting
from llamatron.composition.song_file_error import SongFileError
from llamatron.exporters.timing import timed_events
from rendering import render_data, setlist_from_data
from test_registers import OCTAVE, pattern, song

TUNE = 'tune'
REST = 'rest'
OWN = 'own'
SHARE = 'share'
CHAIN = 'hocketing'
SOURCE = 'melody'
POOL = ['a', 'b', 'c']
# MIDI numbers of C major's degrees 1 to 5 in octave 5, which the melody plays.
C_MAJOR = [60, 62, 64, 65, 67]
CHORD = 'M'
TRIAD = 3


def hocket_data(*, melody, own=None, restart=None, scenes=1, source=SOURCE, source_chain=False, tracks=None):
    """Return a song's data: the source track plays the melody, a list of degrees or None for a rest, and each pool track runs the Hocket over a pattern of rests, or its own degrees."""
    steps = len(melody)
    figure = pattern(steps, **{Row.DEGREE: melody})
    rests = pattern(steps, **{Row.DEGREE: [None] * steps})
    patterns = {TUNE: figure, REST: rests}
    if own is not None:
        patterns[OWN] = pattern(steps, **{Row.DEGREE: own})
    names = tracks or [SOURCE, *POOL]
    clips = {SOURCE: {ClipSlotSetting.PATTERN: TUNE, **({ClipSlotSetting.CHAINS: [CHAIN]} if source_chain else {})}}
    for name in names:
        if name != SOURCE:
            clips[name] = {ClipSlotSetting.PATTERN: OWN if own is not None and name == POOL[0] else REST, ClipSlotSetting.CHAINS: [CHAIN]}
    data = song(patterns=patterns, scenes=[{SceneSetting.TRACKS: dict(clips)} for _ in range(scenes)], tracks=names)
    settings = {} if source is None else {HocketSetting.SOURCE: source}
    if restart is not None:
        settings[HocketSetting.RESTART] = restart
    data[Section.HOCKETS] = {SHARE: settings}
    data[Section.CHAINS] = {CHAIN: [{GeneratorKind.HOCKET: SHARE}]}
    return data


def pitches(data, *, scene=0):
    """Return the MIDI numbers each track plays in a scene, in time order, by the track, chords as lists."""
    grid = render_data(data)
    row = grid.get_rows()[scene]
    played = {}
    for column in grid.get_columns():
        clip = grid.get_clip(row=row, column=column)
        if clip is None:
            continue
        starts = {}
        for start, _, midi, _ in sorted(timed_events(clip=clip, scale=clip.get_scale())[0]):
            starts.setdefault(start, []).append(midi)
        played[column.get_name()] = [notes[0] if len(notes) == 1 else notes for notes in starts.values()]
    return played


class TestTurns(unittest.TestCase):

    def test_the_pool_takes_turns_left_to_right_and_goes_round(self):
        played = pitches(hocket_data(melody=[1, 2, 3, 4, 5]))
        self.assertEqual([played[name] for name in POOL], [[C_MAJOR[0], C_MAJOR[3]], [C_MAJOR[1], C_MAJOR[4]], [C_MAJOR[2]]])

    def test_the_source_plays_its_own_pattern_as_ever(self):
        self.assertEqual(pitches(hocket_data(melody=[1, 2, 3, 4, 5]))[SOURCE], C_MAJOR)

    def test_a_rest_passes_no_turn(self):
        played = pitches(hocket_data(melody=[1, None, 2, 3]))
        self.assertEqual([played[name] for name in POOL], [[C_MAJOR[0]], [C_MAJOR[1]], [C_MAJOR[2]]])

    def test_a_chord_passes_whole_to_one_track(self):
        data = hocket_data(melody=[1, 2])
        data[Section.PATTERNS][TUNE][Row.CHORD] = [CHORD, None]
        played = pitches(data)
        self.assertEqual(len(played[POOL[0]][0]), TRIAD, 'the whole triad goes to the first track')
        self.assertEqual(played[POOL[1]], [C_MAJOR[1]])

    def test_a_tracks_own_notes_play_besides_what_it_is_handed(self):
        played = pitches(hocket_data(melody=[1, None, 3, None], own=[None, 5, None, None]))
        self.assertEqual(played[POOL[0]], [C_MAJOR[0], C_MAJOR[4]])
        self.assertEqual(played[POOL[1]], [C_MAJOR[2]])

    def test_the_source_running_the_hocket_itself_takes_no_turn(self):
        played = pitches(hocket_data(melody=[1, 2, 3], source_chain=True))
        self.assertEqual(played[SOURCE], C_MAJOR[:3])
        self.assertEqual([played[name] for name in POOL], [[C_MAJOR[0]], [C_MAJOR[1]], [C_MAJOR[2]]])

    def test_a_muted_source_still_hands_out_its_notes(self):
        data = hocket_data(melody=[1, 2, 3])
        data[Section.TRACKS][SOURCE] = {TrackSetting.MUTE: True}
        self.assertEqual(pitches(data)[POOL[2]], [C_MAJOR[2]])

    def test_no_source_or_a_source_the_song_lacks_hands_out_nothing(self):
        for source in (None, 'nobody'):
            with self.subTest(source=source):
                played = pitches(hocket_data(melody=[1, 2, 3], source=source))
                self.assertEqual([played[name] for name in POOL], [[], [], []])


class TestRestart(unittest.TestCase):

    def test_every_clip_starts_each_scene_again_with_the_first_track(self):
        played = pitches(hocket_data(melody=[1, 2], scenes=2), scene=1)
        self.assertEqual([played[name] for name in POOL], [[C_MAJOR[0]], [C_MAJOR[1]], []])

    def test_whole_song_carries_the_turns_on(self):
        played = pitches(hocket_data(melody=[1, 2], scenes=2, restart=Restart.WHOLE_SONG), scene=1)
        self.assertEqual([played[name] for name in POOL], [[C_MAJOR[1]], [], [C_MAJOR[0]]])


class TestTheFile(unittest.TestCase):

    def test_renaming_the_source_track_renames_the_hockets_source(self):
        setlist = setlist_from_data(hocket_data(melody=[1, 2]))
        song = setlist.get_songs()[0]
        song.rename_item(section=Section.TRACKS, old=SOURCE, new=TUNE)
        self.assertEqual(setlist.get_generator_settings(kind=GeneratorKind.HOCKET, name=SHARE).get_source(), TUNE)

    def test_a_source_that_is_not_text_is_refused(self):
        data = hocket_data(melody=[1])
        data[Section.HOCKETS][SHARE] = {HocketSetting.SOURCE: OCTAVE}
        with self.assertRaises(SongFileError):
            setlist_from_data(data)
