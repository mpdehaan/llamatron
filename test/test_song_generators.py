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

"""Chains, arpeggiators and ratchet offsets as a song file uses them."""

import unittest
from fractions import Fraction

from llamatron.generators.arp import ChordOrder
from llamatron.music.note import Note, NoteName
from llamatron.exporters.timing import GLIDE_OVERLAP, timed_events
from rendering import render_data
from llamatron.composition.file_format import ClipSlotSetting, GeneratorKind, PatternSetting, Row, Section
from llamatron.composition.generator_settings import ArpSetting, AutoRatchetSetting, written_name
from llamatron.composition.song_file_error import SongFileError
from song_testing import LEAD, X, clip, lead, pat, pitches, with_parts

QUARTER = '1/4'
HALF = '1/2'
NOPE = 'nope'
PATTERN_D = 'd'
C_MINOR = 'C minor'
A = 'a'
BLEND = 'blend'
REPEATER = 'repeater'
TAKE_RHYTHM = 'take_rhythm'
HOLD = 'hold'
NO_ARP_CALLED = 'no arp called'
UNKNOWN_GENERATOR = 'unknown generator'
SLOW = 'slow'
TWICE = 'twice'
SOME = 'some'
PATTERN_C = 'c'
PAINT = 'paint'
BELLS = 'bells'
ROLLS = 'rolls'
WOBBLE = 'wobble'
LENGTH = 'length'


class TestChains(unittest.TestCase):

    def song(self, chains):
        return render_data(with_parts(
            arps={SLOW: {ArpSetting.STEP: HALF}}, auto_ratchets={TWICE: {AutoRatchetSetting.COUNTS: [2]}, SOME: {AutoRatchetSetting.COUNTS: [1, 3]}},
            chains=chains,
            scenes=[{Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: A, ClipSlotSetting.CHAIN: X}}}],
        ))

    def test_a_clip_slot_can_use_a_chain(self):
        song = self.song({X: [{GeneratorKind.AUTO_RATCHET: TWICE}]})
        self.assertEqual(pitches(clip(song=song, scene=1, track=LEAD)), [48, 48, 52, 52])

    def test_a_chain_applies_its_steps_in_order(self):
        song = self.song({X: [{GeneratorKind.AUTO_RATCHET: TWICE}, {GeneratorKind.AUTO_RATCHET: SOME}]})
        self.assertEqual(pitches(clip(song=song, scene=1, track=LEAD)), [48] * 4 + [52] * 4)

    def test_settings_must_be_in_their_own_section(self):
        with self.assertRaisesRegex(SongFileError, NO_ARP_CALLED):
            self.song({X: [{GeneratorKind.ARP: {ArpSetting.STEP: HALF}}]})

    def test_only_arps_and_auto_ratchets_can_be_in_a_chain(self):
        for step in [BLEND, REPEATER, TAKE_RHYTHM, HOLD]:
            with self.subTest(step=step), self.assertRaisesRegex(SongFileError, UNKNOWN_GENERATOR):
                self.song({X: [{step: TWICE}]})


class TestRatchetOffset(unittest.TestCase):

    def test_moves_each_slice_along_the_scale(self):
        found = lead([1, QUARTER], rows={Row.RATCHET: [4], Row.RATCHET_OFFSET: [1]})
        self.assertEqual(pitches(found), [48, 50, 52, 53])
        self.assertEqual(found.total_length(), Fraction(1, 4))

    def test_stays_in_the_scale_it_plays_in(self):
        found = lead([1, QUARTER], scale=C_MINOR, rows={Row.RATCHET: [4], Row.RATCHET_OFFSET: [1]})
        self.assertEqual(pitches(found), [48, 50, 51, 53])

    def test_can_go_down(self):
        found = lead([1, QUARTER], rows={Row.RATCHET: [3], Row.RATCHET_OFFSET: [-1]})
        self.assertEqual(sorted(pitches(found)), [45, 47, 48])
        self.assertEqual(found.get_notes()[1], Note(name=NoteName.B, octave_number=3, length=Fraction(1, 12)))

    def test_zero_or_no_ratchet_changes_nothing(self):
        self.assertEqual(pitches(lead([1, QUARTER], rows={Row.RATCHET: [2], Row.RATCHET_OFFSET: [0]})), [48, 48])
        self.assertEqual(pitches(lead([1, QUARTER], rows={Row.RATCHET_OFFSET: [5]})), [48])

    def test_a_chord_moves_as_a_whole(self):
        found = lead([1, QUARTER], rows={Row.RATCHET: [2], Row.RATCHET_OFFSET: [1], Row.CHORD: [3]})
        self.assertEqual(sorted(n.get_midi_number() for n in found.get_notes()[0].get_notes()), [48, 52, 55])
        self.assertEqual(sorted(n.get_midi_number() for n in found.get_notes()[1].get_notes()), [50, 53, 57])

    def test_a_drum_moves_by_half_steps(self):
        found = lead([NoteName.C, QUARTER], rows={PatternSetting.DRUM: True, Row.RATCHET: [3], Row.RATCHET_OFFSET: [1]})
        self.assertEqual(pitches(found), [36, 37, 38])

    def test_every_slice_keeps_its_velocity_and_only_the_last_glides(self):
        found = lead([1, QUARTER], [5, QUARTER], rows={Row.RATCHET: [2, None], Row.RATCHET_OFFSET: [1, None], Row.VELOCITY: [40, None], Row.GLIDE: [True, False]})
        events, _ = timed_events(clip=found, scale=None)
        self.assertEqual([event[3] for event in sorted(events)[:2]], [40, 40])
        self.assertEqual(sorted(events)[1][1], Fraction(1, 4) + GLIDE_OVERLAP)

    def test_is_a_whole_number(self):
        with self.assertRaises(SongFileError):
            lead([1, QUARTER], rows={Row.RATCHET_OFFSET: [X]})


