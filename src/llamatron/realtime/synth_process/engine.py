# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Synthesis Process's engine: notes scheduled at exact samples, played by voices reading compiled wavetables or
replaying drum hits rendered ahead, mixed a chunk at a time.

Everything here works in samples counted from the start of the stream, so that a note's place is an integer and never drifts.
The process turns each event's time into its sample once, as it arrives; render() then makes one chunk of the mix, as many
frames as the sound card asks for, in a few whole-array numpy operations a voice, never a loop over samples. A note begins
on its exact sample within the chunk, so a song's timing is as exact as the clock it was scheduled by, whatever the chunk
size. Speed rules this module, which may break the code style rules where they would slow it (the user's yes): its hot
paths keep plain attributes, local names and few calls.
"""

import heapq
import math
import numpy

from llamatron.realtime.synth_process import tables

MIDDLE_A = 69
A_FREQUENCY = 440.0
# A voice whose envelope has fallen below this is silent and is dropped.
SILENT = 1e-4
# A drum cut short by its next hit, or choked, fades out over this long rather than clicking.
CUT_FADE_SECONDS = 0.003
# How long a note takes to reach full level from silence at the least, so that no start clicks.
SHORTEST_ATTACK_SECONDS = 0.001
NOTE_ON = 0
NOTE_OFF = 1
# Every note of an instrument ends: a drum's hits fade out, the others release.
ALL_OFF = 2
# Not a note: the notes of a run of instruments still to come from a moment on are taken back (player.py).
FORGET = 3
FULL_SCALE = 1.0
# A drum's tone is rendered for each sixteenth of the velocities, its level following the exact velocity.
VELOCITY_STEP = 8


def frequency_of(pitch):
    """Return a MIDI number's frequency in hertz, equal tempered from A 440."""
    return A_FREQUENCY * 2.0 ** ((pitch - MIDDLE_A) / 12.0)


class BasicPatch:
    """A compiled Basic instrument: its oscillators, each (tables by octave band, detune in cents, level), its envelope in
    seconds and its sustain level, how many notes it plays at once, its volume, and its effects: bits (16 none), the rate
    it holds samples at (0 none) and drive (0 none)."""

    __slots__ = ('oscillators', 'attack', 'decay', 'sustain', 'release', 'voices', 'volume', 'bits', 'hold_rate', 'drive')

    def __init__(self, *, oscillators, envelope, voices=4, volume=0.5, effects=(16, 0, 0.0)):
        self.oscillators = oscillators
        self.attack, self.decay, self.sustain, self.release = envelope
        self.voices = voices
        self.volume = volume
        self.bits, self.hold_rate, self.drive = effects


class DrumPatch:
    """A compiled drum instrument: a function rendering one hit from (pitch, velocity, rate) as float32, its choke group or
    None, whether its hits overlap rather than cutting the last, its volume and its effects as BasicPatch has them; its hits
    are rendered once each and kept."""

    __slots__ = ('render_hit', 'choke', 'overlap', 'volume', 'bits', 'hold_rate', 'drive', 'hits')

    def __init__(self, *, render_hit, choke=None, overlap=False, volume=0.8, effects=(16, 0, 0.0)):
        self.render_hit = render_hit
        self.choke = choke
        self.overlap = overlap
        self.volume = volume
        self.bits, self.hold_rate, self.drive = effects
        self.hits = {}


class SynthVoice:
    """A sounding note: its instrument, its pitch, the sample it starts at, how many of its samples have played, the sample
    its release begins at or None, its level, and for a Basic note each oscillator's (table, read speed, phase), for a drum
    its hit; a voice being cut fades out from the sample its cut begins."""

    __slots__ = ('instrument', 'pitch', 'start', 'age', 'release_at', 'level', 'oscillators', 'hit', 'cut_at', 'silent')

    def __init__(self, *, instrument, pitch, start, level):
        self.instrument = instrument
        self.pitch = pitch
        self.start = start
        self.age = 0
        self.release_at = None
        self.level = level
        self.oscillators = []
        self.hit = None
        self.cut_at = None
        self.silent = False


class SynthEngine:
    """The engine: the instruments by number, the events still to play in time order, the voices sounding, and the sample
    rate; render() makes each chunk of the mix."""

    __slots__ = ('rate', 'instruments', 'events', 'voices', 'order', 'played', 'late')

    def __init__(self, *, rate):
        self.rate = rate
        self.instruments = {}
        self.events = []
        self.voices = []
        self.order = 0
        self.played = 0
        self.late = 0

    def set_instrument(self, *, number, patch):
        self.instruments[number] = patch

    def schedule(self, *, sample, kind, instrument, pitch, velocity=100):
        """Schedule a note on or off at an exact sample, a note off before a note on at one sample, rendering a drum's hit now
        if it isn't kept already, so that the audio callback never renders one."""
        patch = self.instruments.get(instrument)
        if kind == NOTE_ON and isinstance(patch, DrumPatch):
            self._hit(patch=patch, pitch=pitch, velocity=velocity)
        self.order += 1
        heapq.heappush(self.events, (sample, kind != NOTE_OFF, self.order, kind, instrument, pitch, velocity))

    def prepare(self, *, instrument, pitch, velocity):
        """Render a drum's hit for a note ahead, so that neither scheduling nor the callback has to."""
        patch = self.instruments.get(instrument)
        if isinstance(patch, DrumPatch):
            self._hit(patch=patch, pitch=pitch, velocity=velocity)

    def forget(self, *, first, last, sample):
        """Take back every event still to play from a sample on, of the instruments numbered first to last."""
        self.events = [event for event in self.events if not (first <= event[4] <= last and event[0] >= sample)]
        heapq.heapify(self.events)

    def silence(self):
        """Forget every event still to play and stop every voice at once."""
        self.events.clear()
        self.voices.clear()

    def render(self, *, start, frames):
        """Return the mix of the chunk of frames starting at a sample, as float32, every event due in it begun on its sample."""
        mix = numpy.zeros(frames, dtype=numpy.float32)
        end = start + frames
        events = self.events
        while events and events[0][0] < end:
            sample, _, _, kind, instrument, pitch, velocity = heapq.heappop(events)
            if sample < start:
                # Only a late start is counted: a stop is sent the moment it is asked for, and always lands a little after.
                if kind == NOTE_ON:
                    self.late += 1
                sample = start
            self._begin(sample=sample, kind=kind, instrument=instrument, pitch=pitch, velocity=velocity)
        by_instrument = {}
        alive = []
        for voice in self.voices:
            if self._play(voice=voice, start=start, frames=frames, into=by_instrument):
                alive.append(voice)
        self.voices = alive
        for number, buffer in by_instrument.items():
            patch = self.instruments[number]
            mix += _effects(buffer=buffer, patch=patch, rate=self.rate) * patch.volume
        numpy.clip(mix, -FULL_SCALE, FULL_SCALE, out=mix)
        self.played = end
        return mix

    def _begin(self, *, sample, kind, instrument, pitch, velocity):
        patch = self.instruments.get(instrument)
        if patch is None:
            return
        if kind == NOTE_OFF:
            for voice in self.voices:
                if voice.instrument == instrument and voice.pitch == pitch and voice.release_at is None and voice.hit is None:
                    voice.release_at = sample
            return
        if kind == ALL_OFF:
            self._end_every_note(instrument=instrument, sample=sample)
            return
        level = velocity / 127.0
        voice = SynthVoice(instrument=instrument, pitch=pitch, start=sample, level=level)
        if isinstance(patch, DrumPatch):
            self._cut_drums(patch=patch, instrument=instrument, sample=sample)
            voice.hit = self._hit(patch=patch, pitch=pitch, velocity=velocity)
        else:
            self._steal(patch=patch, instrument=instrument, sample=sample)
            for oscillator_tables, cents, oscillator_level in patch.oscillators:
                frequency = frequency_of(pitch) * 2.0 ** (cents / 1200.0)
                speed = frequency * tables.TABLE_SIZE / self.rate
                voice.oscillators.append((oscillator_tables[tables.band_of(frequency)], speed, 0.0, oscillator_level))
        self.voices.append(voice)

    def _end_every_note(self, *, instrument, sample):
        """End every note of an instrument at a sample: a drum's hit fades out, any other note releases."""
        for voice in self.voices:
            if voice.instrument != instrument:
                continue
            if voice.hit is not None and voice.cut_at is None:
                voice.cut_at = sample
            elif voice.hit is None and voice.release_at is None:
                voice.release_at = sample

    def _hit(self, *, patch, pitch, velocity):
        """Return a drum's hit at a pitch, its tone rendered at the middle of the velocity's eighth, rendered once and kept."""
        step = velocity // VELOCITY_STEP
        key = (pitch, step)
        hit = patch.hits.get(key)
        if hit is None:
            hit = patch.render_hit(pitch=pitch, velocity=step * VELOCITY_STEP + VELOCITY_STEP // 2, rate=self.rate)
            patch.hits[key] = hit
        return hit

    def _cut_drums(self, *, patch, instrument, sample):
        """Cut the drum's own last hit, unless its hits overlap, and every hit of its choke group, each fading out."""
        for voice in self.voices:
            if voice.cut_at is not None or voice.hit is None:
                continue
            other = self.instruments[voice.instrument]
            same = voice.instrument == instrument and not patch.overlap
            choked = patch.choke is not None and isinstance(other, DrumPatch) and other.choke == patch.choke and voice.instrument != instrument
            if same or choked:
                voice.cut_at = sample

    def _steal(self, *, patch, instrument, sample):
        """Release the oldest voices of an instrument past its count of voices, so that a mono instrument plays one note."""
        mine = [voice for voice in self.voices if voice.instrument == instrument and voice.cut_at is None]
        while len(mine) >= patch.voices:
            mine.pop(0).cut_at = sample

    def _play(self, *, voice, start, frames, into):
        """Add a voice's part of a chunk to its instrument's buffer, and return whether it still sounds after it."""
        offset = voice.start - start
        if offset >= frames:
            return True
        offset = max(offset, 0)
        count = frames - offset
        if voice.hit is not None:
            samples = voice.hit[voice.age:voice.age + count]
            if not len(samples):
                return False
            out = samples * voice.level
            count = len(out)
        else:
            out = self._oscillators(voice=voice, count=count)
            out *= self._envelope(voice=voice, first=start + offset, count=count)
        alive = True
        if voice.cut_at is not None:
            fade = int(CUT_FADE_SECONDS * self.rate)
            positions = numpy.arange(start + offset, start + offset + count) - voice.cut_at
            out = out * numpy.clip(1.0 - positions / fade, 0.0, 1.0).astype(numpy.float32)
            alive = positions[-1] < fade
        buffer = into.get(voice.instrument)
        if buffer is None:
            buffer = numpy.zeros(frames, dtype=numpy.float32)
            into[voice.instrument] = buffer
        buffer[offset:offset + count] += out
        voice.age += count
        if voice.hit is not None and voice.age >= len(voice.hit):
            return False
        return alive and not voice.silent

    def _oscillators(self, *, voice, count):
        """Return a Basic voice's oscillators read for a stretch of samples, each table read at its speed from its phase."""
        out = numpy.zeros(count, dtype=numpy.float32)
        steps = numpy.arange(count, dtype=numpy.float64)
        read = []
        for table, speed, phase, oscillator_level in voice.oscillators:
            positions = phase + speed * steps
            out += table[positions.astype(numpy.int64) & tables.TABLE_MASK] * oscillator_level
            read.append((table, speed, (phase + speed * count) % tables.TABLE_SIZE, oscillator_level))
        voice.oscillators = read
        return out

    def _envelope(self, *, voice, first, count):
        """Return a Basic voice's envelope over a stretch of samples: a linear attack, an exponential fall to its sustain,
        and after its release an exponential fall to silence, the voice marked silent once below SILENT."""
        patch = self.instruments[voice.instrument]
        rate = self.rate
        ages = (numpy.arange(count, dtype=numpy.float64) + (first - voice.start))
        attack = max(patch.attack, SHORTEST_ATTACK_SECONDS) * rate
        decay = max(patch.decay, SHORTEST_ATTACK_SECONDS) * rate
        level = numpy.where(ages < attack, ages / attack, patch.sustain + (1.0 - patch.sustain) * numpy.exp(-(ages - attack) / decay))
        if voice.release_at is not None:
            release = max(patch.release, SHORTEST_ATTACK_SECONDS) * rate
            since = numpy.arange(first, first + count, dtype=numpy.float64) - voice.release_at
            at_release_age = voice.release_at - voice.start
            if at_release_age < attack:
                released_from = at_release_age / attack
            else:
                released_from = patch.sustain + (1.0 - patch.sustain) * math.exp(-(at_release_age - attack) / decay)
            falling = released_from * numpy.exp(-numpy.maximum(since, 0.0) / release)
            level = numpy.where(since >= 0, falling, level)
            if since[-1] >= 0 and falling[-1] < SILENT:
                voice.silent = True
        return (level * voice.level).astype(numpy.float32)


def _effects(*, buffer, patch, rate):
    """Return an instrument's mix through its effects: the bitcrusher's sample-rate reduction, holding each sample for as long
    as its rate gives, then its bit reduction, then drive."""
    if patch.hold_rate and patch.hold_rate < rate:
        hold = max(1, int(rate / patch.hold_rate))
        buffer = numpy.repeat(buffer[::hold], hold)[:len(buffer)]
    if patch.bits < 16:
        levels = 2 ** (patch.bits - 1)
        buffer = numpy.round(buffer * levels) / levels
    if patch.drive > 0:
        gain = 1.0 + patch.drive * 20.0
        buffer = numpy.tanh(buffer * gain) / math.tanh(gain)
    return buffer.astype(numpy.float32, copy=False)
