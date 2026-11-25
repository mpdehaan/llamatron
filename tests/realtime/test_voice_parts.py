# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The parts a built-in voice is made of (realtime/synth_process/): the envelopes, each its own shape; the low-pass gate and
its ping; the mod matrix; a filter each note's own or shared; the ladder's slopes; and the guards that keep ears and speakers
safe whatever a patch does."""

import numpy
from scipy import signal
from types import SimpleNamespace
import unittest

from llamatron.realtime.synth_process import engine as engine_values, envelopes, gates, matrix, safety
from llamatron.realtime.synth_process.engine import SynthEngine
from llamatron.realtime.synth_process.filters import Filter
from llamatron.realtime.synth_process.gates import LowPassGate
from llamatron.realtime.synth_process.matrix import ModMatrix
from llamatron.realtime.synth_process.player import compiled
from llamatron.realtime.synth_process.safety import OutputGuard

RATE = 44100
CHUNK = 128
SYNTH = 1
MIDDLE_C = 60
LOUD = 120
QUIET = 0.01
# The SID chip's fastest attack is 2 ms, its 9th rate 250 ms.
SID_FASTEST_ATTACK_MS = 2.3
SID_DECAY_RATE = 9
SID_SUSTAIN = 8
HELD_SECONDS = 0.5
# A vactrol of the slow cell, struck for 2 ms.
SLOW_RISE = 0.012
SLOW_FALL = 0.25
STRIKE_WIDTH = 0.002
MEMORY = 0.3
PING_WIDTH = 0.001
OPEN_CUTOFF = 7000.0
RINGING = 0.8


class Voice(SimpleNamespace):
    """A voice as the parts see it: its start, release, level, pitch, and what an acid accent leaves on it."""


def a_voice(*, start=0, release_at=None, level=1.0, pitch=MIDDLE_C):
    return Voice(start=start, release_at=release_at, level=level, pitch=pitch, accent_depth=0.0, short_decay=None)


def played(envelope, *, voice, seconds):
    """Return an envelope's levels over a time, chunk by chunk, and whether it fell silent."""
    state = envelope.start(voice)
    out = []
    for first in range(voice.start, voice.start + int(seconds * RATE), CHUNK):
        out.append(envelope.levels(voice=voice, state=state, first=first, count=CHUNK))
    return numpy.concatenate(out), state.done


def an_envelope(**spec):
    return envelopes.compiled_envelope(spec=spec, rate=RATE, resonance=0.0)


def adsr(kind=envelopes.ADSR, **changes):
    spec = {'type': kind, 'attack': 0.01, 'decay': 0.2, 'sustain': 0.5, 'release': 0.1, 'attack_curve': 50, 'hold': 0.0, 'snap': 0.0}
    return an_envelope(**{**spec, **changes})


def vactrol(**changes):
    spec = {'type': envelopes.VACTROL, 'rise': SLOW_RISE, 'fall': SLOW_FALL, 'drive': envelopes.STRIKE, 'strike_width': STRIKE_WIDTH, 'memory': MEMORY}
    return an_envelope(**{**spec, **changes})


def peaks_of_hits(envelope, *, hits, apart):
    """Return the peak of each of so many strikes a time apart."""
    peaks = []
    for hit in range(hits):
        levels, _ = played(envelope, voice=a_voice(start=int(hit * apart * RATE)), seconds=apart)
        peaks.append(float(levels.max()))
    return peaks


