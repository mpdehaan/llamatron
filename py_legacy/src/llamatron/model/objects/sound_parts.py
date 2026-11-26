# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The types a built-in voice's parts can be, each with its own settings described once and its own defaults: the
oscillators (Basic, SID, Pocket, Acid, Drum), the envelopes (ADSR, AR, ASR, SID ADSR, Vactrol, Acid gate, Chip steps) and the
filter (none, the ladder family, the low-pass gate).

A part is stored as a mapping of its type and the settings it changes; a setting it leaves out is the engine preset's
where the part is the preset's type (engine_presets.py), and otherwise its type's own default, so that a part dropped in
from another engine sounds as that engine has it and a fresh type starts where it sounds good.
"""

from llamatron.model.file import corrections
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.schema import defaults, file_format, limits
from llamatron.model.schema.file_format import AcidWave, ChipDirection, ChipVoice, DrumMachine, Duty, EnvelopeType, FilterMode, FilterType, GateInput, GateMode, Modulation, Noise, OscillatorSetting, OscillatorType, PartSetting, SidWave, SoundPart, VactrolCell, VactrolLight, Waveform, WaveShape
from llamatron.model.schema.setting import check_settings, Checked, Choice, described, Flag, WholeNumber
from llamatron.user_strings import errors


def number(name, *, lowest=0, highest=limits.MAX_PERCENT):
    return WholeNumber(name=name, lowest=lowest, highest=highest, error=errors.ERR_SOUND_NUMBER)


def chosen(name, *, choices):
    return Choice(name=name, choices=choices, default=corrections.LEFT_OUT, error=errors.ERR_SOUND_CHOICE)


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


OSCILLATOR_SETTINGS = described(
    chosen(OscillatorSetting.WAVEFORM, choices=file_format.OSCILLATOR_WAVEFORMS),
    WholeNumber(name=OscillatorSetting.DETUNE, lowest=-limits.MAX_DETUNE_CENTS, highest=limits.MAX_DETUNE_CENTS, error=errors.ERR_SOUND_NUMBER),
    number(OscillatorSetting.LEVEL),
)
OSCILLATOR_DEFAULTS = {OscillatorSetting.WAVEFORM: Waveform.OFF, OscillatorSetting.DETUNE: 0, OscillatorSetting.LEVEL: defaults.DEFAULT_OSCILLATOR_LEVEL}
PITCH_ENV = number(PartSetting.PITCH_ENV, lowest=-limits.MAX_PITCH_ENV, highest=limits.MAX_PITCH_ENV)
TYPE = Choice(name=PartSetting.TYPE, choices=file_format.OSCILLATOR_TYPES + file_format.ENVELOPE_TYPES + file_format.FILTER_TYPES, default=corrections.LEFT_OUT,
              error=errors.ERR_SOUND_CHOICE)
CUTOFF = number(PartSetting.CUTOFF, lowest=limits.MIN_CUTOFF, highest=limits.MAX_CUTOFF)
ENV_AMOUNT = number(PartSetting.ENV_AMOUNT, lowest=-limits.MAX_ENVELOPE_AMOUNT, highest=limits.MAX_ENVELOPE_AMOUNT)
ATTACK = number(PartSetting.ATTACK, highest=limits.MAX_ENVELOPE_MS)
ATTACK_CURVE = number(PartSetting.ATTACK_CURVE, lowest=-limits.MAX_ATTACK_CURVE, highest=limits.MAX_ATTACK_CURVE)
RELEASE = number(PartSetting.RELEASE, highest=limits.MAX_ENVELOPE_MS)

# Each part's types, each a mapping of its settings, described once, the type itself first.
TYPES = {
    SoundPart.OSCILLATORS: {
        OscillatorType.BASIC: described(TYPE, Checked(name=PartSetting.OSCILLATORS, check=check_oscillators), PITCH_ENV),
        OscillatorType.SID: described(
            TYPE, chosen(PartSetting.WAVE, choices=file_format.SID_WAVES), number(PartSetting.PULSE_WIDTH),
            number(PartSetting.PULSE_SWEEP, lowest=-limits.MAX_PULSE_SWEEP, highest=limits.MAX_PULSE_SWEEP), chosen(PartSetting.MODULATION, choices=file_format.MODULATIONS),
            number(PartSetting.INTERVAL, lowest=-limits.MAX_INTERVAL, highest=limits.MAX_INTERVAL), Checked(name=PartSetting.ARPEGGIO, check=check_arpeggio), PITCH_ENV),
        OscillatorType.POCKET: described(
            TYPE, chosen(PartSetting.CHIP_VOICE, choices=file_format.CHIP_VOICES), chosen(PartSetting.DUTY, choices=file_format.DUTIES),
            chosen(PartSetting.WAVE_SHAPE, choices=file_format.WAVE_SHAPES), chosen(PartSetting.NOISE, choices=file_format.NOISES),
            number(PartSetting.SWEEP_PACE, highest=limits.MAX_CHIP_PACE), chosen(PartSetting.SWEEP_DIRECTION, choices=file_format.CHIP_DIRECTIONS),
            number(PartSetting.SWEEP_STEP, lowest=limits.MIN_SWEEP_STEP, highest=limits.MAX_SWEEP_STEP), PITCH_ENV),
        OscillatorType.ACID: described(TYPE, chosen(PartSetting.ACID_WAVE, choices=file_format.ACID_WAVES),
                                       number(PartSetting.TUNING, lowest=-limits.MAX_TUNING, highest=limits.MAX_TUNING), PITCH_ENV),
        OscillatorType.DRUM: described(TYPE, chosen(PartSetting.MACHINE, choices=file_format.DRUM_MACHINES), Checked(name=PartSetting.KNOBS, check=check_knobs),
                                       number(PartSetting.CHOKE, highest=limits.MAX_CHOKE), Flag(name=PartSetting.OVERLAP, error=errors.ERR_SOUND_FLAG)),
    },
    SoundPart.ENV1: {
        EnvelopeType.ADSR: described(TYPE, ATTACK, ATTACK_CURVE, number(PartSetting.HOLD, highest=limits.MAX_HOLD_MS), number(PartSetting.DECAY, highest=limits.MAX_ENVELOPE_MS),
                                     number(PartSetting.SNAP), number(PartSetting.SUSTAIN), RELEASE),
        EnvelopeType.AR: described(TYPE, ATTACK, ATTACK_CURVE, RELEASE),
        EnvelopeType.ASR: described(TYPE, ATTACK, ATTACK_CURVE, RELEASE),
        EnvelopeType.SID_ADSR: described(TYPE, *(number(name, highest=limits.MAX_SID_RATE) for name in (PartSetting.ATTACK, PartSetting.DECAY, PartSetting.SUSTAIN,
                                                                                                         PartSetting.RELEASE))),
        EnvelopeType.VACTROL: described(TYPE, chosen(PartSetting.CELL, choices=file_format.VACTROL_CELLS), chosen(PartSetting.LIGHT, choices=file_format.VACTROL_LIGHTS),
                                        number(PartSetting.STRIKE_WIDTH, lowest=limits.MIN_STRIKE_WIDTH, highest=limits.MAX_STRIKE_WIDTH), number(PartSetting.MEMORY),
                                        number(PartSetting.AGE), number(PartSetting.STABILITY)),
        EnvelopeType.ACID_GATE: described(
            TYPE, number(PartSetting.ACCENT), number(PartSetting.ACCENT_THRESHOLD, lowest=1, highest=limits.MAX_VELOCITY_THRESHOLD), number(PartSetting.ACCENT_SWEEP),
            number(PartSetting.ACCENT_DECAY, lowest=limits.MIN_ACCENT_DECAY_MS, highest=limits.MAX_ACCENT_DECAY_MS),
            number(PartSetting.AMP_DECAY, lowest=limits.MIN_AMP_DECAY_MS, highest=limits.MAX_AMP_DECAY_MS),
            number(PartSetting.SOFT_ATTACK, lowest=limits.MIN_SOFT_ATTACK, highest=limits.MAX_SOFT_ATTACK)),
        EnvelopeType.CHIP_STEPS: described(TYPE, number(PartSetting.START_LEVEL, highest=limits.MAX_CHIP_LEVEL), number(PartSetting.LEVEL_PACE, highest=limits.MAX_CHIP_PACE),
                                           chosen(PartSetting.LEVEL_DIRECTION, choices=file_format.CHIP_DIRECTIONS)),
    },
    SoundPart.FILTER: {
        FilterType.NONE: described(TYPE),
        FilterType.LADDER: described(TYPE, CUTOFF, number(PartSetting.RESONANCE), chosen(PartSetting.SLOPE, choices=file_format.LADDER_SLOPES), ENV_AMOUNT,
                                     number(PartSetting.KEY_TRACK), number(PartSetting.DRIVE)),
        FilterType.MULTIMODE: described(TYPE, CUTOFF, number(PartSetting.RESONANCE), chosen(PartSetting.MODE, choices=file_format.FILTER_MODES), ENV_AMOUNT,
                                        number(PartSetting.KEY_TRACK), number(PartSetting.DRIVE)),
        FilterType.SALLEN_KEY: described(TYPE, CUTOFF, number(PartSetting.RESONANCE), chosen(PartSetting.MODE, choices=file_format.SALLEN_KEY_MODES), ENV_AMOUNT,
                                         number(PartSetting.KEY_TRACK), number(PartSetting.DRIVE)),
        FilterType.DIODE: described(TYPE, CUTOFF, number(PartSetting.RESONANCE), ENV_AMOUNT, number(PartSetting.KEY_TRACK), number(PartSetting.DRIVE)),
        FilterType.OTA: described(TYPE, CUTOFF, number(PartSetting.RESONANCE), ENV_AMOUNT, number(PartSetting.KEY_TRACK), number(PartSetting.DRIVE)),
        FilterType.LOW_PASS_GATE: described(
            TYPE, chosen(PartSetting.GATE_MODE, choices=file_format.GATE_MODES), number(PartSetting.RESONANCE),
            number(PartSetting.OPEN, lowest=limits.MIN_GATE_OPEN, highest=limits.MAX_GATE_OPEN), number(PartSetting.KEY_TRACK),
            chosen(PartSetting.INPUT, choices=file_format.GATE_INPUTS), number(PartSetting.PING_WIDTH, lowest=limits.MIN_PING_WIDTH, highest=limits.MAX_PING_WIDTH)),
    },
}
# The three envelopes share their types.
TYPES[SoundPart.ENV2] = TYPES[SoundPart.ENV1]
TYPES[SoundPart.ENV3] = TYPES[SoundPart.ENV1]

LADDER_FAMILY = {PartSetting.CUTOFF: defaults.DEFAULT_CUTOFF, PartSetting.RESONANCE: defaults.DEFAULT_RESONANCE, PartSetting.ENV_AMOUNT: defaults.DEFAULT_ENVELOPE_AMOUNT,
                 PartSetting.KEY_TRACK: defaults.DEFAULT_KEY_TRACK, PartSetting.DRIVE: defaults.DEFAULT_FILTER_DRIVE}
SNAPPY = {PartSetting.ATTACK: defaults.DEFAULT_ATTACK_MS, PartSetting.ATTACK_CURVE: defaults.DEFAULT_ATTACK_CURVE, PartSetting.RELEASE: defaults.DEFAULT_RELEASE_MS}
# Each type's own defaults, where neither the part nor its engine's preset says.
TYPE_DEFAULTS = {
    OscillatorType.BASIC: {PartSetting.OSCILLATORS: [{OscillatorSetting.WAVEFORM: Waveform.SAW}], PartSetting.PITCH_ENV: 0},
    OscillatorType.SID: {PartSetting.WAVE: SidWave.PULSE, PartSetting.PULSE_WIDTH: defaults.DEFAULT_PULSE_WIDTH, PartSetting.PULSE_SWEEP: 0,
                         PartSetting.MODULATION: Modulation.OFF, PartSetting.INTERVAL: defaults.DEFAULT_INTERVAL, PartSetting.ARPEGGIO: [], PartSetting.PITCH_ENV: 0},
    OscillatorType.POCKET: {PartSetting.CHIP_VOICE: ChipVoice.PULSE, PartSetting.DUTY: Duty.QUARTER, PartSetting.WAVE_SHAPE: WaveShape.TRIANGLE, PartSetting.NOISE: Noise.LONG,
                            PartSetting.SWEEP_PACE: 0, PartSetting.SWEEP_DIRECTION: ChipDirection.DOWN, PartSetting.SWEEP_STEP: defaults.DEFAULT_SWEEP_STEP,
                            PartSetting.PITCH_ENV: 0},
    OscillatorType.ACID: {PartSetting.ACID_WAVE: AcidWave.SAW, PartSetting.TUNING: 0, PartSetting.PITCH_ENV: 0},
    OscillatorType.DRUM: {PartSetting.MACHINE: DrumMachine.KICK, PartSetting.KNOBS: [defaults.DEFAULT_KNOB] * limits.KNOB_COUNT, PartSetting.CHOKE: 0,
                          PartSetting.OVERLAP: False},
    EnvelopeType.ADSR: {**SNAPPY, PartSetting.HOLD: 0, PartSetting.DECAY: defaults.DEFAULT_DECAY_MS, PartSetting.SNAP: 0,
                        PartSetting.SUSTAIN: defaults.DEFAULT_SUSTAIN_PERCENT},
    EnvelopeType.AR: dict(SNAPPY),
    EnvelopeType.ASR: dict(SNAPPY),
    EnvelopeType.SID_ADSR: {PartSetting.ATTACK: defaults.DEFAULT_SID_ATTACK, PartSetting.DECAY: defaults.DEFAULT_SID_DECAY, PartSetting.SUSTAIN: defaults.DEFAULT_SID_SUSTAIN,
                            PartSetting.RELEASE: defaults.DEFAULT_SID_RELEASE},
    EnvelopeType.VACTROL: {PartSetting.CELL: VactrolCell.SLOW, PartSetting.LIGHT: VactrolLight.STRIKE, PartSetting.STRIKE_WIDTH: defaults.DEFAULT_STRIKE_WIDTH,
                           PartSetting.MEMORY: defaults.DEFAULT_MEMORY, PartSetting.AGE: 0, PartSetting.STABILITY: defaults.DEFAULT_STABILITY},
    EnvelopeType.ACID_GATE: {PartSetting.ACCENT: defaults.DEFAULT_ACCENT, PartSetting.ACCENT_THRESHOLD: defaults.DEFAULT_ACCENT_THRESHOLD,
                             PartSetting.ACCENT_SWEEP: defaults.DEFAULT_ACCENT_SWEEP, PartSetting.ACCENT_DECAY: defaults.DEFAULT_ACCENT_DECAY_MS,
                             PartSetting.AMP_DECAY: defaults.DEFAULT_AMP_DECAY_MS, PartSetting.SOFT_ATTACK: defaults.DEFAULT_SOFT_ATTACK},
    EnvelopeType.CHIP_STEPS: {PartSetting.START_LEVEL: defaults.DEFAULT_START_LEVEL, PartSetting.LEVEL_PACE: 0, PartSetting.LEVEL_DIRECTION: ChipDirection.DOWN},
    FilterType.NONE: {},
    FilterType.LADDER: {**LADDER_FAMILY, PartSetting.SLOPE: file_format.LADDER_SLOPES[-1]},
    FilterType.MULTIMODE: {**LADDER_FAMILY, PartSetting.MODE: FilterMode.LOW},
    FilterType.SALLEN_KEY: {**LADDER_FAMILY, PartSetting.MODE: FilterMode.LOW},
    FilterType.DIODE: dict(LADDER_FAMILY),
    FilterType.OTA: dict(LADDER_FAMILY),
    FilterType.LOW_PASS_GATE: {PartSetting.GATE_MODE: GateMode.BOTH, PartSetting.RESONANCE: 0, PartSetting.OPEN: defaults.DEFAULT_GATE_OPEN, PartSetting.KEY_TRACK: 0,
                               PartSetting.INPUT: GateInput.OSCILLATOR, PartSetting.PING_WIDTH: defaults.DEFAULT_PING_WIDTH},
}


def check_part(*, part, value):
    """Refuse a part that isn't a mapping of one of its types and only that type's settings, each in range."""
    if not isinstance(value, dict) or value.get(PartSetting.TYPE) not in TYPES[part]:
        raise InvalidValue(errors.ERR_BAD_SOUND_PART.format(part=part, value=value))
    settings = TYPES[part][value[PartSetting.TYPE]]
    if not set(value) <= set(settings):
        raise InvalidValue(errors.ERR_BAD_SOUND_PART.format(part=part, value=value))
    check_settings(settings=settings, data=value)


def settings_of(*, part, kind):
    """Return the names of a part's type's settings, its type left out, in the order described."""
    return [name for name in TYPES[part][kind] if name != PartSetting.TYPE]
