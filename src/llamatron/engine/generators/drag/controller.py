# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The logic of the Drag generator plugin: the controller's methods it fills in."""

from llamatron.engine.generators.controller import GeneratorController
from llamatron.engine.timing.nudge_plan import amount_moved, MovingRow


class DragController(GeneratorController):
    """What a Drag does."""

    __slots__ = ()

    def moving_row(self, *, settings, place):
        return MovingRow(
            steps=settings.step_row().get_steps(), step=settings.step_row().step_length(default_step=place.pattern_step(), bar=place.bar()),
            amount=amount_moved(percent=settings.get_amount(), later=True), offset=place.run_offset(settings.get_restart()),
        )
