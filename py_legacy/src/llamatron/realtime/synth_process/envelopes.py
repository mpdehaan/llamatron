# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The envelope modules of a built-in voice, each a part its three envelope slots can hold
(.claude/notes/synthesis/ENVELOPES.md).

Env1 is normalled to the amp, Env2 to the filter's cutoff through its Env amount, and Env3 to pitch through the oscillators'
Pitch env; each is also a source of the mod matrix. Each module is compiled once for its instrument and keeps a small state
for each voice, and gives a chunk of levels from 0 to 1 in closed form, never a loop over samples:

- ADSR, the snappy one: an attack whose curve runs from a convex swell through a straight ramp to the analog timer's RC charge
  aimed past the top, a hold, a decay and release that are true RC falls shown as the time they take to fall 60 dB, and Snap,
  a fast fall mixed into the decay for the abrupt first drop of a drum.
- AR, struck: it rises, then falls at once, whatever the gate does; ASR rises, holds at full while the note is held, then
  falls; both share the ADSR's curves, and sound different from it and from each other.
- SID ADSR, the home computer chip's own: four settings of 0 to 15 picking from its rate table, a linear attack up to 255, a
  decay and release that fall in six straight segments, each slower, as its exponential counter divides the rate, and a
  sustain of 16 levels, stepped as its 8-bit counter steps (.claude/notes/synthesis/CHIPS.md).
- Vactrol: a light-dependent cell, a fast rise whose time shortens the harder it is struck, then the photoresistor's
  hyperbolic fall, snappy from a bright strike and lingering from a dim one, a strike before the cell has darkened starting
  from what is left, so that a run of hits builds.
- Acid gate: the acid bass's amp, a quick or soft attack and a long fixed fall, an accent swelling it and deepening and
  shortening the filter's sweep, a run of accents charging a capacitor so that each sweep lands higher.
- Chip steps: the handheld chip's envelope of sixteen levels stepped up or down 64 times a second at a pace.

