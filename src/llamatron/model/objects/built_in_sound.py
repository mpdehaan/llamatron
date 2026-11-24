# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A built-in instrument's sound, as a set stores it under the instrument: what the Synthesis Process compiles and plays.

A sound has an engine, a volume in percent, up to half again as loud as full, and how many notes it plays at once. A Basic
sound has three oscillators, each a waveform or off, a detune in cents and a level, and an envelope of attack, decay and
release in milliseconds and a sustain level in percent, which a SID sound shares. A drum has a machine and its five knobs,
Pitch, Decay, Color, Shape and Sweep, each 0 to 127, a choke group, 0 for none, and whether its hits ring over each other
rather than cutting the last. A SID sound has a wave, a pulse width and its sweep, ring modulation or sync from a second
oscillator an interval away, an arpeggio of semitones stepped at the chip's frame rate, and glide. A Pocket sound is one of
the handheld chip's voices, a pulse of a duty, the drawn wave of a shape, or noise, long or short, with the chip's stepped
envelope, a start level of sixteen that steps up or down at a pace, and its pitch sweep. Every sound has four effect
blocks, each empty, a bitcrusher of bits and rate, or drive of a curve and amount. Every setting has a default, so a sound
stores only what differs from it and older sets load as they are.
"""

from llamatron.model.file import corrections
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.schema import defaults, file_format, limits
from llamatron.model.schema.file_format import AcidWave, ChipDirection, ChipVoice, Curve, DrumMachine, Duty, Effect, EffectSetting, FilterMode, FilterType, LfoSetting, LfoShape, Modulation, Noise, OscillatorSetting, SidWave, SoundEngine, SoundSetting, SynthControl, Waveform, WaveShape
from llamatron.model.schema.setting import check_settings, Checked, Choice, described, Flag, WholeNumber
from llamatron.user_strings import errors

MILLISECONDS = 1000.0
# The note a drum plays at its own pitch on where nothing says otherwise.
MIDDLE_C = 60
PERCENT = 100.0
# An effect block's settings given as fractions and as seconds.
FRACTIONS = (EffectSetting.AMOUNT, EffectSetting.RESONANCE, EffectSetting.ENVELOPE_AMOUNT, EffectSetting.KEY_TRACK, EffectSetting.FILTER_DRIVE, EffectSetting.MIX)
SECONDS = (EffectSetting.ENVELOPE_ATTACK, EffectSetting.ENVELOPE_DECAY)
# A chip pulse's duty as the share of each cycle it is high.
DUTY_SHARES = {Duty.EIGHTH: 0.125, Duty.QUARTER: 0.25, Duty.HALF: 0.5, Duty.THREE_QUARTERS: 0.75}


def check_oscillators(value):
    """Refuse oscillators that aren't a list of one to three, each a waveform or off, a detune and a level."""
    if not isinstance(value, list) or not 1 <= len(value) <= limits.MAX_OSCILLATORS:
        raise InvalidValue(errors.ERR_BAD_OSCILLATORS.format(most=limits.MAX_OSCILLATORS, value=value))
    for oscillator in value:
        if not isinstance(oscillator, dict) or not set(oscillator) <= set(OSCILLATOR_SETTINGS):
            raise InvalidValue(errors.ERR_BAD_OSCILLATORS.format(most=limits.MAX_OSCILLATORS, value=value))
        check_settings(settings=OSCILLATOR_SETTINGS, data=oscillator)


def check_knobs(value):
    """Refuse knobs that aren't five whole numbers from 0 to 127."""
    if not isinstance(value, list) or len(value) != limits.KNOB_COUNT or any(type(knob) is not int or not 0 <= knob <= limits.MAX_KNOB for knob in value):
        raise InvalidValue(errors.ERR_BAD_KNOBS.format(count=limits.KNOB_COUNT, most=limits.MAX_KNOB, value=value))


def check_arpeggio(value):
    """Refuse an arpeggio that isn't a list of up to eight whole numbers of semitones within two octaves either way."""
    if not isinstance(value, list) or len(value) > limits.MAX_ARPEGGIO_STEPS or any(type(step) is not int or abs(step) > limits.MAX_INTERVAL for step in value):
        raise InvalidValue(errors.ERR_BAD_ARPEGGIO.format(most=limits.MAX_ARPEGGIO_STEPS, highest=limits.MAX_INTERVAL, value=value))