class TestEnvelopes(unittest.TestCase):

    def test_an_adsr_peaks_at_its_attack_falls_to_its_sustain_and_releases_to_silence(self):
        release = int(HELD_SECONDS * RATE)
        levels, done = played(adsr(), voice=a_voice(release_at=release), seconds=1.0)
        self.assertAlmostEqual(levels.argmax() / RATE, 0.01, delta=0.001)
        self.assertAlmostEqual(float(levels[release - 1]), 0.5, delta=0.01)
        self.assertTrue(done)

    def test_snap_drops_the_decay_faster_at_first_and_hold_keeps_the_top(self):
        plain, _ = played(adsr(sustain=0.0), voice=a_voice(), seconds=0.1)
        snapped, _ = played(adsr(sustain=0.0, snap=0.6), voice=a_voice(), seconds=0.1)
        held, _ = played(adsr(sustain=0.0, hold=0.02), voice=a_voice(), seconds=0.1)
        early = int(0.02 * RATE)
        self.assertLess(snapped[early], plain[early])
        self.assertAlmostEqual(float(held[early]), 1.0, delta=0.01)

    def test_an_ar_is_struck_whatever_the_gate_and_an_asr_holds_full_while_held(self):
        struck, done = played(adsr(envelopes.AR), voice=a_voice(), seconds=1.0)
        self.assertTrue(done)
        held, _ = played(adsr(envelopes.ASR), voice=a_voice(release_at=int(HELD_SECONDS * RATE)), seconds=0.4)
        self.assertAlmostEqual(float(held[-1]), 1.0, delta=0.01)
        self.assertLess(float(struck[-1]), QUIET)

    def test_the_sid_adsr_rises_in_the_chips_time_and_holds_its_sixteen_level_sustain(self):
        envelope = an_envelope(type=envelopes.SID_ADSR, attack=0, decay=SID_DECAY_RATE, sustain=SID_SUSTAIN, release=SID_DECAY_RATE)
        levels, done = played(envelope, voice=a_voice(release_at=int(HELD_SECONDS * RATE)), seconds=3.0)
        self.assertAlmostEqual(levels.argmax() / RATE * 1000, SID_FASTEST_ATTACK_MS, delta=0.3)
        self.assertAlmostEqual(float(levels[int(HELD_SECONDS * RATE) - 1]) * envelopes.SID_TOP, SID_SUSTAIN * envelopes.SID_SUSTAIN_STEP, delta=1)
        self.assertTrue(done)

    def test_a_stable_vactrol_strikes_alike_an_aged_unstable_one_varies_and_a_softer_strike_peaks_lower(self):
        # Without memory, so that no strike starts from what the last left.
        stable = peaks_of_hits(vactrol(memory=0.0), hits=4, apart=0.7)
        self.assertEqual(len({round(peak, 6) for peak in stable}), 1)
        aged = peaks_of_hits(vactrol(memory=0.0, age=1.0, stability=0.4), hits=4, apart=0.7)
        self.assertGreater(len({round(peak, 3) for peak in aged}), 1)
        soft, _ = played(vactrol(memory=0.0), voice=a_voice(level=0.4), seconds=0.2)
        self.assertLess(float(soft.max()), stable[0])

    def test_vactrol_strikes_close_together_build_on_what_the_last_left(self):
        apart = played(vactrol(), voice=a_voice(), seconds=0.1)[0][-1]
        close = peaks_of_hits(vactrol(), hits=2, apart=0.02)
        self.assertGreater(apart, 0.0)
        self.assertGreater(close[1], close[0])


class TestLowPassGate(unittest.TestCase):

    def gate(self, **changes):
        spec = {'mode': gates.LOWPASS, 'resonance': RINGING, 'open': OPEN_CUTOFF, 'key_track': 1.0, 'input': gates.PING, 'ping_width': PING_WIDTH}
        return LowPassGate(spec={**spec, **changes}, rate=RATE).fresh()

    def test_a_pinged_gate_rings_with_no_oscillator_and_falls_as_its_light_falls(self):
        gate = self.gate()
        self.assertFalse(gate.uses_oscillator())
        voice = a_voice()
        light = numpy.concatenate([numpy.ones(CHUNK * 4), numpy.linspace(1.0, 0.0, CHUNK * 16)])
        out = numpy.concatenate([gate.gated(None, light=light[first:first + CHUNK], voice=voice, first=first) for first in range(0, len(light), CHUNK)])
        self.assertGreater(float(numpy.abs(out[CHUNK:CHUNK * 4]).max()), QUIET)
        self.assertGreater(float(numpy.abs(out[:CHUNK * 4]).max()), float(numpy.abs(out[-CHUNK:]).max()))

    def test_the_vca_mode_follows_the_light_and_both_darkens_the_sound_as_it_fades(self):
        noise = numpy.random.default_rng(3).uniform(-1.0, 1.0, CHUNK).astype(numpy.float32)
        vca = self.gate(mode=gates.VCA, input=gates.OSCILLATOR)
        bright = vca.gated(noise, light=numpy.ones(CHUNK), voice=a_voice(), first=0)
        dim = vca.gated(noise, light=numpy.full(CHUNK, 0.3), voice=a_voice(), first=0)
        self.assertLess(float(numpy.abs(dim).max()), float(numpy.abs(bright).max()))
        both = self.gate(mode=gates.BOTH, input=gates.OSCILLATOR)
        dark = both.gated(noise, light=numpy.full(CHUNK, 0.3), voice=a_voice(), first=0)
        self.assertLess(float(numpy.abs(numpy.diff(dark)).mean()), float(numpy.abs(numpy.diff(dim)).mean()))


