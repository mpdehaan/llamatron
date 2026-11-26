# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""What keeps the built-in synths safe for ears and speakers whatever a patch does, with no setting that turns it off
(.claude/notes/synthesis/SYNTH_SAFETY.md): a ringing filter, a pinged gate, a resonance at its edge, a bad number or a
runaway feedback must never hang the sound or make it overly loud or harsh.

An instrument's guard checks each chunk of its mix: a number that is not finite, or a peak far past anything a patch makes,
is a fault, and the instrument is silenced and made again from rest, so that a filter that has blown up cannot keep
screaming; its next note plays clean. The output's guard then finishes the whole mix, in this order:

- anything not finite becomes silence, and the band filters start again;
- a fourth-order high-pass at 18 Hz takes out DC and the subsonic movement that pushes a speaker's cone unheard, and a
  second-order low-pass at 18 kHz the ultrasonic hash that tires the ear and strains tweeters;
- a limiter that looks ahead within the chunk holds every sample under -1 dB of full scale, its gain falling at once and
  rising back at 30 dB a second, so that it never steps or pumps hard;
- a slow guard against sustained loudness: a mean square over about three seconds past -8 dB of full scale, far louder than
  music stays, turns the whole down at 2 dB a second, by 12 dB at most, and back up at 1 dB a second;
- a backstop that leaves everything under 0.9 untouched and bends what is over it smoothly under 0.98;
- and a latch: faults again and again, or the limiter pulling down 20 dB for half a second, fade the output to silence and
  hold it there until the transport's silence (Ctrl+T) or a stop clears it.