def check_effects(value):
    """Refuse effect blocks that aren't a list of up to four, each a mapping of an effect block's settings."""
    if not isinstance(value, list) or len(value) > limits.EFFECT_BLOCKS:
        raise InvalidValue(errors.ERR_BAD_EFFECTS.format(most=limits.EFFECT_BLOCKS, value=value))
    for block in value:
        if not isinstance(block, dict) or not set(block) <= set(EFFECT_SETTINGS):
            raise InvalidValue(errors.ERR_BAD_EFFECTS.format(most=limits.EFFECT_BLOCKS, value=value))
        check_settings(settings=EFFECT_SETTINGS, data=block)


def check_lfos(value):
    """Refuse LFOs that aren't a list of up to four, each a mapping of an LFO's settings."""
    if not isinstance(value, list) or len(value) > limits.LFO_COUNT:
        raise InvalidValue(errors.ERR_BAD_LFOS.format(most=limits.LFO_COUNT, value=value))
    for lfo in value:
        if not isinstance(lfo, dict) or not set(lfo) <= set(LFO_SETTINGS):
            raise InvalidValue(errors.ERR_BAD_LFOS.format(most=limits.LFO_COUNT, value=value))
        check_settings(settings=LFO_SETTINGS, data=lfo)


def percent(name, *, highest=limits.MAX_PERCENT):
    return WholeNumber(name=name, lowest=0, highest=highest, error=errors.ERR_SOUND_NUMBER)


def milliseconds(name, *, highest=limits.MAX_ENVELOPE_MS):
    return WholeNumber(name=name, lowest=0, highest=highest, error=errors.ERR_SOUND_NUMBER)


def chosen(name, *, choices):
    return Choice(name=name, choices=choices, default=corrections.LEFT_OUT, error=errors.ERR_SOUND_CHOICE)


LFO_SETTINGS = described(
    Flag(name=LfoSetting.ON, error=errors.ERR_SOUND_FLAG),
    chosen(LfoSetting.TARGET, choices=file_format.SYNTH_CONTROLS),
    chosen(LfoSetting.SHAPE, choices=file_format.LFO_SHAPES),
    WholeNumber(name=LfoSetting.RATE, lowest=limits.MIN_LFO_RATE, highest=limits.MAX_LFO_RATE, error=errors.ERR_SOUND_NUMBER),
    WholeNumber(name=LfoSetting.DEPTH, lowest=-limits.MAX_LFO_DEPTH, highest=limits.MAX_LFO_DEPTH, error=errors.ERR_SOUND_NUMBER),
    Flag(name=LfoSetting.RETRIGGER, error=errors.ERR_SOUND_FLAG),
    Flag(name=LfoSetting.EACH_SCENE, error=errors.ERR_SOUND_FLAG),
)
LFO_DEFAULTS = {LfoSetting.ON: False, LfoSetting.TARGET: SynthControl.NONE, LfoSetting.SHAPE: LfoShape.SINE, LfoSetting.RATE: defaults.DEFAULT_LFO_RATE,
                LfoSetting.DEPTH: defaults.DEFAULT_LFO_DEPTH, LfoSetting.RETRIGGER: True, LfoSetting.EACH_SCENE: False}
# An LFO's rate is stored in tenths of a hertz.
TENTHS = 10.0


