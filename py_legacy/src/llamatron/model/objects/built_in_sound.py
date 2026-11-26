# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A built-in instrument's sound, as a set stores it under the instrument: a voice of parts, what the Synthesis Process
compiles and plays (realtime/synth_process/modular.py).

A sound has the engine it was made from, a preset of parts (engine_presets.py); the voice layer, its volume in percent, up to
half again as loud as full, how many notes it plays at once, whether it plays legato, its glide in milliseconds, and whether
its filter is each note's own or shared; its parts, the oscillators, three envelopes and the filter, each a type and that
type's settings (sound_parts.py); its four LFOs; its two effects, each empty, a bitcrusher of bits and rate, or drive of a
curve and amount; and its mod matrix of six slots. Anything a sound leaves out is its engine preset's, and a part's setting
the preset doesn't give is its type's default, so a sound stores only what differs.
"""

from llamatron.model.file import corrections
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects import engine_presets, sound_parts
from llamatron.model.schema import defaults, file_format, limits
from llamatron.model.schema.file_format import ChipDirection, Curve, Duty, Effect, EffectSetting, EnvelopeType, FilterSharing, FilterType, LfoSetting, LfoShape, MatrixDestination, MatrixSetting, MatrixSource, OscillatorSetting, OscillatorType, PartSetting, SoundEngine, SoundPart, SoundSetting, VactrolCell, Waveform
from llamatron.model.schema.setting import check_settings, Checked, Choice, described, Flag, WholeNumber
from llamatron.user_strings import errors

MILLISECONDS = 1000.0
# A vactrol's strike and a gate's ping are stored in tenths of a millisecond, as is the acid gate's soft attack.
TENTHS_OF_MILLISECONDS = 10000.0
# The note a drum plays at its own pitch on where nothing says otherwise.
MIDDLE_C = 60
PERCENT = 100.0
# An LFO's rate is stored in tenths of a hertz.
TENTHS = 10.0
# A chip pulse's duty as the share of each cycle it is high.
DUTY_SHARES = {Duty.EIGHTH: 0.125, Duty.QUARTER: 0.25, Duty.HALF: 0.5, Duty.THREE_QUARTERS: 0.75}
# Each vactrol cell's rise and fall in seconds (.claude/notes/synthesis/ENVELOPES.md, "The Vactrol Sound").
CELLS = {VactrolCell.FAST: (0.0025, 0.035), VactrolCell.CLASSIC: (0.005, 0.08), VactrolCell.SLOW: (0.012, 0.25), VactrolCell.LAZY: (0.02, 0.6)}
# The ladder's slope in decibels an octave a pole.
DB_A_POLE = 6
FOUR_POLES = 4
# The modes a ladder that has no Mode setting passes.
LOW = 'low'
ENVELOPE_PARTS = file_format.ENVELOPE_PARTS


def check_list(value, *, settings, most, error):
    """Refuse a list that isn't up to most mappings, each of the settings given."""
    if not isinstance(value, list) or len(value) > most:
        raise InvalidValue(error.format(most=most, value=value))
    for item in value:
        if not isinstance(item, dict) or not set(item) <= set(settings):
            raise InvalidValue(error.format(most=most, value=value))
        check_settings(settings=settings, data=item)


def check_effects(value):
    check_list(value, settings=EFFECT_SETTINGS, most=limits.EFFECT_BLOCKS, error=errors.ERR_BAD_EFFECTS)


def check_lfos(value):
    check_list(value, settings=LFO_SETTINGS, most=limits.LFO_COUNT, error=errors.ERR_BAD_LFOS)


def check_matrix(value):
    check_list(value, settings=SLOT_SETTINGS, most=limits.MATRIX_SLOTS, error=errors.ERR_BAD_MATRIX)


def check_oscillators(value):
    sound_parts.check_part(part=SoundPart.OSCILLATORS, value=value)


def check_filter(value):
    sound_parts.check_part(part=SoundPart.FILTER, value=value)


def check_envelopes(value):
    """Refuse envelopes that aren't three envelope parts."""
    if not isinstance(value, list) or len(value) != len(ENVELOPE_PARTS):
        raise InvalidValue(errors.ERR_BAD_ENVELOPES.format(value=value))
    for part, envelope in zip(ENVELOPE_PARTS, value):
        sound_parts.check_part(part=part, value=envelope)


