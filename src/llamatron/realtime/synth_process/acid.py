# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fishline, the acid bass (.claude/notes/synthesis/FILTERS_AND_ACID.md and FLAVORS.md, section 9): one voice of a
band-limited saw, or the square a transistor shapes from it, through its own diode filter, which does not follow the keyboard
and whose floor Env Mod lowers a little, and a drive after it, as acid always went through a pedal.

The pattern is the instrument. A note at or above the accent's velocity is accented: its amp swells along the accent's short
envelope and attacks sharper, its filter envelope is deeper and forced short, and a capacitor is charged a little more, by as
much as Resonance allows, since the real one is fed through the Resonance pot's second gang; a fast run of accents leaves it
charged, so that each accent's sweep lands higher: the rising "wow". A note that starts while the last is still held slides
to its pitch through a fixed lag in semitones, the gate held, so that neither envelope starts again and the capacitor keeps
its charge. The amp is a gate: a quick attack, a long fixed fall, a short fade at the note's end. The filter and the drive are the first two of the instrument's effects (player.py), so
that an LFO on Filter cutoff moves Fishline's own filter, and Filter on takes the filter out. Speed rules this module, as it
does the engine (the user's yes).
"""

import math
import numpy

from llamatron.realtime.synth_process import modulation as modulation_values, tables, voices
from llamatron.realtime.synth_process.effects import Drive
from llamatron.realtime.synth_process.filters import Filter

SAW = 'saw'
DIODE = 'diode'
LOW = 'low'
SOFT = 'soft'
# The amp: an accented note's sharp attack, and the fade at a note's end; a plain note's soft attack and the long fall are its
# settings.
ACCENT_ATTACK_SECONDS = 0.001
END_FADE_SECONDS = 0.008
# The filter's envelope at full Env Mod moves the cutoff three of its four octaves.
ENV_MOD_SHARE = 0.75
# How much full accent swells the amp at the note's start, the swell falling away with the accent's short envelope, and how deep
# full accent makes the filter's envelope.
ACCENT_LOUDER = 0.7
ACCENT_DEEPER = 0.25
# Raising Env Mod lowers the cutoff's floor a little, as the real circuit does: half an octave at full.
ENV_MOD_DIP = 0.5
# The accent capacitor: how much each accent charges it at full sweep and full resonance, since the real one is fed through the
# Resonance pot's second gang, as a share of the envelope, and how fast it empties.
CHARGE_STEP = 0.35
CHARGE_SECONDS = 0.5
# An exponential is 60 dB down after this many time constants.
T60 = 6.91
# The square is the saw's pulse shaped by a transistor: a soft clip of this push.
SQUARE_PUSH = 1.8
# The original filter does not follow the keyboard, which is why high acid lines thin out.
KEY_TRACK = 0.0
# Drive at full pushes a quarter as hard as the Drive effect does, a pedal's grit rather than a wall.
DRIVE_SHARE = 0.25


class FishlinePatch:
    """A compiled Fishline instrument: its wave and the saw's tables, its tuning, its filter or None and the filter's own
    amount and decay, its accent, the velocity that accents, how far a run of accents climbs, its slide in seconds, its volume
    and its effects (its filter and drive first), its modulation, and the accent capacitor's charge with the sample it was
    last charged at."""

    __slots__ = ('square', 'saw', 'tuning', 'filter', 'amount', 'decay', 'accent', 'threshold', 'sweep', 'slide', 'voices', 'volume', 'effects',
                 'modulation', 'charge', 'charged_at', 'rate', 'resonance', 'amp_decay', 'soft_attack', 'accent_decay')
    # A note that starts while another is held slides to it.
    slides = True

    def __init__(self, *, spec, rate, effects):
        """spec is the sound as llamatron gives it (model/objects/built_in_sound.py), effects its effects compiled, which follow
        its own filter and drive."""
        self.square = spec['acid_wave'] != SAW
        self.saw = tables.waveform_tables(waveform=SAW, rate=rate)
        self.tuning = spec['tuning']
        self.amount = spec['env_mod'] * ENV_MOD_SHARE
        self.decay = spec['filter_decay']
        self.filter = None
        own = [Drive(curve=SOFT, amount=spec['drive'] * DRIVE_SHARE)]
        if spec['filter_on']:
            self.filter = Filter(spec=filter_spec(spec=spec, amount=self.amount), rate=rate)
            own.insert(0, self.filter)
        self.accent = spec['accent']
        self.threshold = spec['accent_threshold']
        self.sweep = spec['accent_sweep']
        self.resonance = spec['resonance']
        self.amp_decay = spec['amp_decay']
        self.soft_attack = spec['soft_attack']
        self.accent_decay = spec['accent_decay']
        self.slide = spec['slide']
        self.voices = 1
        self.volume = spec['volume']
        self.effects = own + list(effects)
        self.modulation = modulation_values.NO_MODULATION
        self.charge = 0.0
        self.charged_at = 0
        self.rate = rate

    def begin(self, *, voice, rate):
        """Start a note: its phase, whether it is accented, and its filter envelope's depth and length, the capacitor charged
        by an accent."""
        voice.phase = 0.0
        voice.glide_from = voice.pitch
        voice.ticks = voice.start
        accented = round(voice.level * 127) >= self.threshold
        voice.period = int(accented)
        self.charge *= math.exp(-(voice.start - self.charged_at) / (CHARGE_SECONDS * rate))
        self.charged_at = voice.start
        if accented:
            self.charge = min(1.0, self.charge + CHARGE_STEP * self.sweep * self.resonance)
        if self.filter is not None:
            extra = (ACCENT_DEEPER * self.accent + self.charge * ENV_MOD_SHARE) if accented else 0.0
            self.filter.amount = self.amount + extra
            self.filter.decay = self.accent_decay if accented else self.decay

    def slide_to(self, *, voice, pitch, sample):
        """Slide a held note to a new pitch from a sample, the gate held, neither envelope started again."""
        voice.glide_from = self._pitch_at(voice=voice, sample=sample)
        voice.pitch = pitch
        voice.ticks = sample

    def sound(self, *, voice, first, count, rate):
        places = numpy.arange(first, first + count, dtype=numpy.float64)
        pitch = voice.pitch + self.tuning + (voice.glide_from - voice.pitch) * numpy.exp(-numpy.maximum(places - voice.ticks, 0.0) / (self.slide * rate))
        moved = self.modulation.now.get(modulation_values.PITCH)
        if moved is not None:
            pitch = pitch + moved
        speeds = numpy.exp2((pitch - voices.MIDDLE_A) / 12.0) * (voices.A_FREQUENCY * tables.TABLE_SIZE / rate)
        positions, after = modulation_values.phases(phase=voice.phase, speeds=speeds)
        voice.phase = after % tables.TABLE_SIZE
        saw = self.saw[tables.band_of(voices.frequency_of(voice.pitch))]
        indexes = positions.astype(numpy.int64)
        out = saw[indexes & tables.TABLE_MASK]
        if self.square:
            pulse = (out - saw[(indexes + tables.TABLE_SIZE // 2) & tables.TABLE_MASK]) * 0.5
            out = numpy.tanh(pulse * SQUARE_PUSH) / math.tanh(SQUARE_PUSH)
        return (out * self._amp(voice=voice, places=places, rate=rate)).astype(numpy.float32)

    def _pitch_at(self, *, voice, sample):
        """Return the pitch a sliding note has reached at a sample."""
        lag = max(sample - voice.ticks, 0) / (self.slide * self.rate)
        return voice.pitch + (voice.glide_from - voice.pitch) * math.exp(-lag)

    def _amp(self, *, voice, places, rate):
        """Return the gate's level over a chunk: a quick attack, a long fall, a short fade once the note ends."""
        ages = (places - voice.start) / rate
        if voice.period:
            # An accent swells the amp along its own short envelope, a punch rather than a louder note.
            swell = 1.0 + ACCENT_LOUDER * self.accent * numpy.exp(-ages * (T60 / self.accent_decay))
            level = numpy.minimum(ages / ACCENT_ATTACK_SECONDS, 1.0) * numpy.exp(-ages / self.amp_decay) * swell * voice.level
        else:
            level = numpy.minimum(ages / self.soft_attack, 1.0) * numpy.exp(-ages / self.amp_decay) * voice.level
        if voice.release_at is not None:
            since = (places - voice.release_at) / rate
            level = level * numpy.clip(1.0 - since / END_FADE_SECONDS, 0.0, 1.0)
            if since[-1] >= END_FADE_SECONDS:
                voice.silent = True
        return level


def filter_spec(*, spec, amount):
    """Return Fishline's own filter as a Filter effect's settings: the diode ladder, low-pass, its envelope's attack instant,
    its floor lowered a little by Env Mod."""
    return {'filter_type': DIODE, 'filter_mode': LOW, 'cutoff': spec['cutoff'] * 2.0 ** (-ENV_MOD_DIP * spec['env_mod']), 'resonance': spec['resonance'], 'envelope_amount': amount,
            'envelope_attack': 0.0, 'envelope_decay': spec['filter_decay'], 'key_track': KEY_TRACK, 'filter_drive': 0.0, 'mix': 1.0}
