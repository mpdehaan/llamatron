# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A built-in instrument's sound, as a set stores it under the instrument: what the Synthesis Process compiles and plays.

A sound has a family. A Basic sound has up to three oscillators, each a waveform, a detune in cents and a level, an envelope
of attack, decay and release in milliseconds and a sustain level in percent, and how many notes it plays at once. A drum has
a machine and its five knobs, Pitch, Decay, Color, Shape and Sweep, each 0 to 127, a choke group, 0 for none, and whether its
hits ring over each other rather than cutting the last. Every sound has a volume in percent and its effects: the
bitcrusher's bits, 16 for none, and the rate it holds samples at, 0 for none, and drive in percent. Every setting has a
default, so a sound stores only what differs from it and older sets load as they are.
"""

from llamatron.model.file import corrections
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.schema import defaults, file_format, limits
from llamatron.model.schema.file_format import DrumMachine, OscillatorSetting, SoundFamily, SoundSetting, Waveform
from llamatron.model.schema.setting import check_settings, Checked, Choice, described, Flag, WholeNumber
from llamatron.user_strings import errors

MILLISECONDS = 1000.0
PERCENT = 100.0


def check_oscillators(value):
    """Refuse oscillators that aren't a list of one to three, each a waveform, a detune and a level."""
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


OSCILLATOR_SETTINGS = described(
    Choice(name=OscillatorSetting.WAVEFORM, choices=file_format.WAVEFORMS, default=corrections.LEFT_OUT, error=errors.ERR_SOUND_CHOICE),
    WholeNumber(name=OscillatorSetting.DETUNE, lowest=-limits.MAX_DETUNE_CENTS, highest=limits.MAX_DETUNE_CENTS, error=errors.ERR_SOUND_NUMBER),
    WholeNumber(name=OscillatorSetting.LEVEL, lowest=0, highest=limits.MAX_PERCENT, error=errors.ERR_SOUND_NUMBER),
)

# A sound's settings, each described once, in the order they're written to a file.
SOUND_SETTINGS = described(
    Choice(name=SoundSetting.FAMILY, choices=file_format.SOUND_FAMILIES, default=corrections.LEFT_OUT, error=errors.ERR_SOUND_CHOICE),
    Checked(name=SoundSetting.OSCILLATORS, check=check_oscillators),
    WholeNumber(name=SoundSetting.ATTACK, lowest=0, highest=limits.MAX_ENVELOPE_MS, error=errors.ERR_SOUND_NUMBER),
    WholeNumber(name=SoundSetting.DECAY, lowest=0, highest=limits.MAX_ENVELOPE_MS, error=errors.ERR_SOUND_NUMBER),
    WholeNumber(name=SoundSetting.SUSTAIN, lowest=0, highest=limits.MAX_PERCENT, error=errors.ERR_SOUND_NUMBER),
    WholeNumber(name=SoundSetting.RELEASE, lowest=0, highest=limits.MAX_ENVELOPE_MS, error=errors.ERR_SOUND_NUMBER),
    WholeNumber(name=SoundSetting.VOICES, lowest=1, highest=limits.MAX_VOICES, error=errors.ERR_SOUND_NUMBER),
    Choice(name=SoundSetting.MACHINE, choices=file_format.DRUM_MACHINES, default=corrections.LEFT_OUT, error=errors.ERR_SOUND_CHOICE),
    Checked(name=SoundSetting.KNOBS, check=check_knobs),
    WholeNumber(name=SoundSetting.CHOKE, lowest=0, highest=limits.MAX_CHOKE, error=errors.ERR_SOUND_NUMBER),
    Flag(name=SoundSetting.OVERLAP, error=errors.ERR_SOUND_FLAG),
    WholeNumber(name=SoundSetting.VOLUME, lowest=0, highest=limits.MAX_PERCENT, error=errors.ERR_SOUND_NUMBER),
    WholeNumber(name=SoundSetting.BITS, lowest=limits.MIN_BITS, highest=limits.MAX_BITS, error=errors.ERR_SOUND_NUMBER),
    WholeNumber(name=SoundSetting.RATE, lowest=0, highest=limits.MAX_HOLD_RATE, error=errors.ERR_SOUND_NUMBER),
    WholeNumber(name=SoundSetting.DRIVE, lowest=0, highest=limits.MAX_PERCENT, error=errors.ERR_SOUND_NUMBER),
)
DEFAULT_OSCILLATORS = [{OscillatorSetting.WAVEFORM: Waveform.SAW}]
DEFAULT_KNOBS = [defaults.DEFAULT_KNOB] * limits.KNOB_COUNT
# What each setting is where a sound leaves it out.
SOUND_DEFAULTS = {
    SoundSetting.FAMILY: SoundFamily.BASIC, SoundSetting.OSCILLATORS: DEFAULT_OSCILLATORS, SoundSetting.ATTACK: defaults.DEFAULT_ATTACK_MS,
    SoundSetting.DECAY: defaults.DEFAULT_DECAY_MS, SoundSetting.SUSTAIN: defaults.DEFAULT_SUSTAIN_PERCENT, SoundSetting.RELEASE: defaults.DEFAULT_RELEASE_MS,
    SoundSetting.VOICES: defaults.DEFAULT_VOICES, SoundSetting.MACHINE: DrumMachine.KICK, SoundSetting.KNOBS: DEFAULT_KNOBS, SoundSetting.CHOKE: 0,
    SoundSetting.OVERLAP: False, SoundSetting.VOLUME: defaults.DEFAULT_SOUND_VOLUME, SoundSetting.BITS: defaults.DEFAULT_BITS,
    SoundSetting.RATE: defaults.DEFAULT_HOLD_RATE, SoundSetting.DRIVE: defaults.DEFAULT_DRIVE,
}