def percent(name, *, highest=limits.MAX_PERCENT, lowest=0):
    return WholeNumber(name=name, lowest=lowest, highest=highest, error=errors.ERR_SOUND_NUMBER)


def chosen(name, *, choices):
    return Choice(name=name, choices=choices, default=corrections.LEFT_OUT, error=errors.ERR_SOUND_CHOICE)


LFO_SETTINGS = described(
    Flag(name=LfoSetting.ON, error=errors.ERR_SOUND_FLAG),
    chosen(LfoSetting.SHAPE, choices=file_format.LFO_SHAPES),
    WholeNumber(name=LfoSetting.RATE, lowest=limits.MIN_LFO_RATE, highest=limits.MAX_LFO_RATE, error=errors.ERR_SOUND_NUMBER),
    Flag(name=LfoSetting.RETRIGGER, error=errors.ERR_SOUND_FLAG),
    Flag(name=LfoSetting.EACH_SCENE, error=errors.ERR_SOUND_FLAG),
)
LFO_DEFAULTS = {LfoSetting.ON: False, LfoSetting.SHAPE: LfoShape.SINE, LfoSetting.RATE: defaults.DEFAULT_LFO_RATE, LfoSetting.RETRIGGER: True, LfoSetting.EACH_SCENE: False}
EFFECT_SETTINGS = described(
    chosen(EffectSetting.EFFECT, choices=file_format.EFFECTS),
    WholeNumber(name=EffectSetting.BITS, lowest=limits.MIN_BITS, highest=limits.MAX_BITS, error=errors.ERR_SOUND_NUMBER),
    WholeNumber(name=EffectSetting.RATE, lowest=0, highest=limits.MAX_HOLD_RATE, error=errors.ERR_SOUND_NUMBER),
    chosen(EffectSetting.CURVE, choices=file_format.CURVES),
    percent(EffectSetting.AMOUNT),
    percent(EffectSetting.MIX),
)
# What each setting of an effect is where the effect leaves it out.
EFFECT_DEFAULTS = {EffectSetting.EFFECT: Effect.NONE, EffectSetting.BITS: defaults.DEFAULT_CRUSH_BITS, EffectSetting.RATE: defaults.DEFAULT_CRUSH_RATE,
                   EffectSetting.CURVE: Curve.WARM, EffectSetting.AMOUNT: defaults.DEFAULT_DRIVE_AMOUNT, EffectSetting.MIX: defaults.DEFAULT_MIX}
SLOT_SETTINGS = described(
    chosen(MatrixSetting.SOURCE, choices=file_format.MATRIX_SOURCES),
    chosen(MatrixSetting.VIA, choices=file_format.MATRIX_SOURCES),
    chosen(MatrixSetting.DESTINATION, choices=file_format.MATRIX_DESTINATIONS),
    percent(MatrixSetting.AMOUNT, lowest=-limits.MAX_MATRIX_AMOUNT, highest=limits.MAX_MATRIX_AMOUNT),
)
SLOT_DEFAULTS = {MatrixSetting.SOURCE: MatrixSource.NONE, MatrixSetting.VIA: MatrixSource.NONE, MatrixSetting.DESTINATION: MatrixDestination.NONE,
                 MatrixSetting.AMOUNT: 0}
# A sound's settings, each described once, in the order they're written to a file.
SOUND_SETTINGS = described(
    chosen(SoundSetting.ENGINE, choices=file_format.SOUND_ENGINES),
    percent(SoundSetting.VOLUME, highest=limits.MAX_VOLUME_PERCENT),
    WholeNumber(name=SoundSetting.VOICES, lowest=1, highest=limits.MAX_VOICES, error=errors.ERR_SOUND_NUMBER),
    Flag(name=SoundSetting.LEGATO, error=errors.ERR_SOUND_FLAG),
    percent(SoundSetting.GLIDE, highest=limits.MAX_GLIDE_MS),
    chosen(SoundSetting.FILTER_SHARING, choices=file_format.FILTER_SHARINGS),
    Checked(name=SoundSetting.OSCILLATORS, check=check_oscillators),
    Checked(name=SoundSetting.ENVELOPES, check=check_envelopes),
    Checked(name=SoundSetting.FILTER, check=check_filter),
    Checked(name=SoundSetting.LFOS, check=check_lfos),
    Checked(name=SoundSetting.EFFECTS, check=check_effects),
    Checked(name=SoundSetting.MATRIX, check=check_matrix),
)
# What the engine and volume are where a sound leaves them out; the rest is the engine preset's.
SOUND_DEFAULTS = {SoundSetting.ENGINE: SoundEngine.BASIC, SoundSetting.VOLUME: defaults.DEFAULT_SOUND_VOLUME, SoundSetting.LFOS: []}