class TestArps(unittest.TestCase):

    def lead(self, chain=X, **parts):
        scene = {Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: PATTERN_C, ClipSlotSetting.CHAIN: chain}}}
        data = with_parts(patterns={PATTERN_C: pat([1, 1], chord=[3]), PATTERN_D: pat([1, HALF], [3, HALF])}, scenes=[scene], **parts)
        return clip(song=render_data(data), scene=1, track=LEAD)

    def test_a_chain_can_use_a_named_arp(self):
        found = self.lead(arps={BELLS: {ArpSetting.STEP: QUARTER, ArpSetting.ORDER: written_name(ChordOrder.UP)}}, chains={X: [{GeneratorKind.ARP: BELLS}]})
        self.assertEqual(pitches(found), [48, 52, 55, 48])

    def test_an_arp_keeps_the_velocity(self):
        data = with_parts(
            patterns={PATTERN_C: pat([1, 1], chord=[3], velocity=[40])}, arps={BELLS: {ArpSetting.STEP: QUARTER}},
            chains={X: [{GeneratorKind.ARP: BELLS}]}, scenes=[{Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: PATTERN_C, ClipSlotSetting.CHAIN: X}}}],
        )
        events, _ = timed_events(clip=clip(song=render_data(data), scene=1, track=LEAD), scale=None)
        self.assertEqual({event[3] for event in events}, {40})

    def test_a_chain_can_use_a_named_auto_ratchet(self):
        scene = {Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: PATTERN_D, ClipSlotSetting.CHAIN: X}}}
        data = with_parts(patterns={PATTERN_D: pat([1, HALF], [3, HALF])}, scenes=[scene], auto_ratchets={ROLLS: {AutoRatchetSetting.COUNTS: [2]}}, chains={X: [{GeneratorKind.AUTO_RATCHET: ROLLS}]})
        self.assertEqual(pitches(clip(song=render_data(data), scene=1, track=LEAD)), [48, 48, 52, 52])

    def test_named_generators_run_in_chain_order(self):
        found = self.lead(
            arps={BELLS: {ArpSetting.STEP: HALF}}, auto_ratchets={ROLLS: {AutoRatchetSetting.COUNTS: [2]}},
            chains={X: [{GeneratorKind.ARP: BELLS}, {GeneratorKind.AUTO_RATCHET: ROLLS}]},
        )
        self.assertEqual(pitches(found), [48, 48, 52, 52])

    def test_unknown_names_and_types_are_refused(self):
        for parts in [
            {Section.CHAINS: {X: [{GeneratorKind.ARP: NOPE}]}},
            {Section.CHAINS: {X: [{GeneratorKind.AUTO_RATCHET: NOPE}]}},
            {Section.CHAINS: {X: [{HOLD: {LENGTH: '1/128'}}]}},
            {PAINT: [{ClipSlotSetting.CHAIN: X, Section.TRACKS: [LEAD], Section.SCENES: [1]}]},
        ]:
            with self.subTest(parts=parts), self.assertRaises(SongFileError):
                self.lead(**parts)

    def test_a_bad_setting_names_the_problem(self):
        with self.assertRaises(SongFileError):
            self.lead(arps={A: {WOBBLE: 1}}, chains={X: [{GeneratorKind.ARP: A}]})