def check_sound(value):
    """Refuse a sound that isn't a mapping of a sound's settings, each in range."""
    if not isinstance(value, dict) or not set(value) <= set(SOUND_SETTINGS):
        raise InvalidValue(errors.ERR_BAD_BUILT_IN_SOUND.format(value=value))
    check_settings(settings=SOUND_SETTINGS, data=value)


def sound_value(*, sound, name):
    """Return one of a stored sound's settings, its default where the sound leaves it out."""
    if sound is not None and name in sound:
        return sound[name]
    return SOUND_DEFAULTS[name]


def synth_spec(sound):
    """Return a stored sound as the Synthesis Process compiles it: times in seconds and levels as fractions."""
    def value(name):
        return sound_value(sound=sound, name=name)
    effects = [value(SoundSetting.BITS), value(SoundSetting.RATE), value(SoundSetting.DRIVE) / PERCENT]
    volume = value(SoundSetting.VOLUME) / PERCENT
    if value(SoundSetting.FAMILY) == SoundFamily.DRUM:
        choke = value(SoundSetting.CHOKE) or None
        return {'kind': SoundFamily.DRUM, 'machine': value(SoundSetting.MACHINE), 'knobs': list(value(SoundSetting.KNOBS)), 'choke': choke,
                'overlap': value(SoundSetting.OVERLAP), 'volume': volume, 'effects': effects}
    oscillators = []
    for oscillator in value(SoundSetting.OSCILLATORS):
        level = oscillator.get(OscillatorSetting.LEVEL, defaults.DEFAULT_OSCILLATOR_LEVEL) / PERCENT
        oscillators.append([oscillator.get(OscillatorSetting.WAVEFORM, Waveform.SAW), oscillator.get(OscillatorSetting.DETUNE, 0), level])
    envelope = [value(SoundSetting.ATTACK) / MILLISECONDS, value(SoundSetting.DECAY) / MILLISECONDS, value(SoundSetting.SUSTAIN) / PERCENT,
                value(SoundSetting.RELEASE) / MILLISECONDS]
    return {'kind': SoundFamily.BASIC, 'oscillators': oscillators, 'envelope': envelope, 'voices': value(SoundSetting.VOICES), 'volume': volume,
            'effects': effects}
