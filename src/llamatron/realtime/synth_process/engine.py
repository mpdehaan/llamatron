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
import numpy

from llamatron.realtime.synth_process import effects, modulation as modulation_values

# A voice whose envelope has fallen below this is silent and is dropped.
SILENT = 1e-4
# A drum cut short by its next hit, or choked, fades out over this long rather than clicking.
CUT_FADE_SECONDS = 0.003
NOTE_ON = 0
NOTE_OFF = 1
# Every note of an instrument ends: a drum's hits fade out, the others release.
ALL_OFF = 2
# Not a note: the notes of a run of instruments still to come from a moment on are taken back (player.py).
FORGET = 3
# The output guard's knee: x - (4/27)x³ is flat and at full scale where x is 1.5.
GUARD_LIMIT = 1.5
GUARD_CURVE = 4.0 / 27.0
# A drum's tone is rendered for each sixteenth of the velocities, its level following the exact velocity.
# The note the drum recipes play at their own pitch on (drums.py).
RECIPES_TUNED_AT = 60
VELOCITY_STEP = 8


class DrumPatch:
    """A compiled drum instrument: a function rendering one hit from (pitch, velocity, rate) as float32, its choke group or
    None, whether its hits overlap rather than cutting the last, its volume and its effects in order, and the note it plays at
    its own pitch on; its hits are rendered once each and kept."""

    __slots__ = ('render_hit', 'choke', 'overlap', 'volume', 'effects', 'hits', 'tuned_from', 'modulation')

    def __init__(self, *, render_hit, spec, effects=()):
        """render_hit renders a hit, spec is the sound as llamatron gives it (model/objects/built_in_sound.py), each setting it
        leaves out its default, and effects are its effects compiled."""
        self.render_hit = render_hit
        # The note it plays at its own pitch on: the set's drum tuning note, so that a drum pattern written there sounds as
        # its knobs say.
        self.tuned_from = spec.get('tuned_from', RECIPES_TUNED_AT)
        self.choke = spec.get('choke')
        self.overlap = spec.get('overlap', False)
        self.volume = spec.get('volume', 0.8)
        self.effects = list(effects)
        self.hits = {}
        self.modulation = modulation_values.NO_MODULATION

    def recipe_pitch(self, pitch):
        """Return the note a recipe renders for a note played, the recipes playing at their own pitch on middle C."""
        return pitch - self.tuned_from + RECIPES_TUNED_AT


class SynthVoice:
    """A sounding note: its instrument, its pitch, the sample it starts at, how many of its samples have played, the sample
    its release begins at or None, its level, and for a Basic note each oscillator's (table, read speed, phase), for a drum
    its hit, and what a SID or Pocket voice keeps from chunk to chunk; a voice being cut fades out from the sample its cut
    begins."""

    __slots__ = ('instrument', 'pitch', 'start', 'age', 'release_at', 'level', 'oscillators', 'hit', 'cut_at', 'silent', 'phase', 'second_phase',
                 'glide_from', 'period', 'ticks', 'patch')

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
        # What a SID or Pocket voice keeps from chunk to chunk (voices.py).
        self.phase = 0.0
        self.second_phase = 0.0
        self.glide_from = pitch
        self.period = 0
        self.ticks = 0
        # The patch the voice began with (SynthEngine._begin).
        self.patch = None


class SynthEngine:
    """The engine: the instruments by number, the events still to play in time order, the voices sounding, and the sample
    rate; render() makes each chunk of the mix."""

    __slots__ = ('rate', 'instruments', 'events', 'voices', 'order', 'played', 'late', 'places')

    def __init__(self, *, rate):
        self.rate = rate
        self.instruments = {}
        self.events = []
        self.voices = []
        self.order = 0
        self.played = 0
        self.late = 0
        # 0 to a chunk's length, made once for the chunks the sound card asks for.
        self.places = numpy.arange(0, dtype=numpy.float64)

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
        self._modulate(frames)
        by_instrument = {}
        alive = []
        for voice in self.voices:
            if self._play(voice=voice, start=start, frames=frames, into=by_instrument):
                alive.append(voice)
        self.voices = alive
        for number, buffer in by_instrument.items():
            patch = self.instruments[number]
            mix += effects.through_effects(buffer=buffer, effects=patch.effects, start=start) * patch.volume
        # The output guard: a soft knee that reaches full scale, flat, at half again as loud, so that instruments turned up
        # past full never clip harshly, and anything louder is held at full scale.
        numpy.clip(mix, -GUARD_LIMIT, GUARD_LIMIT, out=mix)
        mix -= GUARD_CURVE * mix * mix * mix
        self.played = end
        return mix

    def _modulate(self, frames):
        """Move every instrument's LFOs on over the chunk, and hand the first filter of each its cutoff's movement."""
        if len(self.places) != frames:
            self.places = numpy.arange(frames, dtype=numpy.float64)
        for patch in self.instruments.values():
            modulation = patch.modulation
            if not modulation.lfos:
                continue
            modulation.advance(self.places)
            for effect in patch.effects:
                if effect.moves_cutoff:
                    effect.octaves = modulation.now.get(modulation_values.FILTER_CUTOFF)
                    break

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
        # A voice keeps the patch it began with, so that a sound changed while the note sounds, even to another engine, lets the
        # note finish as it began and gives the change to the next note.
        voice.patch = patch
        for effect in patch.effects:
            effect.note_on(sample=sample, pitch=pitch)
        patch.modulation.note_on()
        if isinstance(patch, DrumPatch):
            self._cut_drums(patch=patch, instrument=instrument, sample=sample)
            voice.hit = self._hit(patch=patch, pitch=pitch, velocity=velocity)
        else:
            self._steal(patch=patch, instrument=instrument, sample=sample)
            patch.begin(voice=voice, rate=self.rate)
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
            hit = patch.render_hit(pitch=patch.recipe_pitch(pitch), velocity=step * VELOCITY_STEP + VELOCITY_STEP // 2, rate=self.rate)
            patch.hits[key] = hit
        return hit

    def _cut_drums(self, *, patch, instrument, sample):
        """Cut the drum's own last hit, unless its hits overlap, and every hit of its choke group, each fading out."""
        for voice in self.voices:
            if voice.cut_at is not None or voice.hit is None:
                continue
            other = voice.patch
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
            out = voice.patch.sound(voice=voice, first=start + offset, count=count, rate=self.rate)
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
