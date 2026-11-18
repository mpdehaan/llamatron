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

from llamatron.composition import limits
from llamatron.strings import labels, legends, marks, messages
from llamatron.macro_composer.breaks import LEAST_CUT, MOST_CUT
from llamatron.macro_composer.loudness import LEAST_DYNAMICS, LEVELS, MOST_DYNAMICS
from llamatron.macro_composer.notation import HIGHEST_VELOCITY, LOWEST_VELOCITY
from llamatron.macro_composer.song_plan import HIGHEST_ENERGY, LOWEST_ENERGY
from llamatron.macro_composer.interplay import LEAST_BUSY as LEAST_BUSY_BESIDE, MOST_BUSY as MOST_BUSY_BESIDE
from llamatron.macro_composer.wizard_choices import FEWEST_ROW_CELLS, MOST_ROW_CELLS, FEWEST_FILLS, FILLS_TRAITS, HIGHEST_PLACE, LEAST_BUSY, LOWEST_PLACE, MOST_BUSY, MOST_FILLS
from llamatron.tui.dialogs.row_dialog import RowDialog
from llamatron.tui.note_names import note_shown
from llamatron.tui.screens.shared.field import Cells, ChoiceField, Field, NumberField, Toggle
from llamatron.tui.screens.wizard.branch import Branch, gauge_shown

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
        fields = [self.way_field(trait=trait, label=labels.MSG_WIZARD_PLAYS_LABEL if len(traits) == 1 else trait.capitalize()) for trait in traits]
        if choices.has_sound(self._role):
            fields.append(self.sound_field())
        fields += self.person_fields()
        fields += self.dynamics_fields()
        if choices.has_busy(self._role) and choices.get_busy(self._role) is not None:
            fields.append(self.busy_field())
            # The player's own gauges, which the Busy field fills in and which each move alone.
            fields += [self.player_gauge_field(gauge) for gauge in choices.player_gauges(self._role)]
        # The rows of numbers the serial style deals to the player's notes, each opened in a window of its own.
        fields += [self.row_field(name) for name in choices.player_rows(self._role)]
        if choices.answered_by() == self._role:
            fields += self.beside_fields()
        if not choices.has_sound(self._role):
            # The drums' break comes first, since it takes the place of the kick's, the snare's and the cymbal's own ways.
            fields = [*self.break_fields(), *fields]
            fields += [*self.fill_pattern_fields(), self.fills_field()]
            if choices.has_quiet_notes() or not choices.plays_quiet_notes():
                fields.append(Toggle(label=labels.MSG_WIZARD_QUIET_NOTES_LABEL, on=choices.plays_quiet_notes(), set=self.page().choosing(choices.set_quiet_notes)))
            # The drums: a row for each piece of the kit the song plays.
            fields += [self.piece_row(piece) for piece in choices.pieces()]
        # The player's levels come last, under a heading that opens and closes, which hides every field after it while closed.
        return [*fields, *self.loudness_fields()]

    def dynamics_fields(self):
        """Return the Dynamics gauge: how far the player's loud and soft notes lie from the normal ones, where that is heard."""
        choices = self.choices()
        page = self.page()
        role = self._role
        if not choices.has_dynamics(role):
            return []
        dynamics = choices.get_dynamics(role)
        return [NumberField(page=page, label=labels.MSG_WIZARD_DYNAMICS_LABEL, number=dynamics, lowest=LEAST_DYNAMICS, highest=MOST_DYNAMICS,
                            shown=gauge_shown(place=dynamics, lowest=LEAST_DYNAMICS + 1, highest=MOST_DYNAMICS, said=labels.MSG_WIZARD_DYNAMICS_SAID[dynamics]),
                            set=page.choosing(lambda number: choices.set_dynamics(role=role, dynamics=number)))]

    def loudness_fields(self):
        """Return the player's levels under the Loudness heading, a velocity for each level the song plays, the genre's until the song
        chooses its own; the drummer's are the whole kit's. The levels are worked out only while the heading is open."""
        choices = self.choices()
        page = self.page()
        role = self._role
        if not choices.has_loudness(role):
            return []
        heading = page.heading(label=labels.MSG_WIZARD_GROUP_LOUDNESS, is_set=lambda: any(choices.loudness_level_is_own(role=role, level=level) for level in LEVELS))
        if not page.is_open(heading):
            return [heading]
        levels = choices.loudness_levels(role)
        fields = [heading]
        for level in choices.loudness_levels_offered(role):
            own = choices.loudness_level_is_own(role=role, level=level)

            def set_level(number, level=level):
                page.choosing(lambda wanted: choices.set_loudness_level(role=role, level=level, number=wanted))(number)
            fields.append(NumberField(page=page, label=labels.MSG_WIZARD_LEVEL_LABELS[level], number=levels[level], lowest=LOWEST_VELOCITY, highest=HIGHEST_VELOCITY,
                                      shown=None if own else marks.MSG_WIZARD_LEVEL_FROM_GENRE.format(number=levels[level]), set=set_level,
                                      clear=(lambda set_level=set_level: set_level(None)) if own else None, clear_what=legends.MSG_FROM_GENRE_WHAT))
        return fields

    def person_fields(self):
        """Return the fields of the player as a person in the band: where the player comes in, where the player lays out, and how strongly the player answers
        to Energy. The first two say which sections the player plays, and read as the person's own where the sections were changed one by one."""
        choices = self.choices()
        page = self.page()
        role = self._role

        def refusing(setter):
            def set_way(value):
                try:
                    page.choosing(setter)(value)
                except ValueError as problem:
                    page.refuse(str(problem))
            return set_way
        fields = []
        comes, lays = choices.comes_in_offered(role), choices.lays_out_offered(role)
        if comes:
            now = choices.get_comes_in(role)
            fields.append(ChoiceField(page=page, label=labels.MSG_WIZARD_COMES_IN_LABEL, choices=comes, current=now or comes[0], shown=None if now is not None else labels.MSG_WIZARD_OWN_START,
                                      set=refusing(lambda way: choices.set_comes_in(role=role, way=way))))
        if lays:
            now = choices.get_lays_out(role)
            fields.append(ChoiceField(page=page, label=labels.MSG_WIZARD_LAYS_OUT_LABEL, choices=lays, current=now or lays[0], shown=None if now is not None else labels.MSG_WIZARD_OWN_START,
                                      set=refusing(lambda way: choices.set_lays_out(role=role, way=way))))
        if choices.reacts(role):
            reacts = choices.get_reacts(role)
            fields.append(NumberField(page=page, label=labels.MSG_WIZARD_REACTS_LABEL, number=reacts, shown=gauge_shown(place=reacts, lowest=LOWEST_ENERGY, highest=HIGHEST_ENERGY, said=labels.MSG_WIZARD_REACTS_SAID[reacts]),
                                      lowest=LOWEST_ENERGY, highest=HIGHEST_ENERGY, set=page.choosing(lambda number: choices.set_reacts(role=role, reacts=number))))
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
            return name if choices.has_own_sound(role) else marks.MSG_WIZARD_BAND_SOUND_SHOWN.format(sound=name)
        return Field(label=labels.MSG_WIZARD_SOUND_LABEL, value=shown, enter=lambda: self.page().pick_sound(role), enter_what=legends.What.CHOOSE)

    def beside_fields(self):
        """Return the fields of the player who answers the tune: Role, the genre's plan section by section or one thing in every section, and
        how busy the fills are, a number stepped or typed, drawn as a horizontal gauge."""
        choices = self.choices()
        page = self.page()
        ways = choices.ways_beside()
        busy = choices.get_fills_busy()
        gauge = marks.MSG_WIZARD_GAUGE_FULL * busy + marks.MSG_WIZARD_GAUGE_EMPTY * (MOST_BUSY_BESIDE - busy)
        return [ChoiceField(page=page, label=labels.MSG_WIZARD_ROLE_LABEL, choices=[labels.MSG_WIZARD_BY_SECTION, *ways], current=choices.get_role_plan() or labels.MSG_WIZARD_BY_SECTION,
                            set=page.choosing(lambda way: choices.set_role_plan(None if way == labels.MSG_WIZARD_BY_SECTION else way))),
                NumberField(page=page, label=labels.MSG_WIZARD_FILLS_BUSY_LABEL, number=busy, shown=marks.MSG_WIZARD_BUSY_SHOWN.format(gauge=gauge, level=busy, most=MOST_BUSY_BESIDE),
                            lowest=LEAST_BUSY_BESIDE, highest=MOST_BUSY_BESIDE, set=page.choosing(choices.set_fills_busy))]

    def piece_row(self, piece):
        """Return the row of a piece of the kit, two cells side by side: whether the piece plays, switched with Space, and what
        the piece sounds as, chosen from a list: its own drum, another drum of the kit, or a General MIDI sound on a note."""
        choices = self.choices()
        page = self.page()

        def shown():
            sound = choices.piece_sound(piece)
            if sound is None:
                return marks.MSG_WIZARD_OWN_DRUM_SHOWN.format(piece=piece)
            if isinstance(sound, str):
                return marks.MSG_WIZARD_KIT_DRUM_SHOWN.format(drum=sound)
            return marks.MSG_WIZARD_SOUND_ON_NOTE.format(sound=labels.MSG_GM_SOUNDS[sound - limits.MIN_GM_SOUND], note=note_shown(choices.piece_note(piece)))
        to_own_drum = page.choosing(lambda sound: choices.set_piece_sound(piece=piece, sound=sound))

        def own_drum():
            to_own_drum(None)
        return Cells(label=labels.MSG_WIZARD_KIT_PIECE.format(piece=piece), cells=[
            Toggle(label=labels.MSG_WIZARD_KIT_PIECE.format(piece=piece), on=choices.piece_is_on(piece), set=self.piece_setter(piece)),
            Field(label=labels.MSG_WIZARD_KIT_PIECE.format(piece=piece), value=shown, enter=lambda: page.pick_piece_sound(piece), enter_what=legends.What.CHOOSE,
                  clear=None if choices.piece_sound(piece) is None else own_drum, clear_what=legends.MSG_OWN_DRUM_WHAT),
        ])

    def break_fields(self):
        """Return the Break field where the song may play a break, and under it, while one is chosen, how far it is cut up:
        a number stepped or typed, drawn as a horizontal gauge that is empty for the break as written."""
        choices = self.choices()
        page = self.page()
        breaks = choices.breaks()
        if not breaks:
            return []
        fields = [ChoiceField(page=page, label=labels.MSG_WIZARD_BREAK_LABEL, choices=[labels.MSG_WIZARD_NO_BREAK, *breaks], current=choices.get_break() or labels.MSG_WIZARD_NO_BREAK,
                              set=page.choosing(lambda name: choices.set_break(None if name == labels.MSG_WIZARD_NO_BREAK else name)))]
        if choices.get_break() is not None:
            cut = choices.get_break_cut()
            gauge = marks.MSG_WIZARD_GAUGE_FULL * (cut - LEAST_CUT) + marks.MSG_WIZARD_GAUGE_EMPTY * (MOST_CUT - cut)
            fields.append(NumberField(page=page, label=labels.MSG_WIZARD_BREAK_CUT_LABEL, number=cut, shown=marks.MSG_WIZARD_BUSY_SHOWN.format(gauge=gauge, level=cut, most=MOST_CUT),
                                      lowest=LEAST_CUT, highest=MOST_CUT, set=page.choosing(choices.set_break_cut)))
        return fields

    def fill_pattern_fields(self):
        """Return the field for what the drums' fill is, where the genre has more than one, since one is nothing to choose."""
        choices = self.choices()
        trait = choices.song_trait(FILLS_TRAITS)
        if trait is None or len(choices.song_ways(trait)) < A_CHOICE:
            return []
        return [ChoiceField(page=self.page(), label=labels.MSG_WIZARD_FILLS_LABEL, choices=choices.song_ways(trait), current=choices.get_way(trait),
                            set=self.page().choosing(lambda value: choices.set_way(trait=trait, value=value)))]

    def fills_field(self):
        """Return the field for how often a fill comes: a number stepped or typed, drawn as a horizontal gauge that is empty at
        never, beside the words for the position."""
        choices = self.choices()
        position = choices.get_fills()
        gauge = marks.MSG_WIZARD_GAUGE_FULL * (position - FEWEST_FILLS) + marks.MSG_WIZARD_GAUGE_EMPTY * (MOST_FILLS - position)
        return NumberField(page=self.page(), label=labels.MSG_WIZARD_DRUM_FILLS_LABEL, number=position, shown=marks.MSG_WIZARD_FILLS_SHOWN.format(gauge=gauge, often=labels.MSG_WIZARD_FILLS_COME[position - FEWEST_FILLS]),
                           lowest=FEWEST_FILLS, highest=MOST_FILLS, set=self.page().choosing(choices.set_fills))

    def busy_field(self):
        """Return the Busy field: a number stepped or typed, drawn as a horizontal Busy gauge beside the number."""
        choices = self.choices()
        page = self.page()
        level = choices.get_busy(self._role)
        gauge = marks.MSG_WIZARD_GAUGE_FULL * level + marks.MSG_WIZARD_GAUGE_EMPTY * (MOST_BUSY - level)
        # A player whose gauges were moved is no longer the preset, and the field says so until a level is chosen again.
        shown = marks.MSG_WIZARD_BUSY_SHOWN if choices.player_preset(self._role) is not None else marks.MSG_WIZARD_BUSY_CUSTOM_SHOWN
        return NumberField(page=page, label=labels.MSG_WIZARD_BUSY_LABEL, number=level, shown=shown.format(gauge=gauge, level=level, most=MOST_BUSY),
                           lowest=LEAST_BUSY, highest=MOST_BUSY, set=page.choosing(lambda value: choices.set_busy(role=self._role, level=value)))

    def row_field(self, name):
        """Return the field of one of the player's rows of numbers: the row shown, the genre's own marked so, and Enter opening the row to edit."""
        choices = self.choices()
        row = marks.MSG_WIZARD_ROW_SEPARATOR.join(str(value) for value in choices.get_player_row(role=self._role, name=name))
        own = choices.player_row_is_own(role=self._role, name=name)
        shown = (marks.MSG_WIZARD_ROW_SHOWN if own else marks.MSG_WIZARD_GENRE_ROW_SHOWN).format(row=row)
        return Field(label=labels.MSG_WIZARD_ROW_LABELS[name], value=lambda: shown, enter=lambda: self.edit_row(name), enter_what=legends.What.EDIT)

    def edit_row(self, name):
        """Open a row of the player's in the Row dialog, and keep the row the dialog answers with."""
        choices = self.choices()
        page = self.page()
        lowest, highest = choices.row_limits(name)
        dialog = RowDialog(title=messages.MSG_WIZARD_ROW_TITLE.format(row=labels.MSG_WIZARD_ROW_LABELS[name], player=self.name()), values=choices.get_player_row(role=self._role, name=name),
                           lowest=lowest, highest=highest, fewest=FEWEST_ROW_CELLS, most=MOST_ROW_CELLS, usual=choices.genre_row(role=self._role, name=name))
        page.ask(dialog=dialog, then=page.choosing(lambda values: choices.set_player_row(role=self._role, name=name, values=values)))

    def player_gauge_field(self, gauge):
        """Return the field of one of the player's own gauges: a number stepped or typed, drawn as a horizontal gauge beside the number."""
        choices = self.choices()
        page = self.page()
        place = choices.get_player_gauge(role=self._role, gauge=gauge)
        drawn = marks.MSG_WIZARD_GAUGE_FULL * (place - LOWEST_PLACE) + marks.MSG_WIZARD_GAUGE_EMPTY * (HIGHEST_PLACE - place)
        return NumberField(page=page, label=labels.MSG_WIZARD_PLAYER_GAUGE_LABELS[gauge], number=place, shown=marks.MSG_WIZARD_PLAYER_GAUGE_SHOWN.format(gauge=drawn, place=place),
                           lowest=LOWEST_PLACE, highest=HIGHEST_PLACE, set=page.choosing(lambda value: choices.set_player_gauge(role=self._role, gauge=gauge, place=value)))
