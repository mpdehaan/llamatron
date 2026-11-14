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
"""Grooves: what a file can hold, the factory grooves, and how a groove moves notes and CC values at export."""

import os
import tempfile
import unittest
from fractions import Fraction

import mido

from llamatron.composition.defaults import DEFAULT_GROOVE_CELL_LENGTH
from llamatron.composition.file_format import ClipSlotSetting, GrooveSetting, PatternSetting, Row, SceneSetting, Section, SongSetting, TrackSetting
from llamatron.composition.groove import FACTORY_GROOVE_NAMES, FactoryGroove, Groove, GROOVE_CELLS, PUSH_AMOUNT, STRAIGHT, new_groove
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.limits import MAX_GROOVE_AMOUNT, MAX_GROOVE_CELLS, MIN_GROOVE_AMOUNT
from llamatron.composition.setlist import Setlist
from llamatron.composition.song_file_error import SongFileError
from llamatron.exporters.clip_tree import MIDI_SUFFIX
from llamatron.exporters.midi_arrangement import MidiSong
from llamatron.exporters.timing import control_events, timed_events
from llamatron.support.rational import Rational
from rendering import render_data, song_from_data
from song_testing import LEAD, X, clip, pat, with_parts

SIXTEENTH = Fraction(1, 16)
EIGHTH = Fraction(1, 8)
# A swing of 58 delays every second 16th by 16% of a 16th.
SWING_58_DELAY = Fraction(16, 100) * SIXTEENTH
# A swing of 66 on 8ths delays every second 8th by 32% of an 8th.
EIGHTH_SWING_66_DELAY = Fraction(32, 100) * EIGHTH
SWING_58_AMOUNT = 16
LATE = 'late'
EARLY = 'early'
DRUMS = 'drums'
ONE_CELL_IN_THREE = 3
MOD_WHEEL = 1
CC_VALUE = 64
# A full bar of 16ths, each a degree of the scale.
A_BAR_OF_SIXTEENTHS = [(1, SIXTEENTH)] * GROOVE_CELLS
# Playing one note every quarter: four steps of 16ths, the first with a note.
QUARTER_STEPS = [(1, SIXTEENTH), (None, SIXTEENTH), (None, SIXTEENTH), (None, SIXTEENTH)]
TOO_LONG = '2'
NOT_A_WHOLE_NUMBER = 1.5
# mido's name for a note on message.
MIDO_NOTE_ON = 'note_on'


def groove_song(*, cells, cell_length=None, song_groove=None, scene_groove=None, track_groove=None, steps=A_BAR_OF_SIXTEENTHS, **parts):
    """Return a song playing steps on the lead track with a groove called late, chosen where the arguments say."""
    groove = {GrooveSetting.CELLS: cells}
    if cell_length is not None:
        groove[GrooveSetting.CELL_LENGTH] = cell_length
    cell = {ClipSlotSetting.PATTERN: X}
    scene = {Section.TRACKS: {LEAD: cell}}
    if scene_groove is not None:
        scene[SceneSetting.GROOVE] = scene_groove
    tracks = {LEAD: {} if track_groove is None else {TrackSetting.GROOVE: track_groove}, **parts.pop(Section.TRACKS, {})}
    data = with_parts(patterns={X: pat(*steps)}, grooves={LATE: groove}, tracks=tracks, scenes=[scene], **parts)
    if song_groove is not None:
        data[SongSetting.GROOVE] = song_groove
    return data


def onsets(a_clip):
    """Return when each note of a clip starts, in order."""
    return [Fraction(event.start) for event in sorted(timed_events(clip=a_clip, scale=a_clip.get_scale())[0])]


def lead_clip(data):
    return clip(song=render_data(data), scene=1, track=LEAD)


