# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A player of the wizard's band: how the player plays, and how busy the player is."""

import functools

from llamatron.interface.tracker.dialogs.row_dialog import RowDialog
from llamatron.interface.tracker.note_names import note_shown
from llamatron.interface.tracker.screens.shared.field import Button, Cells, ChoiceField, Field, gauge_shown, NumberField, Toggle
from llamatron.interface.tracker.screens.wizard.branch import Branch
from llamatron.model.schema import limits
from llamatron.user_strings import labels, legends, marks, messages
from llamatron.wizards.create_song import wizard_limits, wizard_names

# A field is worth showing once there is more than one way to choose.
A_CHOICE = 2


class PlayerBranch(Branch):
    """One player, by the name the genre gives the player."""

    __slots__ = ('_role',)

    def __init__(self, *, page, role):
        super().__init__(page=page)
        self._role = role

    def name(self):
        return self.get_choices().player(self._role).title()

    def key(self):
        # The player's own name, since what a player is called can follow how the player plays.
        return self._role

    def fields(self):
        choices = self.get_choices()
        traits = choices.player(self._role).traits()
        # A player of notes plays one way, called Plays; the drums have a way for each of their parts, each called by the part's name.
        fields = [self.way_field(trait=trait, label=labels.MSG_WIZARD_PLAYS_LABEL if len(traits) == 1 else trait.capitalize()) for trait in traits]
        if choices.get_sounds().has_sound(self._role):
            fields.append(self.sound_field())
        fields += self.person_fields()
        fields += self.dynamics_fields()
        if choices.player(self._role).has_busy() and choices.player(self._role).get_busy() is not None:
            fields.append(self.busy_field())
            # The player's own gauges, which the Busy field fills in and which each move alone.
            fields += [self.player_gauge_field(gauge) for gauge in choices.player(self._role).gauges()]
        # The rows of numbers the serial style deals to the player's notes, each opened in a window of its own.
        fields += [self.row_field(name) for name in choices.player(self._role).rows()]
        if choices.get_band().answered_by() == self._role:
            fields += self.beside_fields()
        if not choices.get_sounds().has_sound(self._role):
            # The drums' break comes first, since it takes the place of the kick's, the snare's and the cymbal's own ways.
            fields = [*self.break_fields(), *fields]
            fields += [*self.fill_pattern_fields(), self.fills_field()]
            if choices.get_kit().has_quiet_notes() or not choices.get_kit().plays_quiet_notes():
                fields.append(Toggle(label=labels.MSG_WIZARD_QUIET_NOTES_LABEL, on=choices.get_kit().plays_quiet_notes(), set=self.get_page().choosing(choices.get_kit().set_quiet_notes)))
            # The drums: a row for each piece of the kit the song plays.
            fields += [self.piece_row(piece) for piece in choices.get_kit().pieces()]
        # The player's levels come last, under a heading that opens and closes, which hides every field after it while closed.
        # The button that opens the player's Musician is a button, and so comes after every setting.
        return [*fields, *self.loudness_fields(), *self.musician_fields()]

    def musician_fields(self):
        """Return the button that opens the player's Musician, the generator that plays the player's clips as a player of the band would, where the genre's songs have them.
        A Musician the person changed says so, and Bksp gives the player back the one players are given."""
        choices = self.get_choices()
        page = self.get_page()
        role = self._role
        if not choices.is_ready() or not choices.get_band().has_musicians():
            return []
        own = choices.player(role).get_musician() is not None
        return [Button(label=labels.MSG_WIZARD_EDIT_OWN_PLAYER_BUTTON if own else labels.MSG_WIZARD_EDIT_PLAYER_BUTTON, key_name=legends.KeyName.ENTER, enter=lambda: page.edit_player(role), enter_what=legends.What.EDIT,
                       clear=(lambda: page.choosing(lambda _: choices.player(role).set_musician(settings=None))(None)) if own else None, clear_what=legends.MSG_FROM_GENRE_WHAT)]

    def dynamics_fields(self):
        """Return the Dynamics gauge: how far the player's loud and soft notes lie from the normal ones, where that is heard."""
        choices = self.get_choices()
        page = self.get_page()
        role = self._role
        if not choices.player(role).has_dynamics():
            return []
        dynamics = choices.player(role).get_dynamics()
        return [NumberField(page=page, label=labels.MSG_WIZARD_DYNAMICS_LABEL, number=dynamics, lowest=wizard_names.LEAST_DYNAMICS, highest=wizard_names.MOST_DYNAMICS,
                            shown=gauge_shown(place=dynamics, lowest=wizard_names.LEAST_DYNAMICS + 1, highest=wizard_names.MOST_DYNAMICS, said=labels.MSG_WIZARD_DYNAMICS_SAID[dynamics]),
                            set=page.choosing(lambda number: choices.player(role).set_dynamics(dynamics=number)))]

    def loudness_fields(self):
        """Return the player's levels under the Loudness heading, a velocity for each level the song plays, the genre's until the song
        chooses its own; the drummer's are the whole kit's. The levels are worked out only while the heading is open."""
        choices = self.get_choices()
        page = self.get_page()
        role = self._role
        if not choices.player(role).has_loudness():
            return []
        heading = page.heading(label=labels.MSG_WIZARD_GROUP_LOUDNESS, is_set=lambda: any(choices.player(role).loudness_level_is_own(level=level) for level in wizard_names.LOUDNESS_LEVELS))
        if not page.is_open(heading):
            return [heading]
        levels = choices.player(role).loudness_levels()
        fields = [heading]
        for level in choices.player(role).loudness_levels_offered():
            own = choices.player(role).loudness_level_is_own(level=level)

            def set_level(number, level=level):
                page.choosing(lambda wanted: choices.player(role).set_loudness_level(level=level, number=wanted))(number)
            fields.append(NumberField(page=page, label=labels.MSG_WIZARD_LEVEL_LABELS[level], number=levels[level], lowest=wizard_names.LOWEST_VELOCITY, highest=wizard_names.HIGHEST_VELOCITY,
                                      shown=None if own else marks.MSG_WIZARD_LEVEL_FROM_GENRE.format(number=levels[level]), set=set_level,
                                      clear=functools.partial(set_level, None) if own else None, clear_what=legends.MSG_FROM_GENRE_WHAT))
        return fields

    def person_fields(self):
        """Return the fields of the player as a person in the band: where the player comes in, where the player lays out, and how strongly the player answers
        to Energy. The first two say which sections the player plays, and read as the person's own where the sections were changed one by one."""
        choices = self.get_choices()
        page = self.get_page()
        role = self._role

        def refusing(setter):
            def set_way(value):
                try:
                    page.choosing(setter)(value)
                except ValueError as problem:
                    page.refuse(str(problem))
            return set_way
        fields = []
        comes, lays = choices.player(role).comes_in_offered(), choices.player(role).lays_out_offered()
        if comes:
            now = choices.player(role).get_comes_in()
            fields.append(ChoiceField(page=page, label=labels.MSG_WIZARD_COMES_IN_LABEL, choices=comes, current=now or comes[0], shown=None if now is not None else labels.MSG_WIZARD_OWN_START,
                                      set=refusing(lambda way: choices.player(role).set_comes_in(way))))
        if lays:
            now = choices.player(role).get_lays_out()
            fields.append(ChoiceField(page=page, label=labels.MSG_WIZARD_LAYS_OUT_LABEL, choices=lays, current=now or lays[0], shown=None if now is not None else labels.MSG_WIZARD_OWN_START,
                                      set=refusing(lambda way: choices.player(role).set_lays_out(way))))
        if choices.player(role).reacts():
            reacts = choices.player(role).get_reacts()
            fields.append(NumberField(page=page, label=labels.MSG_WIZARD_REACTS_LABEL, number=reacts, shown=gauge_shown(place=reacts, lowest=wizard_names.LOWEST_ENERGY, highest=wizard_names.HIGHEST_ENERGY, said=labels.MSG_WIZARD_REACTS_SAID[reacts]),
                                      lowest=wizard_names.LOWEST_ENERGY, highest=wizard_names.HIGHEST_ENERGY, set=page.choosing(lambda number: choices.player(role).set_reacts(number))))
        return fields

    def piece_setter(self, piece):
        """Return what switches a piece of the kit on or off, refusing to switch off the last."""
        choices = self.get_choices()
        page = self.get_page()

        def set_on(on):
            try:
                page.choosing(lambda wanted: choices.get_kit().set_piece_on(piece=piece, on=wanted))(on)
            except ValueError as problem:
                page.refuse(str(problem))
        return set_on

    def way_field(self, *, trait, label):
        choices = self.get_choices()
        page = self.get_page()
        return ChoiceField(page=page, label=label, choices=choices.player(self._role).ways(trait=trait), current=choices.get_band().get_way(trait),
                           set=page.choosing(lambda value: choices.get_band().set_way(trait=trait, value=value)))

    def sound_field(self):
        """Return the Sound field: the band's sound for the player, marked as the band's, or the player's own, chosen from a list."""
        choices = self.get_choices()
        role = self._role

        def shown():
            name = choices.get_sounds().sound_name(choices.get_sounds().get_sound(role))
            return name if choices.get_sounds().has_own_sound(role) else marks.MSG_WIZARD_BAND_SOUND_SHOWN.format(sound=name)
        return Field(label=labels.MSG_WIZARD_SOUND_LABEL, value=shown, enter=lambda: self.get_page().pick_sound(role), enter_what=legends.What.CHOOSE)

    def beside_fields(self):
        """Return the fields of the player who answers the tune: Role, the genre's plan section by section or one thing in every section, and
        how busy the fills are, a number stepped or typed, drawn as a horizontal gauge."""
        choices = self.get_choices()
        page = self.get_page()
        ways = choices.get_band().ways_beside()
        busy = choices.get_band().get_fills_busy()
        gauge = marks.MSG_WIZARD_GAUGE_FULL * busy + marks.MSG_WIZARD_GAUGE_EMPTY * (wizard_names.INTERPLAY_MOST_BUSY - busy)
        return [ChoiceField(page=page, label=labels.MSG_WIZARD_ROLE_LABEL, choices=[labels.MSG_WIZARD_BY_SECTION, *ways], current=choices.get_band().get_role_plan() or labels.MSG_WIZARD_BY_SECTION,
                            set=page.choosing(lambda way: choices.get_band().set_role_plan(None if way == labels.MSG_WIZARD_BY_SECTION else way))),
                NumberField(page=page, label=labels.MSG_WIZARD_FILLS_BUSY_LABEL, number=busy, shown=marks.MSG_WIZARD_BUSY_SHOWN.format(gauge=gauge, level=busy, most=wizard_names.INTERPLAY_MOST_BUSY),
                            lowest=wizard_names.INTERPLAY_LEAST_BUSY, highest=wizard_names.INTERPLAY_MOST_BUSY, set=page.choosing(choices.get_band().set_fills_busy))]

    def piece_row(self, piece):
        """Return the row of a piece of the kit, two cells side by side: whether the piece plays, switched with Space, and what
        the piece sounds as, chosen from a list: its own drum, another drum of the kit, or a General MIDI sound on a note."""
        choices = self.get_choices()
        page = self.get_page()

        def shown():
            sound = choices.get_kit().piece_sound(piece)
            if sound is None:
                return marks.MSG_WIZARD_OWN_DRUM_SHOWN.format(piece=piece)
            if isinstance(sound, str):
                return marks.MSG_WIZARD_KIT_DRUM_SHOWN.format(drum=sound)
            return marks.MSG_WIZARD_SOUND_ON_NOTE.format(sound=labels.MSG_GM_SOUNDS[sound - limits.MIN_GM_SOUND], note=note_shown(choices.get_kit().piece_note(piece)))
        to_own_drum = page.choosing(lambda sound: choices.get_kit().set_piece_sound(piece=piece, sound=sound))

        def own_drum():
            to_own_drum(None)
        return Cells(label=labels.MSG_WIZARD_KIT_PIECE.format(piece=piece), cells=[
            Toggle(label=labels.MSG_WIZARD_KIT_PIECE.format(piece=piece), on=choices.get_kit().piece_is_on(piece), set=self.piece_setter(piece)),
            Field(label=labels.MSG_WIZARD_KIT_PIECE.format(piece=piece), value=shown, enter=lambda: page.pick_piece_sound(piece), enter_what=legends.What.CHOOSE,
                  clear=None if choices.get_kit().piece_sound(piece) is None else own_drum, clear_what=legends.MSG_OWN_DRUM_WHAT),
        ])

    def break_fields(self):
        """Return the Break field where the song may play a break, and under it, while one is chosen, how far it is cut up:
        a number stepped or typed, drawn as a horizontal gauge that is empty for the break as written."""
        choices = self.get_choices()
        page = self.get_page()
        breaks = choices.get_kit().breaks()
        if not breaks:
            return []
        fields = [ChoiceField(page=page, label=labels.MSG_WIZARD_BREAK_LABEL, choices=[labels.MSG_WIZARD_NO_BREAK, *breaks], current=choices.get_kit().get_break() or labels.MSG_WIZARD_NO_BREAK,
                              set=page.choosing(lambda name: choices.get_kit().set_break(None if name == labels.MSG_WIZARD_NO_BREAK else name)))]
        if choices.get_kit().get_break() is not None:
            cut = choices.get_kit().get_break_cut()
            gauge = marks.MSG_WIZARD_GAUGE_FULL * (cut - wizard_names.LEAST_CUT) + marks.MSG_WIZARD_GAUGE_EMPTY * (wizard_names.MOST_CUT - cut)
            fields.append(NumberField(page=page, label=labels.MSG_WIZARD_BREAK_CUT_LABEL, number=cut, shown=marks.MSG_WIZARD_BUSY_SHOWN.format(gauge=gauge, level=cut, most=wizard_names.MOST_CUT),
                                      lowest=wizard_names.LEAST_CUT, highest=wizard_names.MOST_CUT, set=page.choosing(choices.get_kit().set_break_cut)))
        return fields

    def fill_pattern_fields(self):
        """Return the field for what the drums' fill is, where the genre has more than one, since one is nothing to choose."""
        choices = self.get_choices()
        trait = choices.get_band().song_trait(wizard_limits.FILLS_TRAITS)
        if trait is None or len(choices.get_band().song_ways(trait)) < A_CHOICE:
            return []
        return [ChoiceField(page=self.get_page(), label=labels.MSG_WIZARD_FILLS_LABEL, choices=choices.get_band().song_ways(trait), current=choices.get_band().get_way(trait),
                            set=self.get_page().choosing(lambda value: choices.get_band().set_way(trait=trait, value=value)))]

    def fills_field(self):
        """Return the field for how often a fill comes: a number stepped or typed, drawn as a horizontal gauge that is empty at
        never, beside the words for the position."""
        choices = self.get_choices()
        position = choices.get_kit().get_fills()
        gauge = marks.MSG_WIZARD_GAUGE_FULL * (position - wizard_limits.FEWEST_FILLS) + marks.MSG_WIZARD_GAUGE_EMPTY * (wizard_limits.MOST_FILLS - position)
        return NumberField(page=self.get_page(), label=labels.MSG_WIZARD_DRUM_FILLS_LABEL, number=position, shown=marks.MSG_WIZARD_FILLS_SHOWN.format(gauge=gauge, often=labels.MSG_WIZARD_FILLS_COME[position - wizard_limits.FEWEST_FILLS]),
                           lowest=wizard_limits.FEWEST_FILLS, highest=wizard_limits.MOST_FILLS, set=self.get_page().choosing(choices.get_kit().set_fills))

    def busy_field(self):
        """Return the Busy field: a number stepped or typed, drawn as a horizontal Busy gauge beside the number."""
        choices = self.get_choices()
        page = self.get_page()
        level = choices.player(self._role).get_busy()
        gauge = marks.MSG_WIZARD_GAUGE_FULL * level + marks.MSG_WIZARD_GAUGE_EMPTY * (wizard_limits.MOST_BUSY - level)
        # A player whose gauges were moved is no longer the preset, and the field says so until a level is chosen again.
        shown = marks.MSG_WIZARD_BUSY_SHOWN if choices.player(self._role).preset() is not None else marks.MSG_WIZARD_BUSY_CUSTOM_SHOWN
        return NumberField(page=page, label=labels.MSG_WIZARD_BUSY_LABEL, number=level, shown=shown.format(gauge=gauge, level=level, most=wizard_limits.MOST_BUSY),
                           lowest=wizard_limits.LEAST_BUSY, highest=wizard_limits.MOST_BUSY, set=page.choosing(lambda value: choices.player(self._role).set_busy(level=value)))

    def row_field(self, name):
        """Return the field of one of the player's rows of numbers: the row shown, the genre's own marked so, and Enter opening the row to edit."""
        choices = self.get_choices()
        row = marks.MSG_WIZARD_ROW_SEPARATOR.join(str(value) for value in choices.player(self._role).get_row(name=name))
        own = choices.player(self._role).row_is_own(name=name)
        shown = (marks.MSG_WIZARD_ROW_SHOWN if own else marks.MSG_WIZARD_GENRE_ROW_SHOWN).format(row=row)
        return Field(label=labels.MSG_WIZARD_ROW_LABELS[name], value=lambda: shown, enter=lambda: self.edit_row(name), enter_what=legends.What.EDIT)

    def edit_row(self, name):
        """Open a row of the player's in the Row dialog, and keep the row the dialog answers with."""
        choices = self.get_choices()
        page = self.get_page()
        lowest, highest = choices.get_band().row_limits(name)
        dialog = RowDialog(title=messages.MSG_WIZARD_ROW_TITLE.format(row=labels.MSG_WIZARD_ROW_LABELS[name], player=self.name()), values=choices.player(self._role).get_row(name=name),
                           lowest=lowest, highest=highest, fewest=wizard_limits.FEWEST_ROW_CELLS, most=wizard_limits.MOST_ROW_CELLS, usual=choices.player(self._role).genre_row(name=name))
        page.ask(dialog=dialog, then=page.choosing(lambda values: choices.player(self._role).set_row(name=name, values=values)))

    def player_gauge_field(self, gauge):
        """Return the field of one of the player's own gauges: a number stepped or typed, drawn as a horizontal gauge beside the number."""
        choices = self.get_choices()
        page = self.get_page()
        place = choices.player(self._role).get_gauge(gauge=gauge)
        drawn = marks.MSG_WIZARD_GAUGE_FULL * (place - wizard_names.CHARACTERS_LOWEST) + marks.MSG_WIZARD_GAUGE_EMPTY * (wizard_names.CHARACTERS_HIGHEST - place)
        return NumberField(page=page, label=labels.MSG_WIZARD_PLAYER_GAUGE_LABELS[gauge], number=place, shown=marks.MSG_WIZARD_PLAYER_GAUGE_SHOWN.format(gauge=drawn, place=place),
                           lowest=wizard_names.CHARACTERS_LOWEST, highest=wizard_names.CHARACTERS_HIGHEST, set=page.choosing(lambda value: choices.player(self._role).set_gauge(gauge=gauge, place=value)))
