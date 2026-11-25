# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A built-in instrument's voice as swappable parts: an oscillator module, three envelopes, four LFOs, a filter or none,
two effects and a mod matrix, an engine being a preset of these parts (.claude/planning's design, and
.claude/notes/synthesis/MOD_MATRIX.md).

Each note runs, a chunk at a time: its envelopes; the matrix, from the envelopes, the LFOs, its velocity, key and a random
value; the oscillator, its pitch moved by glide, Env3's pitch envelope through Pitch env and the matrix; its filter, its
cutoff moved by Env2 through the Env amount (and an acid accent's extra depth), key tracking and the matrix; and the amp,
Env1 times its velocity, moved by the matrix. A filter is each note's own, or the instrument's, shared by every note and
moved by the newest, as a paraphonic synth's is; a low-pass gate is always the note's own and is its amp, lit by Env1. The
voice layer plays a number of notes at once, and when legato a note starting while another is held slides to it, the
envelopes going on; otherwise a note glides from the last one's pitch. Speed rules this module, as it does the engine (the
user's yes): plain attributes, few calls, the work skipped where nothing reads it.
"""

import numpy

from llamatron.realtime.synth_process import effects, envelopes, filters, gates, matrix, modulation, oscillators
from llamatron.realtime.synth_process.matrix import ModMatrix

MIDDLE_C = 60
SEMITONES = 12.0
# The key as a source of the matrix: -1 to 1 over five octaves either side of middle C.
KEY_SPAN = 60.0
# The matrix moves the amp from silence to doubled.
MOST_AMP = 2.0
# The random source is the same every playing of the set.
RANDOM_SEED = 101
NONE = 'none'
LOW_PASS_GATE = 'low_pass_gate'


class SharedFilter(effects.SoundEffect):
    """A filter shared by every note of an instrument, first of its effects, moved by the newest note's Env2 and matrix: the
    filter, and the cutoff's movement in octaves and the resonance's for the chunk, each None for none."""

    __slots__ = ('filter', 'octaves', 'resonance')

    def __init__(self, *, filter_part):
        super().__init__(mix=1.0)
        self.filter = filter_part
        self.octaves = None
        self.resonance = None

    def apply(self, buffer, *, start=0):
        if self.octaves is not None and len(self.octaves) != len(buffer):
            self.octaves = numpy.full(len(buffer), float(self.octaves[-1]))
        return self.filter.filtered(buffer, octaves=self.octaves, resonance=self.resonance)


class ModularPatch:
    """A compiled instrument of parts: its oscillator module and its Pitch env in semitones, its three envelopes, its filter
    or None and whether each note has its own, the shared filter or None, its matrix, how many notes it plays at once,
    whether it plays legato and its glide in seconds, its volume, its effects in order, its LFOs, and the pitch it last played
    with the note it last began."""

    __slots__ = ('oscillator', 'pitch_env', 'envelopes', 'filter', 'own_filter', 'shared', 'matrix', 'voices', 'slides', 'glide', 'volume',
                 'effects', 'modulation', 'last_pitch', 'newest', 'random', 'remake', 'rate', 'reads_env2', 'reads_env3', 'matrix_reads_env2')

    def __init__(self, *, spec, rate, effects_compiled):
        """spec is the sound as llamatron gives it (model/objects/built_in_sound.py), effects_compiled its effects."""
        self.oscillator = oscillators.compiled_oscillators(spec=spec['oscillators'], rate=rate)
        self.pitch_env = spec['oscillators'].get('pitch_env', 0.0)
        filter_spec = spec['filter']
        resonance = filter_spec.get('resonance', 0.0)
        self.envelopes = [envelopes.compiled_envelope(spec=envelope, rate=rate, resonance=resonance) for envelope in spec['envelopes']]
        self.effects = list(effects_compiled)
        self._take_filter(spec=filter_spec, per_note=spec['filter_per_note'], rate=rate)
        self.matrix = ModMatrix(spec.get('matrix', ()))
        # Env2 and Env3 are worked out only where something reads them: the filter, the pitch envelope, or the matrix.
        self.matrix_reads_env2 = self.matrix.uses(matrix.ENV2)
        self.reads_env2 = self.filter is not None and not self.filter.is_gate or self.matrix_reads_env2
        self.reads_env3 = bool(self.pitch_env) or self.matrix.uses(matrix.ENV3)
        self.voices = spec['voices']
        self.slides = spec['legato']
        self.glide = spec['glide']
        self.volume = spec['volume']
        self.modulation = modulation.LfoBank(lfos=spec.get('lfos', ()), rate=rate)
        self.last_pitch = None
        self.newest = None
        self.random = numpy.random.default_rng(RANDOM_SEED)
        # Makes the patch again from its settings, from rest, after a runaway (player.py).
        self.remake = None
        self.rate = rate

    def begin(self, *, voice, rate):
        """Start a note: where its glide starts, its random value, its envelopes, its oscillator and its own filter."""
        voice.glide_from = voice.pitch
        if not self.slides and self.glide > 0 and self.last_pitch is not None:
            voice.glide_from = self.last_pitch
        voice.glide_at = voice.start
        self.last_pitch = voice.pitch
        voice.random = float(self.random.uniform(-1.0, 1.0))
        voice.accent_depth = 0.0
        voice.short_decay = None
        voice.states = [envelope.start(voice) for envelope in self.envelopes]
        self.oscillator.begin(voice=voice, rate=rate)
        if self.own_filter:
            voice.filter = self.filter.fresh()
        self.newest = voice

    def slide_to(self, *, voice, pitch, sample):
        """Slide a held note to a new pitch from a sample, legato, its envelopes going on."""
        voice.glide_from = voice.pitch + float(self._glided(voice=voice, places=numpy.array([float(sample)]))[0])
        voice.pitch = pitch
        voice.glide_at = sample
        self.last_pitch = pitch
        self.newest = voice

    def sound(self, *, voice, first, count, rate):
        levels = self._levels(voice=voice, first=first, count=count)
        moved = self._moved(voice=voice, levels=levels)
        pitch = self._pitch(voice=voice, first=first, count=count, env3=levels[2], moved=moved.get(matrix.PITCH))
        filter_part = self.filter
        wave = None
        if filter_part is None or not filter_part.is_gate or filter_part.uses_oscillator():
            wave = self.oscillator.wave(voice=voice, first=first, count=count, pitch=pitch, moved=moved)
        if voice.states[0].done:
            voice.silent = True
        if filter_part is not None and filter_part.is_gate:
            light = levels[0]
            if not self.envelopes[0].takes_velocity:
                light = light * voice.level
            return voice.filter.gated(wave, light=light, voice=voice, first=first, octaves=moved.get(matrix.CUTOFF))
        if filter_part is not None:
            wave = self._filtered(wave, voice=voice, env2=levels[1], moved=moved)
        amp = levels[0]
        if not self.envelopes[0].takes_velocity:
            amp = amp * voice.level
        if matrix.AMP in moved:
            amp = amp * numpy.clip(1.0 + moved[matrix.AMP], 0.0, MOST_AMP)
        return (wave * amp).astype(numpy.float32)

    def _take_filter(self, *, spec, per_note, rate):
        """Take the voice's filter: none, the low-pass gate, always a note's own, or one of the ladder family, each note's own
        or shared by them as the first of the effects."""
        self.filter = None
        self.own_filter = False
        self.shared = None
        if spec['type'] == LOW_PASS_GATE:
            self.filter = gates.LowPassGate(spec=spec, rate=rate)
            self.own_filter = True
        elif spec['type'] != NONE:
            self.filter = filters.Filter(spec=spec, rate=rate)
            self.own_filter = per_note
            if not per_note:
                self.shared = SharedFilter(filter_part=self.filter)
                self.effects.insert(0, self.shared)

    def _levels(self, *, voice, first, count):
        """Return the three envelopes over the chunk, Env2's decay forced short for an accent where one asks, Env2 and Env3 None
        where nothing reads them."""
        states = voice.states
        env1, env2, env3 = self.envelopes
        second = None
        third = None
        # A shared filter is moved by the newest note alone, so the others' Env2 is left unworked unless the matrix reads it.
        if self.reads_env2 and (self.own_filter or voice is self.newest or self.matrix_reads_env2):
            second = env2.levels(voice=voice, state=states[1], first=first, count=count, short=voice.short_decay)
        if self.reads_env3:
            third = env3.levels(voice=voice, state=states[2], first=first, count=count)
        return env1.levels(voice=voice, state=states[0], first=first, count=count), second, third

    def _moved(self, *, voice, levels):
        """Return what the matrix moves this chunk, nothing where it has no routes."""
        if not self.matrix.routes:
            return {}
        sources = {matrix.ENV1: levels[0], matrix.ENV2: levels[1], matrix.ENV3: levels[2], matrix.VELOCITY: voice.level,
                   matrix.KEY: (voice.pitch - MIDDLE_C) / KEY_SPAN, matrix.RANDOM: voice.random}
        for name, lfo in zip(matrix.LFO_SOURCES, self.modulation.now):
            sources[name] = 0.0 if lfo is None else lfo
        return self.matrix.moved(sources)

    def _pitch(self, *, voice, first, count, env3, moved):
        """Return the semitones the oscillator's pitch is moved by a sample, or None where nothing moves it."""
        pitch = None
        if self.glide > 0 and voice.glide_from != voice.pitch:
            pitch = self._glided(voice=voice, places=numpy.arange(first, first + count, dtype=numpy.float64))
        if self.pitch_env:
            pitch = env3 * self.pitch_env if pitch is None else pitch + env3 * self.pitch_env
        if moved is not None:
            if numpy.ndim(moved) == 0:
                moved = numpy.full(count, float(moved))
            pitch = moved if pitch is None else pitch + moved
        return pitch

    def _glided(self, *, voice, places):
        """Return how far a gliding note still is from its pitch, in semitones, at each of some samples."""
        if self.glide <= 0:
            return places * 0.0
        return (voice.glide_from - voice.pitch) * numpy.exp(-numpy.maximum(places - voice.glide_at, 0.0) / (self.glide * self.rate))

    def _filtered(self, wave, *, voice, env2, moved):
        """Return the note through its own filter, or hand the shared filter the movement if this is the newest note."""
        if not self.own_filter and voice is not self.newest:
            return wave
        filter_part = self.filter
        octaves = env2 * ((filter_part.amount + voice.accent_depth) * filters.ENVELOPE_OCTAVES)
        if filter_part.key_track:
            octaves = octaves + filter_part.key_track * (voice.pitch - MIDDLE_C) / SEMITONES
        cutoff = moved.get(matrix.CUTOFF)
        if cutoff is not None:
            octaves = octaves + cutoff
        resonance = moved.get(matrix.RESONANCE)
        if resonance is not None and numpy.ndim(resonance) == 0:
            resonance = numpy.full(len(octaves), float(resonance))
        if self.own_filter:
            return voice.filter.filtered(wave, octaves=octaves, resonance=resonance)
        if voice is self.newest:
            self.shared.octaves = octaves
            self.shared.resonance = resonance
        return wave
