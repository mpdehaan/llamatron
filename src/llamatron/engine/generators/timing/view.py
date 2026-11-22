# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Timing generator's page: a section for each of Rush, Drag, Shorten and Glide, each its step, its amount and its row of
steps, then the generator's Restart."""

from llamatron.engine.generators.timing import model, parts, strings
from llamatron.model.schema.generator_views import ChoiceView, ColumnView, GeneratorView, NumberView, RestartView, SectionView, StepsView, TimeView

# The lengths a Glide may run into the next note, shortest first, as a file writes them.
GLIDE_AMOUNTS = ('1/256', '1/128', '1/64', '1/32', '1/16')
DEFAULT_GLIDE_WRITTEN = '1/128'
# Each part's name and what a lit step of it does.
PART_NAMES = {parts.RUSH: strings.MSG_RUSH, parts.DRAG: strings.MSG_DRAG, parts.SHORTEN: strings.MSG_SHORTEN, parts.GLIDE: strings.MSG_GLIDE}
PART_NOTES = {parts.RUSH: strings.MSG_RUSH_NOTE, parts.DRAG: strings.MSG_DRAG_NOTE, parts.SHORTEN: strings.MSG_SHORTEN_NOTE, parts.GLIDE: strings.MSG_GLIDE_NOTE}


def _amount_view(part):
    """Return how a part's amount is edited: a Glide's chosen from its lengths, the others' stepped as numbers."""
    label = strings.MSG_AMOUNT_LABEL.format(part=PART_NAMES[part])
    if part == parts.GLIDE:
        return ChoiceView(setting=parts.amount_of(part), label=label, choices=GLIDE_AMOUNTS, default=DEFAULT_GLIDE_WRITTEN)
    return NumberView(setting=parts.amount_of(part), label=label, default=model.DEFAULT_AMOUNTS[part])


def _part_section(part):
    """Return a part's section: its step, its amount and its row of steps."""
    name = PART_NAMES[part]
    return SectionView(heading=name, settings=(
        TimeView(setting=parts.step_of(part), label=strings.MSG_STEP_LABEL.format(part=name)),
        _amount_view(part),
        StepsView(setting=parts.steps_of(part), row=part, label=strings.MSG_STEPS_LABEL.format(part=name), row_name=name, note=PART_NOTES[part]),
    ))


VIEW = GeneratorView(
    columns=(ColumnView(heading=None, settings=(*[_part_section(part) for part in parts.PARTS], RestartView())),),
    help=strings.HELP_PAGE,
)