OSCILLATOR_SETTINGS = described(
    chosen(OscillatorSetting.WAVEFORM, choices=file_format.OSCILLATOR_WAVEFORMS),
    WholeNumber(name=OscillatorSetting.DETUNE, lowest=-limits.MAX_DETUNE_CENTS, highest=limits.MAX_DETUNE_CENTS, error=errors.ERR_SOUND_NUMBER),
    percent(OscillatorSetting.LEVEL),
)
EFFECT_SETTINGS = described(
    chosen(EffectSetting.EFFECT, choices=file_format.EFFECTS),
    WholeNumber(name=EffectSetting.BITS, lowest=limits.MIN_BITS, highest=limits.MAX_BITS, error=errors.ERR_SOUND_NUMBER),
    WholeNumber(name=EffectSetting.RATE, lowest=0, highest=limits.MAX_HOLD_RATE, error=errors.ERR_SOUND_NUMBER),
    chosen(EffectSetting.CURVE, choices=file_format.CURVES),
    percent(EffectSetting.AMOUNT),
    chosen(EffectSetting.FILTER_TYPE, choices=file_format.FILTER_TYPES),
    chosen(EffectSetting.FILTER_MODE, choices=file_format.FILTER_MODES),
    WholeNumber(name=EffectSetting.CUTOFF, lowest=limits.MIN_CUTOFF, highest=limits.MAX_CUTOFF, error=errors.ERR_SOUND_NUMBER),
    percent(EffectSetting.RESONANCE),
    WholeNumber(name=EffectSetting.ENVELOPE_AMOUNT, lowest=-limits.MAX_ENVELOPE_AMOUNT, highest=limits.MAX_ENVELOPE_AMOUNT, error=errors.ERR_SOUND_NUMBER),
    milliseconds(EffectSetting.ENVELOPE_ATTACK),
    milliseconds(EffectSetting.ENVELOPE_DECAY),
    percent(EffectSetting.KEY_TRACK),
    percent(EffectSetting.FILTER_DRIVE),
    percent(EffectSetting.MIX),
)
# What each setting of an effect block is where the block leaves it out.
EFFECT_DEFAULTS = {
    EffectSetting.EFFECT: Effect.NONE, EffectSetting.BITS: defaults.DEFAULT_CRUSH_BITS, EffectSetting.RATE: defaults.DEFAULT_CRUSH_RATE,
    EffectSetting.CURVE: Curve.WARM, EffectSetting.AMOUNT: defaults.DEFAULT_DRIVE_AMOUNT, EffectSetting.FILTER_TYPE: FilterType.LADDER,
    EffectSetting.FILTER_MODE: FilterMode.LOW, EffectSetting.CUTOFF: defaults.DEFAULT_CUTOFF, EffectSetting.RESONANCE: defaults.DEFAULT_RESONANCE,
    EffectSetting.ENVELOPE_AMOUNT: defaults.DEFAULT_ENVELOPE_AMOUNT, EffectSetting.ENVELOPE_ATTACK: defaults.DEFAULT_ENVELOPE_ATTACK,
    EffectSetting.ENVELOPE_DECAY: defaults.DEFAULT_ENVELOPE_DECAY, EffectSetting.KEY_TRACK: defaults.DEFAULT_KEY_TRACK,
    EffectSetting.FILTER_DRIVE: defaults.DEFAULT_FILTER_DRIVE, EffectSetting.MIX: defaults.DEFAULT_MIX,
}

