# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""A player of the wizard's band: how the player plays, and how busy the player is."""

from llamatron.macro_composer.wizard_choices import FEWEST_FILLS, LEAST_BUSY, MOST_BUSY, MOST_FILLS
from llamatron.strings.labels import MSG_WIZARD_DRUM_FILLS_LABEL, MSG_WIZARD_FILLS_COME, MSG_WIZARD_QUIET_NOTES_LABEL, MSG_WIZARD_KIT_PIECE, MSG_WIZARD_BUSY_LABEL, MSG_WIZARD_PLAYS_LABEL, MSG_WIZARD_SOUND_LABEL
from llamatron.strings.legends import What
from llamatron.strings.marks import MSG_WIZARD_FILLS_SHOWN, MSG_WIZARD_BAND_SOUND_SHOWN, MSG_WIZARD_BUSY_SHOWN, MSG_WIZARD_GAUGE_EMPTY, MSG_WIZARD_GAUGE_FULL
from llamatron.tui.screens.shared.field import ChoiceField, Field, NumberField, Toggle
from llamatron.tui.screens.wizard.branch import Branch


class PlayerBranch(Branch):
    """One player, by the name the genre gives the player."""

    __slots__ = ('_role',)

    def __init__(self, *, page, role):
        super().__init__(page=page)
        self._role = role

    def name(self):
        return self.choices().role_title(self._role)

    def key(self):
        # The player's own name, since what a player is called can follow how the player plays.
        return self._role

    def fields(self):
        choices = self.choices()
        traits = choices.role_traits(self._role)
        # A player of notes plays one way, called Plays; the drums have a way for each of their parts, each called by the part's name.
        fields = [self.way_field(trait=trait, label=MSG_WIZARD_PLAYS_LABEL if len(traits) == 1 else trait.capitalize()) for trait in traits]
        if choices.has_sound(self._role):
            fields.append(self.sound_field())
        if choices.has_busy(self._role) and choices.get_busy(self._role) is not None:
            fields.append(self.busy_field())
        if not choices.has_sound(self._role):
            fields.append(self.fills_field())
            if choices.has_quiet_notes() or not choices.plays_quiet_notes():
                fields.append(Toggle(label=MSG_WIZARD_QUIET_NOTES_LABEL, on=choices.plays_quiet_notes(), set=self.page().choosing(choices.set_quiet_notes)))
            # The drums: a toggle for each piece of the kit the song plays, the user's design.
            fields += [Toggle(label=MSG_WIZARD_KIT_PIECE.format(piece=piece), on=choices.piece_is_on(piece), set=self.piece_setter(piece)) for piece in choices.pieces()]
        return fields

    def piece_setter(self, piece):
        """Return what switches a piece of the kit on or off, refusing to switch off the last."""
        choices = self.choices()
        page = self.page()

        def set_on(on):
            try:
                page.choosing(lambda wanted: choices.set_piece_on(piece=piece, on=wanted))(on)
            except ValueError as problem:
                page.refuse(str(problem))
        return set_on

    def way_field(self, *, trait, label):
        choices = self.choices()
        page = self.page()
        return ChoiceField(page=page, label=label, choices=choices.ways(role=self._role, trait=trait), current=choices.get_way(trait),
                           set=page.choosing(lambda value: choices.set_way(trait=trait, value=value)))

    def sound_field(self):
        """Return the Sound field: the band's sound for the player, marked as the band's, or the player's own, chosen from a list."""
        choices = self.choices()
        role = self._role

        def shown():
            name = choices.sound_name(choices.get_sound(role))
            return name if choices.has_own_sound(role) else MSG_WIZARD_BAND_SOUND_SHOWN.format(sound=name)
        return Field(label=MSG_WIZARD_SOUND_LABEL, value=shown, enter=lambda: self.page().pick_sound(role), enter_what=What.CHOOSE)

    def fills_field(self):
        """Return the field for how often a fill comes: a number stepped or typed, drawn as a horizontal gauge that is empty at
        never, the user's design, beside the words for the position."""
        choices = self.choices()
        position = choices.get_fills()
        gauge = MSG_WIZARD_GAUGE_FULL * (position - FEWEST_FILLS) + MSG_WIZARD_GAUGE_EMPTY * (MOST_FILLS - position)
        return NumberField(page=self.page(), label=MSG_WIZARD_DRUM_FILLS_LABEL, number=position, shown=MSG_WIZARD_FILLS_SHOWN.format(gauge=gauge, often=MSG_WIZARD_FILLS_COME[position - FEWEST_FILLS]),
                           lowest=FEWEST_FILLS, highest=MOST_FILLS, set=self.page().choosing(choices.set_fills))

    def busy_field(self):
        """Return the Busy field: a number stepped or typed, drawn as a horizontal Busy gauge beside the number."""
        choices = self.choices()
        page = self.page()
        level = choices.get_busy(self._role)
        gauge = MSG_WIZARD_GAUGE_FULL * level + MSG_WIZARD_GAUGE_EMPTY * (MOST_BUSY - level)
        return NumberField(page=page, label=MSG_WIZARD_BUSY_LABEL, number=level, shown=MSG_WIZARD_BUSY_SHOWN.format(gauge=gauge, level=level, most=MOST_BUSY),
                           lowest=LEAST_BUSY, highest=MOST_BUSY, set=page.choosing(lambda value: choices.set_busy(role=self._role, level=value)))
