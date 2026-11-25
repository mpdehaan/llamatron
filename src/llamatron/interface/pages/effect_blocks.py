# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Instrument page's FX tab, as plain nodes, for one instrument by name: the two effects side by side, each choosing its
effect and showing that effect's settings and its Mix.

The bitcrusher shows its bits and its rate; drive its curve and amount. The voice's filter is a part of its own, on the Filter
tab. The tab is drawn dim while the instrument isn't built in.
"""

from llamatron.interface.forms.nodes import ChoiceField, GaugeField, NumberField
from llamatron.interface.forms.tab_box import Tab, TabColumn
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import Effect, EffectSetting
from llamatron.user_strings import labels, marks

# The rates a bitcrusher holds samples at, in hertz, 0 for none, as its picker offers them.
CRUSH_RATES = (0, 32000, 22050, 16000, 11025, 8000, 6000, 4000, 3000, 2000, 1000)
EFFECT_NUMBERS = range(1, limits.EFFECT_BLOCKS + 1)
# The blocks that start a new band, so that the four are drawn two over two, and how many cells a block's gauge has, so
# that two boxed blocks stand side by side at 80 columns.
BLOCK_GAUGE_CELLS = 8


class EffectBlocks:
    """The Effects tab of an instrument of the set, by name: page is what fields ask through, document what every change goes
    through, as one undo step each."""

    __slots__ = ('_page', '_document', '_name')

    def __init__(self, *, page, document, name):
        self._page = page
        self._document = document
        self._name = name

    def instrument(self):
        return self._document.get_setlist().get_instrument(self._name)

    def effects_tab(self):
        """Return the FX tab: the two effects side by side, dim while the instrument isn't built in."""
        columns = [TabColumn(heading=None, fields=self.block_fields(number), boxed=True) for number in EFFECT_NUMBERS]
        return Tab(label=labels.MSG_FX_TAB, columns=columns, not_ready=not self.instrument().is_built_in())

    def block_fields(self, number):
        """Return an effect block's fields: its effect, that effect's own settings, then its Mix; an empty block its effect alone."""
        effect = self.instrument().get_effect(number=number, name=EffectSetting.EFFECT)
        chosen = ChoiceField(page=self._page, label=labels.MSG_EFFECT_BLOCK_LABEL.format(number=number), choices=list(file_format.EFFECTS), current=effect,
                             names=[labels.MSG_EFFECT_NAMES[choice] for choice in file_format.EFFECTS], shown=labels.MSG_EFFECT_NAMES[effect],
                             set=self.setter(number=number, name=EffectSetting.EFFECT))
        if effect == Effect.NONE:
            return [chosen]
        own = {Effect.BITCRUSH: self.bitcrush_fields, Effect.DRIVE: self.drive_fields}[effect](number)
        return [chosen, *own, self.gauge(number=number, label=labels.MSG_EFFECT_MIX_LABEL, name=EffectSetting.MIX)]

    def bitcrush_fields(self, number):
        rate = self.instrument().get_effect(number=number, name=EffectSetting.RATE)
        rates = [str(choice) for choice in CRUSH_RATES]
        return [
            self.number(number=number, label=labels.MSG_EFFECT_BITS_LABEL, name=EffectSetting.BITS, lowest=limits.MIN_BITS, highest=limits.MAX_BITS),
            ChoiceField(page=self._page, label=labels.MSG_EFFECT_RATE_LABEL.format(number=number), shown_label=shown_label(labels.MSG_EFFECT_RATE_LABEL),
                        choices=rates, current=str(rate), names=[rate_shown(choice) for choice in CRUSH_RATES], shown=rate_shown(rate),
                        set=lambda chosen: self.set_effect(number=number, name=EffectSetting.RATE, value=int(chosen))),
        ]

    def drive_fields(self, number):
        return [
            self.choice(number=number, label=labels.MSG_EFFECT_CURVE_LABEL, name=EffectSetting.CURVE, choices=file_format.CURVES, names=labels.MSG_CURVE_NAMES),
            self.gauge(number=number, label=labels.MSG_EFFECT_AMOUNT_LABEL, name=EffectSetting.AMOUNT),
        ]

    # Making fields, and storing what they set.

    def set_effect(self, *, number, name, value):
        self._document.change_set(self.instrument().set_effect, number=number, name=name, value=value)

    def setter(self, *, number, name):
        """Return what stores a value of one of a block's settings, as a field sets it."""
        return lambda value: self.set_effect(number=number, name=name, value=value)

    def choice(self, *, number, label, name, choices, names):
        current = self.instrument().get_effect(number=number, name=name)
        if current not in choices:
            current = choices[0]
        return ChoiceField(page=self._page, label=label.format(number=number), shown_label=shown_label(label), choices=list(choices), current=current,
                           names=[names[choice] for choice in choices], shown=names[current], set=self.setter(number=number, name=name))

    def gauge(self, *, number, label, name, highest=limits.MAX_PERCENT, unit=marks.MSG_SOUND_PERCENT_SHOWN):
        """Return a block's gauge, a share in percent unless a unit is given, a unit filling by its logarithm."""
        return GaugeField(page=self._page, label=label.format(number=number), shown_label=shown_label(label),
                          number=self.instrument().get_effect(number=number, name=name), lowest=0, highest=highest, cells=BLOCK_GAUGE_CELLS, unit=unit,
                          logarithmic=unit != marks.MSG_SOUND_PERCENT_SHOWN, set=self.setter(number=number, name=name))

    def number(self, *, number, label, name, lowest, highest):
        return NumberField(page=self._page, label=label.format(number=number), shown_label=shown_label(label),
                           number=self.instrument().get_effect(number=number, name=name), lowest=lowest, highest=highest, set=self.setter(number=number, name=name))


def shown_label(label):
    """Return a block's field label as the box shows it, without the block's number, which only F1 and the keys need."""
    return labels.MSG_EFFECT_SHOWN_LABELS[label]


def rate_shown(rate):
    """Return how a bitcrusher's rate is shown: off, or its hertz."""
    if rate == 0:
        return marks.MSG_RATE_OFF_SHOWN
    return marks.MSG_HERTZ_SHOWN.format(number=rate)