class TestMatrix(unittest.TestCase):

    def test_routes_sum_into_their_destinations_and_empty_slots_are_left_out(self):
        slots = [{'source': matrix.VELOCITY, 'via': matrix.NONE, 'destination': matrix.CUTOFF, 'amount': 0.5},
                 {'source': matrix.ENV1, 'via': matrix.VELOCITY, 'destination': matrix.CUTOFF, 'amount': 0.5},
                 {'source': matrix.NONE, 'via': matrix.NONE, 'destination': matrix.PITCH, 'amount': 1.0},
                 {'source': matrix.LFO1, 'via': matrix.NONE, 'destination': matrix.PITCH, 'amount': 0.0}]
        routes = ModMatrix(slots)
        self.assertEqual(len(routes.routes), 2)
        moved = routes.moved({matrix.VELOCITY: 1.0, matrix.ENV1: numpy.ones(CHUNK)})
        self.assertEqual(set(moved), {matrix.CUTOFF})
        self.assertAlmostEqual(float(moved[matrix.CUTOFF][0]), matrix.RANGES[matrix.CUTOFF])


def a_sound(*, filter_part, per_note, slots=()):
    """Return a sound of parts, a saw through a filter, as llamatron gives it to the Synthesis Process."""
    quiet = {'type': envelopes.ADSR, 'attack': 0.0, 'decay': 0.01, 'sustain': 0.0, 'release': 0.01}
    amp = {'type': envelopes.ADSR, 'attack': 0.001, 'decay': 0.5, 'sustain': 1.0, 'release': 0.05}
    sweep = {'type': envelopes.ADSR, 'attack': 0.0, 'decay': 0.2, 'sustain': 0.0, 'release': 0.05}
    return {'volume': 1.0, 'voices': 4, 'legato': False, 'glide': 0.0, 'filter_per_note': per_note, 'effects': [], 'lfos': [None] * 4,
            'matrix': list(slots), 'oscillators': {'type': 'basic', 'oscillators': [['saw', 0, 1.0]]}, 'envelopes': [amp, sweep, quiet],
            'filter': filter_part}


LADDER = {'type': 'ladder', 'mode': 'low', 'cutoff': 400.0, 'resonance': 0.3, 'env_amount': 1.0, 'key_track': 0.0, 'drive': 0.0}


