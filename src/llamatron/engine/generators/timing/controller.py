# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The logic of the Timing generator plugin: the controller's methods it fills in."""

from llamatron.engine.generators.controller import GeneratorController
from llamatron.engine.generators.timing import parts
from llamatron.engine.generators.timing.generator import Glide, Shorten, TimingGenerator
from llamatron.engine.timing.nudge_plan import amount_moved, MovingRow


class TimingController(GeneratorController):
    """What a Timing generator does: its lit Glide and Shorten change a clip's notes as a step of a chain, and its lit Rush and
    Drag move the notes in time after the chains, on top of the groove."""

    __slots__ = ()

    def make_generator(self, *, settings, place):
        rows = []
        offset = place.continuation(settings)
        glide = settings.step_row(parts.GLIDE)
        if glide.is_lit():
            rows.append(Glide(steps=glide.get_steps(), step=_step_length(row=glide, place=place), glide_amount=settings.get_amount(parts.GLIDE), continuation=offset))
        shorten = settings.step_row(parts.SHORTEN)
        if shorten.is_lit():
            rows.append(Shorten(steps=shorten.get_steps(), step=_step_length(row=shorten, place=place), shorten=settings.get_amount(parts.SHORTEN), continuation=offset))
        return TimingGenerator(rows=rows)

    def moving_rows(self, *, settings, place):
        rows = []
        for part in parts.MOVING_PARTS:
            row = settings.step_row(part)
            if row.is_lit():
                rows.append(MovingRow(
                    steps=row.get_steps(), step=_step_length(row=row, place=place),
                    amount=amount_moved(percent=settings.get_amount(part), later=part == parts.DRAG), offset=place.run_offset(settings.get_restart()),
                ))
        return rows


def _step_length(*, row, place):
    """Return how long each of a row's steps is at a place in the clip's chains, the pattern's step unless the row sets its own."""
    return row.step_length(default_step=place.pattern_step(), bar=place.bar())