# A sound's settings, each described once, in the order they're written to a file.
SOUND_SETTINGS = described(
    chosen(SoundSetting.ENGINE, choices=file_format.SOUND_ENGINES),
    percent(SoundSetting.VOLUME, highest=limits.MAX_VOLUME_PERCENT),
    WholeNumber(name=SoundSetting.VOICES, lowest=1, highest=limits.MAX_VOICES, error=errors.ERR_SOUND_NUMBER),
    Checked(name=SoundSetting.OSCILLATORS, check=check_oscillators),
    milliseconds(SoundSetting.ATTACK),
    milliseconds(SoundSetting.DECAY),
    percent(SoundSetting.SUSTAIN),
    milliseconds(SoundSetting.RELEASE),
    chosen(SoundSetting.MACHINE, choices=file_format.DRUM_MACHINES),
    Checked(name=SoundSetting.KNOBS, check=check_knobs),
    WholeNumber(name=SoundSetting.CHOKE, lowest=0, highest=limits.MAX_CHOKE, error=errors.ERR_SOUND_NUMBER),
    Flag(name=SoundSetting.OVERLAP, error=errors.ERR_SOUND_FLAG),
    chosen(SoundSetting.WAVE, choices=file_format.SID_WAVES),
    percent(SoundSetting.PULSE_WIDTH),
    WholeNumber(name=SoundSetting.PULSE_SWEEP, lowest=-limits.MAX_PULSE_SWEEP, highest=limits.MAX_PULSE_SWEEP, error=errors.ERR_SOUND_NUMBER),
    chosen(SoundSetting.MODULATION, choices=file_format.MODULATIONS),
    WholeNumber(name=SoundSetting.INTERVAL, lowest=-limits.MAX_INTERVAL, highest=limits.MAX_INTERVAL, error=errors.ERR_SOUND_NUMBER),
    Checked(name=SoundSetting.ARPEGGIO, check=check_arpeggio),
    milliseconds(SoundSetting.GLIDE, highest=limits.MAX_GLIDE_MS),
    chosen(SoundSetting.CHIP_VOICE, choices=file_format.CHIP_VOICES),
    chosen(SoundSetting.DUTY, choices=file_format.DUTIES),
    WholeNumber(name=SoundSetting.START_LEVEL, lowest=0, highest=limits.MAX_CHIP_LEVEL, error=errors.ERR_SOUND_NUMBER),
    WholeNumber(name=SoundSetting.LEVEL_PACE, lowest=0, highest=limits.MAX_CHIP_PACE, error=errors.ERR_SOUND_NUMBER),
    chosen(SoundSetting.LEVEL_DIRECTION, choices=file_format.CHIP_DIRECTIONS),
    WholeNumber(name=SoundSetting.SWEEP_PACE, lowest=0, highest=limits.MAX_CHIP_PACE, error=errors.ERR_SOUND_NUMBER),
    chosen(SoundSetting.SWEEP_DIRECTION, choices=file_format.CHIP_DIRECTIONS),
    WholeNumber(name=SoundSetting.SWEEP_STEP, lowest=limits.MIN_SWEEP_STEP, highest=limits.MAX_SWEEP_STEP, error=errors.ERR_SOUND_NUMBER),
    chosen(SoundSetting.WAVE_SHAPE, choices=file_format.WAVE_SHAPES),
    chosen(SoundSetting.NOISE, choices=file_format.NOISES),
    chosen(SoundSetting.ACID_WAVE, choices=file_format.ACID_WAVES),
    WholeNumber(name=SoundSetting.TUNING, lowest=-limits.MAX_TUNING, highest=limits.MAX_TUNING, error=errors.ERR_SOUND_NUMBER),
    Flag(name=SoundSetting.FILTER_ON, error=errors.ERR_SOUND_FLAG),
    WholeNumber(name=SoundSetting.CUTOFF, lowest=limits.MIN_CUTOFF, highest=limits.MAX_CUTOFF, error=errors.ERR_SOUND_NUMBER),
    percent(SoundSetting.RESONANCE),
    percent(SoundSetting.ENV_MOD),
    WholeNumber(name=SoundSetting.FILTER_DECAY, lowest=limits.MIN_FILTER_DECAY_MS, highest=limits.MAX_FILTER_DECAY_MS, error=errors.ERR_SOUND_NUMBER),
    percent(SoundSetting.ACCENT),
    WholeNumber(name=SoundSetting.ACCENT_THRESHOLD, lowest=1, highest=limits.MAX_VELOCITY_THRESHOLD, error=errors.ERR_SOUND_NUMBER),
    percent(SoundSetting.ACCENT_SWEEP),
    WholeNumber(name=SoundSetting.SLIDE, lowest=limits.MIN_SLIDE_MS, highest=limits.MAX_SLIDE_MS, error=errors.ERR_SOUND_NUMBER),
    percent(SoundSetting.DRIVE),
    WholeNumber(name=SoundSetting.AMP_DECAY, lowest=limits.MIN_AMP_DECAY_MS, highest=limits.MAX_AMP_DECAY_MS, error=errors.ERR_SOUND_NUMBER),
    WholeNumber(name=SoundSetting.SOFT_ATTACK, lowest=limits.MIN_SOFT_ATTACK, highest=limits.MAX_SOFT_ATTACK, error=errors.ERR_SOUND_NUMBER),
    WholeNumber(name=SoundSetting.ACCENT_DECAY, lowest=limits.MIN_ACCENT_DECAY_MS, highest=limits.MAX_ACCENT_DECAY_MS, error=errors.ERR_SOUND_NUMBER),
    Checked(name=SoundSetting.EFFECTS, check=check_effects),
    Checked(name=SoundSetting.LFOS, check=check_lfos),
)
DEFAULT_OSCILLATORS = [{OscillatorSetting.WAVEFORM: Waveform.SAW}]
DEFAULT_KNOBS = [defaults.DEFAULT_KNOB] * limits.KNOB_COUNT
# What each setting is where a sound leaves it out.
SOUND_DEFAULTS = {
    SoundSetting.ENGINE: SoundEngine.BASIC, SoundSetting.VOLUME: defaults.DEFAULT_SOUND_VOLUME, SoundSetting.VOICES: defaults.DEFAULT_VOICES,
    SoundSetting.OSCILLATORS: DEFAULT_OSCILLATORS, SoundSetting.ATTACK: defaults.DEFAULT_ATTACK_MS, SoundSetting.DECAY: defaults.DEFAULT_DECAY_MS,
    SoundSetting.SUSTAIN: defaults.DEFAULT_SUSTAIN_PERCENT, SoundSetting.RELEASE: defaults.DEFAULT_RELEASE_MS, SoundSetting.MACHINE: DrumMachine.KICK,
    SoundSetting.KNOBS: DEFAULT_KNOBS, SoundSetting.CHOKE: 0, SoundSetting.OVERLAP: False, SoundSetting.WAVE: SidWave.PULSE,
    SoundSetting.PULSE_WIDTH: defaults.DEFAULT_PULSE_WIDTH, SoundSetting.PULSE_SWEEP: 0, SoundSetting.MODULATION: Modulation.OFF,
    SoundSetting.INTERVAL: defaults.DEFAULT_INTERVAL, SoundSetting.ARPEGGIO: [], SoundSetting.GLIDE: 0, SoundSetting.CHIP_VOICE: ChipVoice.PULSE,
    SoundSetting.DUTY: Duty.QUARTER, SoundSetting.START_LEVEL: defaults.DEFAULT_START_LEVEL, SoundSetting.LEVEL_PACE: 0,
    SoundSetting.LEVEL_DIRECTION: ChipDirection.DOWN, SoundSetting.SWEEP_PACE: 0, SoundSetting.SWEEP_DIRECTION: ChipDirection.DOWN,
    SoundSetting.SWEEP_STEP: defaults.DEFAULT_SWEEP_STEP, SoundSetting.WAVE_SHAPE: WaveShape.TRIANGLE, SoundSetting.NOISE: Noise.LONG,
    SoundSetting.ACID_WAVE: AcidWave.SAW, SoundSetting.TUNING: 0, SoundSetting.FILTER_ON: True, SoundSetting.CUTOFF: defaults.DEFAULT_ACID_CUTOFF,
    SoundSetting.RESONANCE: defaults.DEFAULT_ACID_RESONANCE, SoundSetting.ENV_MOD: defaults.DEFAULT_ENV_MOD, SoundSetting.FILTER_DECAY: defaults.DEFAULT_FILTER_DECAY_MS,
    SoundSetting.ACCENT: defaults.DEFAULT_ACCENT, SoundSetting.ACCENT_THRESHOLD: defaults.DEFAULT_ACCENT_THRESHOLD, SoundSetting.ACCENT_SWEEP: defaults.DEFAULT_ACCENT_SWEEP,
    SoundSetting.SLIDE: defaults.DEFAULT_SLIDE_MS, SoundSetting.DRIVE: defaults.DEFAULT_ACID_DRIVE, SoundSetting.AMP_DECAY: defaults.DEFAULT_AMP_DECAY_MS,
    SoundSetting.SOFT_ATTACK: defaults.DEFAULT_SOFT_ATTACK, SoundSetting.ACCENT_DECAY: defaults.DEFAULT_ACCENT_DECAY_MS,
    SoundSetting.EFFECTS: [],
    SoundSetting.LFOS: [],
}