def check_sound(value):
    """Refuse a sound that isn't a mapping of a sound's settings, each in range."""
    if not isinstance(value, dict) or not set(value) <= set(SOUND_SETTINGS):
        raise InvalidValue(errors.ERR_BAD_BUILT_IN_SOUND.format(value=value))
    check_settings(settings=SOUND_SETTINGS, data=value)


def sound_value(*, sound, name):
    """Return one of a stored sound's own settings, its engine preset's where the sound leaves it out."""
    if sound is not None and name in sound:
        return sound[name]
    if name in SOUND_DEFAULTS:
        return SOUND_DEFAULTS[name]
    return engine_presets.preset_value(engine=sound_value(sound=sound, name=SoundSetting.ENGINE), name=name)


def part_of(*, sound, part):
    """Return a sound's part as stored, or its engine preset's where it has none."""
    if part == SoundPart.OSCILLATORS or part == SoundPart.FILTER:
        if sound is not None and part in sound:
            return sound[part]
    elif sound is not None and SoundSetting.ENVELOPES in sound:
        return sound[SoundSetting.ENVELOPES][ENVELOPE_PARTS.index(part)]
    return engine_presets.preset_part(engine=sound_value(sound=sound, name=SoundSetting.ENGINE), part=part)


def part_value(*, sound, part, name):
    """Return one setting of a sound's part: the part's own, its engine preset's where the part is still the preset's type,
    or its type's default."""
    stored = part_of(sound=sound, part=part)
    if name in stored:
        return stored[name]
    preset = engine_presets.preset_part(engine=sound_value(sound=sound, name=SoundSetting.ENGINE), part=part)
    if preset[PartSetting.TYPE] == stored[PartSetting.TYPE] and name in preset:
        return preset[name]
    return sound_parts.TYPE_DEFAULTS[stored[PartSetting.TYPE]][name]


def item_value(*, item, name, items_defaults):
    """Return one setting of an LFO, an effect, a slot or an oscillator, its default where it leaves it out."""
    if name in item:
        return item[name]
    return items_defaults[name]


def synth_spec(sound, *, drums_from=MIDDLE_C):
    """Return a stored sound as the Synthesis Process compiles it, its times in seconds and its shares as fractions; a drum plays
    at its own pitch on the note drums_from, the set's drum tuning note."""
    return SoundSpec(sound=sound, drums_from=drums_from).spec()