Speed rules this module, as it does the engine (the user's yes): plain attributes, few calls.
"""

import math
import numpy

ADSR = 'adsr'
AR = 'ar'
ASR = 'asr'
SID_ADSR = 'sid_adsr'
VACTROL = 'vactrol'
ACID_GATE = 'acid_gate'
CHIP_STEPS = 'chip_steps'
STRIKE = 'strike'
# A level below this, after the note has ended, is silence: the voice frees itself.
SILENT = 1e-4
# An exponential is 60 dB down after this many time constants.
T60 = 6.908
# Every onset takes at least this long, the drum machine's smoother, so that an attack of 0 never clicks.
SHORTEST_ATTACK = 0.0001
SHORTEST_TIME = 0.001
# The attack curve's knob: at +100 the RC charge aims at 1.01, the most front-loaded; at +50 at 1.5, the analog timer's law;
# toward 0 the target goes far away and the charge straightens into a ramp; below 0 a convex swell, its bend at -100 this.
CURVE_POWER = 5.64
TIMER_CURVE = 50.0
STRAIGHT = 1.0
SWELL_BEND = 5.0
# Snap's fast fall is this many times quicker than the decay.
SNAP_SPEED = 8.0
# The vactrol: its conductance's rise time shrinks with the drive by this power, and its fall is timed to this share of full.
RISE_POWER = 0.7
FALL_TO = 0.01
WEAKEST_DRIVE = 0.05
# A slow leak under the hyperbolic tail, so that the tail ends.
LEAK_SECONDS = 2.0
# Age at full: the LED a quarter dimmer, the rise half again as slow, the fall 60% longer, the memory three times, and each
# hit less alike.
AGE_DIMMING = 0.25
AGE_SLOWER_RISE = 0.5
AGE_LONGER_FALL = 0.6
AGE_MORE_MEMORY = 2.0
AGE_SPREAD = 0.05
AGE_RISE_SPREAD = 0.03
# Stability at none: how much each hit's fall, rise and light vary, as spreads of a normal's exponent, and how far the room's
# warmth moves the fall either way; a hit's light never past this.
FALL_SPREAD = 0.15
RISE_SPREAD = 0.10
LIGHT_SPREAD = 0.08
DRIFT = 0.10
MOST_LIGHT_SPREAD = 1.05
# The room's warmth: three slow sines of these periods in seconds, weights and phases, a function of time alone so that a
# song played from any scene sounds as it does from the top.
WARMTH = ((17.3, 0.5, 0.7), (29.1, 0.3, 2.1), (7.9, 0.2, 4.4))
# A run of strikes may build past a single strike's peak, up to this.
MOST_LIGHT = 1.5
# The acid gate (.claude/notes/synthesis/FILTERS_AND_ACID.md): an accent's sharp attack, the fade at a note's end, how much
# full accent swells the amp and deepens the sweep, and the accent capacitor's charge a step and how fast it empties.
ACCENT_ATTACK = 0.001
END_FADE = 0.008
ACCENT_LOUDER = 0.7
ACCENT_DEEPER = 0.25
ENV_MOD_SHARE = 0.75
CHARGE_STEP = 0.35
CHARGE_SECONDS = 0.5
# The SID chip: its clock, the periods of its sixteen rates in cycles a step (the reference emulation's, each plus one),
# its 8-bit counter, and the exponential counter's divisions as the envelope falls past each level; sustain is S * 17.
SID_CLOCK = 985248.0
SID_PERIODS = (9, 32, 63, 95, 149, 220, 267, 313, 392, 977, 1954, 3126, 3907, 11720, 19532, 31251)
SID_TOP = 255
SID_SUSTAIN_STEP = 17
SID_DIVISIONS = ((93, 1), (54, 2), (26, 4), (14, 8), (6, 16), (0, 30))
# splitmix64's constants.
MIX_STEP = 0x9E3779B97F4A7C15
MIX_ONE = 0xBF58476D1CE4E5B9
MIX_TWO = 0x94D049BB133111EB
MASK = 0xFFFFFFFFFFFFFFFF
# The handheld chip: its envelope steps 64 times a second through fifteen levels, and a note off fades it over 5 ms.
CHIP_TICKS = 64.0
CHIP_LEVELS = 15.0
CHIP_FADE = 0.005


class EnvelopeState:
    """What one voice's envelope keeps: its level where its note ended, the conductance a vactrol started from and where its
    strike ended, and whether it has fallen silent."""

    __slots__ = ('released_from', 'start_level', 'drive', 'done')

    def __init__(self):
        self.released_from = None
        self.start_level = 0.0
        self.drive = 1.0
        self.done = False


class Adsr:
    """The snappy ADSR: attack, hold, decay and release in seconds, the decay and release each the time to fall 60 dB, the
    attack's curve from -100 to +100, Snap and sustain from 0 to 1."""

    __slots__ = ('attack', 'hold', 'decay', 'sustain', 'release', 'snap', 'target', 'bend', 'rate', 'struck')
    # The vactrol alone takes the note's velocity as how hard it is struck; every other envelope is scaled by it after.
    takes_velocity = False

    def __init__(self, *, spec, rate):
        self.attack = max(spec['attack'], SHORTEST_ATTACK)
        self.hold = spec.get('hold', 0.0)
        self.decay = max(spec['decay'], SHORTEST_TIME) / T60
        self.sustain = spec['sustain']
        self.release = max(spec['release'], SHORTEST_TIME) / T60
        self.snap = spec.get('snap', 0.0)
        # An AR is struck: it falls after its attack at its release, the gate unheard; an ASR holds at full.
        self.struck = spec['type'] == AR
        if self.struck:
            self.sustain = 0.0
            self.decay = self.release
        elif spec['type'] == ASR:
            self.sustain = 1.0
        curve = spec.get('attack_curve', TIMER_CURVE)
        # target is where an RC attack aims, None for a ramp; bend shapes a convex swell, None for none.
        self.target = None
        self.bend = None
        if curve > STRAIGHT:
            self.target = 1.0 + 0.5 * (TIMER_CURVE / curve) ** CURVE_POWER
        elif curve < -STRAIGHT:
            self.bend = SWELL_BEND * -curve / 100.0
        self.rate = rate

    def start(self, voice):
        return EnvelopeState()

    def levels(self, *, voice, state, first, count, short=None):
        """Return the envelope over a chunk from its first sample; short, when given, is a decay time in seconds that an accent
        forces in place of the envelope's own."""
        rate = self.rate
        ages = (numpy.arange(first, first + count, dtype=numpy.float64) - voice.start) / rate
        if self.struck:
            out = self._held(ages, short=short)
            if ages[-1] > self.attack and out[-1] < SILENT:
                state.done = True
            return out
        if voice.release_at is None:
            return self._held(ages, short=short)
        released = (voice.release_at - voice.start) / rate
        if state.released_from is None:
            state.released_from = float(self._held(numpy.array([released]), short=short)[0])
        since = ages - released
        falling = state.released_from * numpy.exp(-numpy.maximum(since, 0.0) / self.release)
        if since[-1] >= 0 and falling[-1] < SILENT:
            state.done = True
        return numpy.where(since >= 0, falling, self._held(ages, short=short))

    def _held(self, ages, *, short):
        """Return the envelope while the note is held: the attack, the hold at the top, then the decay to the sustain."""
        attack = self.attack
        x = numpy.minimum(ages / attack, 1.0)
        if self.target is not None:
            target = self.target
            rising = target * (1.0 - numpy.power((target - 1.0) / target, x))
        elif self.bend is not None:
            rising = (numpy.exp(self.bend * x) - 1.0) / (math.exp(self.bend) - 1.0)
        else:
            rising = x
        decay = self.decay
        if short is not None:
            decay = short / T60
        gone = numpy.maximum(ages - attack - self.hold, 0.0)
        fall = numpy.exp(-gone / decay)
        if self.snap:
            fall = (1.0 - self.snap) * fall + self.snap * numpy.exp(-gone * (SNAP_SPEED / decay))
        sustain = self.sustain
        return numpy.where(ages < attack, rising, sustain + (1.0 - sustain) * fall)


class SidAdsr:
    """The SID chip's envelope: the seconds a step of its counter takes at its attack, decay and release, and its sustain
    level of 255; held, its course is a table of times and levels, read between them and stepped as the counter steps."""

    __slots__ = ('attack_step', 'decay_step', 'release_step', 'sustain', 'held_times', 'held_levels', 'rate')
    takes_velocity = False

    def __init__(self, *, spec, rate):
        self.attack_step = SID_PERIODS[spec['attack']] / SID_CLOCK
        self.decay_step = SID_PERIODS[spec['decay']] / SID_CLOCK
        self.release_step = SID_PERIODS[spec['release']] / SID_CLOCK
        self.sustain = spec['sustain'] * SID_SUSTAIN_STEP
        rise = SID_TOP * self.attack_step
        times, levels = sid_fall(start=SID_TOP, floor=self.sustain, step=self.decay_step)
        self.held_times = numpy.array([0.0] + [rise + time for time in times])
        self.held_levels = numpy.array([0.0] + levels)
        self.rate = rate

    def start(self, voice):
        return EnvelopeState()

    def levels(self, *, voice, state, first, count, short=None):
        rate = self.rate
        ages = (numpy.arange(first, first + count, dtype=numpy.float64) - voice.start) / rate
        counter = numpy.interp(ages, self.held_times, self.held_levels)
        if voice.release_at is not None:
            released = (voice.release_at - voice.start) / rate
            if state.released_from is None:
                state.released_from = float(numpy.floor(numpy.interp(released, self.held_times, self.held_levels)))
            times, levels = sid_fall(start=state.released_from, floor=0, step=self.release_step)
            falling = numpy.interp(ages - released, numpy.array(times), numpy.array(levels))
            counter = numpy.where(ages >= released, falling, counter)
            if ages[-1] >= released and falling[-1] < 1.0:
                state.done = True
        return numpy.floor(counter) / SID_TOP


class Vactrol:
    """The vactrol: how long its cell takes to rise and to fall, in seconds, aged; whether each note strikes it with a pulse
    of a width or holds it lit while the note is held; how much a strike's leftover light carries into the next; its age's
    dimmer light and its instability, how much each hit and the slow warmth of the room vary it; and the cell's conductance
    where its last note left it, with how many hits it has had."""

    __slots__ = ('rise', 'fall', 'drive_mode', 'width', 'memory', 'light', 'unstable', 'drift', 'rate', 'left', 'left_at', 'full', 'hits')
    takes_velocity = True

    def __init__(self, *, spec, rate):
        age = spec.get('age', 0.0)
        # Age (.claude/notes/synthesis/ENVELOPES.md, "Vactrol Age and Stability"): a dimmer LED, a slower rise, a longer
        # fall, more memory, and less alike from hit to hit.
        self.light = 1.0 - AGE_DIMMING * age
        self.rise = max(spec['rise'], SHORTEST_ATTACK) * (1.0 + AGE_SLOWER_RISE * age)
        self.fall = max(spec['fall'], SHORTEST_TIME) * (1.0 + AGE_LONGER_FALL * age)
        self.memory = min(1.0, spec['memory'] * (1.0 + AGE_MORE_MEMORY * age))
        unstable = 1.0 - spec.get('stability', 1.0)
        self.unstable = (FALL_SPREAD * unstable + AGE_SPREAD * age, RISE_SPREAD * unstable + AGE_RISE_SPREAD * age,
                         LIGHT_SPREAD * unstable + AGE_SPREAD * age)
        self.drift = DRIFT * unstable
        self.drive_mode = spec['drive']
        self.width = spec['strike_width']
        self.rate = rate
        # A short strike lights a slow cell only partly; the cell is heard scaled so that a full strike from dark peaks at full,
        # a softer one still peaking lower and falling slower, as the hardware does.
        self.full = 1.0
        if self.drive_mode == STRIKE:
            self.full = 1.0 - math.exp(-self.width / (self.rise * self.light ** -RISE_POWER))
        self.left = 0.0
        self.left_at = 0
        self.hits = 0

    def start(self, voice):
        """Start a hit: from the light the last left, its own rise and fall varied by the cell's instability, kept on the state."""
        state = EnvelopeState()
        since = (voice.start - self.left_at) / self.rate
        state.start_level = self.memory * float(self._fallen(level=self.left, seconds=since, hyperbola=(1.0 / FALL_TO - 1.0) / self.fall))
        fall_spread, rise_spread, light_spread = self.unstable
        rise = self.rise
        fall = self.fall
        light = self.light
        if fall_spread or rise_spread or light_spread:
            first, second, third = hit_normals(self.hits)
            warmth = room_warmth(voice.start / self.rate)
            fall *= math.exp(fall_spread * first) * (1.0 + self.drift * warmth)
            rise *= math.exp(rise_spread * second) * (1.0 + 0.5 * self.drift * warmth)
            light = min(light * math.exp(light_spread * third), MOST_LIGHT_SPREAD)
        self.hits += 1
        state.drive = max(voice.level * light, WEAKEST_DRIVE)
        # The hit's rise time, shortened by its drive, and the k of its hyperbolic fall g0 / (1 + k g0 t), timed so that full
        # falls to FALL_TO in the fall time.
        state.released_from = (rise * state.drive ** -RISE_POWER, (1.0 / FALL_TO - 1.0) / fall)
        return state

    def levels(self, *, voice, state, first, count, short=None):
        """Return the cell's conductance over a chunk: rising toward the drive while lit, then falling hyperbolically."""
        rate = self.rate
        ages = (numpy.arange(first, first + count, dtype=numpy.float64) - voice.start) / rate
        lit = self.width
        if self.drive_mode != STRIKE:
            lit = math.inf if voice.release_at is None else (voice.release_at - voice.start) / rate
        drive = state.drive
        tau, hyperbola = state.released_from
        rising = drive + (state.start_level - drive) * numpy.exp(-numpy.minimum(ages, lit) / tau)
        out = rising
        if ages[-1] >= lit:
            peak = drive + (state.start_level - drive) * math.exp(-lit / tau)
            out = numpy.where(ages < lit, rising, self._fallen(level=peak, seconds=numpy.maximum(ages - lit, 0.0), hyperbola=hyperbola))
            if out[-1] < SILENT:
                state.done = True
        self.left = float(out[-1])
        self.left_at = first + count
        return numpy.minimum(out / self.full, MOST_LIGHT)

    @staticmethod
    def _fallen(*, level, seconds, hyperbola):
        """Return the conductance a time after the light went off: the hyperbolic fall, and a slow leak under its tail."""
        return level / (1.0 + hyperbola * level * seconds) * numpy.exp(-seconds / LEAK_SECONDS)


class AcidGate:
    """The acid bass's amp: its accent from 0 to 1, the velocity that accents, how far a run of accents climbs, the accent's
    decay, the amp's long fall and a plain note's soft attack, in seconds, the filter's resonance, which the capacitor is fed
    through, and the capacitor's charge with the sample it was last charged at."""

    __slots__ = ('accent', 'threshold', 'sweep', 'accent_decay', 'amp_decay', 'soft_attack', 'resonance', 'charge', 'charged_at', 'rate')
    takes_velocity = False

    def __init__(self, *, spec, rate, resonance):
        self.accent = spec['accent']
        self.threshold = spec['accent_threshold']
        self.sweep = spec['accent_sweep']
        self.accent_decay = spec['accent_decay']
        self.amp_decay = spec['amp_decay']
        self.soft_attack = max(spec['soft_attack'], SHORTEST_ATTACK)
        self.resonance = resonance
        self.charge = 0.0
        self.charged_at = 0
        self.rate = rate

    def start(self, voice):
        """Start a note: whether it is accented, and for an accent the deeper, shorter sweep it gives the filter."""
        accented = round(voice.level * 127) >= self.threshold
        self.charge *= math.exp(-(voice.start - self.charged_at) / (CHARGE_SECONDS * self.rate))
        self.charged_at = voice.start
        voice.accent_depth = 0.0
        voice.short_decay = None
        if accented:
            self.charge = min(1.0, self.charge + CHARGE_STEP * self.sweep * self.resonance)
            voice.accent_depth = ACCENT_DEEPER * self.accent + self.charge * ENV_MOD_SHARE
            voice.short_decay = self.accent_decay
        state = EnvelopeState()
        state.drive = float(accented)
        return state

    def levels(self, *, voice, state, first, count, short=None):
        rate = self.rate
        places = numpy.arange(first, first + count, dtype=numpy.float64)
        ages = (places - voice.start) / rate
        if state.drive:
            # An accent swells the amp along its own short envelope, a punch rather than a louder note.
            swell = 1.0 + ACCENT_LOUDER * self.accent * numpy.exp(-ages * (T60 / self.accent_decay))
            level = numpy.minimum(ages / ACCENT_ATTACK, 1.0) * numpy.exp(-ages / self.amp_decay) * swell
        else:
            level = numpy.minimum(ages / self.soft_attack, 1.0) * numpy.exp(-ages / self.amp_decay)
        if voice.release_at is not None:
            since = (places - voice.release_at) / rate
            level = level * numpy.clip(1.0 - since / END_FADE, 0.0, 1.0)
            if since[-1] >= END_FADE:
                state.done = True
        return level


class ChipSteps:
    """The handheld chip's envelope: its start level of fifteen, its pace in ticks, 0 holding, and whether it steps up."""

    __slots__ = ('start_level', 'pace', 'up', 'rate')
    takes_velocity = False

    def __init__(self, *, spec, rate):
        self.start_level = spec['start_level']
        self.pace = spec['level_pace']
        self.up = spec['level_up']
        self.rate = rate

    def start(self, voice):
        return EnvelopeState()

    def levels(self, *, voice, state, first, count, short=None):
        rate = self.rate
        seconds = (first - voice.start) / rate
        level = self.start_level
        if self.pace:
            moved = int(seconds * CHIP_TICKS / self.pace)
            level = min(CHIP_LEVELS, level + moved) if self.up else max(0, level - moved)
        if level == 0 and (self.pace or self.start_level == 0) and not self.up:
            state.done = True
        out = numpy.full(count, level / CHIP_LEVELS)
        if voice.release_at is not None:
            since = numpy.arange(first, first + count, dtype=numpy.float64) - voice.release_at
            out = out * numpy.clip(1.0 - since / (CHIP_FADE * rate), 0.0, 1.0)
            if since[-1] >= CHIP_FADE * rate:
                state.done = True
        return out


def hit_normals(hit):
    """Return three standard normals for a vactrol's hit by its number, the same every playing: a splitmix64 hash of the
    number through the Box-Muller transform."""
    first, second = _uniforms(hit * 2 + 1)
    third, fourth = _uniforms(hit * 2 + 2)
    radius = math.sqrt(-2.0 * math.log(first))
    return radius * math.cos(2.0 * math.pi * second), radius * math.sin(2.0 * math.pi * second), math.sqrt(-2.0 * math.log(third)) * math.cos(2.0 * math.pi * fourth)


def room_warmth(seconds):
    """Return the room's warmth from -1 to 1 at a time: slow, smooth and the same every playing."""
    return sum(weight * math.sin(2.0 * math.pi * seconds / period + phase) for period, weight, phase in WARMTH)


def _uniforms(number):
    """Return two uniforms in (0, 1] from a number by splitmix64."""
    out = []
    for step in (number, number + MIX_STEP):
        value = (step * MIX_STEP) & MASK
        value = ((value ^ (value >> 30)) * MIX_ONE) & MASK
        value = ((value ^ (value >> 27)) * MIX_TWO) & MASK
        value ^= value >> 31
        out.append((value + 1) / (MASK + 2))
    return out


def sid_fall(*, start, floor, step):
    """Return the SID chip's fall from a level of its counter to a floor as times in seconds and levels, one straight segment
    for each division of its exponential counter, each slower, a step taking step seconds times the division."""
    times = [0.0]
    levels = [float(start)]
    level = float(start)
    for below, division in SID_DIVISIONS:
        lowest = max(below, floor)
        if level <= lowest:
            continue
        times.append(times[-1] + (level - lowest) * step * division)
        levels.append(float(lowest))
        level = lowest
        if level <= floor:
            break
    return times, levels


def compiled_envelope(*, spec, rate, resonance):
    """Return an envelope module from its settings; resonance is the filter's, which the acid gate's capacitor is fed through."""
    kind = spec['type']
    if kind == VACTROL:
        return Vactrol(spec=spec, rate=rate)
    if kind == ACID_GATE:
        return AcidGate(spec=spec, rate=rate, resonance=resonance)
    if kind == SID_ADSR:
        return SidAdsr(spec=spec, rate=rate)
    if kind == CHIP_STEPS:
        return ChipSteps(spec=spec, rate=rate)
    return Adsr(spec=spec, rate=rate)