def check_sound(value):
    """Refuse a sound that isn't a mapping of a sound's settings, each in range."""
    if not isinstance(value, dict) or not set(value) <= set(SOUND_SETTINGS):
        raise InvalidValue(errors.ERR_BAD_BUILT_IN_SOUND.format(value=value))
    check_settings(settings=SOUND_SETTINGS, data=value)


def sound_value(*, sound, name):
    """Return one of a stored sound's settings, its default where the sound leaves it out: a chip engine plays one note at
    once unless it says otherwise, as the chips' voices do, and every other engine four."""
    if sound is not None and name in sound:
        return sound[name]
    if name == SoundSetting.VOICES and sound_value(sound=sound, name=SoundSetting.ENGINE) in CHIP_ENGINES:
        return 1
    return SOUND_DEFAULTS[name]


# The engines that play one note at once unless they say otherwise.
CHIP_ENGINES = (SoundEngine.SID, SoundEngine.POCKET)


def oscillator_value(*, oscillator, name):
    """Return one of an oscillator's settings, its default where it leaves it out."""
    if name in oscillator:
        return oscillator[name]
    return OSCILLATOR_DEFAULTS[name]


def lfo_value(*, lfo, name):
    """Return one of an LFO's settings, its default where it leaves it out."""
    if name in lfo:
        return lfo[name]
    return LFO_DEFAULTS[name]