class SoundSpec:
    """A stored sound read for the Synthesis Process, a part at a time."""

    __slots__ = ('_sound', '_drums_from')

    def __init__(self, *, sound, drums_from):
        self._sound = sound
        self._drums_from = drums_from

    def value(self, name):
        return sound_value(sound=self._sound, name=name)

    def part(self, *, part, name):
        return part_value(sound=self._sound, part=part, name=name)

    def kind(self, part):
        return part_of(sound=self._sound, part=part)[PartSetting.TYPE]

    def spec(self):
        spec = {'kind': self.value(SoundSetting.ENGINE), 'volume': self.value(SoundSetting.VOLUME) / PERCENT, 'voices': self.value(SoundSetting.VOICES),
                'legato': self.value(SoundSetting.LEGATO), 'glide': self.value(SoundSetting.GLIDE) / MILLISECONDS,
                'filter_per_note': self.value(SoundSetting.FILTER_SHARING) == FilterSharing.PER_NOTE, 'oscillators': self.oscillators(),
                'envelopes': [self.envelope(part) for part in ENVELOPE_PARTS], 'filter': self.filter(), 'lfos': self.lfos(), 'effects': self.effects(),
                'matrix': self.matrix()}
        if spec['oscillators']['type'] == OscillatorType.DRUM:
            spec['tuned_from'] = self._drums_from
        return spec

    def oscillators(self):
        """Return the oscillators part as the Synthesis Process reads it (realtime/synth_process/oscillators.py)."""
        kind = self.kind(SoundPart.OSCILLATORS)
        def setting(name):
            return self.part(part=SoundPart.OSCILLATORS, name=name)
        if kind == OscillatorType.DRUM:
            return {'type': kind, 'machine': setting(PartSetting.MACHINE), 'knobs': list(setting(PartSetting.KNOBS)), 'choke': setting(PartSetting.CHOKE) or None,
                    'overlap': setting(PartSetting.OVERLAP)}
        spec = {'type': kind, 'pitch_env': setting(PartSetting.PITCH_ENV)}
        if kind == OscillatorType.SID:
            spec.update(wave=setting(PartSetting.WAVE), pulse_width=setting(PartSetting.PULSE_WIDTH) / PERCENT, pulse_sweep=setting(PartSetting.PULSE_SWEEP) / PERCENT,
                        modulation=setting(PartSetting.MODULATION), interval=setting(PartSetting.INTERVAL), arpeggio=list(setting(PartSetting.ARPEGGIO)))
        elif kind == OscillatorType.POCKET:
            spec.update(chip_voice=setting(PartSetting.CHIP_VOICE), duty=DUTY_SHARES[setting(PartSetting.DUTY)], wave_shape=setting(PartSetting.WAVE_SHAPE),
                        noise=setting(PartSetting.NOISE), sweep_pace=setting(PartSetting.SWEEP_PACE),
                        sweep_up=setting(PartSetting.SWEEP_DIRECTION) == ChipDirection.UP, sweep_step=setting(PartSetting.SWEEP_STEP))
        elif kind == OscillatorType.ACID:
            spec.update(acid_wave=setting(PartSetting.ACID_WAVE), tuning=setting(PartSetting.TUNING))
        else:
            spec['oscillators'] = basic_oscillators(setting(PartSetting.OSCILLATORS))
        return spec

    def envelope(self, part):
        """Return an envelope part as the Synthesis Process reads it (realtime/synth_process/envelopes.py)."""
        kind = self.kind(part)
        def setting(name):
            return self.part(part=part, name=name)
        if kind == EnvelopeType.SID_ADSR:
            return {'type': kind, 'attack': setting(PartSetting.ATTACK), 'decay': setting(PartSetting.DECAY), 'sustain': setting(PartSetting.SUSTAIN),
                    'release': setting(PartSetting.RELEASE)}
        if kind == EnvelopeType.VACTROL:
            rise, fall = CELLS[setting(PartSetting.CELL)]
            return {'type': kind, 'rise': rise, 'fall': fall, 'drive': setting(PartSetting.LIGHT), 'strike_width': setting(PartSetting.STRIKE_WIDTH) / TENTHS_OF_MILLISECONDS,
                    'memory': setting(PartSetting.MEMORY) / PERCENT, 'age': setting(PartSetting.AGE) / PERCENT, 'stability': setting(PartSetting.STABILITY) / PERCENT}
        if kind == EnvelopeType.ACID_GATE:
            return {'type': kind, 'accent': setting(PartSetting.ACCENT) / PERCENT, 'accent_threshold': setting(PartSetting.ACCENT_THRESHOLD),
                    'accent_sweep': setting(PartSetting.ACCENT_SWEEP) / PERCENT, 'accent_decay': setting(PartSetting.ACCENT_DECAY) / MILLISECONDS,
                    'amp_decay': setting(PartSetting.AMP_DECAY) / MILLISECONDS, 'soft_attack': setting(PartSetting.SOFT_ATTACK) / TENTHS_OF_MILLISECONDS}
        if kind == EnvelopeType.CHIP_STEPS:
            return {'type': kind, 'start_level': setting(PartSetting.START_LEVEL), 'level_pace': setting(PartSetting.LEVEL_PACE),
                    'level_up': setting(PartSetting.LEVEL_DIRECTION) == ChipDirection.UP}
        return self.adsr(kind=kind, setting=setting)

    @staticmethod
    def adsr(*, kind, setting):
        """Return the snappy ADSR, AR or ASR: times in seconds, Snap and Sustain as fractions; an AR or ASR has neither hold nor
        decay, and falls at its release."""
        spec = {'type': kind, 'attack': setting(PartSetting.ATTACK) / MILLISECONDS, 'attack_curve': setting(PartSetting.ATTACK_CURVE),
                'release': setting(PartSetting.RELEASE) / MILLISECONDS, 'hold': 0.0, 'decay': setting(PartSetting.RELEASE) / MILLISECONDS, 'snap': 0.0, 'sustain': 0.0}
        if kind == EnvelopeType.ADSR:
            spec.update(hold=setting(PartSetting.HOLD) / MILLISECONDS, decay=setting(PartSetting.DECAY) / MILLISECONDS, snap=setting(PartSetting.SNAP) / PERCENT,
                        sustain=setting(PartSetting.SUSTAIN) / PERCENT)
        return spec

    def filter(self):
        """Return the filter part as the Synthesis Process reads it (filters.py, gates.py), or none."""
        kind = self.kind(SoundPart.FILTER)
        def setting(name):
            return self.part(part=SoundPart.FILTER, name=name)
        if kind == FilterType.NONE:
            return {'type': kind}
        if kind == FilterType.LOW_PASS_GATE:
            return {'type': kind, 'mode': setting(PartSetting.GATE_MODE), 'resonance': setting(PartSetting.RESONANCE) / PERCENT, 'open': setting(PartSetting.OPEN),
                    'key_track': setting(PartSetting.KEY_TRACK) / PERCENT, 'input': setting(PartSetting.INPUT),
                    'ping_width': setting(PartSetting.PING_WIDTH) / TENTHS_OF_MILLISECONDS}
        mode = LOW
        poles = FOUR_POLES
        if kind in (FilterType.MULTIMODE, FilterType.SALLEN_KEY):
            mode = setting(PartSetting.MODE)
        if kind == FilterType.LADDER:
            poles = setting(PartSetting.SLOPE) // DB_A_POLE
        return {'type': kind, 'mode': mode, 'poles': poles, 'cutoff': setting(PartSetting.CUTOFF), 'resonance': setting(PartSetting.RESONANCE) / PERCENT,
                'env_amount': setting(PartSetting.ENV_AMOUNT) / PERCENT, 'key_track': setting(PartSetting.KEY_TRACK) / PERCENT, 'drive': setting(PartSetting.DRIVE) / PERCENT}

    def lfos(self):
        """Return the LFOs in their places, None for one that is off, so that the matrix finds each by its number."""
        lfos = []
        for lfo in self.value(SoundSetting.LFOS):
            def setting(name):
                return item_value(item=lfo, name=name, items_defaults=LFO_DEFAULTS)
            if not setting(LfoSetting.ON):
                lfos.append(None)
                continue
            lfos.append({'shape': setting(LfoSetting.SHAPE), 'rate': setting(LfoSetting.RATE) / TENTHS, 'retrigger': setting(LfoSetting.RETRIGGER),
                         'each_scene': setting(LfoSetting.EACH_SCENE)})
        return lfos

    def effects(self):
        """Return the effects in order, each a mapping of its settings, every setting given, shares as fractions, the empty
        left out."""
        effects = []
        for block in self.value(SoundSetting.EFFECTS):
            effect = {name: item_value(item=block, name=name, items_defaults=EFFECT_DEFAULTS) for name in EFFECT_DEFAULTS}
            if effect[EffectSetting.EFFECT] == Effect.NONE:
                continue
            effect[EffectSetting.AMOUNT] = effect[EffectSetting.AMOUNT] / PERCENT
            effect[EffectSetting.MIX] = effect[EffectSetting.MIX] / PERCENT
            effects.append(effect)
        return effects

    def matrix(self):
        """Return the matrix's slots, each amount a fraction either way."""
        slots = []
        for slot in self.value(SoundSetting.MATRIX):
            routed = {name: item_value(item=slot, name=name, items_defaults=SLOT_DEFAULTS) for name in SLOT_DEFAULTS}
            routed[MatrixSetting.AMOUNT] = routed[MatrixSetting.AMOUNT] / PERCENT
            slots.append(routed)
        return slots


def basic_oscillators(oscillators):
    """Return Basic's oscillators that sound, each (waveform, detune in cents, level as a fraction), those off left out."""
    sounding = []
    for oscillator in oscillators:
        waveform = item_value(item=oscillator, name=OscillatorSetting.WAVEFORM, items_defaults=sound_parts.OSCILLATOR_DEFAULTS)
        if waveform != Waveform.OFF:
            level = item_value(item=oscillator, name=OscillatorSetting.LEVEL, items_defaults=sound_parts.OSCILLATOR_DEFAULTS) / PERCENT
            sounding.append([waveform, item_value(item=oscillator, name=OscillatorSetting.DETUNE, items_defaults=sound_parts.OSCILLATOR_DEFAULTS), level])
    return sounding