Speed rules this module, as it does the engine (the user's yes).
"""

import math
import numpy
from scipy import signal

# An instrument's chunk past this is a fault, not music: the last resort, after the checks for numbers that are not finite.
RUNAWAY = 16.0
# The output's band.
LOWEST_KEPT = 18.0
HIGHEST_KEPT = 18000.0
HIGHEST_SHARE = 0.45
# Filter states smaller than this are flushed to zero, so that no processor slows on subnormal numbers.
TINY = 1e-20
# The limiter: its ceiling, -1 dB of full scale, and how fast it lets go, in decibels a second.
CEILING = 0.891
RELEASE_DB_PER_SECOND = 30.0
# The sustained guard: its window, the mean square it lets pass, how fast it turns down and back up, and how far at most.
LOUDNESS_SECONDS = 3.0
LOUDEST = 10.0 ** (-8.0 / 10.0)
TURN_DOWN_DB_PER_SECOND = 2.0
TURN_UP_DB_PER_SECOND = 1.0
MOST_TURNED_DOWN_DB = 12.0
# The backstop: untouched under KNEE, bent smoothly under BACKSTOP.
KNEE = 0.9
BACKSTOP = 0.98
# The latch: three faults within a second, or the limiter down by 20 dB for half a second, past where any music goes, mute
# until cleared; muting and
# clearing fade over a chunk and 50 ms.
FAULTS_TO_LATCH = 3
FAULT_WINDOW_SECONDS = 1.0
HARD_LIMITING_DB = 20.0
HARD_LIMITING_SECONDS = 0.5
UNMUTE_SECONDS = 0.05
# A note released this long ago still sounding is let go, faded: nothing rings on for ever.
LONGEST_RING_SECONDS = 30.0


def is_runaway(buffer):
    """Return whether an instrument's chunk is a fault: a number not finite, or far louder than any patch makes."""
    if not len(buffer):
        return False
    peak = float(numpy.max(numpy.abs(buffer)))
    return not math.isfinite(peak) or peak > RUNAWAY


def decibels(gain):
    return 20.0 * math.log10(max(gain, 1e-12))


class OutputGuard:
    """The output's guard: its band filter and state, the limiter's gain, the sustained guard's loudness and gain, the
    latch's state, and how many faults it has seen."""

    __slots__ = ('sections', 'state', 'gain', 'release', 'loudness', 'smoothing', 'turned', 'down_step', 'up_step', 'muted', 'unmuting',
                 'fault_times', 'hard_for', 'played', 'rate', 'faults')

    def __init__(self, *, rate):
        high = signal.butter(4, LOWEST_KEPT, btype='highpass', fs=rate, output='sos')
        low = signal.butter(2, min(HIGHEST_KEPT, HIGHEST_SHARE * rate), btype='lowpass', fs=rate, output='sos')
        self.sections = numpy.vstack([high, low])
        self.state = numpy.zeros((len(self.sections), 2))
        self.gain = 1.0
        self.release = RELEASE_DB_PER_SECOND
        self.loudness = 0.0
        self.smoothing = None
        self.turned = 1.0
        self.down_step = TURN_DOWN_DB_PER_SECOND
        self.up_step = TURN_UP_DB_PER_SECOND
        self.muted = False
        self.unmuting = 1.0
        self.fault_times = []
        self.hard_for = 0
        self.played = 0
        self.rate = rate
        self.faults = 0

    def clear(self):
        """Clear the latch, as the transport's silence or a stop does: the output fades back in."""
        if self.muted:
            self.muted = False
            self.unmuting = 0.0
        self.fault_times = []
        self.hard_for = 0

    def fault(self):
        """Count a fault, an instrument's or the output's own; enough of them close together latch the output silent."""
        self.faults += 1
        now = self.played / self.rate
        self.fault_times = [time for time in self.fault_times if now - time < FAULT_WINDOW_SECONDS] + [now]
        if len(self.fault_times) >= FAULTS_TO_LATCH:
            self.muted = True

    def guarded(self, mix):
        """Return the mix of a chunk made safe, float32."""
        count = len(mix)
        self.played += count
        peak = float(numpy.max(numpy.abs(mix))) if count else 0.0
        if not math.isfinite(peak):
            self.fault()
            mix = numpy.zeros(count)
            self.state[:] = 0.0
        out, self.state = signal.sosfilt(self.sections, mix, zi=self.state)
        self.state[numpy.abs(self.state) < TINY] = 0.0
        out = self._limited(out)
        out = self._sustained(out)
        out = self._backstopped(out)
        out = self._latched(out)
        return out.astype(numpy.float32)

    def _limited(self, out):
        """Return a chunk under the ceiling: each sample's gain at most what every later peak of the chunk needs, ramped from
        the last chunk's gain and rising back in decibels; a chunk under the ceiling with the gain at full passes untouched."""
        count = len(out)
        if not count:
            return out
        peak = float(numpy.max(numpy.abs(out)))
        if self.gain >= 1.0 and peak <= CEILING:
            self.hard_for = 0
            return out
        needed = numpy.minimum(1.0, CEILING / numpy.maximum(numpy.abs(out), 1e-12))
        ahead = numpy.minimum.accumulate(needed[::-1])[::-1]
        released = self.gain * 10.0 ** (self.release * count / self.rate / 20.0)
        end = min(1.0, released, float(ahead[-1]))
        gains = numpy.minimum(numpy.linspace(self.gain, end, count), ahead)
        self.gain = float(gains[-1])
        if decibels(float(gains.min())) < -HARD_LIMITING_DB:
            self.hard_for += count
            if self.hard_for >= HARD_LIMITING_SECONDS * self.rate:
                self.muted = True
        else:
            self.hard_for = 0
        return out * gains

    def _sustained(self, out):
        """Return a chunk turned down slowly while it has stayed far louder than music does."""
        count = len(out)
        if not count:
            return out
        if self.smoothing is None or self.smoothing[0] != count:
            self.smoothing = (count, 1.0 - math.exp(-count / (LOUDNESS_SECONDS * self.rate)))
        self.loudness += self.smoothing[1] * (float(numpy.dot(out, out)) / count - self.loudness)
        seconds = count / self.rate
        before = self.turned
        if self.loudness > LOUDEST:
            self.turned = max(10.0 ** (-MOST_TURNED_DOWN_DB / 20.0), self.turned * 10.0 ** (-self.down_step * seconds / 20.0))
        elif self.turned < 1.0:
            self.turned = min(1.0, self.turned * 10.0 ** (self.up_step * seconds / 20.0))
        if before == 1.0 and self.turned == 1.0:
            return out
        return out * numpy.linspace(before, self.turned, count)

    @staticmethod
    def _backstopped(out):
        """Return a chunk with everything over KNEE bent smoothly under BACKSTOP, everything under it untouched."""
        over = numpy.abs(out) > KNEE
        if not over.any():
            return out
        out = out.copy()
        bent = out[over]
        out[over] = numpy.sign(bent) * (KNEE + (BACKSTOP - KNEE) * numpy.tanh((numpy.abs(bent) - KNEE) / (BACKSTOP - KNEE)))
        return out

    def _latched(self, out):
        """Return a chunk faded to silence while the latch holds, and faded back in once cleared."""
        count = len(out)
        if self.muted:
            if self.unmuting <= 0.0:
                return out * 0.0
            fade = numpy.linspace(self.unmuting, 0.0, count)
            self.unmuting = 0.0
            return out * fade
        if self.unmuting < 1.0:
            after = min(1.0, self.unmuting + count / (UNMUTE_SECONDS * self.rate))
            fade = numpy.linspace(self.unmuting, after, count)
            self.unmuting = after
            return out * fade
        return out
