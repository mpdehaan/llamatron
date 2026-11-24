# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Synthesis Process's engine, drums and tables (realtime/synth_process/), none of it opening the sound card: a note
begins on its exact sample, releases and falls silent, a mono instrument plays one note, a drum cuts its own last hit and its
choke group, the bitcrusher crushes, every drum renders alike each time, and built-in sound is off off macOS unless asked."""

import numpy
import unittest
from unittest import mock

from llamatron.model.objects.built_in_sound import synth_spec
from llamatron.model.objects.setlist import Setlist
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import ChipVoice, Curve, DrumMachine, Effect, Modulation, Noise, SidWave, SoundEngine, SoundSetting, Waveform
from llamatron.realtime.synth_process import drums, effects as effect_values, engine as engine_values, process, tables
from llamatron.realtime.synth_process.effects import Bitcrush, compiled_effects
from llamatron.realtime.synth_process.engine import DrumPatch, SynthEngine
from llamatron.realtime.synth_process.player import compiled
from llamatron.realtime.synth_process.process import SynthesisNotStarted, SynthesisProcess
from llamatron.realtime.synth_process.voices import BasicPatch

RATE = 44100
CHUNK = 128
SYNTH = 1
KICK = 2
CLOSED_HAT = 3
OPEN_HAT = 4
MIDDLE_C = 60
LOUD = 120
KNOBS = (64, 64, 64, 64, 64)
LINUX = 'linux'
MACOS = 'darwin'
YES = '1'
QUIET = 0.01
# Long enough for the default release, 200 ms, to fall below silence.
SECONDS_TO_FALL_SILENT = 3
PULSE_SWEEP = 40
ARPEGGIO = [0, 4, 7]
GLIDE_MS = 50


def saw_patch(*, voices=4, effects=()):
    """Return a Basic patch of one saw with a short envelope."""
    saw = tables.waveform_tables(waveform=Waveform.SAW, rate=RATE)
    return BasicPatch(oscillators=[(saw, 0, 1.0)], envelope=(0.001, 0.05, 0.5, 0.01), voices=voices, volume=1.0, effects=compiled_effects(effects=effects, rate=RATE))


def drum_patch(*, machine, choke=None):
    """Return a drum patch of a machine at its middle knobs."""
    def render(*, pitch, velocity, rate):
        return drums.render_hit(machine=machine, knobs=KNOBS, pitch=pitch, velocity=velocity, rate=rate)
    return DrumPatch(render_hit=render, spec={'choke': choke, 'volume': 1.0})


def rendered(engine, *, chunks):
    """Return so many chunks of an engine's mix, end to end."""
    return numpy.concatenate([engine.render(start=place * CHUNK, frames=CHUNK) for place in range(chunks)])


