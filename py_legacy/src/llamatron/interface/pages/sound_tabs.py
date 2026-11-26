# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Instrument page's built-in sound, as plain nodes, for one instrument by name: its Role, Kind and Engine above the tabs,
then the Oscillators, Envelopes, Filter and Matrix tabs; the LFOs and FX tabs are in lfo_blocks.py and effect_blocks.py.

The Role shows whether the instrument is normal or percussion, chosen when it was made and never changed. The Kind makes it
off, MIDI or built in. The Engine is a preset of parts: choosing one fills every part from it. The Oscillators tab chooses the
oscillators' type, named by the engine it comes from, beside the voice layer: volume, voices, legato, glide, and whether the
filter is each note's own or shared. The Envelopes tab holds the three envelopes side by side, each choosing its type; the
Filter tab the filter's type and settings; the Matrix tab the six slots, each a source, what scales it, what it moves and how
far. Each built-in tab is drawn dim while the instrument isn't built in.
"""

import functools

from llamatron.interface.forms.nodes import ChoiceField, Field, GaugeField, NumberField, Toggle
from llamatron.interface.forms.tab_box import Tab, TabColumn
from llamatron.interface.pages.part_fields import PartFields
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import MatrixSetting, OscillatorType, SoundPart, SoundSetting
from llamatron.user_strings import labels, marks

OSCILLATOR_NUMBERS = range(1, limits.MAX_OSCILLATORS + 1)
SLOT_NUMBERS = range(1, limits.MATRIX_SLOTS + 1)
# The slot that starts the matrix's second band, so that the six are drawn three over three.
SECOND_ROW_SLOT = 4
SLOT_GAUGE_CELLS = 8


class SoundTabs:
    """An instrument of the set's built-in sound, by name: page is what fields ask through, document what every change goes
    through, as one undo step each."""

    __slots__ = ('_page', '_document', '_name')

    def __init__(self, *, page, document, name):
        self._page = page
        self._document = document
        self._name = name

    def instrument(self):
        return self._document.get_setlist().get_instrument(self._name)

    def part(self, part):
        return PartFields(page=self._page, document=self._document, name=self._name, part=part)

    def above_tabs(self):
        """Return the fields above the tabs: the Role, shown and never changed, the Kind, and the Engine of the Role's engines."""
        instrument = self.instrument()
        role = instrument.get_role()
        kind = instrument.get_kind()
        engines = file_format.ENGINES_OF_ROLE[role]
        engine = instrument.get_sound(SoundSetting.ENGINE)
        if engine not in engines:
            engine = engines[0]
        return [
            Field(label=labels.MSG_ROLE_LABEL, value=lambda: labels.MSG_ROLE_NAMES[role]),
            ChoiceField(page=self._page, label=labels.MSG_INSTRUMENT_KIND_LABEL, choices=list(file_format.INSTRUMENT_KINDS), current=kind,
                        names=[labels.MSG_KIND_NAMES[choice] for choice in file_format.INSTRUMENT_KINDS], shown=labels.MSG_KIND_NAMES[kind], set=self.set_kind),
            ChoiceField(page=self._page, label=labels.MSG_ENGINE_LABEL, choices=list(engines), current=engine, names=[labels.MSG_ENGINE_NAMES[choice] for choice in engines],
                        shown=labels.MSG_ENGINE_NAMES[engine], set=self.set_engine),
        ]

    def oscillators_tab(self):
        """Return the Oscillators tab: the type across its top, then the voice layer, then the type's own columns."""
        oscillators = self.part(SoundPart.OSCILLATORS)
        columns = [TabColumn(heading=labels.MSG_VOICE_HEADING, fields=self.voice_fields())]
        kind = oscillators.kind()
        if kind == OscillatorType.BASIC:
            columns += [TabColumn(heading=labels.MSG_OSCILLATOR_LABEL.format(number=number), fields=oscillators.oscillator_fields(number)) for number in OSCILLATOR_NUMBERS]
        own = oscillators.setting_fields()
        if kind == OscillatorType.DRUM:
            own += oscillators.knob_fields()
        columns.append(TabColumn(heading=labels.MSG_PART_HEADINGS[SoundPart.OSCILLATORS], fields=own))
        return Tab(label=labels.MSG_OSCILLATORS_TAB, top=[oscillators.type_field()], columns=columns, not_ready=self.not_built_in())

    def envelopes_tab(self):
        """Return the Envelopes tab: Env 1 for the amp, Env 2 for the filter, Env 3 for pitch, side by side, each its type first."""
        columns = []
        for part in file_format.ENVELOPE_PARTS:
            envelope = self.part(part)
            columns.append(TabColumn(heading=labels.MSG_PART_HEADINGS[part], fields=[envelope.type_field(), *envelope.setting_fields()]))
        return Tab(label=labels.MSG_ENVELOPES_TAB, columns=columns, not_ready=self.not_built_in())

    def filter_tab(self):
        """Return the Filter tab: its type across the top, then its settings."""
        filter_part = self.part(SoundPart.FILTER)
        return Tab(label=labels.MSG_FILTER_TAB, top=[filter_part.type_field()], columns=[TabColumn(heading=None, fields=filter_part.setting_fields())],
                   not_ready=self.not_built_in())

    def matrix_tab(self):
        """Return the Matrix tab: the six slots, three over three, each boxed."""
        columns = [TabColumn(heading=None, fields=self.slot_fields(number), under=number == SECOND_ROW_SLOT, boxed=True) for number in SLOT_NUMBERS]
        return Tab(label=labels.MSG_MATRIX_TAB, columns=columns, not_ready=self.not_built_in())

    def voice_fields(self):
        """Return the voice layer: volume, voices, legato, glide, and whether the filter is each note's own or shared."""
        instrument = self.instrument()
        sharing = instrument.get_sound(SoundSetting.FILTER_SHARING)
        return [
            GaugeField(page=self._page, label=labels.MSG_VOLUME_LABEL, number=instrument.get_sound(SoundSetting.VOLUME), lowest=0, highest=limits.MAX_VOLUME_PERCENT,
                       set=functools.partial(self.set_sound, name=SoundSetting.VOLUME)),
            NumberField(page=self._page, label=labels.MSG_VOICES_LABEL, number=instrument.get_sound(SoundSetting.VOICES), lowest=1, highest=limits.MAX_VOICES,
                        set=functools.partial(self.set_sound, name=SoundSetting.VOICES)),
            Toggle(label=labels.MSG_LEGATO_LABEL, on=instrument.get_sound(SoundSetting.LEGATO), set=functools.partial(self.set_sound, name=SoundSetting.LEGATO)),
            GaugeField(page=self._page, label=labels.MSG_GLIDE_LABEL, number=instrument.get_sound(SoundSetting.GLIDE), lowest=0, highest=limits.MAX_GLIDE_MS,
                       unit=marks.MSG_MILLISECONDS_SHOWN, logarithmic=True, set=functools.partial(self.set_sound, name=SoundSetting.GLIDE)),
            ChoiceField(page=self._page, label=labels.MSG_FILTER_SHARING_LABEL, choices=list(file_format.FILTER_SHARINGS), current=sharing,
                        names=[labels.MSG_FILTER_SHARING_NAMES[choice] for choice in file_format.FILTER_SHARINGS], shown=labels.MSG_FILTER_SHARING_NAMES[sharing],
                        set=functools.partial(self.set_sound, name=SoundSetting.FILTER_SHARING)),
        ]

    def slot_fields(self, number):
        """Return a slot's fields: its source, what scales it, what it moves, and how far either way."""
        instrument = self.instrument()
        amount = instrument.get_slot(number=number, name=MatrixSetting.AMOUNT)
        return [
            self.slot_choice(number=number, label=labels.MSG_SLOT_SOURCE_LABEL, name=MatrixSetting.SOURCE, choices=file_format.MATRIX_SOURCES,
                             names=labels.MSG_MATRIX_SOURCE_NAMES),
            self.slot_choice(number=number, label=labels.MSG_SLOT_VIA_LABEL, name=MatrixSetting.VIA, choices=file_format.MATRIX_SOURCES, names=labels.MSG_MATRIX_SOURCE_NAMES),
            self.slot_choice(number=number, label=labels.MSG_SLOT_DESTINATION_LABEL, name=MatrixSetting.DESTINATION, choices=file_format.MATRIX_DESTINATIONS,
                             names=labels.MSG_MATRIX_DESTINATION_NAMES),
            NumberField(page=self._page, label=labels.MSG_SLOT_AMOUNT_LABEL.format(number=number), shown_label=labels.MSG_SLOT_SHOWN_LABELS[labels.MSG_SLOT_AMOUNT_LABEL],
                        number=amount, lowest=-limits.MAX_MATRIX_AMOUNT, highest=limits.MAX_MATRIX_AMOUNT, shown=marks.MSG_SIGNED_PERCENT_SHOWN.format(number=amount),
                        set=functools.partial(self.set_slot, number=number, name=MatrixSetting.AMOUNT)),
        ]

    def slot_choice(self, *, number, label, name, choices, names):
        current = self.instrument().get_slot(number=number, name=name)
        return ChoiceField(page=self._page, label=label.format(number=number), shown_label=labels.MSG_SLOT_SHOWN_LABELS[label], choices=list(choices), current=current,
                           names=[names[choice] for choice in choices], shown=names[current], set=functools.partial(self.set_slot, number=number, name=name))

    # Storing what the fields set.

    def not_built_in(self):
        return not self.instrument().is_built_in()

    def set_kind(self, kind):
        self._document.change_set(self.instrument().set_kind, kind)

    def set_engine(self, engine):
        self._document.change_set(self.instrument().set_engine, engine)

    def set_sound(self, value, *, name):
        self._document.change_set(self.instrument().set_sound, name=name, value=value)

    def set_slot(self, value, *, number, name):
        self._document.change_set(self.instrument().set_slot, number=number, name=name, value=value)
