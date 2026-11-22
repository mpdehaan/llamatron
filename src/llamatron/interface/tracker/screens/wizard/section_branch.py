# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A section of the wizard's form: its kind, how long it lasts and who plays in it; it can be copied, removed and moved."""

import functools

from llamatron.interface.tracker.screens.shared.field import ChoiceField, Field, Toggle
from llamatron.interface.tracker.screens.shared.section_fade import fade_field
from llamatron.interface.tracker.screens.shared.section_own_fields import SectionOwnFields
from llamatron.interface.tracker.screens.wizard.branch import Branch
from llamatron.user_strings import labels, legends, marks, messages
from llamatron.wizards.create_song import wizard_limits, wizard_names

# What two sections of one name are told apart by: the section's number in the form and its name.
SECTION_KEY = '{number} {name}'
# Sections are counted from 1, as they are shown.
FIRST_SECTION_NUMBER = 1


# The groups of what a section is given of its own, in the order they show, each with its fields in order.
OWN_GROUPS = (
    (labels.MSG_WIZARD_GROUP_HARMONY, (wizard_names.ARRANGER_CHORDS, wizard_names.ROOT_OF_PLACE, wizard_names.TYPE_OF_PLACE)),
    (labels.MSG_WIZARD_GROUP_SHAPE, (
        wizard_limits.SHAPE_OF_SECTION, wizard_names.SONG_PLAN_RISES, wizard_names.SONG_PLAN_FADES, wizard_names.FADE_LEVEL,
        wizard_names.FADE_OVER, wizard_names.TEMPO_OF_PLACE, wizard_names.TEMPO_END_OF_PLACE,
    )),
    (labels.MSG_WIZARD_GROUP_JOINS, (wizard_names.JOINS_LEAVES, wizard_names.SONG_PLAN_SETUP)),
)




