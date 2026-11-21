# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The logic of the Hocket generator plugin: the controller's methods it fills in."""

from llamatron.engine.generators.controller import GeneratorController


class HocketController(GeneratorController):
    """What a Hocket does."""

    __slots__ = ()

    def notes_dealt(self, *, settings, place):
        """Each turn is the source's notes that start together, a chord passing whole, and a rest passes no turn. The turns go
        round the pool from its first track, carrying on from the scenes before in the Hocket's run, as its Restart says,
        counted from the source's clips."""
        source = settings.get_source()
        pool = place.pool(source=source)
        dealt = {}
        if not pool or not place.plays(source=source):
            return dealt
        turn = sum(len(place.turns(source=source, scene=written)) for written in place.earlier_scenes_in_run(settings.get_restart())
                   if place.pool(source=source, scene=written) and place.plays(source=source, scene=written))
        for notes in place.turns(source=source):
            dealt.setdefault(pool[turn % len(pool)], []).extend(notes)
            turn += 1
        return dealt
