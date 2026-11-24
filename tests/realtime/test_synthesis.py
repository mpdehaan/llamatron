# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Synthesis Process's engine, drums and tables (realtime/synth_process/), none of it opening the sound card: a note
begins on its exact sample, releases and falls silent, a mono instrument plays one note, a drum cuts its own last hit and its
choke group, the bitcrusher crushes, every drum renders alike each time, and built-in sound is off off macOS unless asked."""

import numpy
import unittest
from unittest import mock

from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import DrumMachine, Waveform
from llamatron.realtime.synth_process import drums, engine as engine_values, process, tables
from llamatron.realtime.synth_process.engine import BasicPatch, DrumPatch, SynthEngine
from llamatron.realtime.synth_process.process import SynthesisNotStarted, SynthesisProcess

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


def saw_patch(*, voices=4, effects=(16, 0, 0.0)):
    """Return a Basic patch of one saw with a short envelope."""
    saw = tables.waveform_tables(waveform=Waveform.SAW, rate=RATE)
    return BasicPatch(oscillators=[(saw, 0, 1.0)], envelope=(0.001, 0.05, 0.5, 0.01), voices=voices, volume=1.0, effects=effects)


def drum_patch(*, machine, choke=None):
    """Return a drum patch of a machine at its middle knobs."""
    def render(*, pitch, velocity, rate):
        return drums.render_hit(machine=machine, knobs=KNOBS, pitch=pitch, velocity=velocity, rate=rate)
    return DrumPatch(render_hit=render, choke=choke, volume=1.0)


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
        crushed.set_instrument(number=SYNTH, patch=saw_patch(effects=(2, RATE // 8, 0.0)))
        crushed.schedule(sample=0, kind=engine_values.NOTE_ON, instrument=SYNTH, pitch=MIDDLE_C, velocity=127)
        mix = rendered(crushed, chunks=4)
        self.assertLessEqual(len(numpy.unique(numpy.round(mix, 4))), 8)
        self.assertTrue(numpy.all(mix[CHUNK:CHUNK + 8] == mix[CHUNK]))

    def test_a_note_that_arrives_late_plays_at_once_and_is_counted(self):
        self.engine.render(start=0, frames=CHUNK)
        self.engine.schedule(sample=10, kind=engine_values.NOTE_ON, instrument=SYNTH, pitch=MIDDLE_C)
        self.assertTrue(self.engine.render(start=CHUNK, frames=CHUNK)[:8].any())
        self.assertEqual(self.engine.late, 1)


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
