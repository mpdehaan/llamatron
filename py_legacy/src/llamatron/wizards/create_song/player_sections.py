# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Where one player of the band plays in the song wizard's form: where the player comes in and when the player lays out."""

from llamatron.user_strings import errors
from llamatron.wizards.create_song import arranger, wizard_limits


class PlayerSections:
    """The sections of the form one player plays in: the way the player comes in, at the start, after the intro or in a
    chorus, and the way the player lays out, never, in the breakdowns or whenever it is quiet. Reached as
    choices.player(role).sections()."""

    __slots__ = ('_choices', '_role')

    def __init__(self, *, choices, role):
        self._choices = choices
        self._role = role

    def plays_at(self):
        """Return the places of the form's sections the player plays in."""
        places = []
        for place in range(self._choices.section_count()):
            section = self._choices.section(place)
            if self._role in section.plays():
                places.append(place)
        return places

    def _first_place(self):
        """Return the place of the first section the player plays in, or None."""
        places = self.plays_at()
        if places:
            return places[0]
        return None

    def comes_in_offered(self):
        """Return the ways the player may come in, where the song has sections and the player is in the band."""
        player = self._choices.player(self._role)
        if not self._choices.is_ready() or not player.is_in():
            return []
        return list(self._choices.comes_in_places())

    def get_comes_in(self):
        """Return the way the player comes in, or None where the player's first section is none of the ways' or the player
        plays nowhere."""
        first = self._first_place()
        places = self._choices.comes_in_places()
        for way, place in places.items():
            if place == first:
                return way
        return None

    def set_comes_in(self, way):
        """Have the player come in at a place of the form and sit out every section before it; the sections after are left as they are."""
        if way not in self.comes_in_offered():
            raise ValueError(errors.ERR_WIZARD_COMES_IN.format(value=way))
        places = self._choices.comes_in_places()
        first = places[way]
        plays = []
        for place in range(first, self._choices.section_count()):
            section = self._choices.section(place)
            if place == first or self._role in section.plays():
                plays.append(place)
        self._choices.set_plays_of(role=self._role, plays=plays)

    def lays_out_offered(self):
        """Return the ways the player may lay out: never, only in the breakdowns where the form has one, and whenever it is
        quiet in a planned song with a quiet section."""
        if not self.comes_in_offered() or self._first_place() is None:
            return []
        offered = [wizard_limits.NEVER_LAYS_OUT]
        if self._choices.breakdown_places():
            offered.append(wizard_limits.IN_BREAKDOWNS)
        if self._choices.quiet_places():
            offered.append(wizard_limits.WHEN_QUIET)
        return offered

    def get_lays_out(self):
        """Return the way the player lays out, or None where the sections the player plays are none of the ways'."""
        first = self._first_place()
        plays = self.plays_at()
        for way in self.lays_out_offered():
            if self._laid_out(way=way, first=first) == plays:
                return way
        return None

    def set_lays_out(self, way):
        """Have the player lay out never, only in the breakdowns, or whenever it is quiet, from the player's first section on."""
        if way not in self.lays_out_offered():
            raise ValueError(errors.ERR_WIZARD_LAYS_OUT.format(value=way))
        plays = self._laid_out(way=way, first=self._first_place())
        self._choices.set_plays_of(role=self._role, plays=plays)

    def _laid_out(self, *, way, first):
        """Return which sections the player plays under a way of laying out, from the player's first section on: never is
        every section the genre gives the player any part in."""
        out = self._out_places(way)
        played = []
        for place in range(first, self._choices.section_count()):
            if place == first or self._plays_unless_out(place=place, out=out):
                played.append(place)
        return played

    def _out_places(self, way):
        """Return the places a way of laying out leaves the player out of: none, the breakdowns, or the quiet sections."""
        if way == wizard_limits.NEVER_LAYS_OUT:
            return []
        if way == wizard_limits.IN_BREAKDOWNS:
            return self._choices.breakdown_places()
        return self._choices.quiet_places()

    def _plays_unless_out(self, *, place, out):
        """Return whether the player plays in a section a way of laying out does not leave the player out of: any but a held
        chord the player has no part in."""
        if place in out:
            return False
        section = self._choices.section(place)
        if not section.is_held():
            return True
        usual = section.usual()
        return self._role in usual.get(arranger.PLAYS, [])
