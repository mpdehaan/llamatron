# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The fields of a built-in voice's parts, as plain nodes: for one part of an instrument, its type's picker, then a field for
each of its type's settings, each built from what kind of setting it is.

Every setting is one of a few kinds: a share in percent, a gauge; a time in milliseconds or a frequency in hertz, a gauge that
fills by its logarithm, as an ear hears it; a time in tenths of a millisecond; a number with a unit; one of a fixed list of
choices; or on and off. KINDS names each setting's kind and range once, so that a part of any type shows its settings alike.
A field's label is the part's name and the setting's, Env 2 decay, so that every field of the page is told apart; its box
shows the setting's alone.
"""

import functools

from llamatron.interface.forms import nodes
from llamatron.interface.forms.nodes import ChoiceField, Field, GaugeField, NumberField, Toggle
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import EnvelopeType, FilterType, OscillatorSetting, OscillatorType, PartSetting, SoundPart
from llamatron.user_strings import errors, labels, marks, messages

PERCENT = 'percent'
MILLISECONDS = 'milliseconds'
TENTHS = 'tenths'
HERTZ = 'hertz'
NUMBER = 'number'
CHOICE = 'choice'
TOGGLE = 'toggle'
SID_TIME = 'sid_time'
# A number's kind, range and unit; a fifth place, where there is one, says what 0 shows.
NUMBER_PLACES = 4
# Tenths of a millisecond to a millisecond.
TENTHS_A_MILLISECOND = 10
# The SID chip's attack at each of its sixteen rates in milliseconds; its decay and release take three times as long.
SID_ATTACK_MS = (2, 8, 16, 24, 38, 56, 68, 80, 100, 250, 500, 800, 1000, 3000, 5000, 8000)
SID_FALL_TIMES = 3
OSCILLATOR_NUMBERS = range(1, limits.MAX_OSCILLATORS + 1)
KNOB_PLACES = range(limits.KNOB_COUNT)
# How each setting is shown and stepped: its kind, then its lowest and highest, its unit and, for a number whose 0 means none,
# what 0 shows, or its choices and their names.
KINDS = {
    PartSetting.PITCH_ENV: (NUMBER, -limits.MAX_PITCH_ENV, limits.MAX_PITCH_ENV, marks.MSG_SEMITONES_SHOWN),
    PartSetting.WAVE: (CHOICE, file_format.SID_WAVES, labels.MSG_SID_WAVE_NAMES),
    PartSetting.PULSE_WIDTH: (PERCENT, 0, limits.MAX_PERCENT),
    PartSetting.PULSE_SWEEP: (NUMBER, -limits.MAX_PULSE_SWEEP, limits.MAX_PULSE_SWEEP, marks.MSG_SWEEP_SHOWN),
    PartSetting.MODULATION: (CHOICE, file_format.MODULATIONS, labels.MSG_MODULATION_NAMES),
    PartSetting.INTERVAL: (NUMBER, -limits.MAX_INTERVAL, limits.MAX_INTERVAL, marks.MSG_SEMITONES_SHOWN),
    PartSetting.CHIP_VOICE: (CHOICE, file_format.CHIP_VOICES, labels.MSG_CHIP_VOICE_NAMES),
    PartSetting.DUTY: (CHOICE, file_format.DUTIES, labels.MSG_DUTY_NAMES),
    PartSetting.WAVE_SHAPE: (CHOICE, file_format.WAVE_SHAPES, labels.MSG_WAVE_SHAPE_NAMES),
    PartSetting.NOISE: (CHOICE, file_format.NOISES, labels.MSG_NOISE_NAMES),
    PartSetting.SWEEP_PACE: (NUMBER, 0, limits.MAX_CHIP_PACE, marks.MSG_PACE_SHOWN, marks.MSG_PACE_HELD_SHOWN),
    PartSetting.SWEEP_DIRECTION: (CHOICE, file_format.CHIP_DIRECTIONS, labels.MSG_CHIP_DIRECTION_NAMES),
    PartSetting.SWEEP_STEP: (NUMBER, limits.MIN_SWEEP_STEP, limits.MAX_SWEEP_STEP, marks.MSG_NUMBER_SHOWN),
    PartSetting.ACID_WAVE: (CHOICE, file_format.ACID_WAVES, labels.MSG_ACID_WAVE_NAMES),
    PartSetting.TUNING: (NUMBER, -limits.MAX_TUNING, limits.MAX_TUNING, marks.MSG_SEMITONES_SHOWN),
    PartSetting.MACHINE: (CHOICE, file_format.DRUM_MACHINES, labels.MSG_DRUM_MACHINE_NAMES),
    PartSetting.CHOKE: (NUMBER, 0, limits.MAX_CHOKE, marks.MSG_NUMBER_SHOWN, marks.MSG_CHOKE_NONE_SHOWN),
    PartSetting.OVERLAP: (TOGGLE,),
    PartSetting.ATTACK: (MILLISECONDS, 0, limits.MAX_ENVELOPE_MS),
    PartSetting.ATTACK_CURVE: (NUMBER, -limits.MAX_ATTACK_CURVE, limits.MAX_ATTACK_CURVE, marks.MSG_SIGNED_NUMBER_SHOWN),
    PartSetting.HOLD: (MILLISECONDS, 0, limits.MAX_HOLD_MS),
    PartSetting.DECAY: (MILLISECONDS, 0, limits.MAX_ENVELOPE_MS),
    PartSetting.SNAP: (PERCENT, 0, limits.MAX_PERCENT),
    PartSetting.SUSTAIN: (PERCENT, 0, limits.MAX_PERCENT),
    PartSetting.RELEASE: (MILLISECONDS, 0, limits.MAX_ENVELOPE_MS),
    PartSetting.CELL: (CHOICE, file_format.VACTROL_CELLS, labels.MSG_VACTROL_CELL_NAMES),
    PartSetting.LIGHT: (CHOICE, file_format.VACTROL_LIGHTS, labels.MSG_VACTROL_LIGHT_NAMES),
    PartSetting.STRIKE_WIDTH: (TENTHS, limits.MIN_STRIKE_WIDTH, limits.MAX_STRIKE_WIDTH),
    PartSetting.MEMORY: (PERCENT, 0, limits.MAX_PERCENT),
    PartSetting.AGE: (PERCENT, 0, limits.MAX_PERCENT),
    PartSetting.STABILITY: (PERCENT, 0, limits.MAX_PERCENT),
    PartSetting.ACCENT: (PERCENT, 0, limits.MAX_PERCENT),
    PartSetting.ACCENT_THRESHOLD: (NUMBER, 1, limits.MAX_VELOCITY_THRESHOLD, marks.MSG_VELOCITY_AT_SHOWN),
    PartSetting.ACCENT_SWEEP: (PERCENT, 0, limits.MAX_PERCENT),
    PartSetting.ACCENT_DECAY: (MILLISECONDS, limits.MIN_ACCENT_DECAY_MS, limits.MAX_ACCENT_DECAY_MS),
    PartSetting.AMP_DECAY: (MILLISECONDS, limits.MIN_AMP_DECAY_MS, limits.MAX_AMP_DECAY_MS),
    PartSetting.SOFT_ATTACK: (TENTHS, limits.MIN_SOFT_ATTACK, limits.MAX_SOFT_ATTACK),
    PartSetting.START_LEVEL: (NUMBER, 0, limits.MAX_CHIP_LEVEL, marks.MSG_LEVEL_SHOWN),
    PartSetting.LEVEL_PACE: (NUMBER, 0, limits.MAX_CHIP_PACE, marks.MSG_PACE_SHOWN, marks.MSG_PACE_HELD_SHOWN),
    PartSetting.LEVEL_DIRECTION: (CHOICE, file_format.CHIP_DIRECTIONS, labels.MSG_CHIP_DIRECTION_NAMES),
    PartSetting.CUTOFF: (HERTZ, limits.MIN_CUTOFF, limits.MAX_CUTOFF),
    PartSetting.RESONANCE: (PERCENT, 0, limits.MAX_PERCENT),
    PartSetting.SLOPE: (CHOICE, file_format.LADDER_SLOPES, labels.MSG_SLOPE_NAMES),
    PartSetting.MODE: (CHOICE, file_format.FILTER_MODES, labels.MSG_FILTER_MODE_NAMES),
    PartSetting.ENV_AMOUNT: (NUMBER, -limits.MAX_ENVELOPE_AMOUNT, limits.MAX_ENVELOPE_AMOUNT, marks.MSG_SIGNED_PERCENT_SHOWN),
    PartSetting.KEY_TRACK: (PERCENT, 0, limits.MAX_PERCENT),
    PartSetting.DRIVE: (PERCENT, 0, limits.MAX_PERCENT),
    PartSetting.GATE_MODE: (CHOICE, file_format.GATE_MODES, labels.MSG_GATE_MODE_NAMES),
    PartSetting.OPEN: (HERTZ, limits.MIN_GATE_OPEN, limits.MAX_GATE_OPEN),
    PartSetting.INPUT: (CHOICE, file_format.GATE_INPUTS, labels.MSG_GATE_INPUT_NAMES),
    PartSetting.PING_WIDTH: (TENTHS, limits.MIN_PING_WIDTH, limits.MAX_PING_WIDTH),
}
# Where a type's setting is shown otherwise than KINDS says: the SID chip's four rates, its sustain sixteen levels, and the
# Sallen-Key's two modes.
TYPE_KINDS = {
    (EnvelopeType.SID_ADSR, PartSetting.ATTACK): (SID_TIME, 0, limits.MAX_SID_RATE, 1),
    (EnvelopeType.SID_ADSR, PartSetting.DECAY): (SID_TIME, 0, limits.MAX_SID_RATE, SID_FALL_TIMES),
    (EnvelopeType.SID_ADSR, PartSetting.RELEASE): (SID_TIME, 0, limits.MAX_SID_RATE, SID_FALL_TIMES),
    (EnvelopeType.SID_ADSR, PartSetting.SUSTAIN): (NUMBER, 0, limits.MAX_SID_RATE, marks.MSG_LEVEL_SHOWN),
    (FilterType.SALLEN_KEY, PartSetting.MODE): (CHOICE, file_format.SALLEN_KEY_MODES, labels.MSG_FILTER_MODE_NAMES),
}
# Each part's types, in the order its picker lists them, and their names.
PART_TYPES = {SoundPart.OSCILLATORS: (file_format.OSCILLATOR_TYPES, labels.MSG_OSCILLATOR_TYPE_NAMES), SoundPart.FILTER: (file_format.FILTER_TYPES, labels.MSG_FILTER_TYPE_NAMES)}
for envelope_part in file_format.ENVELOPE_PARTS:
    PART_TYPES[envelope_part] = (file_format.ENVELOPE_TYPES, labels.MSG_ENVELOPE_TYPE_NAMES)
# Each type's settings in the order its fields are drawn; Basic's oscillators and a drum's knobs are drawn by fields of their own.
TYPE_SETTINGS = {
    OscillatorType.BASIC: (PartSetting.PITCH_ENV,),
    OscillatorType.SID: (PartSetting.WAVE, PartSetting.PULSE_WIDTH, PartSetting.PULSE_SWEEP, PartSetting.MODULATION, PartSetting.INTERVAL, PartSetting.ARPEGGIO,
                         PartSetting.PITCH_ENV),
    OscillatorType.POCKET: (PartSetting.CHIP_VOICE, PartSetting.DUTY, PartSetting.WAVE_SHAPE, PartSetting.NOISE, PartSetting.SWEEP_PACE, PartSetting.SWEEP_DIRECTION,
                            PartSetting.SWEEP_STEP, PartSetting.PITCH_ENV),
    OscillatorType.ACID: (PartSetting.ACID_WAVE, PartSetting.TUNING, PartSetting.PITCH_ENV),
    OscillatorType.DRUM: (PartSetting.MACHINE, PartSetting.CHOKE, PartSetting.OVERLAP),
    EnvelopeType.ADSR: (PartSetting.ATTACK, PartSetting.ATTACK_CURVE, PartSetting.HOLD, PartSetting.DECAY, PartSetting.SNAP, PartSetting.SUSTAIN, PartSetting.RELEASE),
    EnvelopeType.AR: (PartSetting.ATTACK, PartSetting.ATTACK_CURVE, PartSetting.RELEASE),
    EnvelopeType.ASR: (PartSetting.ATTACK, PartSetting.ATTACK_CURVE, PartSetting.RELEASE),
    EnvelopeType.SID_ADSR: (PartSetting.ATTACK, PartSetting.DECAY, PartSetting.SUSTAIN, PartSetting.RELEASE),
    EnvelopeType.VACTROL: (PartSetting.CELL, PartSetting.LIGHT, PartSetting.STRIKE_WIDTH, PartSetting.MEMORY, PartSetting.AGE, PartSetting.STABILITY),
    EnvelopeType.ACID_GATE: (PartSetting.ACCENT, PartSetting.ACCENT_THRESHOLD, PartSetting.ACCENT_SWEEP, PartSetting.ACCENT_DECAY, PartSetting.AMP_DECAY,
                             PartSetting.SOFT_ATTACK),
    EnvelopeType.CHIP_STEPS: (PartSetting.START_LEVEL, PartSetting.LEVEL_PACE, PartSetting.LEVEL_DIRECTION),
    FilterType.NONE: (),
    FilterType.LADDER: (PartSetting.CUTOFF, PartSetting.RESONANCE, PartSetting.SLOPE, PartSetting.ENV_AMOUNT, PartSetting.KEY_TRACK, PartSetting.DRIVE),
    FilterType.MULTIMODE: (PartSetting.CUTOFF, PartSetting.RESONANCE, PartSetting.MODE, PartSetting.ENV_AMOUNT, PartSetting.KEY_TRACK, PartSetting.DRIVE),
    FilterType.SALLEN_KEY: (PartSetting.CUTOFF, PartSetting.RESONANCE, PartSetting.MODE, PartSetting.ENV_AMOUNT, PartSetting.KEY_TRACK, PartSetting.DRIVE),
    FilterType.DIODE: (PartSetting.CUTOFF, PartSetting.RESONANCE, PartSetting.ENV_AMOUNT, PartSetting.KEY_TRACK, PartSetting.DRIVE),
    FilterType.OTA: (PartSetting.CUTOFF, PartSetting.RESONANCE, PartSetting.ENV_AMOUNT, PartSetting.KEY_TRACK, PartSetting.DRIVE),
    FilterType.LOW_PASS_GATE: (PartSetting.GATE_MODE, PartSetting.INPUT, PartSetting.RESONANCE, PartSetting.OPEN, PartSetting.KEY_TRACK, PartSetting.PING_WIDTH),
}


class PartFields:
    """The fields of one part of an instrument of the set, by name: page is what fields ask through, document what every change
    goes through, as one undo step each."""

    __slots__ = ('_page', '_document', '_name', '_part')

    def __init__(self, *, page, document, name, part):
        self._page = page
        self._document = document
        self._name = name
        self._part = part

    def instrument(self):
        return self._document.get_setlist().get_instrument(self._name)

    def kind(self):
        return self.instrument().get_part_type(self._part)

    def type_field(self):
        """Return the part's type's picker: choosing a type swaps the part for it."""
        kinds, names = PART_TYPES[self._part]
        kind = self.kind()
        return ChoiceField(page=self._page, label=self.label(labels.MSG_PART_TYPE_LABEL), shown_label=labels.MSG_PART_TYPE_LABEL, choices=list(kinds), current=kind,
                           names=[names[choice] for choice in kinds], shown=names[kind], set=self.set_type)

    def setting_fields(self):
        """Return a field for each of the part's type's settings, in order."""
        kind = self.kind()
        fields = []
        for name in TYPE_SETTINGS[kind]:
            if name == PartSetting.ARPEGGIO:
                fields.append(self.arpeggio_field())
                continue
            fields.append(self.setting_field(name=name, how=TYPE_KINDS.get((kind, name), KINDS[name])))
        return fields

    def setting_field(self, *, name, how):
        """Return one setting's field, built as its kind says."""
        what = how[0]
        if what == CHOICE:
            return self.choice(name=name, choices=how[1], names=how[2])
        if what == TOGGLE:
            return Toggle(label=self.label(labels.MSG_PART_SETTING_NAMES[name]), shown_label=labels.MSG_PART_SETTING_NAMES[name], on=self.value(name), set=self.setter(name))
        if what == NUMBER:
            zero = None
            if len(how) > NUMBER_PLACES:
                zero = how[NUMBER_PLACES]
            return self.number(name=name, lowest=how[1], highest=how[2], unit=how[3], zero=zero)
        if what == SID_TIME:
            return self.sid_time(name=name, times=how[3])
        return self.gauge(name=name, what=what, lowest=how[1], highest=how[2])

    def oscillator_fields(self, number):
        """Return one of Basic's oscillators' Wave, Detune and Level, labelled by its number for the keys."""
        instrument = self.instrument()
        def setter(name):
            return functools.partial(self.set_oscillator, number=number, name=name)
        waveform = instrument.get_oscillator(number=number, name=OscillatorSetting.WAVEFORM)
        detune = instrument.get_oscillator(number=number, name=OscillatorSetting.DETUNE)
        return [
            ChoiceField(page=self._page, label=labels.MSG_OSCILLATOR_LABEL.format(number=number), shown_label=labels.MSG_WAVE_LABEL, choices=list(file_format.OSCILLATOR_WAVEFORMS),
                        current=waveform, names=[labels.MSG_WAVEFORM_NAMES[choice] for choice in file_format.OSCILLATOR_WAVEFORMS], shown=labels.MSG_WAVEFORM_NAMES[waveform],
                        set=setter(OscillatorSetting.WAVEFORM)),
            NumberField(page=self._page, label=labels.MSG_OSCILLATOR_DETUNE_LABEL.format(number=number), shown_label=labels.MSG_DETUNE_LABEL, number=detune,
                        lowest=-limits.MAX_DETUNE_CENTS, highest=limits.MAX_DETUNE_CENTS, shown=marks.MSG_CENTS_SHOWN.format(number=detune), set=setter(OscillatorSetting.DETUNE)),
            GaugeField(page=self._page, label=labels.MSG_OSCILLATOR_LEVEL_LABEL.format(number=number), shown_label=labels.MSG_LEVEL_LABEL,
                       number=instrument.get_oscillator(number=number, name=OscillatorSetting.LEVEL), lowest=0, highest=limits.MAX_PERCENT, set=setter(OscillatorSetting.LEVEL)),
        ]

    def knob_fields(self):
        """Return a drum's five knobs."""
        return [GaugeField(page=self._page, label=labels.MSG_KNOB_LABELS[place], number=self.instrument().get_knob(place), lowest=0, highest=limits.MAX_KNOB,
                           unit=marks.MSG_NUMBER_SHOWN, set=functools.partial(self.set_knob, place=place))
                for place in KNOB_PLACES]

    def set_oscillator(self, value, *, number, name):
        self._document.change_set(self.instrument().set_oscillator, number=number, name=name, value=value)

    def set_knob(self, value, *, place):
        self._document.change_set(self.instrument().set_knob, place=place, value=value)

    def arpeggio_field(self):
        """Return the Arpeggio field: semitones from the note, stepped at the chip's frame rate, typed apart by spaces."""
        steps = self.value(PartSetting.ARPEGGIO)
        shown = marks.MSG_ARPEGGIO_SEPARATOR.join(str(step) for step in steps) or marks.MSG_ARPEGGIO_NONE_SHOWN
        return Field(label=labels.MSG_ARPEGGIO_LABEL, value=lambda: shown, enter=self.ask_arpeggio, clear=lambda: self.set_value(name=PartSetting.ARPEGGIO, value=[]),
                     clear_what=marks.MSG_ARPEGGIO_NONE_SHOWN)

    def ask_arpeggio(self):
        typed = marks.MSG_ARPEGGIO_SEPARATOR.join(str(step) for step in self.value(PartSetting.ARPEGGIO))
        self._page.ask_text(title=messages.MSG_ARPEGGIO_PROMPT.format(most=limits.MAX_ARPEGGIO_STEPS), value=typed, then=self.set_arpeggio_text)

    def set_arpeggio_text(self, text):
        """Store an arpeggio typed as semitones apart by spaces, refusing on the status line one that isn't whole numbers in range."""
        words = text.split()
        if not all(word.lstrip('-').isdigit() for word in words):
            self._page.refuse(errors.ERR_BAD_ARPEGGIO.format(most=limits.MAX_ARPEGGIO_STEPS, highest=limits.MAX_INTERVAL, value=text))
            return
        steps = [int(word) for word in words]
        if len(steps) > limits.MAX_ARPEGGIO_STEPS or any(abs(step) > limits.MAX_INTERVAL for step in steps):
            self._page.refuse(errors.ERR_BAD_ARPEGGIO.format(most=limits.MAX_ARPEGGIO_STEPS, highest=limits.MAX_INTERVAL, value=text))
            return
        self.set_value(name=PartSetting.ARPEGGIO, value=steps)

    # Making fields, and storing what they set.

    def label(self, setting):
        return labels.MSG_PART_SETTING_LABEL.format(part=labels.MSG_PART_NAMES[self._part], setting=setting)

    def value(self, name):
        return self.instrument().get_part_setting(part=self._part, name=name)

    def set_type(self, kind):
        self._document.change_set(self.instrument().set_part_type, part=self._part, kind=kind)

    def set_value(self, *, name, value):
        self._document.change_set(self.instrument().set_part_setting, part=self._part, name=name, value=value)

    def setter(self, name):
        """Return what stores a value of one of the part's settings, as a field sets it."""
        return lambda value: self.set_value(name=name, value=value)

    def choice(self, *, name, choices, names):
        current = self.value(name)
        shown_label = labels.MSG_PART_SETTING_NAMES[name]
        return ChoiceField(page=self._page, label=self.label(shown_label), shown_label=shown_label, choices=list(choices), current=current,
                           names=[names[choice] for choice in choices], shown=names[current], set=self.setter(name))

    def number(self, *, name, lowest, highest, unit, zero):
        """Return a number shown in its unit, or as zero says where it is 0 and that means none or held."""
        number = self.value(name)
        shown_label = labels.MSG_PART_SETTING_NAMES[name]
        shown = unit.format(number=number)
        if number == 0 and zero is not None:
            shown = zero
        return NumberField(page=self._page, label=self.label(shown_label), shown_label=shown_label, number=number, lowest=lowest, highest=highest, shown=shown,
                           set=self.setter(name))

    def sid_time(self, *, name, times):
        """Return one of the SID chip's rates, 0 to 15, shown as the time it takes, as the chip's table gives it."""
        rate = self.value(name)
        shown_label = labels.MSG_PART_SETTING_NAMES[name]
        shown = marks.MSG_SID_RATE_SHOWN.format(number=rate, milliseconds=SID_ATTACK_MS[rate] * times)
        return NumberField(page=self._page, label=self.label(shown_label), shown_label=shown_label, number=rate, lowest=0, highest=limits.MAX_SID_RATE, shown=shown,
                           set=self.setter(name))

    def gauge(self, *, name, what, lowest, highest):
        """Return a share in percent, a time in milliseconds or tenths of one, or a frequency in hertz, as a gauge."""
        shown_label = labels.MSG_PART_SETTING_NAMES[name]
        field = GaugeField(page=self._page, label=self.label(shown_label), shown_label=shown_label, number=self.value(name), lowest=lowest, highest=highest,
                           set=self.setter(name))
        if what == MILLISECONDS:
            field.unit = marks.MSG_MILLISECONDS_SHOWN
            field.logarithmic = True
        elif what == TENTHS:
            field.unit = marks.MSG_TENTH_MILLISECONDS_SHOWN
            field.divisor = TENTHS_A_MILLISECOND
            field.logarithmic = True
        elif what == HERTZ:
            field.unit = marks.MSG_HERTZ_SHOWN
            field.logarithmic = True
            field.strides = nodes.HERTZ_STRIDES
            field.longest_stride = nodes.LONGEST_HERTZ_STRIDE
        return field
