# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Arpeggiator's page: the Notes column (Step, Order, Octave range, Octave jump, Offsets, Restart)."""

from llamatron.engine.generators.arp import model, schema, strings
from llamatron.engine.generators.arp.model import ArpSetting
from llamatron.model.objects.naming import words
from llamatron.model.schema.generator_views import ChoiceView, ColumnView, GeneratorView, NumberView, OffsetsView, RestartView, TimeView
from llamatron.user_strings import labels

ORDERS = tuple(model.ORDERS)
JUMPS = tuple(model.OCTAVE_JUMPS)
JUMP_NAMES = {jump: words(jump) for jump in JUMPS}


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
    ),
    help=strings.HELP_PAGE,
)
