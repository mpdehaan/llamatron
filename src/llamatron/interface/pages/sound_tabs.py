# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Instrument page's Synth and Effects tabs, as plain nodes, for one instrument by name.

The Synth tab starts with On, which makes the instrument built in, and its Engine, then the engine's own settings in columns:
Basic's voices, volume, envelope and three oscillators; a drum's machine, volume, choke group, overlap and five knobs; SID's
wave, pulse width and its sweep, ring or sync and its interval, arpeggio, glide, voices, volume and envelope; Pocket's voice,
duty, drawn wave, noise, stepped envelope and pitch sweep. Every share or time is a gauge, stepped by [ and ]. The Effects
tab holds the four effect blocks, two over two, each choosing its effect and showing that effect's settings; it is drawn dim
while the instrument isn't built in.
"""

from llamatron.interface.forms.nodes import ChoiceField, Field, GaugeField, NumberField, Toggle
from llamatron.interface.forms.tab_box import Tab, TabColumn
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import Effect, EffectSetting, InstrumentKind, OscillatorSetting, SoundEngine, SoundSetting
from llamatron.user_strings import errors, labels, marks, messages

# The rates a bitcrusher holds samples at, in hertz, 0 for none, as its picker offers them.
CRUSH_RATES = (0, 32000, 22050, 16000, 11025, 8000, 6000, 4000, 3000, 2000, 1000)
KNOB_PLACES = range(limits.KNOB_COUNT)
OSCILLATOR_NUMBERS = range(1, limits.MAX_OSCILLATORS + 1)
EFFECT_NUMBERS = range(1, limits.EFFECT_BLOCKS + 1)
# The blocks that start a new band, so that the four are drawn two over two.
SECOND_ROW_BLOCK = 3


class SoundTabs:
    """The Synth and Effects tabs of an instrument of the set, by name: page is what fields ask through, document what every
    change goes through, as one undo step each."""

    __slots__ = ('_page', '_document', '_name')

    def __init__(self, *, page, document, name):
        self._page = page
        self._document = document
        self._name = name

    def instrument(self):
        return self._document.get_setlist().get_instrument(self._name)

    def synth_tab(self):
        """Return the Synth tab: On and Engine across its top, then its engine's columns."""
        instrument = self.instrument()
        on = Toggle(label=labels.MSG_SYNTH_ON_LABEL, shown_label=labels.MSG_ON_LABEL, on=instrument.is_built_in(), set=self.set_built_in)
        engine = self.choice(label=labels.MSG_ENGINE_LABEL, name=SoundSetting.ENGINE, choices=file_format.SOUND_ENGINES, names=labels.MSG_ENGINE_NAMES)
        columns = {
            SoundEngine.BASIC: self.basic_columns, SoundEngine.DRUM: self.drum_columns, SoundEngine.SID: self.sid_columns, SoundEngine.POCKET: self.pocket_columns,
        }[instrument.get_sound(SoundSetting.ENGINE)]()
        return Tab(label=labels.MSG_SYNTH_TAB, top=[on, engine], columns=columns, on=instrument.is_built_in())

    def effects_tab(self):
        """Return the Effects tab: the four blocks two over two, dim while the instrument isn't built in."""
        columns = [TabColumn(heading=None, fields=self.block_fields(number), under=number == SECOND_ROW_BLOCK) for number in EFFECT_NUMBERS]
        return Tab(label=labels.MSG_EFFECTS_TAB, columns=columns, not_ready=not self.instrument().is_built_in())

    # Each engine's columns.

    def basic_columns(self):
        oscillators = [TabColumn(heading=labels.MSG_OSCILLATOR_LABEL.format(number=number), fields=self.oscillator_fields(number)) for number in OSCILLATOR_NUMBERS]
        return [TabColumn(heading=labels.MSG_SOUND_HEADING, fields=[self.voices_field(), self.volume_field()]),
                TabColumn(heading=labels.MSG_ENVELOPE_HEADING, fields=self.envelope_fields()), *oscillators]

    def drum_columns(self):
        knobs = [self.knob_field(place) for place in KNOB_PLACES]
        sound = [
            self.choice(label=labels.MSG_MACHINE_LABEL, name=SoundSetting.MACHINE, choices=file_format.DRUM_MACHINES, names=labels.MSG_DRUM_MACHINE_NAMES),
            self.volume_field(), self.choke_field(), self.toggle(label=labels.MSG_OVERLAP_LABEL, name=SoundSetting.OVERLAP),
        ]
        return [TabColumn(heading=labels.MSG_SOUND_HEADING, fields=sound), TabColumn(heading=None, fields=knobs)]

    def sid_columns(self):
        wave = [
            self.choice(label=labels.MSG_WAVE_LABEL, name=SoundSetting.WAVE, choices=file_format.SID_WAVES, names=labels.MSG_SID_WAVE_NAMES),
            self.gauge(label=labels.MSG_PULSE_WIDTH_LABEL, name=SoundSetting.PULSE_WIDTH, highest=limits.MAX_PERCENT),
            self.number(label=labels.MSG_PULSE_SWEEP_LABEL, name=SoundSetting.PULSE_SWEEP, lowest=-limits.MAX_PULSE_SWEEP, highest=limits.MAX_PULSE_SWEEP, unit=marks.MSG_SWEEP_SHOWN),
            self.choice(label=labels.MSG_MODULATION_LABEL, name=SoundSetting.MODULATION, choices=file_format.MODULATIONS, names=labels.MSG_MODULATION_NAMES),
            self.number(label=labels.MSG_INTERVAL_LABEL, name=SoundSetting.INTERVAL, lowest=-limits.MAX_INTERVAL, highest=limits.MAX_INTERVAL, unit=marks.MSG_SEMITONES_SHOWN),
            self.arpeggio_field(),
            self.gauge(label=labels.MSG_GLIDE_LABEL, name=SoundSetting.GLIDE, highest=limits.MAX_GLIDE_MS, timed=True),
        ]
        return [TabColumn(heading=labels.MSG_SOUND_HEADING, fields=[self.voices_field(), self.volume_field()]), TabColumn(heading=labels.MSG_WAVE_LABEL, fields=wave),
                TabColumn(heading=labels.MSG_ENVELOPE_HEADING, fields=self.envelope_fields())]

    def pocket_columns(self):
        voice = [
            self.choice(label=labels.MSG_CHIP_VOICE_LABEL, name=SoundSetting.CHIP_VOICE, choices=file_format.CHIP_VOICES, names=labels.MSG_CHIP_VOICE_NAMES),
            self.choice(label=labels.MSG_DUTY_LABEL, name=SoundSetting.DUTY, choices=file_format.DUTIES, names=labels.MSG_DUTY_NAMES),
            self.choice(label=labels.MSG_WAVE_SHAPE_LABEL, name=SoundSetting.WAVE_SHAPE, choices=file_format.WAVE_SHAPES, names=labels.MSG_WAVE_SHAPE_NAMES),
            self.choice(label=labels.MSG_NOISE_LABEL, name=SoundSetting.NOISE, choices=file_format.NOISES, names=labels.MSG_NOISE_NAMES),
        ]
        return [TabColumn(heading=labels.MSG_SOUND_HEADING, fields=[self.voices_field(), self.volume_field(), *voice]),
                TabColumn(heading=labels.MSG_ENVELOPE_HEADING, fields=self.chip_level_fields()), TabColumn(heading=labels.MSG_SWEEP_HEADING, fields=self.chip_sweep_fields())]

    # Fields shared by several engines.

    def voices_field(self):
        return self.number(label=labels.MSG_VOICES_LABEL, name=SoundSetting.VOICES, lowest=1, highest=limits.MAX_VOICES)

    def volume_field(self):
        return self.gauge(label=labels.MSG_VOLUME_LABEL, name=SoundSetting.VOLUME, highest=limits.MAX_VOLUME_PERCENT)

    def envelope_fields(self):
        return [
            self.gauge(label=labels.MSG_ATTACK_LABEL, name=SoundSetting.ATTACK, highest=limits.MAX_ENVELOPE_MS, timed=True),
            self.gauge(label=labels.MSG_DECAY_LABEL, name=SoundSetting.DECAY, highest=limits.MAX_ENVELOPE_MS, timed=True),
            self.gauge(label=labels.MSG_SUSTAIN_LABEL, name=SoundSetting.SUSTAIN, highest=limits.MAX_PERCENT),
            self.gauge(label=labels.MSG_RELEASE_LABEL, name=SoundSetting.RELEASE, highest=limits.MAX_ENVELOPE_MS, timed=True),
        ]

    def oscillator_fields(self, number):
        """Return an oscillator's Wave, Detune and Level, labelled by its number for the keys and drawn under its heading."""
        instrument = self.instrument()
        def setter(name):
            return lambda value: self._document.change_set(self.instrument().set_oscillator, number=number, name=name, value=value)
        waveform = instrument.get_oscillator(number=number, name=OscillatorSetting.WAVEFORM)
        return [
            ChoiceField(page=self._page, label=labels.MSG_OSCILLATOR_LABEL.format(number=number), shown_label=labels.MSG_WAVE_LABEL, choices=list(file_format.OSCILLATOR_WAVEFORMS),
                        current=waveform, names=[labels.MSG_WAVEFORM_NAMES[choice] for choice in file_format.OSCILLATOR_WAVEFORMS], shown=labels.MSG_WAVEFORM_NAMES[waveform],
                        set=setter(OscillatorSetting.WAVEFORM)),
            NumberField(page=self._page, label=labels.MSG_OSCILLATOR_DETUNE_LABEL.format(number=number), shown_label=labels.MSG_DETUNE_LABEL,
                        number=instrument.get_oscillator(number=number, name=OscillatorSetting.DETUNE), lowest=-limits.MAX_DETUNE_CENTS, highest=limits.MAX_DETUNE_CENTS,
                        shown=marks.MSG_CENTS_SHOWN.format(number=instrument.get_oscillator(number=number, name=OscillatorSetting.DETUNE)), set=setter(OscillatorSetting.DETUNE)),
            GaugeField(page=self._page, label=labels.MSG_OSCILLATOR_LEVEL_LABEL.format(number=number), shown_label=labels.MSG_LEVEL_LABEL,
                       number=instrument.get_oscillator(number=number, name=OscillatorSetting.LEVEL), lowest=0, highest=limits.MAX_PERCENT, set=setter(OscillatorSetting.LEVEL)),
        ]

    def knob_field(self, place):
        return GaugeField(page=self._page, label=labels.MSG_KNOB_LABELS[place], number=self.instrument().get_knob(place), lowest=0, highest=limits.MAX_KNOB,
                          unit=marks.MSG_NUMBER_SHOWN, set=lambda value: self._document.change_set(self.instrument().set_knob, place=place, value=value))

    def choke_field(self):
        choke = self.instrument().get_sound(SoundSetting.CHOKE)
        shown = marks.MSG_CHOKE_NONE_SHOWN if choke == 0 else str(choke)
        return NumberField(page=self._page, label=labels.MSG_CHOKE_LABEL, number=choke, lowest=0, highest=limits.MAX_CHOKE, shown=shown,
                           set=self.setter(SoundSetting.CHOKE))

    def arpeggio_field(self):
        """Return the Arpeggio field: semitones from the note, stepped at the chip's frame rate, typed apart by spaces."""
        steps = self.instrument().get_sound(SoundSetting.ARPEGGIO)
        shown = marks.MSG_ARPEGGIO_SEPARATOR.join(str(step) for step in steps) or marks.MSG_ARPEGGIO_NONE_SHOWN
        return Field(label=labels.MSG_ARPEGGIO_LABEL, value=lambda: shown, enter=self.ask_arpeggio, clear=lambda: self.set_sound(name=SoundSetting.ARPEGGIO, value=[]),
                     clear_what=marks.MSG_ARPEGGIO_NONE_SHOWN)

    def ask_arpeggio(self):
        steps = self.instrument().get_sound(SoundSetting.ARPEGGIO)
        typed = marks.MSG_ARPEGGIO_SEPARATOR.join(str(step) for step in steps)
        self._page.ask_text(title=messages.MSG_ARPEGGIO_PROMPT.format(most=limits.MAX_ARPEGGIO_STEPS), value=typed, then=self.set_arpeggio_text)

    def set_arpeggio_text(self, text):
        """Store an arpeggio typed as semitones apart by spaces, refusing on the status line one that isn't whole numbers in range."""
        try:
            steps = [int(word) for word in text.split()]
        except ValueError:
            steps = None
        if steps is None or len(steps) > limits.MAX_ARPEGGIO_STEPS or any(abs(step) > limits.MAX_INTERVAL for step in steps):
            self._page.refuse(errors.ERR_BAD_ARPEGGIO.format(most=limits.MAX_ARPEGGIO_STEPS, highest=limits.MAX_INTERVAL, value=text))
            return
        self.set_sound(name=SoundSetting.ARPEGGIO, value=steps)

    def chip_level_fields(self):
        level = self.instrument().get_sound(SoundSetting.START_LEVEL)
        return [
            NumberField(page=self._page, label=labels.MSG_START_LEVEL_LABEL, number=level, lowest=0, highest=limits.MAX_CHIP_LEVEL,
                        shown=marks.MSG_LEVEL_SHOWN.format(number=level), set=self.setter(SoundSetting.START_LEVEL)),
            self.pace_field(label=labels.MSG_LEVEL_PACE_LABEL, name=SoundSetting.LEVEL_PACE),
            self.choice(label=labels.MSG_LEVEL_DIRECTION_LABEL, name=SoundSetting.LEVEL_DIRECTION, choices=file_format.CHIP_DIRECTIONS, names=labels.MSG_CHIP_DIRECTION_NAMES),
        ]

    def chip_sweep_fields(self):
        return [
            self.pace_field(label=labels.MSG_SWEEP_PACE_LABEL, name=SoundSetting.SWEEP_PACE),
            self.choice(label=labels.MSG_SWEEP_DIRECTION_LABEL, name=SoundSetting.SWEEP_DIRECTION, choices=file_format.CHIP_DIRECTIONS, names=labels.MSG_CHIP_DIRECTION_NAMES),
            self.number(label=labels.MSG_SWEEP_STEP_LABEL, name=SoundSetting.SWEEP_STEP, lowest=limits.MIN_SWEEP_STEP, highest=limits.MAX_SWEEP_STEP),
        ]

    def pace_field(self, *, label, name):
        """Return a chip's pace, in its ticks, 0 holding still."""
        pace = self.instrument().get_sound(name)
        shown = marks.MSG_PACE_HELD_SHOWN if pace == 0 else marks.MSG_PACE_SHOWN.format(number=pace)
        return NumberField(page=self._page, label=label, number=pace, lowest=0, highest=limits.MAX_CHIP_PACE, shown=shown, set=self.setter(name))

    # The effect blocks.

    def block_fields(self, number):
        """Return an effect block's fields: its effect, then that effect's own settings."""
        instrument = self.instrument()
        effect = instrument.get_effect(number=number, name=EffectSetting.EFFECT)
        chosen = ChoiceField(page=self._page, label=labels.MSG_EFFECT_BLOCK_LABEL.format(number=number), choices=list(file_format.EFFECTS), current=effect,
                             names=[labels.MSG_EFFECT_NAMES[choice] for choice in file_format.EFFECTS], shown=labels.MSG_EFFECT_NAMES[effect],
                             set=self.effect_setter(number=number, name=EffectSetting.EFFECT))
        if effect == Effect.BITCRUSH:
            return [chosen, *self.bitcrush_fields(number)]
        if effect == Effect.DRIVE:
            return [chosen, *self.drive_fields(number)]
        return [chosen]

    def bitcrush_fields(self, number):
        instrument = self.instrument()
        rate = instrument.get_effect(number=number, name=EffectSetting.RATE)
        rates = [str(choice) for choice in CRUSH_RATES]
        return [
            NumberField(page=self._page, label=labels.MSG_EFFECT_BITS_LABEL.format(number=number), shown_label=labels.MSG_BITS_LABEL,
                        number=instrument.get_effect(number=number, name=EffectSetting.BITS), lowest=limits.MIN_BITS, highest=limits.MAX_BITS,
                        set=self.effect_setter(number=number, name=EffectSetting.BITS)),
            ChoiceField(page=self._page, label=labels.MSG_EFFECT_RATE_LABEL.format(number=number), shown_label=labels.MSG_RATE_LABEL, choices=rates, current=str(rate),
                        names=[rate_shown(choice) for choice in CRUSH_RATES], shown=rate_shown(rate),
                        set=lambda chosen: self._document.change_set(self.instrument().set_effect, number=number, name=EffectSetting.RATE, value=int(chosen))),
        ]

    def drive_fields(self, number):
        instrument = self.instrument()
        curve = instrument.get_effect(number=number, name=EffectSetting.CURVE)
        return [
            ChoiceField(page=self._page, label=labels.MSG_EFFECT_CURVE_LABEL.format(number=number), shown_label=labels.MSG_CURVE_LABEL, choices=list(file_format.CURVES),
                        current=curve, names=[labels.MSG_CURVE_NAMES[choice] for choice in file_format.CURVES], shown=labels.MSG_CURVE_NAMES[curve],
                        set=self.effect_setter(number=number, name=EffectSetting.CURVE)),
            GaugeField(page=self._page, label=labels.MSG_EFFECT_AMOUNT_LABEL.format(number=number), shown_label=labels.MSG_AMOUNT_LABEL,
                       number=instrument.get_effect(number=number, name=EffectSetting.AMOUNT), lowest=0, highest=limits.MAX_PERCENT,
                       set=self.effect_setter(number=number, name=EffectSetting.AMOUNT)),
        ]

    def effect_setter(self, *, number, name):
        return lambda value: self._document.change_set(self.instrument().set_effect, number=number, name=name, value=value)

    # Making fields, and storing what they set.

    def set_built_in(self, on):
        """Make the instrument built in, or switch it off: neither MIDI nor built in."""
        kind = InstrumentKind.BUILT_IN if on else InstrumentKind.OFF
        self._document.change_set(self.instrument().set_kind, kind)

    def set_sound(self, *, name, value):
        self._document.change_set(self.instrument().set_sound, name=name, value=value)

    def setter(self, name):
        """Return what stores a value of one of the sound's settings, as a field sets it."""
        return lambda value: self.set_sound(name=name, value=value)

    def choice(self, *, label, name, choices, names):
        current = self.instrument().get_sound(name)
        return ChoiceField(page=self._page, label=label, choices=list(choices), current=current, names=[names[choice] for choice in choices], shown=names[current],
                           set=self.setter(name))

    def gauge(self, *, label, name, highest, timed=False):
        unit = marks.MSG_MILLISECONDS_SHOWN if timed else marks.MSG_SOUND_PERCENT_SHOWN
        return GaugeField(page=self._page, label=label, number=self.instrument().get_sound(name), lowest=0, highest=highest, unit=unit, timed=timed,
                          set=self.setter(name))

    def number(self, *, label, name, lowest, highest, unit=None):
        number = self.instrument().get_sound(name)
        shown = None if unit is None else unit.format(number=number)
        return NumberField(page=self._page, label=label, number=number, lowest=lowest, highest=highest, shown=shown, set=self.setter(name))

    def toggle(self, *, label, name):
        return Toggle(label=label, on=self.instrument().get_sound(name), set=self.setter(name))


def rate_shown(rate):
    """Return how a bitcrusher's rate is shown: off, or its hertz."""
    if rate == 0:
        return marks.MSG_RATE_OFF_SHOWN
    return marks.MSG_HERTZ_SHOWN.format(number=rate)
