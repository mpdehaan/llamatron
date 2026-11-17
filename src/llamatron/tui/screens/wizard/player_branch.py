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

from llamatron.composition.limits import MIN_GM_SOUND
from llamatron.macro_composer.breaks import LEAST_CUT, MOST_CUT
from llamatron.macro_composer.interplay import LEAST_BUSY as LEAST_BUSY_BESIDE, MOST_BUSY as MOST_BUSY_BESIDE
from llamatron.macro_composer.wizard_choices import FEWEST_FILLS, FILLS_TRAITS, HIGHEST_PLACE, LEAST_BUSY, LOWEST_PLACE, MOST_BUSY, MOST_FILLS
from llamatron.strings.labels import MSG_WIZARD_BY_SECTION, MSG_WIZARD_FILLS_BUSY_LABEL, MSG_WIZARD_ROLE_LABEL, MSG_GM_SOUNDS, MSG_WIZARD_BREAK_CUT_LABEL, MSG_WIZARD_BREAK_LABEL, MSG_WIZARD_NO_BREAK, MSG_WIZARD_DRUM_FILLS_LABEL, MSG_WIZARD_FILLS_COME, MSG_WIZARD_FILLS_LABEL, MSG_WIZARD_QUIET_NOTES_LABEL, MSG_WIZARD_KIT_PIECE, MSG_WIZARD_BUSY_LABEL, MSG_WIZARD_PLAYER_GAUGE_LABELS, MSG_WIZARD_PLAYS_LABEL, MSG_WIZARD_SOUND_LABEL
from llamatron.strings.legends import MSG_OWN_DRUM_WHAT, What
from llamatron.strings.marks import MSG_WIZARD_KIT_DRUM_SHOWN, MSG_WIZARD_OWN_DRUM_SHOWN, MSG_WIZARD_SOUND_ON_NOTE, MSG_WIZARD_FILLS_SHOWN, MSG_WIZARD_BAND_SOUND_SHOWN, MSG_WIZARD_BUSY_CUSTOM_SHOWN, MSG_WIZARD_BUSY_SHOWN, MSG_WIZARD_PLAYER_GAUGE_SHOWN, MSG_WIZARD_GAUGE_EMPTY, MSG_WIZARD_GAUGE_FULL
from llamatron.tui.note_names import note_shown
from llamatron.tui.screens.shared.field import Cells, ChoiceField, Field, NumberField, Toggle
from llamatron.tui.screens.wizard.branch import Branch

