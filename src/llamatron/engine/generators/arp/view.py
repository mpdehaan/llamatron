# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Arpeggiator's page: the Notes column (Step, Order, Octave range, Octave jump, Offsets, Restart) and the Registers column,
what every note adds to each register."""

from llamatron.engine.generators.arp import model, schema, strings
from llamatron.engine.generators.arp.model import ArpSetting
from llamatron.model.objects.naming import words
from llamatron.model.schema import file_format
from llamatron.model.schema.generator_views import ChoiceView, ColumnView, GeneratorView, NumberView, OffsetsView, RegisterAddView, RestartView, TimeView
from llamatron.user_strings import labels

ORDERS = tuple(model.ORDERS)
JUMPS = tuple(model.OCTAVE_JUMPS)
JUMP_NAMES = {jump: words(jump) for jump in JUMPS}


def _register_add(register):
    """Return how what every note adds to a register is edited."""
    return RegisterAddView(setting=model.ARP_NOTE_ADDS[register], label=labels.MSG_ARP_NOTE_ADD_LABEL.format(name=register), register=register)


VIEW = GeneratorView(
    columns=(
        ColumnView(heading=strings.MSG_NOTES_HEADING, settings=(
            TimeView(setting=ArpSetting.STEP, label=labels.MSG_STEP_LABEL),
            ChoiceView(setting=ArpSetting.ORDER, label=labels.MSG_ORDER_LABEL, choices=ORDERS, default=ORDERS[0]),
            NumberView(setting=ArpSetting.OCTAVE_RANGE, label=labels.MSG_OCTAVE_RANGE_LABEL, default=schema.MIN_OCTAVE_RANGE),
            ChoiceView(setting=ArpSetting.OCTAVE_JUMP, label=labels.MSG_OCTAVE_JUMP_LABEL, choices=JUMPS, default=JUMPS[0], names=JUMP_NAMES),
            OffsetsView(setting=ArpSetting.OFFSETS, label=labels.MSG_OFFSETS_LABEL),
            RestartView(),
        )),
        ColumnView(heading=strings.MSG_REGISTERS_HEADING, settings=tuple(_register_add(register) for register in file_format.REGISTER_NAMES)),
    ),
    help=strings.HELP_PAGE,
)
