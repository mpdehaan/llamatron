# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Shapes generator's page: Density, Swell and Articulate, each a shape's start, end, over and then, the Swell with its accent,
and the generator's Restart."""

from llamatron.engine.generators.shapes import model, strings
from llamatron.model.schema.file_format import Shape
from llamatron.model.schema.generator_views import ColumnView, GeneratorView, NumberView, RestartView, ShapeView

VIEW = GeneratorView(
    columns=(
        ColumnView(heading=None, settings=(
            ShapeView(shape=Shape.DENSITY),
            ShapeView(shape=Shape.SWELL),
            NumberView(setting=model.SWELL_ACCENT, label=strings.MSG_SWELL_ACCENT_LABEL),
            ShapeView(shape=Shape.ARTICULATE),
            RestartView(),
        )),
    ),
    help=strings.HELP_PAGE,
)
