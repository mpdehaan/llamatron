# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Hocket's page: the track whose notes it shares out, and its Restart."""

from llamatron.engine.generators.hocket import strings
from llamatron.engine.generators.hocket.model import HocketSetting
from llamatron.model.schema.generator_views import ColumnView, GeneratorView, RestartView, TrackView
from llamatron.user_strings import labels

VIEW = GeneratorView(
    columns=(ColumnView(heading=None, settings=(TrackView(setting=HocketSetting.SOURCE, label=labels.MSG_SOURCE_TRACK_LABEL), RestartView())),),
    help=strings.HELP_PAGE,
)