class TestSynthesisEngine(unittest.TestCase):

    def setUp(self):
        self.engine = SynthEngine(rate=RATE)
        self.engine.set_instrument(number=SYNTH, patch=saw_patch())

    def test_a_note_begins_on_its_exact_sample_inside_a_chunk(self):
        start = CHUNK + 37
        self.engine.schedule(sample=start, kind=engine_values.NOTE_ON, instrument=SYNTH, pitch=MIDDLE_C, velocity=LOUD)
        mix = rendered(self.engine, chunks=3)
        self.assertFalse(mix[:start].any())
        self.assertTrue(mix[start:start + 8].any())

    def test_a_released_note_falls_silent_and_its_voice_is_dropped(self):
        self.engine.schedule(sample=0, kind=engine_values.NOTE_ON, instrument=SYNTH, pitch=MIDDLE_C)
        self.engine.schedule(sample=CHUNK * 2, kind=engine_values.NOTE_OFF, instrument=SYNTH, pitch=MIDDLE_C)
        mix = rendered(self.engine, chunks=200)
        self.assertLess(numpy.abs(mix[-CHUNK:]).max(), engine_values.SILENT * 10)
        self.assertEqual(self.engine.voices, [])

    def test_a_mono_instrument_plays_one_note_at_once(self):
        self.engine.set_instrument(number=SYNTH, patch=saw_patch(voices=1))
        for offset, pitch in enumerate((MIDDLE_C, MIDDLE_C + 4, MIDDLE_C + 7)):
            self.engine.schedule(sample=offset * CHUNK * 4, kind=engine_values.NOTE_ON, instrument=SYNTH, pitch=pitch)
        rendered(self.engine, chunks=20)
        self.assertEqual([voice.pitch for voice in self.engine.voices], [MIDDLE_C + 7])

    def test_a_drum_cuts_its_own_last_hit_and_a_closed_hat_chokes_the_open(self):
        self.engine.set_instrument(number=KICK, patch=drum_patch(machine=DrumMachine.KICK))
        self.engine.set_instrument(number=CLOSED_HAT, patch=drum_patch(machine=DrumMachine.HATS, choke=1))
        self.engine.set_instrument(number=OPEN_HAT, patch=drum_patch(machine=DrumMachine.HATS, choke=1))
        self.engine.schedule(sample=0, kind=engine_values.NOTE_ON, instrument=KICK, pitch=MIDDLE_C)
        self.engine.schedule(sample=0, kind=engine_values.NOTE_ON, instrument=OPEN_HAT, pitch=MIDDLE_C)
        self.engine.schedule(sample=CHUNK * 4, kind=engine_values.NOTE_ON, instrument=KICK, pitch=MIDDLE_C)
        self.engine.schedule(sample=CHUNK * 4, kind=engine_values.NOTE_ON, instrument=CLOSED_HAT, pitch=MIDDLE_C)
        rendered(self.engine, chunks=8)
        sounding = sorted(voice.instrument for voice in self.engine.voices)
        self.assertEqual(sounding, [KICK, CLOSED_HAT])

    def test_a_drum_hit_is_rendered_when_scheduled_never_in_the_callback(self):
        patch = drum_patch(machine=DrumMachine.SNARE)
        self.engine.set_instrument(number=KICK, patch=patch)
        self.engine.schedule(sample=CHUNK * 100, kind=engine_values.NOTE_ON, instrument=KICK, pitch=MIDDLE_C, velocity=LOUD)
        self.assertEqual(len(patch.hits), 1)

    def test_the_bitcrusher_holds_samples_and_reduces_bits(self):
        crushed = SynthEngine(rate=RATE)
        crushed.set_instrument(number=SYNTH, patch=saw_patch(effects=[(Effect.BITCRUSH, 2, RATE // 8)]))
        crushed.schedule(sample=0, kind=engine_values.NOTE_ON, instrument=SYNTH, pitch=MIDDLE_C, velocity=127)
        mix = rendered(crushed, chunks=4)
        self.assertLessEqual(len(numpy.unique(numpy.round(mix, 4))), 8)
        self.assertTrue(numpy.all(mix[CHUNK:CHUNK + 8] == mix[CHUNK]))

    def test_a_note_that_arrives_late_plays_at_once_and_is_counted(self):
        self.engine.render(start=0, frames=CHUNK)
        self.engine.schedule(sample=10, kind=engine_values.NOTE_ON, instrument=SYNTH, pitch=MIDDLE_C)
        self.assertTrue(self.engine.render(start=CHUNK, frames=CHUNK)[:8].any())
        self.assertEqual(self.engine.late, 1)


class TestEngines(unittest.TestCase):

    def test_every_engine_sounds_its_note_and_falls_silent_after_it(self):
        sounds = {
            'basic': {},
            'sid pulse sweeping, arpeggiated': {SoundSetting.ENGINE: SoundEngine.SID, SoundSetting.PULSE_SWEEP: PULSE_SWEEP, SoundSetting.ARPEGGIO: ARPEGGIO},
            'sid ring': {SoundSetting.ENGINE: SoundEngine.SID, SoundSetting.WAVE: SidWave.TRIANGLE, SoundSetting.MODULATION: Modulation.RING},
            'sid sync gliding': {SoundSetting.ENGINE: SoundEngine.SID, SoundSetting.WAVE: SidWave.SAW, SoundSetting.MODULATION: Modulation.SYNC, SoundSetting.GLIDE: GLIDE_MS},
            'sid noise': {SoundSetting.ENGINE: SoundEngine.SID, SoundSetting.WAVE: SidWave.NOISE},
            'pocket pulse': {SoundSetting.ENGINE: SoundEngine.POCKET, SoundSetting.SWEEP_PACE: 1},
            'pocket wave': {SoundSetting.ENGINE: SoundEngine.POCKET, SoundSetting.CHIP_VOICE: ChipVoice.WAVE},
            'pocket short noise': {SoundSetting.ENGINE: SoundEngine.POCKET, SoundSetting.CHIP_VOICE: ChipVoice.NOISE, SoundSetting.NOISE: Noise.SHORT},
        }
        for name, sound in sounds.items():
            with self.subTest(sound=name):
                engine = SynthEngine(rate=RATE)
                engine.set_instrument(number=SYNTH, patch=compiled(spec=synth_spec(sound), rate=RATE))
                engine.schedule(sample=0, kind=engine_values.NOTE_ON, instrument=SYNTH, pitch=MIDDLE_C, velocity=LOUD)
                engine.schedule(sample=CHUNK * 8, kind=engine_values.NOTE_OFF, instrument=SYNTH, pitch=MIDDLE_C)
                mix = rendered(engine, chunks=SECONDS_TO_FALL_SILENT * RATE // CHUNK)
                self.assertGreater(numpy.abs(mix[:CHUNK * 8]).max(), QUIET)
                self.assertEqual(engine.voices, [])

    def test_a_sound_changed_to_another_engine_while_its_note_sounds_lets_the_note_finish_and_plays_on(self):
        engines = (SoundEngine.BASIC, SoundEngine.DRUM, SoundEngine.SID, SoundEngine.POCKET)
        for first in engines:
            for second in engines:
                with self.subTest(first=first, second=second):
                    engine = SynthEngine(rate=RATE)
                    engine.set_instrument(number=SYNTH, patch=compiled(spec=synth_spec({SoundSetting.ENGINE: first}), rate=RATE))
                    engine.schedule(sample=0, kind=engine_values.NOTE_ON, instrument=SYNTH, pitch=MIDDLE_C, velocity=LOUD)
                    rendered(engine, chunks=1)
                    engine.set_instrument(number=SYNTH, patch=compiled(spec=synth_spec({SoundSetting.ENGINE: second}), rate=RATE))
                    engine.schedule(sample=CHUNK * 2, kind=engine_values.NOTE_ON, instrument=SYNTH, pitch=MIDDLE_C + 4, velocity=LOUD)
                    self.assertTrue(rendered(engine, chunks=8).any())

    def test_a_pocket_envelope_steps_down_to_silence_at_its_pace(self):
        sound = {SoundSetting.ENGINE: SoundEngine.POCKET, SoundSetting.LEVEL_PACE: 1, SoundSetting.START_LEVEL: 2}
        engine = SynthEngine(rate=RATE)
        engine.set_instrument(number=SYNTH, patch=compiled(spec=synth_spec(sound), rate=RATE))
        engine.schedule(sample=0, kind=engine_values.NOTE_ON, instrument=SYNTH, pitch=MIDDLE_C, velocity=LOUD)
        # Two levels a sixty-fourth of a second each: silent within a twentieth of a second, the note still held.
        rendered(engine, chunks=int(RATE / 20 / CHUNK))
        self.assertEqual(engine.voices, [])


class TestEffects(unittest.TestCase):

    def test_the_hold_carries_across_chunks_so_a_held_sample_never_restarts_at_an_edge(self):
        ramp = numpy.arange(CHUNK * 2, dtype=numpy.float32)
        whole = Bitcrush(bits=16, hold_rate=RATE // 10, rate=RATE).apply(ramp.copy())
        crusher = Bitcrush(bits=16, hold_rate=RATE // 10, rate=RATE)
        halves = numpy.concatenate([crusher.apply(ramp[:CHUNK].copy()), crusher.apply(ramp[CHUNK:].copy())])
        self.assertTrue(numpy.array_equal(whole, halves))
        self.assertLessEqual(len(numpy.unique(whole)), CHUNK * 2 // 10 + 2)

    def test_every_drive_curve_keeps_within_full_scale(self):
        loud = numpy.linspace(-2.0, 2.0, CHUNK, dtype=numpy.float32)
        for curve in (Curve.SOFT, Curve.WARM, Curve.HARD, Curve.FOLD, Curve.WRAP):
            with self.subTest(curve=curve):
                driven = effect_values.Drive(curve=curve, amount=0.5).apply(loud)
                self.assertLessEqual(float(numpy.abs(driven).max()), 1.0 + 1e-6)

    def test_the_output_guard_holds_a_mix_turned_up_past_full_at_full_scale(self):
        engine = SynthEngine(rate=RATE)
        engine.set_instrument(number=SYNTH, patch=saw_patch())
        for offset in range(4):
            engine.schedule(sample=0, kind=engine_values.NOTE_ON, instrument=SYNTH, pitch=MIDDLE_C + offset * 7, velocity=127)
        mix = rendered(engine, chunks=20)
        self.assertLessEqual(float(numpy.abs(mix).max()), 1.0 + 1e-6)


class TestDrumsAndTables(unittest.TestCase):

    def test_every_drum_renders_alike_each_time_and_peaks_below_full_scale(self):
        for machine in file_format.DRUM_MACHINES:
            with self.subTest(machine=machine):
                first = drums.render_hit(machine=machine, knobs=KNOBS, pitch=MIDDLE_C, velocity=LOUD, rate=RATE)
                again = drums.render_hit(machine=machine, knobs=KNOBS, pitch=MIDDLE_C, velocity=LOUD, rate=RATE)
                self.assertTrue(numpy.array_equal(first, again))
                self.assertAlmostEqual(float(numpy.abs(first).max()), drums.PEAK, places=4)

    def test_a_drums_note_tunes_it_from_middle_c(self):
        low = drums.render_hit(machine=DrumMachine.ACOUSTIC_TOM, knobs=KNOBS, pitch=MIDDLE_C, velocity=LOUD, rate=RATE)
        high = drums.render_hit(machine=DrumMachine.ACOUSTIC_TOM, knobs=KNOBS, pitch=MIDDLE_C + 12, velocity=LOUD, rate=RATE)
        self.assertFalse(numpy.array_equal(low[:1000], high[:1000]))

    def test_a_drum_plays_at_its_own_pitch_on_the_note_it_is_tuned_from(self):
        drum_c = Setlist().drum_tuning_note()
        spec = synth_spec({SoundSetting.ENGINE: SoundEngine.DRUM, SoundSetting.KNOBS: list(KNOBS)}, drums_from=drum_c)
        patch = compiled(spec=spec, rate=RATE)
        self.assertEqual(patch.recipe_pitch(drum_c), MIDDLE_C)
        engine = SynthEngine(rate=RATE)
        engine.set_instrument(number=KICK, patch=patch)
        engine.schedule(sample=0, kind=engine_values.NOTE_ON, instrument=KICK, pitch=drum_c, velocity=LOUD)
        at_middle_c = drums.render_hit(machine=DrumMachine.KICK, knobs=KNOBS, pitch=MIDDLE_C, velocity=LOUD // engine_values.VELOCITY_STEP * engine_values.VELOCITY_STEP + engine_values.VELOCITY_STEP // 2, rate=RATE)
        self.assertTrue(numpy.array_equal(next(iter(patch.hits.values())), at_middle_c))

    def test_a_table_holds_no_harmonic_above_half_the_rate_for_its_band(self):
        top_band = tables.waveform_tables(waveform=Waveform.SAW, rate=RATE)[-1]
        spectrum = numpy.abs(numpy.fft.rfft(top_band))
        self.assertLess(spectrum[3:].max(), spectrum[1] * 0.01)


class TestSynthesisAvailable(unittest.TestCase):

    def test_built_in_sound_is_on_on_macos_and_off_elsewhere_unless_asked(self):
        self.assertTrue(process.synthesis_available(environment={}, platform=MACOS))
        self.assertFalse(process.synthesis_available(environment={}, platform=LINUX))
        self.assertTrue(process.synthesis_available(environment={process.TRY_ANYWAY: YES}, platform=LINUX))

    def test_starting_where_it_is_off_says_why_and_starts_no_process(self):
        with mock.patch.object(process, 'synthesis_available', return_value=False):
            with self.assertRaises(SynthesisNotStarted):
                SynthesisProcess().start()
