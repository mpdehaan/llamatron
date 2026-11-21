# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Chains, arpeggiators and ratchet offsets as a song file uses them."""

from fractions import Fraction
import unittest

from llamatron.engine.generators.arp.generator import ChordOrder
from llamatron.engine.generators.arp.settings import ArpSetting, written_name
from llamatron.engine.generators.auto_ratchet.settings import AutoRatchetSetting
from llamatron.engine.timing import sounding
from llamatron.engine.timing.timing import timed_events
from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.schema.file_format import ClipSlotSetting, GeneratorKind, PatternSetting, Row, Section
from llamatron.model.values.note import Note, NoteName
from tests.support import song_testing
from tests.support.rendering import render_data
from tests.support.song_testing import clip, lead, pat, pitches, with_parts

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
            scenes=[{Section.TRACKS: {song_testing.LEAD: {ClipSlotSetting.PATTERN: A, ClipSlotSetting.CHAINS: [song_testing.X]}}}],
        ))

    def test_a_clip_slot_can_use_a_chain(self):
        song = self.song({song_testing.X: [{GeneratorKind.AUTO_RATCHET: TWICE}]})
        self.assertEqual(pitches(clip(song=song, scene=1, track=song_testing.LEAD)), [48, 48, 52, 52])

    def test_a_chain_applies_its_steps_in_order(self):
        song = self.song({song_testing.X: [{GeneratorKind.AUTO_RATCHET: TWICE}, {GeneratorKind.AUTO_RATCHET: SOME}]})
        self.assertEqual(pitches(clip(song=song, scene=1, track=song_testing.LEAD)), [48] * 4 + [52] * 4)

    def test_settings_must_be_in_their_own_section(self):
        with self.assertRaisesRegex(SongFileError, NO_ARP_CALLED):
            self.song({song_testing.X: [{GeneratorKind.ARP: {ArpSetting.STEP: HALF}}]})

    def test_only_arps_and_auto_ratchets_can_be_in_a_chain(self):
        for step in [BLEND, REPEATER, TAKE_RHYTHM, HOLD]:
            with self.subTest(step=step), self.assertRaisesRegex(SongFileError, UNKNOWN_GENERATOR):
                self.song({song_testing.X: [{step: TWICE}]})


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
        self.assertEqual([event.velocity for event in sorted(events)[:2]], [40, 40])
        self.assertEqual(sorted(events)[1].end, Fraction(1, 4) + sounding.GLIDE_OVERLAP)

    def test_is_a_whole_number(self):
        with self.assertRaises(SongFileError):
            lead([1, QUARTER], rows={Row.RATCHET_OFFSET: [song_testing.X]})


class TestArps(unittest.TestCase):

    def lead(self, chain=song_testing.X, **parts):
        scene = {Section.TRACKS: {song_testing.LEAD: {ClipSlotSetting.PATTERN: PATTERN_C, ClipSlotSetting.CHAINS: [chain]}}}
        data = with_parts(patterns={PATTERN_C: pat([1, 1], chord=[3]), PATTERN_D: pat([1, HALF], [3, HALF])}, scenes=[scene], **parts)
        return clip(song=render_data(data), scene=1, track=song_testing.LEAD)

    def test_a_chain_can_use_a_named_arp(self):
        found = self.lead(arps={BELLS: {ArpSetting.STEP: QUARTER, ArpSetting.ORDER: written_name(ChordOrder.UP)}}, chains={song_testing.X: [{GeneratorKind.ARP: BELLS}]})
        self.assertEqual(pitches(found), [48, 52, 55, 48])

    def test_an_arp_keeps_the_velocity(self):
        data = with_parts(
            patterns={PATTERN_C: pat([1, 1], chord=[3], velocity=[40])}, arps={BELLS: {ArpSetting.STEP: QUARTER}},
            chains={song_testing.X: [{GeneratorKind.ARP: BELLS}]}, scenes=[{Section.TRACKS: {song_testing.LEAD: {ClipSlotSetting.PATTERN: PATTERN_C, ClipSlotSetting.CHAINS: [song_testing.X]}}}],
        )
        events, _ = timed_events(clip=clip(song=render_data(data), scene=1, track=song_testing.LEAD), scale=None)
        self.assertEqual({event[3] for event in events}, {40})

    def test_a_chain_can_use_a_named_auto_ratchet(self):
        scene = {Section.TRACKS: {song_testing.LEAD: {ClipSlotSetting.PATTERN: PATTERN_D, ClipSlotSetting.CHAINS: [song_testing.X]}}}
        data = with_parts(patterns={PATTERN_D: pat([1, HALF], [3, HALF])}, scenes=[scene], auto_ratchets={ROLLS: {AutoRatchetSetting.COUNTS: [2]}}, chains={song_testing.X: [{GeneratorKind.AUTO_RATCHET: ROLLS}]})
        self.assertEqual(pitches(clip(song=render_data(data), scene=1, track=song_testing.LEAD)), [48, 48, 52, 52])

    def test_named_generators_run_in_chain_order(self):
        found = self.lead(
            arps={BELLS: {ArpSetting.STEP: HALF}}, auto_ratchets={ROLLS: {AutoRatchetSetting.COUNTS: [2]}},
            chains={song_testing.X: [{GeneratorKind.ARP: BELLS}, {GeneratorKind.AUTO_RATCHET: ROLLS}]},
        )
        self.assertEqual(pitches(found), [48, 48, 52, 52])

    def test_unknown_names_and_types_are_refused(self):
        for parts in [
            {Section.CHAINS: {song_testing.X: [{GeneratorKind.ARP: NOPE}]}},
            {Section.CHAINS: {song_testing.X: [{GeneratorKind.AUTO_RATCHET: NOPE}]}},
            {Section.CHAINS: {song_testing.X: [{HOLD: {LENGTH: '1/128'}}]}},
            {PAINT: [{ClipSlotSetting.CHAINS: [song_testing.X], Section.TRACKS: [song_testing.LEAD], Section.SCENES: [1]}]},
        ]:
            with self.subTest(parts=parts), self.assertRaises(SongFileError):
                self.lead(**parts)

    def test_a_setting_no_arp_has_is_passed_over(self):
        # A file from another version may hold one; the arp plays as it would without it.
        self.assertEqual(pitches(self.lead(arps={A: {WOBBLE: 1}}, chains={song_testing.X: [{GeneratorKind.ARP: A}]})), pitches(self.lead(arps={A: {}}, chains={song_testing.X: [{GeneratorKind.ARP: A}]})))
