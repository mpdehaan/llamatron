# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Synthesis Process's player: the engine behind a PortAudio stream, inside the process.

Each chunk the callback reads when PortAudio says the chunk's first sample reaches the speakers, on the same clock as the
notes' times, time.perf_counter, and places every note that has arrived at the sample its time falls on, plus the delay every
instrument is held back by: the stream's own output latency and one chunk, so that a note sent at its time is never late.
Notes arrive from the reader thread, which renders any drum hit first, into a deque the callback drains: the callback
never renders, allocates beyond its chunk or waits on a lock. It counts what timing needs watching: chunks, underflows,
late notes and how long each callback took. Speed rules this module (the user's yes to break the style rules here).
"""

import collections
import functools
import time

from llamatron.realtime.synth_process import drums, engine as engine_values, tables
from llamatron.realtime.synth_process.effects import compiled_effects
from llamatron.realtime.synth_process.engine import DrumPatch, SynthEngine
from llamatron.realtime.synth_process.voices import BasicPatch, PocketPatch, SidPatch

DRUM = 'drum'
SID = 'sid'
POCKET = 'pocket'
LOW_LATENCY = 'low'
FLOAT32 = 'float32'
CHANNELS = 2
MILLISECONDS = 1000.0


def compiled(*, spec, rate):
    """Return an instrument's patch from its settings, a dict of its engine, volume, voices, effects and the engine's own
    settings (model/objects/built_in_sound.py); its tables or hits made now, not playing."""
    effects = compiled_effects(effects=spec.get('effects', ()), rate=rate)
    volume = spec.get('volume', 0.8)
    voices = spec.get('voices', 1)
    kind = spec['kind']
    if kind == DRUM:
        render = functools.partial(drums.render_hit, machine=spec['machine'], knobs=tuple(spec['knobs']))
        return DrumPatch(render_hit=render, choke=spec.get('choke'), overlap=spec.get('overlap', False), volume=volume, effects=effects)
    if kind == SID:
        return SidPatch(spec=spec, rate=rate, effects=effects)
    if kind == POCKET:
        return PocketPatch(spec=spec, rate=rate, effects=effects)
    oscillators = [(tables.waveform_tables(waveform=waveform, rate=rate), cents, level) for waveform, cents, level in spec['oscillators']]
    return BasicPatch(oscillators=oscillators, envelope=tuple(spec['envelope']), voices=voices, volume=volume, effects=effects)


class SynthPlayer:
    """The engine behind a PortAudio stream: start() opens it and learns the rate and the delay; add_notes() and
    set_instrument() come from the reader thread; stop() closes it and returns its timing statistics."""

    __slots__ = ('_sounddevice', '_block', '_device', '_stream', '_pending', 'engine', 'rate', 'delay', 'played', 'chunks', 'underflows',
                 'longest', 'durations')

    def __init__(self, *, sounddevice, block, device):
        self._sounddevice = sounddevice
        self._block = block
        self._device = device
        self._stream = None
        self._pending = collections.deque()
        self.engine = None
        self.rate = None
        self.delay = 0.0
        self.played = 0
        self.chunks = 0
        self.underflows = 0
        self.longest = 0.0
        self.durations = []

    def start(self):
        info = self._sounddevice.query_devices(self._device, kind='output')
        self.rate = int(info['default_samplerate'])
        self.engine = SynthEngine(rate=self.rate)
        self._stream = self._sounddevice.OutputStream(samplerate=self.rate, blocksize=self._block, channels=CHANNELS, dtype=FLOAT32,
                                                      latency=LOW_LATENCY, device=self._device, callback=self.audio_callback)
        self._stream.start()
        self.delay = self._stream.latency + self._block / self.rate

    def set_instrument(self, *, number, spec):
        self.engine.set_instrument(number=number, patch=compiled(spec=spec, rate=self.rate))

    def add_notes(self, notes):
        """Take notes, each (perf_counter seconds, kind, instrument, pitch, velocity), rendering any drum hit now."""
        for _, kind, instrument, pitch, velocity in notes:
            if kind == engine_values.NOTE_ON:
                self.engine.prepare(instrument=instrument, pitch=pitch, velocity=velocity)
        self._pending.extend(notes)

    def silence(self):
        self._pending.append(None)

    def stop(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        durations = sorted(self.durations)
        p99 = durations[int(len(durations) * 0.99)] if durations else 0.0
        budget = self._block / self.rate * MILLISECONDS if self.rate else 0.0
        return {'rate': self.rate, 'block': self._block, 'delay_ms': self.delay * MILLISECONDS, 'chunks': self.chunks,
                'underflows': self.underflows, 'late_notes': self.engine.late if self.engine else 0,
                'longest_callback_ms': self.longest * MILLISECONDS, 'p99_callback_ms': p99 * MILLISECONDS, 'budget_ms': budget}

    def audio_callback(self, outdata, frames, time_info, status):
        began = time.perf_counter()
        if status.output_underflow:
            self.underflows += 1
        # When this chunk's first sample reaches the speakers, on the notes' clock.
        dac = began + (time_info.outputBufferDacTime - time_info.currentTime)
        engine = self.engine
        rate = self.rate
        delay = self.delay
        played = self.played
        pending = self._pending
        while pending:
            note = pending.popleft()
            if note is None:
                engine.silence()
                continue
            when, kind, instrument, pitch, velocity = note
            if kind == engine_values.FORGET:
                engine.forget(first=instrument, last=pitch, sample=played + int(round((when + delay - dac) * rate)))
                continue
            engine.schedule(sample=played + int(round((when + delay - dac) * rate)), kind=kind, instrument=instrument, pitch=pitch,
                            velocity=velocity)
        mix = engine.render(start=played, frames=frames)
        outdata[:, 0] = mix
        outdata[:, 1] = mix
        self.played = played + frames
        self.chunks += 1
        took = time.perf_counter() - began
        if took > self.longest:
            self.longest = took
        if len(self.durations) < 100000:
            self.durations.append(took)