class SectionBranch(Branch):
    """A section of the form, by its place in the form."""

    __slots__ = ('_place',)

    def __init__(self, *, page, place):
        super().__init__(page=page)
        self._place = place

    def key(self):
        return SECTION_KEY.format(number=self._place + FIRST_SECTION_NUMBER, name=self.name())

    def name(self):
        form = self.get_choices().get_song_form()
        return form.section_labels()[self._place]

    def fields(self):
        page = self.get_page()
        section = self._section()
        own = section.own_fields()
        own_fields = self._own_fields()
        fields = [self._kind_field(), self._bars_field()]
        if wizard_names.SONG_PLAN_ENERGY in own:
            fields.append(own_fields.field(wizard_names.SONG_PLAN_ENERGY))
        # The rest in groups, the same on every section and in the order a section is shaped; a group with nothing to offer in
        # this section is left out.
        tune = self.own_lines_fields()
        if section.has_role():
            tune.append(self.role_field())
        groups = [(labels.MSG_WIZARD_GROUP_TUNE, tune, self._has_own_tune)]
        for label, of_group in OWN_GROUPS:
            groups.append((label, own_fields.fields_in(own=own, of_group=of_group), own_fields.checker(of_group)))
        groups.append((labels.MSG_WIZARD_GROUP_PLAYERS, self._player_fields(), self._has_own_players))
        for label, inside, is_set in groups:
            if inside:
                fields.append(page.heading(label=label, is_set=is_set))
                fields += inside
        return fields

    def _kind_field(self):
        """Return the field of the section's kind."""
        page = self.get_page()
        section = self._section()
        form = self.get_choices().get_song_form()
        return ChoiceField(page=page, label=labels.MSG_WIZARD_KIND_LABEL, choices=form.section_kinds(), current=section.kind(),
                           set=page.choosing(self._set_kind))

    def _set_kind(self, kind):
        section = self._section()
        section.set_kind(kind=kind)

    def _bars_field(self):
        """Return the field of how many bars the section lasts: chosen from the lengths it is offered, or shown alone, taking no
        key, for a held section or one whose parts fill only its usual length."""
        page = self.get_page()
        section = self._section()
        lengths = section.bars_offered()
        if len(lengths) <= 1:
            return Field(label=labels.MSG_WIZARD_BARS_LABEL, value=self._bars)
        names = []
        for bars in lengths:
            names.append(str(bars))
        return ChoiceField(page=page, label=labels.MSG_WIZARD_BARS_LABEL, choices=lengths, names=names, current=section.bars(),
                           set=page.choosing(self._set_bars))

    def _bars(self):
        section = self._section()
        return section.bars()

    def _set_bars(self, bars):
        section = self._section()
        section.set_bars(bars=bars)

    def _player_fields(self):
        """Return a switch for each player the band shows, on where the player plays in the section."""
        choices = self.get_choices()
        band = choices.get_band()
        shown = band.roles_shown()
        plays = self._section().plays()
        players = []
        for role in band.roles_in():
            if role in shown:
                player = choices.player(role)
                players.append(Toggle(label=player.title(), on=role in plays, set=self.plays_setter(role)))
        return players

    def _has_own_tune(self):
        return self.has_own_lines() or self.has_own_role()

    def _has_own_players(self):
        """Return whether the players who play in the section differ from those who usually do."""
        section = self._section()
        return sorted(section.plays()) != sorted(section.usually_plays())

    def own_lines_fields(self):
        """Return the field that says how many of the section's lines a person gave notes, a breath or an early note of their
        own, in a song made before tunes were patterns; Bksp gives every line back to the wizard. A tune's notes are now edited
        on the panel of its kind of section, so a section with no such line has no such field."""
        lines = self._section().lines()
        made = lines.as_made()
        own = {}
        for count, line in enumerate(made):
            if line[wizard_limits.LINE_OWN]:
                own[count] = line[wizard_limits.LINE_OWN]
        if not own:
            return []
        page = self.get_page()
        shown = marks.MSG_LINES_COUNT_OWN.format(count=len(made), own=len(own))
        give_back = page.choosing(functools.partial(self._give_lines_back, own=own))
        return [Field(label=labels.MSG_WIZARD_LINES_LABEL, value=lambda: shown, clear=functools.partial(give_back, None),
                      clear_what=legends.MSG_TUNE_USUAL_WHAT)]

    def _give_lines_back(self, nothing, *, own):
        """Give every line the section was given of its own back to the wizard."""
        lines = self._section().lines()
        for count, given in own.items():
            for field in given:
                lines.set_line(line=count, field=field, value=None)

    def has_own_lines(self):
        lines = self._section().lines()
        for line in lines.as_made():
            if line[wizard_limits.LINE_OWN]:
                return True
        return False

    def has_own_role(self):
        section = self._section()
        return section.has_role() and section.has_own_role()

    # What a section of a planned song is given of its own: each field shows what the section takes and where from until it is given, and Bksp gives it back.

    def _section(self):
        """Return the section of the form this panel shows."""
        choices = self.get_choices()
        return choices.section(self._place)

    def fade_field(self, field):
        return fade_field(branch=self, place=self._place, field=field)

    def listens(self):
        said = messages.MSG_WIZARD_LISTEN_SECTION.format(number=self._place + FIRST_SECTION_NUMBER, name=self.name())
        return said, self._place, None

    def role_field(self):
        """Return the field of what the answering player does in the section: the plan's, marked as the plan's, until the section
        is given its own from a list, and Bksp gives the section back to the plan."""
        choices = self.get_choices()
        page = self.get_page()
        section = self._section()
        interplay = choices.interplay()
        way = section.role()
        own = section.has_own_role()
        chosen = page.choosing(self._set_role)
        current = labels.MSG_WIZARD_FROM_PLAN
        shown = marks.MSG_WIZARD_ROLE_FROM_PLAN.format(way=way)
        clear = None
        if own:
            current = way
            shown = way
            clear = functools.partial(chosen, labels.MSG_WIZARD_FROM_PLAN)
        answering = choices.player(interplay.answered_by())
        label = labels.MSG_WIZARD_SECTION_ROLE_LABEL.format(player=answering.title())
        return ChoiceField(page=page, label=label, choices=[labels.MSG_WIZARD_FROM_PLAN, *interplay.ways_beside()], current=current,
                           shown=shown, set=chosen, clear=clear, clear_what=legends.MSG_FROM_PLAN_WHAT)

    def _set_role(self, picked):
        """Give the section the answering player's way picked, or give it back to the plan."""
        if picked == labels.MSG_WIZARD_FROM_PLAN:
            picked = None
        section = self._section()
        section.set_own_role(picked)

    def plays_setter(self, role):
        """Return what has a player play in the section or sit it out, refusing to leave the section with nobody."""
        page = self.get_page()
        return page.refusing(functools.partial(self._set_plays, role=role))

    def _set_plays(self, on, *, role):
        section = self._section()
        section.set_plays(role=role, on=on)

    # A section is one of a list, the form's.

    def adds(self):
        return True

    def add(self, kind):
        """Put a new section of a kind at the end of the form, as A does on any row of a list."""
        form = self.get_choices().get_song_form()
        form.add_section(place=len(form.form_sections()), kind=kind)

    def insert(self, kind):
        """Put a new section of a kind before this one, as insert does on Arrange."""
        form = self.get_choices().get_song_form()
        form.add_section(place=self._place, kind=kind)

    def kinds_to_add(self):
        form = self.get_choices().get_song_form()
        return form.section_kinds()

    def is_listed(self):
        return True

    def copy(self):
        self._section().copy()

    def remove(self):
        self._section().remove()

    def shift(self, offset):
        section = self._section()
        return section.move(offset=offset)

    def _own_fields(self):
        """Return the fields of what the section may be given of its own."""
        return SectionOwnFields(branch=self, place=self._place)
