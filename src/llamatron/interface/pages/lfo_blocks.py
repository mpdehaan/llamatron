# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Instrument page's LFOs tab, as plain nodes, for one instrument by name: four LFOs, two over two, each switched on or off,
off for a new one, then its shape, its rate in hertz, whether each note starts it again and whether each scene does. What an
LFO moves, and how far, is the Matrix tab's. The tab is drawn dim while the instrument isn't built in.
"""

from llamatron.interface.forms.nodes import ChoiceField, GaugeField, Toggle
from llamatron.interface.forms.tab_box import Tab, TabColumn
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import LfoSetting
from llamatron.user_strings import labels, marks

LFO_NUMBERS = range(1, limits.LFO_COUNT + 1)
# The LFO that starts the second band, so that the four are drawn two over two, and how many cells an LFO's gauge has.
SECOND_ROW_LFO = 3
LFO_GAUGE_CELLS = 8
# An LFO's rate is stored in tenths of a hertz; [ and ] step it by more as it grows.
TENTHS = 10
RATE_STRIDES = ((20, 1), (50, 2), (100, 5), (300, 10), (600, 25))
LONGEST_RATE_STRIDE = 50


class LfoBlocks:
    """The LFOs tab of an instrument of the set, by name: page is what fields ask through, document what every change goes
    through, as one undo step each."""

    __slots__ = ('_page', '_document', '_name')

    def __init__(self, *, page, document, name):
        self._page = page
        self._document = document
        self._name = name

    def instrument(self):
        return self._document.get_setlist().get_instrument(self._name)

    def lfos_tab(self):
        """Return the LFOs tab: the four LFOs two over two, dim while the instrument isn't built in."""
        columns = [TabColumn(heading=None, fields=self.lfo_fields(number), under=number == SECOND_ROW_LFO, boxed=True) for number in LFO_NUMBERS]
        return Tab(label=labels.MSG_LFOS_TAB, columns=columns, not_ready=not self.instrument().is_built_in())

    def lfo_fields(self, number):
        """Return an LFO's fields: whether it is on, then its shape, rate, retrigger and each scene."""
        on = Toggle(label=labels.MSG_LFO_LABEL.format(number=number), on=self.instrument().get_lfo(number=number, name=LfoSetting.ON),
                    set=self.setter(number=number, name=LfoSetting.ON))
        return [on, self.shape_field(number), self.rate_field(number), self.retrigger_field(number),
                self.toggle(number=number, label=labels.MSG_LFO_EACH_SCENE_LABEL, name=LfoSetting.EACH_SCENE)]

    def shape_field(self, number):
        shape = self.instrument().get_lfo(number=number, name=LfoSetting.SHAPE)
        return ChoiceField(page=self._page, label=labels.MSG_LFO_SHAPE_LABEL.format(number=number), shown_label=shown_label(labels.MSG_LFO_SHAPE_LABEL),
                           choices=list(file_format.LFO_SHAPES), current=shape, names=[labels.MSG_LFO_SHAPE_NAMES[choice] for choice in file_format.LFO_SHAPES],
                           shown=labels.MSG_LFO_SHAPE_NAMES[shape], set=self.setter(number=number, name=LfoSetting.SHAPE))

    def rate_field(self, number):
        """Return an LFO's rate, a gauge filling by the logarithm of its hertz, from a tenth of a hertz to a hundred."""
        return GaugeField(page=self._page, label=labels.MSG_LFO_RATE_LABEL.format(number=number), shown_label=shown_label(labels.MSG_LFO_RATE_LABEL),
                          number=self.instrument().get_lfo(number=number, name=LfoSetting.RATE), lowest=limits.MIN_LFO_RATE, highest=limits.MAX_LFO_RATE,
                          cells=LFO_GAUGE_CELLS, unit=marks.MSG_LFO_RATE_SHOWN, divisor=TENTHS, logarithmic=True, strides=RATE_STRIDES,
                          longest_stride=LONGEST_RATE_STRIDE, set=self.setter(number=number, name=LfoSetting.RATE))

    def retrigger_field(self, number):
        return self.toggle(number=number, label=labels.MSG_LFO_RETRIGGER_LABEL, name=LfoSetting.RETRIGGER)

    def toggle(self, *, number, label, name):
        return Toggle(label=label.format(number=number), shown_label=shown_label(label), on=self.instrument().get_lfo(number=number, name=name),
                      set=self.setter(number=number, name=name))

    def setter(self, *, number, name):
        """Return what stores a value of one of an LFO's settings, as a field sets it."""
        return lambda value: self._document.change_set(self.instrument().set_lfo, number=number, name=name, value=value)


def shown_label(label):
    """Return an LFO's field label as its box shows it, without the LFO's number, which only F1 and the keys need."""
    return labels.MSG_LFO_SHOWN_LABELS[label]