class TestGrooveFiles(unittest.TestCase):
    """What a file's grooves section can hold, and what refuses to load."""

    def test_a_groove_reads_and_writes_its_cells_and_cell_length(self):
        groove = Groove.from_data(data={GrooveSetting.CELLS: [0, SWING_58_AMOUNT], GrooveSetting.CELL_LENGTH: '1/8'}, where=LATE)
        self.assertEqual(groove.get_cells(), [0, SWING_58_AMOUNT])
        self.assertEqual(groove.get_cell_length(), Rational(1, 8))
        self.assertEqual(groove.to_data(), {GrooveSetting.CELLS: [0, SWING_58_AMOUNT], GrooveSetting.CELL_LENGTH: '1/8'})
        plain = Groove.from_data(data={GrooveSetting.CELLS: [0]}, where=LATE)
        self.assertEqual(plain.get_cell_length_text(), DEFAULT_GROOVE_CELL_LENGTH)
        self.assertEqual(plain.to_data(), {GrooveSetting.CELLS: [0]})

    def test_bad_grooves_are_refused(self):
        for data in [
            [0, 1], {}, {GrooveSetting.CELLS: []}, {GrooveSetting.CELLS: [MAX_GROOVE_AMOUNT + 1]}, {GrooveSetting.CELLS: [MIN_GROOVE_AMOUNT - 1]},
            {GrooveSetting.CELLS: [NOT_A_WHOLE_NUMBER]}, {GrooveSetting.CELLS: [0] * (MAX_GROOVE_CELLS + 1)},
            {GrooveSetting.CELLS: [0], GrooveSetting.CELL_LENGTH: TOO_LONG}, {GrooveSetting.CELLS: [0], LATE: 1},
        ]:
            with self.subTest(data=data), self.assertRaises(SongFileError):
                Groove.from_data(data=data, where=LATE)

    def test_a_groove_cannot_take_a_factory_name_and_a_choice_must_exist(self):
        with self.assertRaises(SongFileError):
            song_from_data(with_parts(grooves={FactoryGroove.SWING_58: {GrooveSetting.CELLS: [0]}}))
        for setting in [{SongSetting.GROOVE: EARLY}, {SongSetting.GROOVE: False}]:
            with self.subTest(setting=setting), self.assertRaises(SongFileError):
                song_from_data(with_parts(**setting))
        with self.assertRaises(SongFileError):
            song_from_data(with_parts(tracks={LEAD: {TrackSetting.GROOVE: EARLY}}))
        with self.assertRaises(SongFileError):
            song_from_data(with_parts(tracks={LEAD: {TrackSetting.GROOVE: True}}))
        with self.assertRaises(SongFileError):
            song_from_data(with_parts(scenes=[{SceneSetting.GROOVE: EARLY}]))

    def test_every_set_has_the_factory_grooves_and_can_add_its_own(self):
        setlist = Setlist.new()
        self.assertEqual(setlist.get_groove_names(), FACTORY_GROOVE_NAMES)
        self.assertEqual(setlist.get_own_groove_names(), [])
        self.assertTrue(setlist.get_groove(FactoryGroove.NONE).is_straight())
        self.assertFalse(setlist.get_groove(FactoryGroove.SWING_58).is_straight())
        self.assertEqual(setlist.get_groove(FactoryGroove.SWING_58).get_cells(), [STRAIGHT, SWING_58_AMOUNT] * (GROOVE_CELLS // 2))
        self.assertEqual(setlist.get_groove(FactoryGroove.EIGHTH_SWING_66).get_cell_length(), Rational(1, 8))
        self.assertEqual(setlist.get_groove(FactoryGroove.PUSH).get_cells()[1], PUSH_AMOUNT)
        setlist.add_item(section=Section.GROOVES, name=LATE, item=new_groove())
        self.assertEqual(setlist.get_groove_names(), [*FACTORY_GROOVE_NAMES, LATE])
        with self.assertRaises(InvalidValue):
            setlist.add_item(section=Section.GROOVES, name=FactoryGroove.PUSH, item=new_groove())
        with self.assertRaises(InvalidValue):
            setlist.rename_item(section=Section.GROOVES, old=LATE, new=FactoryGroove.NONE)
        self.assertNotIn(Section.GROOVES, Setlist.new().to_data())
        self.assertEqual(setlist.to_data()[Section.GROOVES], {LATE: new_groove().to_data()})

    def test_a_factory_groove_cannot_be_changed_through_the_set(self):
        setlist = Setlist.new()
        setlist.get_groove(FactoryGroove.SWING_58).set_cell(step=0, amount=MAX_GROOVE_AMOUNT)
        self.assertEqual(setlist.get_groove(FactoryGroove.SWING_58).get_cells()[0], STRAIGHT)

    def test_editing_a_groove_checks_its_cells(self):
        groove = new_groove()
        groove.set_cell(step=1, amount=MAX_GROOVE_AMOUNT)
        self.assertEqual(groove.get_cells()[1], MAX_GROOVE_AMOUNT)
        with self.assertRaises(InvalidValue):
            groove.set_cell(step=1, amount=MAX_GROOVE_AMOUNT + 1)
        with self.assertRaises(InvalidValue):
            groove.set_cell(step=GROOVE_CELLS, amount=0)
        groove.insert_cell(0)
        self.assertEqual(len(groove.get_cells()), GROOVE_CELLS + 1)
        for _ in range(MAX_GROOVE_CELLS):
            groove.insert_cell(0)
        self.assertEqual(len(groove.get_cells()), MAX_GROOVE_CELLS)
        for _ in range(MAX_GROOVE_CELLS):
            groove.remove_cell(0)
        self.assertEqual(len(groove.get_cells()), 1)
        groove.set_cell_length('1/8')
        self.assertEqual(groove.get_cell_length(), Rational(1, 8))
        groove.set_cell_length(DEFAULT_GROOVE_CELL_LENGTH)
        self.assertNotIn(GrooveSetting.CELL_LENGTH, groove.to_data())
        with self.assertRaises(InvalidValue):
            groove.set_cell_length(TOO_LONG)


class TestGrooveTiming(unittest.TestCase):
    """How a groove moves notes and CC values when a song is exported."""

    def test_swing_delays_every_second_sixteenth_and_keeps_the_gate(self):
        a_clip = lead_clip(groove_song(cells=[0, SWING_58_AMOUNT], song_groove=LATE))
        self.assertEqual(onsets(a_clip), [place * SIXTEENTH + (SWING_58_DELAY if place % 2 else 0) for place in range(GROOVE_CELLS)])
        events, _ = timed_events(clip=a_clip, scale=a_clip.get_scale())
        # Every note keeps its gate, except the last, which the end of the clip cuts as it always does.
        *within, last = sorted(events)
        for event in within:
            self.assertEqual(Fraction(event.end - event.start), SIXTEENTH)
        self.assertEqual(Fraction(last.end), 1)

    def test_the_factory_swings_match_their_percentages(self):
        a_clip = lead_clip(groove_song(cells=[0], song_groove=FactoryGroove.SWING_58))
        self.assertEqual(onsets(a_clip)[1], SIXTEENTH + SWING_58_DELAY)
        steps = [(1, EIGHTH)] * (GROOVE_CELLS // 2)
        a_clip = lead_clip(groove_song(cells=[0], song_groove=FactoryGroove.EIGHTH_SWING_66, steps=steps))
        self.assertEqual(onsets(a_clip)[:3], [0, EIGHTH + EIGHTH_SWING_66_DELAY, 2 * EIGHTH])

    def test_a_push_plays_early_and_never_before_the_start(self):
        a_clip = lead_clip(groove_song(cells=[PUSH_AMOUNT], song_groove=LATE))
        starts = onsets(a_clip)
        self.assertEqual(starts[0], 0)
        self.assertEqual(starts[1], SIXTEENTH + Fraction(PUSH_AMOUNT, 100) * SIXTEENTH)

    def test_the_groove_follows_time_not_steps(self):
        # Notes a quarter apart land on cells 0, 4, 8 and 12 of a 16-cell groove, whatever the pattern's steps.
        cells = [0] * GROOVE_CELLS
        cells[4] = SWING_58_AMOUNT
        a_clip = lead_clip(groove_song(cells=cells, song_groove=LATE, steps=QUARTER_STEPS * 4))
        self.assertEqual(onsets(a_clip), [0, Fraction(1, 4) + SWING_58_DELAY, Fraction(1, 2), Fraction(3, 4)])

    def test_the_row_repeats_its_own_length(self):
        a_clip = lead_clip(groove_song(cells=[0, 0, SWING_58_AMOUNT], song_groove=LATE))
        late = [place for place, start in enumerate(onsets(a_clip)) if start != place * SIXTEENTH]
        self.assertEqual(late, [place for place in range(GROOVE_CELLS) if place % ONE_CELL_IN_THREE == 2])

    def test_cc_values_move_with_their_steps(self):
        rows = {Row.CC1: [CC_VALUE] * GROOVE_CELLS}
        data = groove_song(cells=[0, SWING_58_AMOUNT], song_groove=LATE, tracks={LEAD: {TrackSetting.CC: [MOD_WHEEL, None, None, None]}})
        data[Section.PATTERNS][X].update(rows)
        a_clip = lead_clip(data)
        times = [Fraction(event.time) for event in control_events(clip=a_clip, length=Rational(1))]
        self.assertEqual(times[:2], [0, SIXTEENTH + SWING_58_DELAY])

    def test_the_track_wins_then_the_scene_then_the_song_and_false_switches_grooving_off(self):
        swung = [0, SWING_58_AMOUNT]
        straight = [place * SIXTEENTH for place in range(GROOVE_CELLS)]
        swung_onsets = onsets(lead_clip(groove_song(cells=swung, song_groove=LATE)))
        self.assertNotEqual(swung_onsets, straight)
        # The scene's choice beats the song's, and the track's beats the scene's.
        self.assertEqual(onsets(lead_clip(groove_song(cells=swung, song_groove=LATE, scene_groove=FactoryGroove.NONE))), straight)
        self.assertEqual(onsets(lead_clip(groove_song(cells=swung, scene_groove=LATE))), swung_onsets)
        self.assertEqual(onsets(lead_clip(groove_song(cells=swung, scene_groove=LATE, track_groove=FactoryGroove.NONE))), straight)
        self.assertEqual(onsets(lead_clip(groove_song(cells=swung, track_groove=LATE))), swung_onsets)
        # A false anywhere switches grooving off, whatever else is chosen.
        self.assertEqual(onsets(lead_clip(groove_song(cells=swung, track_groove=LATE, scene_groove=False))), straight)
        self.assertEqual(onsets(lead_clip(groove_song(cells=swung, scene_groove=LATE, track_groove=False))), straight)
        self.assertEqual(onsets(lead_clip(groove_song(cells=swung, song_groove=LATE, track_groove=False))), straight)
        # With nothing chosen anywhere, the song's default is none.
        self.assertEqual(onsets(lead_clip(groove_song(cells=swung))), straight)

    def test_a_grab_reads_the_other_track_where_the_grid_puts_it(self):
        # The lead is swung; the drums grab from it on every step and must get the same pitches
        # as from a straight lead, since grooves only move timing.
        def grabbed(cells):
            grab = {PatternSetting.STEPS: GROOVE_CELLS, Row.GRAB: [True] * GROOVE_CELLS, Row.DEGREE: [1] * GROOVE_CELLS}
            data = groove_song(cells=cells, song_groove=LATE, steps=[(degree, SIXTEENTH) for degree in [1, 2, 3, 4] * 4])
            data[Section.PATTERNS][EARLY] = grab
            data[Section.TRACKS][DRUMS] = {TrackSetting.GROOVE: False}
            data[Section.SCENES][0][Section.TRACKS][DRUMS] = {ClipSlotSetting.PATTERN: EARLY, ClipSlotSetting.GRAB_TRACK: LEAD}
            song = render_data(data)
            drums = clip(song=song, scene=1, track=DRUMS)
            return [event.midi_number for event in sorted(timed_events(clip=drums, scale=drums.get_scale())[0])]
        self.assertEqual(grabbed([0, MAX_GROOVE_AMOUNT]), grabbed([0]))

    def test_a_grooved_song_exports_to_midi(self):
        grid = render_data(groove_song(cells=[0, SWING_58_AMOUNT], song_groove=LATE))
        with tempfile.TemporaryDirectory() as folder:
            directory = os.path.join(folder, LATE)
            MidiSong(directory=directory, grid=grid).export()
            midi = mido.MidiFile(os.path.join(directory, LATE + MIDI_SUFFIX))
            starts = []
            for track in midi.tracks:
                tick = 0
                for message in track:
                    tick += message.time
                    if message.type == MIDO_NOTE_ON:
                        starts.append(tick)
        self.assertEqual(starts[1] - starts[0], round(midi.ticks_per_beat * 4 * (SIXTEENTH + SWING_58_DELAY)))