# A field is worth showing once there is more than one way to choose.
A_CHOICE = 2


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
            # The player's own gauges, which the Busy field fills in and which each move alone.
            fields += [self.player_gauge_field(gauge) for gauge in choices.player_gauges(self._role)]
        if choices.answered_by() == self._role:
            fields += self.beside_fields()
        if not choices.has_sound(self._role):
            # The drums' break comes first, since it takes the place of the kick's, the snare's and the cymbal's own ways.
            fields = [*self.break_fields(), *fields]
            fields += [*self.fill_pattern_fields(), self.fills_field()]
            if choices.has_quiet_notes() or not choices.plays_quiet_notes():
                fields.append(Toggle(label=MSG_WIZARD_QUIET_NOTES_LABEL, on=choices.plays_quiet_notes(), set=self.page().choosing(choices.set_quiet_notes)))
            # The drums: a row for each piece of the kit the song plays.
            fields += [self.piece_row(piece) for piece in choices.pieces()]
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

    def beside_fields(self):
        """Return the fields of the player who answers the tune: Role, the genre's plan section by section or one thing in every section, and
        how busy the fills are, a number stepped or typed, drawn as a horizontal gauge."""
        choices = self.choices()
        page = self.page()
        ways = choices.ways_beside()
        busy = choices.get_fills_busy()
        gauge = MSG_WIZARD_GAUGE_FULL * busy + MSG_WIZARD_GAUGE_EMPTY * (MOST_BUSY_BESIDE - busy)
        return [ChoiceField(page=page, label=MSG_WIZARD_ROLE_LABEL, choices=[MSG_WIZARD_BY_SECTION, *ways], current=choices.get_role_plan() or MSG_WIZARD_BY_SECTION,
                            set=page.choosing(lambda way: choices.set_role_plan(None if way == MSG_WIZARD_BY_SECTION else way))),
                NumberField(page=page, label=MSG_WIZARD_FILLS_BUSY_LABEL, number=busy, shown=MSG_WIZARD_BUSY_SHOWN.format(gauge=gauge, level=busy, most=MOST_BUSY_BESIDE),
                            lowest=LEAST_BUSY_BESIDE, highest=MOST_BUSY_BESIDE, set=page.choosing(choices.set_fills_busy))]

    def piece_row(self, piece):
        """Return the row of a piece of the kit, two cells side by side: whether the piece plays, switched with Space, and what
        the piece sounds as, chosen from a list: its own drum, another drum of the kit, or a General MIDI sound on a note."""
        choices = self.choices()
        page = self.page()

        def shown():
            sound = choices.piece_sound(piece)
            if sound is None:
                return MSG_WIZARD_OWN_DRUM_SHOWN.format(piece=piece)
            if isinstance(sound, str):
                return MSG_WIZARD_KIT_DRUM_SHOWN.format(drum=sound)
            return MSG_WIZARD_SOUND_ON_NOTE.format(sound=MSG_GM_SOUNDS[sound - MIN_GM_SOUND], note=note_shown(choices.piece_note(piece)))
        to_own_drum = page.choosing(lambda sound: choices.set_piece_sound(piece=piece, sound=sound))

        def own_drum():
            to_own_drum(None)
        return Cells(label=MSG_WIZARD_KIT_PIECE.format(piece=piece), cells=[
            Toggle(label=MSG_WIZARD_KIT_PIECE.format(piece=piece), on=choices.piece_is_on(piece), set=self.piece_setter(piece)),
            Field(label=MSG_WIZARD_KIT_PIECE.format(piece=piece), value=shown, enter=lambda: page.pick_piece_sound(piece), enter_what=What.CHOOSE,
                  clear=None if choices.piece_sound(piece) is None else own_drum, clear_what=MSG_OWN_DRUM_WHAT),
        ])

    def break_fields(self):
        """Return the Break field where the song may play a break, and under it, while one is chosen, how far it is cut up:
        a number stepped or typed, drawn as a horizontal gauge that is empty for the break as written."""
        choices = self.choices()
        page = self.page()
        breaks = choices.breaks()
        if not breaks:
            return []
        fields = [ChoiceField(page=page, label=MSG_WIZARD_BREAK_LABEL, choices=[MSG_WIZARD_NO_BREAK, *breaks], current=choices.get_break() or MSG_WIZARD_NO_BREAK,
                              set=page.choosing(lambda name: choices.set_break(None if name == MSG_WIZARD_NO_BREAK else name)))]
        if choices.get_break() is not None:
            cut = choices.get_break_cut()
            gauge = MSG_WIZARD_GAUGE_FULL * (cut - LEAST_CUT) + MSG_WIZARD_GAUGE_EMPTY * (MOST_CUT - cut)
            fields.append(NumberField(page=page, label=MSG_WIZARD_BREAK_CUT_LABEL, number=cut, shown=MSG_WIZARD_BUSY_SHOWN.format(gauge=gauge, level=cut, most=MOST_CUT),
                                      lowest=LEAST_CUT, highest=MOST_CUT, set=page.choosing(choices.set_break_cut)))
        return fields

    def fill_pattern_fields(self):
        """Return the field for what the drums' fill is, where the genre has more than one, since one is nothing to choose."""
        choices = self.choices()
        trait = choices.song_trait(FILLS_TRAITS)
        if trait is None or len(choices.song_ways(trait)) < A_CHOICE:
            return []
        return [ChoiceField(page=self.page(), label=MSG_WIZARD_FILLS_LABEL, choices=choices.song_ways(trait), current=choices.get_way(trait),
                            set=self.page().choosing(lambda value: choices.set_way(trait=trait, value=value)))]

    def fills_field(self):
        """Return the field for how often a fill comes: a number stepped or typed, drawn as a horizontal gauge that is empty at
        never, beside the words for the position."""
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
        # A player whose gauges were moved is no longer the preset, and the field says so until a level is chosen again.
        shown = MSG_WIZARD_BUSY_SHOWN if choices.player_preset(self._role) is not None else MSG_WIZARD_BUSY_CUSTOM_SHOWN
        return NumberField(page=page, label=MSG_WIZARD_BUSY_LABEL, number=level, shown=shown.format(gauge=gauge, level=level, most=MOST_BUSY),
                           lowest=LEAST_BUSY, highest=MOST_BUSY, set=page.choosing(lambda value: choices.set_busy(role=self._role, level=value)))

    def player_gauge_field(self, gauge):
        """Return the field of one of the player's own gauges: a number stepped or typed, drawn as a horizontal gauge beside the number."""
        choices = self.choices()
        page = self.page()
        place = choices.get_player_gauge(role=self._role, gauge=gauge)
        drawn = MSG_WIZARD_GAUGE_FULL * (place - LOWEST_PLACE) + MSG_WIZARD_GAUGE_EMPTY * (HIGHEST_PLACE - place)
        return NumberField(page=page, label=MSG_WIZARD_PLAYER_GAUGE_LABELS[gauge], number=place, shown=MSG_WIZARD_PLAYER_GAUGE_SHOWN.format(gauge=drawn, place=place),
                           lowest=LOWEST_PLACE, highest=HIGHEST_PLACE, set=page.choosing(lambda value: choices.set_player_gauge(role=self._role, gauge=gauge, place=value)))
