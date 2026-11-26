# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A built-in instrument in the set (model/objects/instrument.py, built_in_sound.py, sound_parts.py and engine_presets.py): its
kind and role, a MIDI instrument's latency, its sound as parts with their engine preset's and their types' defaults and
refusals, kept through writing and reading, and its sound as the Synthesis Process compiles it."""

import unittest

from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects import built_in_sound, engine_presets, sound_parts
from llamatron.model.objects.instrument import Instrument
from llamatron.model.objects.setlist import Setlist
from llamatron.model.schema import defaults, limits
from llamatron.model.schema.file_format import DrumMachine, Effect, EffectSetting, EnvelopeType, FilterType, InstrumentKind, InstrumentRole, InstrumentSetting, OscillatorSetting, OscillatorType, PartSetting, Section, SoundEngine, SoundPart, SoundSetting, Waveform

WHERE = 'instruments'
LATENCY_MS = 12
ATTACK_MS = 400
CHOKE = 1
KNOBS = [30, 64, 64, 40, 60]
DRIVE_PERCENT = 40
BITS = 6
KNOB_PLACE = 2
DEVICE = 'IAC Driver Bus 1'
SONG = 'song'
KIT = 'kit'
KEYS = 'keys'
DRUMS = 'drums'
CHORDS = 'chords'


class TestBuiltInSound(unittest.TestCase):

    def test_an_instrument_is_midi_until_made_built_in_and_its_latency_starts_at_zero(self):
        instrument = Instrument()
        self.assertEqual(instrument.get_kind(), InstrumentKind.MIDI)
        instrument.set_kind(InstrumentKind.OFF)
        self.assertEqual(instrument.get_kind(), InstrumentKind.OFF)
        self.assertFalse(instrument.is_built_in())
        self.assertFalse(instrument.is_built_in())
        self.assertEqual(instrument.get_latency(), defaults.DEFAULT_INSTRUMENT_LATENCY)
        instrument.set_kind(InstrumentKind.BUILT_IN)
        instrument.set_latency(LATENCY_MS)
        self.assertTrue(instrument.is_built_in())
        self.assertEqual(instrument.get_latency(), LATENCY_MS)

    def test_a_sound_setting_left_out_reads_as_its_presets_and_one_out_of_range_or_of_another_type_is_refused(self):
        instrument = Instrument(kind=InstrumentKind.BUILT_IN)
        self.assertEqual(instrument.get_sound(SoundSetting.ENGINE), SoundEngine.BASIC)
        self.assertEqual(instrument.get_sound(SoundSetting.VOICES), defaults.DEFAULT_VOICES)
        instrument.set_part_setting(part=SoundPart.ENV1, name=PartSetting.ATTACK, value=ATTACK_MS)
        self.assertEqual(instrument.get_part_setting(part=SoundPart.ENV1, name=PartSetting.ATTACK), ATTACK_MS)
        with self.assertRaises(InvalidValue):
            instrument.set_sound(name=SoundSetting.VOICES, value=limits.MAX_VOICES + 1)
        with self.assertRaises(InvalidValue):
            instrument.set_part_setting(part=SoundPart.OSCILLATORS, name=PartSetting.KNOBS, value=KNOBS)
        with self.assertRaises(InvalidValue):
            instrument.set_part_setting(part=SoundPart.OSCILLATORS, name=PartSetting.OSCILLATORS, value=[{OscillatorSetting.WAVEFORM: Waveform.SAW}] * (limits.MAX_OSCILLATORS + 1))

    def test_an_engine_fills_every_part_and_a_swapped_part_is_its_presets_or_its_types_defaults(self):
        instrument = Instrument(kind=InstrumentKind.BUILT_IN)
        instrument.set_engine(SoundEngine.FISHLINE)
        self.assertEqual(instrument.get_part_type(SoundPart.FILTER), FilterType.DIODE)
        self.assertEqual(instrument.get_part_setting(part=SoundPart.FILTER, name=PartSetting.CUTOFF), defaults.DEFAULT_ACID_CUTOFF)
        instrument.set_part_type(part=SoundPart.FILTER, kind=FilterType.LADDER)
        self.assertEqual(instrument.get_part_setting(part=SoundPart.FILTER, name=PartSetting.CUTOFF), sound_parts.TYPE_DEFAULTS[FilterType.LADDER][PartSetting.CUTOFF])
        instrument.set_part_type(part=SoundPart.FILTER, kind=FilterType.DIODE)
        self.assertEqual(instrument.get_part_setting(part=SoundPart.FILTER, name=PartSetting.CUTOFF), defaults.DEFAULT_ACID_CUTOFF)
        instrument.set_part_type(part=SoundPart.ENV2, kind=EnvelopeType.VACTROL)
        self.assertEqual([instrument.get_part_type(part) for part in (SoundPart.ENV1, SoundPart.ENV2)], [EnvelopeType.ACID_GATE, EnvelopeType.VACTROL])
        instrument.set_engine(SoundEngine.BASIC)
        self.assertEqual(instrument.get_part_type(SoundPart.ENV2), engine_presets.preset_part(engine=SoundEngine.BASIC, part=SoundPart.ENV2)[PartSetting.TYPE])

    def test_a_role_left_out_is_percussion_for_a_drum_machine_and_normal_otherwise(self):
        drum = Instrument(kind=InstrumentKind.BUILT_IN)
        drum.set_engine(SoundEngine.DRUM)
        self.assertEqual(drum.get_role(), InstrumentRole.PERCUSSION)
        self.assertEqual(Instrument().get_role(), InstrumentRole.NORMAL)
        chosen = Instrument(role=InstrumentRole.PERCUSSION)
        self.assertEqual(Instrument.from_data(data=chosen.to_data(), where=WHERE).get_role(), InstrumentRole.PERCUSSION)

    def test_an_instrument_read_with_no_role_is_percussion_where_only_drum_tracks_play_it(self):
        setlist = Setlist()
        song = setlist.add_new_song(SONG)
        for instrument in (KIT, KEYS):
            setlist.add_new_instrument(instrument)
        song.add_new_track(name=DRUMS, drum=True).set_instrument_name(name=KIT, song=song)
        song.add_new_track(name=CHORDS).set_instrument_name(name=KEYS, song=song)
        data = setlist.to_data()
        for instrument in data[Section.INSTRUMENTS].values():
            del instrument[InstrumentSetting.ROLE]
        read = Setlist.from_data(data=data)
        self.assertEqual([read.get_instrument(name).get_role() for name in (KIT, KEYS)], [InstrumentRole.PERCUSSION, InstrumentRole.NORMAL])
        # Opening a file never changes it: the role settled is not written.
        self.assertNotIn(InstrumentSetting.ROLE, read.get_instrument(KIT).to_data())

    def test_a_built_in_instrument_is_kept_through_writing_and_reading(self):
        instrument = Instrument(kind=InstrumentKind.BUILT_IN)
        instrument.set_engine(SoundEngine.DRUM)
        instrument.set_part_setting(part=SoundPart.OSCILLATORS, name=PartSetting.MACHINE, value=DrumMachine.SYNTH_KICK)
        instrument.set_part_setting(part=SoundPart.OSCILLATORS, name=PartSetting.KNOBS, value=KNOBS)
        data = instrument.to_data()
        again = Instrument.from_data(data=data, where=WHERE)
        self.assertEqual(again.to_data(), data)
        self.assertEqual(again.copy().to_data(), data)
        self.assertEqual(data[InstrumentSetting.KIND], InstrumentKind.BUILT_IN)

    def test_a_sound_is_given_to_the_synthesis_process_in_seconds_and_fractions(self):
        drum = {SoundSetting.ENGINE: SoundEngine.DRUM, SoundSetting.OSCILLATORS: {PartSetting.TYPE: OscillatorType.DRUM, PartSetting.MACHINE: DrumMachine.HATS,
                                                                                PartSetting.CHOKE: CHOKE}}
        spec = built_in_sound.synth_spec(drum)
        drum_part = spec['oscillators']
        self.assertEqual((drum_part['machine'], drum_part['choke'], spec['volume']), (DrumMachine.HATS, CHOKE, defaults.DEFAULT_SOUND_VOLUME / 100))
        basic_part = {PartSetting.TYPE: OscillatorType.BASIC, PartSetting.OSCILLATORS: [{OscillatorSetting.WAVEFORM: Waveform.SAW}, {}]}
        attack = {PartSetting.TYPE: EnvelopeType.ADSR, PartSetting.ATTACK: ATTACK_MS}
        quiet = engine_presets.QUIET
        basic = built_in_sound.synth_spec({SoundSetting.OSCILLATORS: basic_part, SoundSetting.ENVELOPES: [attack, quiet, quiet]})
        self.assertEqual(basic['envelopes'][0]['attack'], ATTACK_MS / 1000)
        # An oscillator left off, as the second is, does not sound.
        self.assertEqual(basic['oscillators']['oscillators'], [[Waveform.SAW, 0, 1.0]])

    def test_a_sounds_effect_blocks_reach_the_synthesis_process_in_order_the_empty_left_out(self):
        blocks = [{EffectSetting.EFFECT: Effect.DRIVE, EffectSetting.AMOUNT: DRIVE_PERCENT}, {}, {EffectSetting.EFFECT: Effect.BITCRUSH, EffectSetting.BITS: BITS}]
        spec = built_in_sound.synth_spec({SoundSetting.EFFECTS: blocks})
        kinds = [(effect[EffectSetting.EFFECT], effect[EffectSetting.AMOUNT], effect[EffectSetting.BITS]) for effect in spec['effects']]
        self.assertEqual(kinds, [(Effect.DRIVE, DRIVE_PERCENT / 100, defaults.DEFAULT_CRUSH_BITS), (Effect.BITCRUSH, defaults.DEFAULT_DRIVE_AMOUNT / 100, BITS)])
        self.assertEqual(spec['effects'][0][EffectSetting.MIX], defaults.DEFAULT_MIX / 100)
        with self.assertRaises(InvalidValue):
            Instrument(kind=InstrumentKind.BUILT_IN).set_sound(name=SoundSetting.EFFECTS, value=[{}] * (limits.EFFECT_BLOCKS + 1))

    def test_oscillators_knobs_and_effect_blocks_are_set_one_at_a_time_the_ones_before_made(self):
        instrument = Instrument(kind=InstrumentKind.BUILT_IN)
        drum = Instrument(kind=InstrumentKind.BUILT_IN)
        drum.set_engine(SoundEngine.DRUM)
        drum.set_knob(place=KNOB_PLACE, value=KNOBS[0])
        self.assertEqual(drum.get_knob(KNOB_PLACE), KNOBS[0])
        instrument.set_oscillator(number=limits.MAX_OSCILLATORS, name=OscillatorSetting.WAVEFORM, value=Waveform.SQUARE)
        self.assertEqual(instrument.get_oscillator(number=2, name=OscillatorSetting.WAVEFORM), Waveform.OFF)
        self.assertEqual(instrument.get_oscillator(number=limits.MAX_OSCILLATORS, name=OscillatorSetting.WAVEFORM), Waveform.SQUARE)
        instrument.set_effect(number=limits.EFFECT_BLOCKS, name=EffectSetting.EFFECT, value=Effect.DRIVE)
        self.assertEqual(instrument.get_effect(number=1, name=EffectSetting.EFFECT), Effect.NONE)
        self.assertEqual(len(instrument.get_sound(SoundSetting.EFFECTS)), limits.EFFECT_BLOCKS)

    def test_a_new_instrument_is_off_and_plays_through_its_device_only_once_it_is_midi(self):
        setlist = Setlist()
        instrument = setlist.add_new_instrument(WHERE)
        self.assertEqual(instrument.get_kind(), InstrumentKind.OFF)
        instrument.set_device(DEVICE)
        self.assertEqual(instrument.get_kind(), InstrumentKind.OFF)
        self.assertFalse(instrument.has_device())
        instrument.set_kind(InstrumentKind.MIDI)
        self.assertTrue(instrument.has_device())
        instrument.set_kind(InstrumentKind.BUILT_IN)
        self.assertFalse(instrument.has_device())
        self.assertEqual(instrument.get_device(), DEVICE)

    def test_a_chip_engine_plays_one_note_at_once_unless_it_says_otherwise(self):
        self.assertEqual(built_in_sound.sound_value(sound={SoundSetting.ENGINE: SoundEngine.SID}, name=SoundSetting.VOICES), 1)
        self.assertEqual(built_in_sound.sound_value(sound={}, name=SoundSetting.VOICES), defaults.DEFAULT_VOICES)
