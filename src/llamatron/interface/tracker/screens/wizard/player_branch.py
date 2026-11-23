# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A player of the wizard's band: how the player plays, and how busy the player is."""

import functools

from llamatron.interface.forms.nodes import Field, NumberField
from llamatron.interface.tracker.dialogs.row_dialog import RowDialog
from llamatron.interface.tracker.screens.shared.field import Button, ChoiceField, gauge_shown
from llamatron.interface.tracker.screens.shared.kit_fields import KitFields
from llamatron.interface.tracker.screens.wizard.branch import Branch
from llamatron.music_theory.composing import notation
from llamatron.user_strings import labels, legends, marks, messages
from llamatron.wizards.create_song import wizard_limits, wizard_names



class PlayerBranch(Branch):
    """One player, by the name the genre gives the player."""

    __slots__ = ('_role',)

    def __init__(self, *, page, role):
        super().__init__(page=page)
        self._role = role

    def name(self):
        player = self._player()
        return player.title()

    def _player(self):
        """Return the player this panel shows, as the wizard's choices hold it."""
        choices = self.get_choices()
        return choices.player(self._role)

    def key(self):
        # The player's own name, since what a player is called can follow how the player plays.
        return self._role

    def fields(self):
        # The player's levels come last, under a heading that opens and closes, which hides every field after it while closed.
        # The button that opens the player's Musician is a button, and so comes after every setting.
        return [*self._own_fields(), *self.loudness_fields(), *self.musician_fields()]

    def _own_fields(self):
        """Return the player's own fields: the ways it plays, its sound, as a person in the band, its dynamics, how busy it is
        with its gauges, the rows the serial style deals it, how it answers the tune where it does, and the drummer's kit."""
        choices = self.get_choices()
        player = self._player()
        sounds = choices.get_sounds()
        interplay = choices.interplay()
        fields = self._way_fields()
        if sounds.has_sound(self._role):
            fields.append(self.sound_field())
        fields += self.person_fields()
        fields += self.dynamics_fields()
        if player.has_busy() and player.get_busy() is not None:
            fields.append(self.busy_field())
            # The player's own gauges, which the Busy field fills in and which each move alone.
            fields += [self.player_gauge_field(gauge) for gauge in player.gauges()]
        # The rows of numbers the serial style deals to the player's notes, each opened in a window of its own.
        fields += [self.row_field(name) for name in player.rows()]
        if interplay.answered_by() == self._role:
            fields += self.beside_fields()
        if not sounds.has_sound(self._role):
            kit_fields = KitFields(choices=choices, page=self.get_page())
            fields = kit_fields.around(fields)
        return fields

    def _way_fields(self):
        """Return the fields of the ways the player plays: a player of notes plays one way, called Plays; the drums have a way for
        each of their parts, each called by the part's name."""
        player = self._player()
        traits = player.traits()
        fields = []
        for trait in traits:
            label = trait.capitalize()
            if len(traits) == 1:
                label = labels.MSG_WIZARD_PLAYS_LABEL
            fields.append(self.way_field(trait=trait, label=label))
        return fields

    def musician_fields(self):
        """Return the button that opens the player's Musician, the generator that plays the player's clips as a player of the band
        would, where the genre's songs have them. A Musician the person changed says so, and Bksp gives the player back the one
        players are given."""
        choices = self.get_choices()
        band = choices.get_band()
        if not choices.is_ready() or not band.has_musicians():
            return []
        page = self.get_page()
        player = self._player()
        edit = functools.partial(page.edit_player, self._role)
        if player.get_musician() is None:
            return [Button(label=labels.MSG_WIZARD_EDIT_PLAYER_BUTTON, key_name=legends.KeyName.ENTER, enter=edit, enter_what=legends.What.EDIT,
                           clear=None, clear_what=legends.MSG_FROM_GENRE_WHAT)]
        give_back = functools.partial(page.choosing(self._musician_given_back), None)
        return [Button(label=labels.MSG_WIZARD_EDIT_OWN_PLAYER_BUTTON, key_name=legends.KeyName.ENTER, enter=edit, enter_what=legends.What.EDIT,
                       clear=give_back, clear_what=legends.MSG_FROM_GENRE_WHAT)]

    def _musician_given_back(self, _):
        """Give the player back the Musician players are given."""
        player = self._player()
        player.set_musician(settings=None)

    def dynamics_fields(self):
        """Return the Dynamics gauge: how far the player's loud and soft notes lie from the normal ones, where that is heard."""
        page = self.get_page()
        loudness = self._player().loudness()
        if not loudness.has_dynamics():
            return []
        dynamics = loudness.get_dynamics()
        shown = gauge_shown(place=dynamics, lowest=wizard_names.LEAST_DYNAMICS + 1, highest=wizard_names.MOST_DYNAMICS, said=labels.MSG_WIZARD_DYNAMICS_SAID[dynamics])
        return [NumberField(page=page, label=labels.MSG_WIZARD_DYNAMICS_LABEL, number=dynamics, lowest=wizard_names.LEAST_DYNAMICS, highest=wizard_names.MOST_DYNAMICS,
                            shown=shown, set=page.choosing(loudness.set_dynamics))]

    def loudness_fields(self):
        """Return the player's levels under the Loudness heading, a velocity for each level the song plays, the genre's until the
        song chooses its own; the drummer's are the whole kit's. The levels are worked out only while the heading is open."""
        page = self.get_page()
        loudness = self._player().loudness()
        if not loudness.has_levels():
            return []
        heading = page.heading(label=labels.MSG_WIZARD_GROUP_LOUDNESS, is_set=functools.partial(self._has_own_level, loudness))
        if not page.is_open(heading):
            return [heading]
        levels = loudness.levels()
        fields = [heading]
        for level in loudness.levels_offered():
            fields.append(self._level_field(loudness=loudness, level=level, number=levels[level]))
        return fields

    @staticmethod
    def _has_own_level(loudness):
        """Return whether the player has any level of the song's own."""
        for level in notation.LOUDNESS_LEVELS:
            if loudness.level_is_own(level=level):
                return True
        return False

    def _level_field(self, *, loudness, level, number):
        """Return the field of one of the player's levels: its velocity, shown as the genre's until the song chooses its own."""
        page = self.get_page()
        own = loudness.level_is_own(level=level)

        def set_level(wanted):
            page.choosing(functools.partial(self._set_level, loudness=loudness, level=level))(wanted)
        shown = None
        clear = None
        if not own:
            shown = marks.MSG_WIZARD_LEVEL_FROM_GENRE.format(number=number)
        else:
            clear = functools.partial(set_level, None)
        return NumberField(page=page, label=labels.MSG_WIZARD_LEVEL_LABELS[level], number=number, lowest=notation.LOWEST_VELOCITY, highest=notation.HIGHEST_VELOCITY,
                           shown=shown, set=set_level, clear=clear, clear_what=legends.MSG_FROM_GENRE_WHAT)

    @staticmethod
    def _set_level(number, *, loudness, level):
        """Give one of the player's levels a velocity of the song's own, or back to the genre with None."""
        loudness.set_level(level=level, number=number)

    def person_fields(self):
        """Return the fields of the player as a person in the band: where the player comes in, where the player lays out, and how
        strongly the player answers to Energy. The first two say which sections the player plays, and read as the person's own
        where the sections were changed one by one."""
        page = self.get_page()
        player = self._player()
        sections = player.sections()
        fields = []
        comes = sections.comes_in_offered()
        if comes:
            fields.append(self._section_way_field(label=labels.MSG_WIZARD_COMES_IN_LABEL, offered=comes, now=sections.get_comes_in(), setter=sections.set_comes_in))
        lays = sections.lays_out_offered()
        if lays:
            fields.append(self._section_way_field(label=labels.MSG_WIZARD_LAYS_OUT_LABEL, offered=lays, now=sections.get_lays_out(), setter=sections.set_lays_out))
        if player.reacts():
            reacts = player.get_reacts()
            shown = gauge_shown(place=reacts, lowest=wizard_names.LOWEST_ENERGY, highest=wizard_names.HIGHEST_ENERGY, said=labels.MSG_WIZARD_REACTS_SAID[reacts])
            fields.append(NumberField(page=page, label=labels.MSG_WIZARD_REACTS_LABEL, number=reacts, shown=shown, lowest=wizard_names.LOWEST_ENERGY,
                                      highest=wizard_names.HIGHEST_ENERGY, set=page.choosing(player.set_reacts)))
        return fields

    def _section_way_field(self, *, label, offered, now, setter):
        """Return the field of a way the player comes in or lays out, read as the person's own where none of the ways fits; a
        way the song cannot be made with is refused on the status line."""
        page = self.get_page()
        current = now or offered[0]
        shown = None
        if now is None:
            shown = labels.MSG_WIZARD_OWN_START
        return ChoiceField(page=page, label=label, choices=offered, current=current, shown=shown, set=page.refusing(setter))

    def way_field(self, *, trait, label):
        """Return the field of a way the player plays a trait, chosen from those that fit the song."""
        choices = self.get_choices()
        page = self.get_page()
        band = choices.get_band()
        player = self._player()
        choose = page.choosing(functools.partial(self._set_way, band=band, trait=trait))
        return ChoiceField(page=page, label=label, choices=player.ways(trait=trait), current=band.get_way(trait), set=choose)

    @staticmethod
    def _set_way(value, *, band, trait):
        """Have the band play a trait a way."""
        band.set_way(trait=trait, value=value)

    def sound_field(self):
        """Return the Sound field: the band's sound for the player, marked as the band's, or the player's own, chosen from a list."""
        page = self.get_page()
        pick = functools.partial(page.pick_sound, self._role)
        return Field(label=labels.MSG_WIZARD_SOUND_LABEL, value=self._sound_shown, enter=pick, enter_what=legends.What.CHOOSE)

    def _sound_shown(self):
        """Return what the Sound field shows: the player's own sound, or the band's, marked as the band's."""
        choices = self.get_choices()
        sounds = choices.get_sounds()
        name = sounds.sound_name(sounds.get_sound(self._role))
        if sounds.has_own_sound(self._role):
            return name
        return marks.MSG_WIZARD_BAND_SOUND_SHOWN.format(sound=name)

    def beside_fields(self):
        """Return the fields of the player who answers the tune: Role, the genre's plan section by section or one thing in every
        section, and how busy the fills are, a number stepped or typed, drawn as a horizontal gauge."""
        choices = self.get_choices()
        page = self.get_page()
        interplay = choices.interplay()
        busy = interplay.get_fills_busy()
        gauge = marks.MSG_WIZARD_GAUGE_FULL * busy + marks.MSG_WIZARD_GAUGE_EMPTY * (wizard_names.INTERPLAY_MOST_BUSY - busy)
        current = interplay.get_role_plan() or labels.MSG_WIZARD_BY_SECTION
        role = ChoiceField(page=page, label=labels.MSG_WIZARD_ROLE_LABEL, choices=[labels.MSG_WIZARD_BY_SECTION, *interplay.ways_beside()], current=current,
                           set=page.choosing(functools.partial(self._set_role_plan, interplay=interplay)))
        shown = marks.MSG_WIZARD_BUSY_SHOWN.format(gauge=gauge, level=busy, most=wizard_names.INTERPLAY_MOST_BUSY)
        fills_busy = NumberField(page=page, label=labels.MSG_WIZARD_FILLS_BUSY_LABEL, number=busy, shown=shown, lowest=wizard_names.INTERPLAY_LEAST_BUSY,
                                 highest=wizard_names.INTERPLAY_MOST_BUSY, set=page.choosing(interplay.set_fills_busy))
        return [role, fills_busy]

    @staticmethod
    def _set_role_plan(way, *, interplay):
        """Have the answering player do one thing in every section, or go by the plan section by section."""
        if way == labels.MSG_WIZARD_BY_SECTION:
            way = None
        interplay.set_role_plan(way)

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
        lowest, highest = wizard_limits.ROW_LIMITS[name]
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