def effect_value(*, block, name):
    """Return one of an effect block's settings, its default where it leaves it out."""
    if name in block:
        return block[name]
    return EFFECT_DEFAULTS[name]


OSCILLATOR_DEFAULTS = {OscillatorSetting.WAVEFORM: Waveform.OFF, OscillatorSetting.DETUNE: 0, OscillatorSetting.LEVEL: defaults.DEFAULT_OSCILLATOR_LEVEL}


def synth_spec(sound, *, drums_from=MIDDLE_C):
    """Return a stored sound as the Synthesis Process compiles it: its engine's settings, times in seconds and levels as
    fractions, and its effects in order, the empty blocks left out; a drum plays at its own pitch on the note drums_from,
    the set's drum tuning note, and its other notes tune it from there."""
    return SoundSpec(sound=sound, drums_from=drums_from).spec()


class SoundSpec:
    """A stored sound read for the Synthesis Process, a setting at a time."""

    __slots__ = ('_sound', '_drums_from')

    def __init__(self, *, sound, drums_from):
        self._sound = sound
        self._drums_from = drums_from

    def value(self, name):
        return sound_value(sound=self._sound, name=name)

    def spec(self):
        engine = self.value(SoundSetting.ENGINE)
        spec = {'kind': engine, 'volume': self.value(SoundSetting.VOLUME) / PERCENT, 'voices': self.value(SoundSetting.VOICES), 'effects': self.effects(), 'lfos': self.lfos(engine)}
        if engine == SoundEngine.DRUM:
            spec.update(self.drum())
        elif engine == SoundEngine.SID:
            spec.update(self.sid())
        elif engine == SoundEngine.POCKET:
            spec.update(self.pocket())
        elif engine == SoundEngine.FISHLINE:
            spec.update(self.fishline())
        else:
            spec.update(self.basic())
        return spec

    def envelope(self):
        return [self.value(SoundSetting.ATTACK) / MILLISECONDS, self.value(SoundSetting.DECAY) / MILLISECONDS, self.value(SoundSetting.SUSTAIN) / PERCENT,
                self.value(SoundSetting.RELEASE) / MILLISECONDS]

    def basic(self):
        oscillators = []
        for oscillator in self.value(SoundSetting.OSCILLATORS):
            waveform = oscillator_value(oscillator=oscillator, name=OscillatorSetting.WAVEFORM)
            if waveform != Waveform.OFF:
                level = oscillator_value(oscillator=oscillator, name=OscillatorSetting.LEVEL) / PERCENT
                oscillators.append([waveform, oscillator_value(oscillator=oscillator, name=OscillatorSetting.DETUNE), level])
        return {'oscillators': oscillators, 'envelope': self.envelope()}

    def drum(self):
        return {'machine': self.value(SoundSetting.MACHINE), 'knobs': list(self.value(SoundSetting.KNOBS)), 'choke': self.value(SoundSetting.CHOKE) or None,
                'overlap': self.value(SoundSetting.OVERLAP), 'tuned_from': self._drums_from}

    def sid(self):
        return {'wave': self.value(SoundSetting.WAVE), 'pulse_width': self.value(SoundSetting.PULSE_WIDTH) / PERCENT,
                'pulse_sweep': self.value(SoundSetting.PULSE_SWEEP) / PERCENT, 'modulation': self.value(SoundSetting.MODULATION),
                'interval': self.value(SoundSetting.INTERVAL), 'arpeggio': list(self.value(SoundSetting.ARPEGGIO)),
                'glide': self.value(SoundSetting.GLIDE) / MILLISECONDS, 'envelope': self.envelope()}

    def pocket(self):
        return {'chip_voice': self.value(SoundSetting.CHIP_VOICE), 'duty': DUTY_SHARES[self.value(SoundSetting.DUTY)],
                'start_level': self.value(SoundSetting.START_LEVEL), 'level_pace': self.value(SoundSetting.LEVEL_PACE),
                'level_up': self.value(SoundSetting.LEVEL_DIRECTION) == ChipDirection.UP, 'sweep_pace': self.value(SoundSetting.SWEEP_PACE),
                'sweep_up': self.value(SoundSetting.SWEEP_DIRECTION) == ChipDirection.UP, 'sweep_step': self.value(SoundSetting.SWEEP_STEP),
                'wave_shape': self.value(SoundSetting.WAVE_SHAPE), 'noise': self.value(SoundSetting.NOISE)}

    def fishline(self):
        """Return Fishline's settings, always one voice, shares as fractions and times in seconds."""
        return {'voices': 1, 'acid_wave': self.value(SoundSetting.ACID_WAVE), 'tuning': self.value(SoundSetting.TUNING), 'filter_on': self.value(SoundSetting.FILTER_ON),
                'cutoff': self.value(SoundSetting.CUTOFF), 'resonance': self.value(SoundSetting.RESONANCE) / PERCENT, 'env_mod': self.value(SoundSetting.ENV_MOD) / PERCENT,
                'filter_decay': self.value(SoundSetting.FILTER_DECAY) / MILLISECONDS, 'accent': self.value(SoundSetting.ACCENT) / PERCENT,
                'accent_threshold': self.value(SoundSetting.ACCENT_THRESHOLD), 'accent_sweep': self.value(SoundSetting.ACCENT_SWEEP) / PERCENT,
                'slide': self.value(SoundSetting.SLIDE) / MILLISECONDS, 'drive': self.value(SoundSetting.DRIVE) / PERCENT,
                'amp_decay': self.value(SoundSetting.AMP_DECAY) / MILLISECONDS, 'soft_attack': self.value(SoundSetting.SOFT_ATTACK) / TENTHS / MILLISECONDS,
                'accent_decay': self.value(SoundSetting.ACCENT_DECAY) / MILLISECONDS}

    def lfos(self, engine):
        """Return the LFOs that are on and move something on the engine, each its target, shape, rate in hertz, depth as a
        fraction either way and whether each note starts it again; an LFO that is off, whose target the engine lacks, or that
        has none, left out."""
        lfos = []
        for lfo in self.value(SoundSetting.LFOS):
            target = lfo_value(lfo=lfo, name=LfoSetting.TARGET)
            if not lfo_value(lfo=lfo, name=LfoSetting.ON) or target not in file_format.LFO_TARGETS[engine] or target == SynthControl.NONE:
                continue
            lfos.append({'target': target, 'shape': lfo_value(lfo=lfo, name=LfoSetting.SHAPE), 'rate': lfo_value(lfo=lfo, name=LfoSetting.RATE) / TENTHS,
                         'depth': lfo_value(lfo=lfo, name=LfoSetting.DEPTH) / PERCENT, 'retrigger': lfo_value(lfo=lfo, name=LfoSetting.RETRIGGER),
                         'each_scene': lfo_value(lfo=lfo, name=LfoSetting.EACH_SCENE)})
        return lfos

    def effects(self):
        """Return the effects in order, each a mapping of its settings, every setting given, shares as fractions and times in
        seconds, the empty blocks left out."""
        effects = []
        for block in self.value(SoundSetting.EFFECTS):
            if effect_value(block=block, name=EffectSetting.EFFECT) == Effect.NONE:
                continue
            effect = {name: effect_value(block=block, name=name) for name in EFFECT_DEFAULTS}
            for name in FRACTIONS:
                effect[name] = effect[name] / PERCENT
            for name in SECONDS:
                effect[name] = effect[name] / MILLISECONDS
            effects.append(effect)
        return effects
