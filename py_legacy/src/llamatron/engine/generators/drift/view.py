# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Drift's page: how often it triggers, how many triggers reach version B, its direction and Restart, then each of its
values as a row of version A and version B side by side."""

from llamatron.engine.generators.drift import model, strings
from llamatron.engine.generators.drift.model import DriftSetting
from llamatron.model.schema import file_format
from llamatron.model.schema.generator_views import ChoiceView, ColumnView, DriftValuesView, GeneratorView, NumberView, RestartView, TimeView
from llamatron.user_strings import labels

DIRECTIONS = tuple(file_format.DRIFT_DIRECTIONS)

VIEW = GeneratorView(
    columns=(
        ColumnView(heading=None, settings=(
            TimeView(setting=DriftSetting.EVERY, label=labels.MSG_EVERY_LABEL, first=file_format.ONE_BAR_WRITTEN),
            NumberView(setting=DriftSetting.STEPS_TO_B, label=labels.MSG_STEPS_TO_B_LABEL, default=model.DEFAULT_STEPS_TO_B),
            ChoiceView(setting=DriftSetting.DIRECTION, label=labels.MSG_DRIFT_DIRECTION_LABEL, choices=DIRECTIONS, default=DIRECTIONS[0]),
            RestartView(),
            DriftValuesView(),
        )),
    ),
    help=strings.HELP_PAGE,
)
