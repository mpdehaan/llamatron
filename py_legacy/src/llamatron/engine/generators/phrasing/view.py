# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Phrasing generator's page: how long a line of the tune is, the breath after it, how far it rises and falls, and how its
notes are joined, each chosen from its list."""

from llamatron.engine.generators.phrasing import model, schema, strings
from llamatron.engine.generators.phrasing.model import PhrasingSetting
from llamatron.model.schema.generator_views import ChoiceView, ColumnView, GeneratorView

VIEW = GeneratorView(
    columns=(
        ColumnView(heading=None, settings=(
            ChoiceView(setting=PhrasingSetting.LINE_BARS, label=strings.MSG_LINE_LABEL, choices=model.LINES_IN_BARS, default=model.DEFAULT_LINE_BARS,
                       names=strings.MSG_LINE_NAMES),
            ChoiceView(setting=PhrasingSetting.BREATH, label=strings.MSG_BREATH_LABEL, choices=schema.BREATHS, default=schema.QUICK_BREATH),
            ChoiceView(setting=PhrasingSetting.RISE_AND_FALL, label=strings.MSG_RISE_LABEL, choices=schema.RISES, default=schema.LITTLE_RISE),
            ChoiceView(setting=PhrasingSetting.NOTES, label=strings.MSG_NOTES_LABEL, choices=schema.JOINS, default=schema.NOTES_AS_WRITTEN),
        )),
    ),
    help=strings.HELP_PAGE,
)