class TestFilterParts(unittest.TestCase):

    def test_a_note_of_its_own_filter_keeps_its_sweep_while_a_shared_filter_follows_the_newest_note(self):
        later = int(0.15 * RATE)
        mixes = {}
        for per_note in (True, False):
            engine = SynthEngine(rate=RATE)
            engine.set_instrument(number=SYNTH, patch=compiled(spec=a_sound(filter_part=LADDER, per_note=per_note), rate=RATE))
            engine.schedule(sample=0, kind=engine_values.NOTE_ON, instrument=SYNTH, pitch=MIDDLE_C, velocity=LOUD)
            engine.schedule(sample=later, kind=engine_values.NOTE_ON, instrument=SYNTH, pitch=MIDDLE_C + 7, velocity=LOUD)
            mixes[per_note] = numpy.concatenate([engine.render(start=first, frames=CHUNK) for first in range(0, later + CHUNK * 20, CHUNK)])
        self.assertTrue(numpy.isfinite(mixes[True]).all())
        self.assertGreater(float(numpy.abs(mixes[True] - mixes[False])[later:].max()), QUIET)

    def test_velocity_routed_to_cutoff_brightens_a_harder_note(self):
        slots = [{'source': matrix.VELOCITY, 'via': matrix.NONE, 'destination': matrix.CUTOFF, 'amount': 0.5}]
        heard = []
        for velocity in (40, 127):
            engine = SynthEngine(rate=RATE)
            engine.set_instrument(number=SYNTH, patch=compiled(spec=a_sound(filter_part={**LADDER, 'env_amount': 0.0}, per_note=True, slots=slots), rate=RATE))
            engine.schedule(sample=0, kind=engine_values.NOTE_ON, instrument=SYNTH, pitch=MIDDLE_C, velocity=velocity)
            mix = numpy.concatenate([engine.render(start=first, frames=CHUNK) for first in range(0, CHUNK * 40, CHUNK)])
            heard.append(float(numpy.abs(numpy.diff(mix[-CHUNK * 8:])).mean() / max(numpy.abs(mix[-CHUNK * 8:]).mean(), 1e-9)))
        self.assertGreater(heard[1], heard[0])

    def test_the_ladder_is_tapped_for_six_twelve_eighteen_and_twenty_four_db_an_octave(self):
        for poles in (1, 2, 3, 4):
            with self.subTest(poles=poles):
                ladder = Filter(spec={**LADDER, 'cutoff': 1000.0, 'poles': poles}, rate=RATE)
                numerator, denominator = ladder._ladder(1000.0)
                _, response = signal.freqz(numerator, denominator, worN=[2000.0, 8000.0], fs=RATE)
                slope = 20.0 * numpy.log10(numpy.abs(response[1]) / numpy.abs(response[0])) / 2.0
                self.assertAlmostEqual(slope, -6.0 * poles, delta=0.6)


class TestSafety(unittest.TestCase):

    def test_quiet_music_passes_untouched_and_every_peak_is_held_under_the_ceiling(self):
        guard = OutputGuard(rate=RATE)
        places = numpy.arange(CHUNK * 200) / RATE
        sine = 0.5 * numpy.sin(2.0 * numpy.pi * 440.0 * places)
        out = numpy.concatenate([guard.guarded(sine[first:first + CHUNK]) for first in range(0, len(sine), CHUNK)])
        self.assertAlmostEqual(float(numpy.abs(out[-CHUNK * 50:]).max()), 0.5, delta=0.01)
        loud = OutputGuard(rate=RATE)
        spike = numpy.zeros(CHUNK)
        spike[0] = 5.0
        self.assertLessEqual(float(numpy.abs(loud.guarded(spike)).max()), safety.CEILING + 1e-6)

    def test_a_bad_number_is_silence_and_faults_close_together_latch_the_output_until_cleared(self):
        guard = OutputGuard(rate=RATE)
        bad = numpy.zeros(CHUNK)
        bad[5] = numpy.nan
        for _ in range(safety.FAULTS_TO_LATCH):
            self.assertEqual(float(numpy.abs(guard.guarded(bad)).max()), 0.0)
        self.assertTrue(guard.muted)
        guard.clear()
        self.assertFalse(guard.muted)

    def test_dc_is_taken_out_of_the_output(self):
        guard = OutputGuard(rate=RATE)
        held = numpy.full(CHUNK, 0.5)
        out = numpy.concatenate([guard.guarded(held) for _ in range(int(2 * RATE / CHUNK))])
        self.assertLess(float(numpy.abs(out[-CHUNK:]).max()), QUIET)

    def test_a_runaway_instrument_is_silenced_and_made_again_from_rest(self):
        engine = SynthEngine(rate=RATE)
        engine.set_instrument(number=SYNTH, patch=compiled(spec=a_sound(filter_part=LADDER, per_note=True), rate=RATE))
        engine.schedule(sample=0, kind=engine_values.NOTE_ON, instrument=SYNTH, pitch=MIDDLE_C, velocity=LOUD)
        engine.render(start=0, frames=CHUNK)
        before = engine.instruments[SYNTH]
        engine.voices[0].level = numpy.inf
        engine.render(start=CHUNK, frames=CHUNK)
        self.assertEqual((engine.runaways, engine.voices), (1, []))
        self.assertIsNot(engine.instruments[SYNTH], before)
        # The output's filters let the last good chunk's tail fade, then all is quiet.
        after = engine.render(start=CHUNK * 40, frames=CHUNK)
        self.assertLess(float(numpy.abs(after).max()), QUIET)
