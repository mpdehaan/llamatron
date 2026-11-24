# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A built-in instrument in the set (model/objects/instrument.py and built_in_sound.py): its kind, a MIDI instrument's
latency, its sound's settings with their defaults and refusals, kept through writing and reading, and its sound as the
Synthesis Process compiles it."""

import unittest

from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects import built_in_sound
from llamatron.model.objects.instrument import Instrument
from llamatron.model.schema import defaults, limits
from llamatron.model.schema.file_format import DrumMachine, Effect, EffectSetting, InstrumentKind, InstrumentSetting, OscillatorSetting, SoundEngine, SoundSetting, Waveform

WHERE = 'instruments'
LATENCY_MS = 12
ATTACK_MS = 400
CHOKE = 1
KNOBS = [30, 64, 64, 40, 60]
DRIVE_PERCENT = 40
BITS = 6


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

    def test_a_sound_setting_left_out_reads_as_its_default_and_one_out_of_range_is_refused(self):
        instrument = Instrument(kind=InstrumentKind.BUILT_IN)
        self.assertEqual(instrument.get_sound(SoundSetting.ENGINE), SoundEngine.BASIC)
        self.assertEqual(instrument.get_sound(SoundSetting.VOICES), defaults.DEFAULT_VOICES)
        instrument.set_sound(name=SoundSetting.ATTACK, value=ATTACK_MS)
        self.assertEqual(instrument.get_sound(SoundSetting.ATTACK), ATTACK_MS)
        with self.assertRaises(InvalidValue):
            instrument.set_sound(name=SoundSetting.VOICES, value=limits.MAX_VOICES + 1)
        with self.assertRaises(InvalidValue):
            instrument.set_sound(name=SoundSetting.KNOBS, value=KNOBS[:limits.KNOB_COUNT - 1])
        with self.assertRaises(InvalidValue):
            instrument.set_sound(name=SoundSetting.OSCILLATORS, value=[{OscillatorSetting.WAVEFORM: Waveform.SAW}] * (limits.MAX_OSCILLATORS + 1))

    def test_a_built_in_instrument_is_kept_through_writing_and_reading(self):
        instrument = Instrument(kind=InstrumentKind.BUILT_IN)
        instrument.set_sound(name=SoundSetting.ENGINE, value=SoundEngine.DRUM)
        instrument.set_sound(name=SoundSetting.MACHINE, value=DrumMachine.SYNTH_KICK)
        instrument.set_sound(name=SoundSetting.KNOBS, value=KNOBS)
        data = instrument.to_data()
        again = Instrument.from_data(data=data, where=WHERE)
        self.assertEqual(again.to_data(), data)
        self.assertEqual(again.copy().to_data(), data)
        self.assertEqual(data[InstrumentSetting.KIND], InstrumentKind.BUILT_IN)

    def test_a_sound_is_given_to_the_synthesis_process_in_seconds_and_fractions(self):
        drum = {SoundSetting.ENGINE: SoundEngine.DRUM, SoundSetting.MACHINE: DrumMachine.HATS, SoundSetting.CHOKE: CHOKE}
        spec = built_in_sound.synth_spec(drum)
        self.assertEqual((spec['machine'], spec['choke'], spec['volume']), (DrumMachine.HATS, CHOKE, defaults.DEFAULT_SOUND_VOLUME / 100))
        basic = built_in_sound.synth_spec({SoundSetting.ATTACK: ATTACK_MS, SoundSetting.OSCILLATORS: [{OscillatorSetting.WAVEFORM: Waveform.SAW}, {}]})
        self.assertEqual(basic['envelope'][0], ATTACK_MS / 1000)
        # An oscillator left off, as the second is, does not sound.
        self.assertEqual(basic['oscillators'], [[Waveform.SAW, 0, 1.0]])

    def test_a_sounds_effect_blocks_reach_the_synthesis_process_in_order_the_empty_left_out(self):
        blocks = [{EffectSetting.EFFECT: Effect.DRIVE, EffectSetting.AMOUNT: DRIVE_PERCENT}, {}, {EffectSetting.EFFECT: Effect.BITCRUSH, EffectSetting.BITS: BITS}]
        spec = built_in_sound.synth_spec({SoundSetting.EFFECTS: blocks})
        self.assertEqual(spec['effects'], [(Effect.DRIVE, built_in_sound.EFFECT_DEFAULTS[EffectSetting.CURVE], DRIVE_PERCENT / 100),
                                           (Effect.BITCRUSH, BITS, defaults.DEFAULT_CRUSH_RATE)])
        with self.assertRaises(InvalidValue):
            Instrument(kind=InstrumentKind.BUILT_IN).set_sound(name=SoundSetting.EFFECTS, value=[{}] * (limits.EFFECT_BLOCKS + 1))
