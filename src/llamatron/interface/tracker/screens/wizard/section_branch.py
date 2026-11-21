# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A section of the wizard's form: its kind, how long it lasts and who plays in it; it can be copied, removed and moved."""

import functools

from llamatron.interface.tracker.screens.shared.field import ChoiceField, Field, gauge_shown, NumberField, Toggle
from llamatron.interface.tracker.screens.wizard.branch import Branch
from llamatron.model.schema import limits
from llamatron.model.values import note
from llamatron.user_strings import labels, legends, marks, messages
from llamatron.wizards.create_song import wizard_limits, wizard_names

# What two sections of one name are told apart by: the section's number in the form and its name.
SECTION_KEY = '{number} {name}'
# Sections are counted from 1, as they are shown.
FIRST_SECTION_NUMBER = 1


# The numbers a section can be given of its own, each with its range, and the choices of each field chosen from a list.
NUMBERS_OF_SECTION = {wizard_names.SONG_PLAN_ENERGY: (wizard_names.LOWEST_ENERGY, wizard_names.HIGHEST_ENERGY), wizard_names.TEMPO_OF_PLACE: (limits.MIN_TEMPO, limits.MAX_TEMPO), wizard_names.TEMPO_END_OF_PLACE: (limits.MIN_TEMPO, limits.MAX_TEMPO)}
CHOICES_OF_SECTION = {wizard_names.JOINS_LEAVES: list(wizard_limits.LEAVES_AS_JOIN), wizard_names.SONG_PLAN_SETUP: [wizard_names.NOT_AT_ALL], wizard_names.ROOT_OF_PLACE: list(note.ROOT_NAMES), wizard_names.TYPE_OF_PLACE: list(wizard_limits.SCALE_TYPES)}


# The groups of what a section is given of its own, in the order they show, each with its fields in order.
OWN_GROUPS = ((labels.MSG_WIZARD_GROUP_HARMONY, (wizard_names.ARRANGER_CHORDS, wizard_names.ROOT_OF_PLACE, wizard_names.TYPE_OF_PLACE)),
              (labels.MSG_WIZARD_GROUP_SHAPE, (wizard_limits.SHAPE_OF_SECTION, wizard_names.SONG_PLAN_RISES, wizard_names.SONG_PLAN_FADES, wizard_names.FADE_LEVEL, wizard_names.FADE_OVER, wizard_names.TEMPO_OF_PLACE, wizard_names.TEMPO_END_OF_PLACE)),
              (labels.MSG_WIZARD_GROUP_JOINS, (wizard_names.JOINS_LEAVES, wizard_names.SONG_PLAN_SETUP)))


def fade_field(*, branch, place, field):
    """Return a field of a section's fade, named for the fade's way: the switch, Fade in where the section opens the song and
    Fade out where the section closes it; the level, the velocity the fade starts from or ends at; or the
    bars the fade takes, the first of the section for a fade in and the last for a fade out. The level and the bars show what a fade takes until they are given, and Bksp gives each back."""
    choices = branch.get_choices()
    page = branch.get_page()
    label = labels.MSG_WIZARD_FADE_LABELS[choices.section(place).fade_way()][field]
    own = choices.section(place).own(field=field)

    def set_own(value):
        try:
            page.choosing(lambda wanted: choices.section(place).set_own(field=field, value=wanted))(value)
        except ValueError as problem:
            page.refuse(str(problem))
    if field == wizard_names.SONG_PLAN_FADES:
        return Toggle(label=label, on=bool(own), set=set_own)
    usual = choices.section(place).from_plan(field=field)
    lowest, highest = (wizard_names.FADED, wizard_names.LOUDEST_FADE_LEVEL) if field == wizard_names.FADE_LEVEL else (FIRST_SECTION_NUMBER, choices.section(place).bars())
    now = usual if own is None else min(own, highest)
    said = labels.MSG_WIZARD_FADE_VELOCITY.format(value=now) if field == wizard_names.FADE_LEVEL else labels.MSG_WIZARD_FADE_ONE_BAR if now == 1 else labels.MSG_WIZARD_FADE_BARS.format(value=now)
    clear = dict(clear=lambda: set_own(None), clear_what=legends.MSG_TUNE_USUAL_WHAT) if own is not None else {}
    return NumberField(page=page, label=label, number=own, start=usual, shown=said, lowest=lowest, highest=highest, set=set_own, **clear)


class SectionBranch(Branch):
    """A section of the form, by its place in the form."""

    __slots__ = ('_place',)

    def __init__(self, *, page, place):
        super().__init__(page=page)
        self._place = place

    def key(self):
        return SECTION_KEY.format(number=self._place + FIRST_SECTION_NUMBER, name=self.name())

    def name(self):
        return self.get_choices().get_song_form().section_labels()[self._place]

    def fields(self):
        choices = self.get_choices()
        page = self.get_page()
        place = self._place
        kinds = choices.get_song_form().section_kinds()
        fields = [ChoiceField(page=page, label=labels.MSG_WIZARD_KIND_LABEL, choices=kinds, current=choices.section(place).kind(),
                              set=page.choosing(lambda kind: choices.section(place).set_kind(kind=kind)))]
        lengths = choices.section(place).bars_offered()
        if len(lengths) > 1:
            fields.append(ChoiceField(page=page, label=labels.MSG_WIZARD_BARS_LABEL, choices=lengths, names=[str(bars) for bars in lengths], current=choices.section(place).bars(),
                                      set=page.choosing(lambda bars: choices.section(place).set_bars(bars=bars))))
        else:
            # A held section, or one whose parts fill only its usual length, shows its bars and takes no key.
            fields.append(Field(label=labels.MSG_WIZARD_BARS_LABEL, value=lambda: choices.section(place).bars()))
        own = choices.section(place).own_fields()
        fields += [self.own_field(field) for field in own if field == wizard_names.SONG_PLAN_ENERGY]
        plays = choices.section(place).plays()
        usual = choices.section(place).usually_plays()
        players = [Toggle(label=choices.player(role).title(), on=role in plays, set=self.plays_setter(role)) for role in choices.get_band().roles_in() if role in choices.get_band().roles_shown()]
        # The rest in groups, the same on every section and in the order a section is shaped; a group with nothing to offer in this section is left out.
        groups = [(labels.MSG_WIZARD_GROUP_TUNE, [*self.own_lines_fields(), *([self.role_field()] if choices.section(place).has_role() else [])], lambda: self.has_own_lines() or self.has_own_role()),
                  *[(label, self.own_fields_in(own=own, of_group=of_group), self.own_checker(of_group)) for label, of_group in OWN_GROUPS],
                  (labels.MSG_WIZARD_GROUP_PLAYERS, players, lambda: sorted(plays) != sorted(usual))]
        for label, inside, is_set in groups:
            if inside:
                fields += [page.heading(label=label, is_set=is_set), *inside]
        return fields

    def own_lines_fields(self):
        """Return the field that says how many of the section's lines a person gave notes, a breath or an early note of their own, in
        a song made before tunes were patterns; Bksp gives every line back to the wizard. A tune's notes are now edited on the
        panel of its kind of section, so a section with no such line has no such field."""
        choices = self.get_choices()
        place = self._place
        own = {count: line[wizard_limits.LINE_OWN] for count, line in enumerate(choices.section(place).lines()) if line[wizard_limits.LINE_OWN]}
        if not own:
            return []

        def give_back(nothing):
            for count, given in own.items():
                for field in given:
                    choices.section(place).set_line(line=count, field=field, value=None)
        return [Field(label=labels.MSG_WIZARD_LINES_LABEL, value=lambda: marks.MSG_LINES_COUNT_OWN.format(count=len(choices.section(place).lines()), own=len(own)),
                      clear=lambda: self.get_page().choosing(give_back)(None), clear_what=legends.MSG_TUNE_USUAL_WHAT)]

    def has_own_lines(self):
        return any(line[wizard_limits.LINE_OWN] for line in self.get_choices().section(self._place).lines())

    def has_own_role(self):
        choices = self.get_choices()
        return choices.section(self._place).has_role() and choices.section(self._place).has_own_role()

    def own_fields_in(self, *, own, of_group):
        """Return the fields of a group of a section's own settings that the section offers."""
        return [self.own_field(field) for field in own if field in of_group]

    def own_checker(self, of_group):
        """Return what says whether the section was given anything of its own for a group's fields."""
        choices = self.get_choices()
        return lambda: any(choices.section(self._place).own(field=field) is not None for field in of_group)

    # A section's lines, one by one, in the Lines dialog.

    # What a section of a planned song is given of its own: each field shows what the section takes and where from until it is given, and Bksp gives it back.

    def own_setter(self, field):
        """Return what gives the section a value of its own for a field, None giving the field back, and says why where the song cannot take it."""
        choices = self.get_choices()
        page = self.get_page()
        place = self._place

        def set_own(value):
            try:
                page.choosing(lambda wanted: choices.section(place).set_own(field=field, value=wanted))(value)
            except ValueError as problem:
                page.refuse(str(problem))
        return set_own

    def own_field(self, field):
        """Return the field of something the section may be given of its own, of the kind that thing is."""
        if field in (wizard_names.SONG_PLAN_FADES, wizard_names.FADE_LEVEL, wizard_names.FADE_OVER):
            return self.fade_field(field)
        if field in NUMBERS_OF_SECTION:
            return self._own_number_field(field)
        if field == wizard_names.ARRANGER_CHORDS:
            return self._own_chords_field()
        if field == wizard_names.SONG_PLAN_RISES:
            return self._own_toggle_field(field)
        return self._own_choice_field(field)

    def _section(self):
        """Return the section of the form this panel shows."""
        choices = self.get_choices()
        return choices.section(self._place)

    def _shown_from_above(self, *, field, own, usual):
        """Return what a field shows while the section was given nothing of its own: the value from above and where from."""
        if own is not None:
            return None
        origin = labels.MSG_WIZARD_SECTION_ORIGINS[field]
        return labels.MSG_WIZARD_VALUE_FROM.format(value=usual, origin=origin)

    def _cleared_by(self, *, field, own):
        """Return what lets a field the section was given a value of its own for be cleared back to the value from above."""
        if own is None:
            return {}
        set_own = self.own_setter(field)
        return dict(clear=functools.partial(set_own, None), clear_what=labels.MSG_WIZARD_SECTION_ORIGINS[field])

    def _own_number_field(self, field):
        """Return the field of a number the section may be given of its own: its Energy, shown as a gauge, or a tempo."""
        section = self._section()
        own = section.own(field=field)
        usual = section.from_plan(field=field)
        shown = self._shown_from_above(field=field, own=own, usual=usual)
        lowest, highest = NUMBERS_OF_SECTION[field]
        if field == wizard_names.SONG_PLAN_ENERGY:
            # Energy is a gauge, as Contrast and the players' gauges are, the plan's saying so after the number.
            place = own
            if own is None:
                place = usual
            shown = gauge_shown(place=place, lowest=lowest, highest=highest, said=shown)
        clear = self._cleared_by(field=field, own=own)
        return NumberField(page=self.get_page(), label=labels.MSG_WIZARD_SECTION_OWN_LABELS[field], number=own, start=usual, shown=shown,
                           lowest=lowest, highest=highest, set=self.own_setter(field), **clear)

    def _own_chords_field(self):
        """Return the field of the chords the section may be given of its own, typed as degrees."""
        field = wizard_names.ARRANGER_CHORDS
        section = self._section()
        own = section.own(field=field)
        usual = section.from_plan(field=field)
        text = self._shown_from_above(field=field, own=own, usual=usual)
        typed = usual
        if own is not None:
            text = section.own_chords_typed()
            typed = text
        page = self.get_page()
        ask = functools.partial(page.ask_text, title=messages.MSG_WIZARD_SECTION_CHORDS_PROMPT, value=typed, then=self.own_setter(field), is_name=True)
        clear = self._cleared_by(field=field, own=own)
        return Field(label=labels.MSG_WIZARD_SECTION_OWN_LABELS[field], value=lambda: text, enter=ask, **clear)

    def _own_toggle_field(self, field):
        """Return the field of something the section may switch on or off of its own, such as whether it rises."""
        section = self._section()
        own = section.own(field=field)
        on = own
        if own is None:
            on = section.from_plan(field=field)
        clear = self._cleared_by(field=field, own=own)
        return Toggle(label=labels.MSG_WIZARD_SECTION_OWN_LABELS[field], on=on, set=self.own_setter(field), **clear)

    def _own_choice_field(self, field):
        """Return the field of something the section may be given of its own from a list, the value from above first."""
        section = self._section()
        own = section.own(field=field)
        usual = section.from_plan(field=field)
        from_above = labels.MSG_WIZARD_FROM_ORIGIN.format(origin=labels.MSG_WIZARD_SECTION_ORIGINS[field])
        if field == wizard_limits.SHAPE_OF_SECTION:
            offered = section.shapes()
        else:
            offered = CHOICES_OF_SECTION[field]
        current = own
        if own is None:
            current = from_above
        pick = functools.partial(self._pick_own, field=field, from_above=from_above)
        clear = self._cleared_by(field=field, own=own)
        return ChoiceField(page=self.get_page(), label=labels.MSG_WIZARD_SECTION_OWN_LABELS[field], choices=[from_above, *offered], current=current,
                           shown=self._shown_from_above(field=field, own=own, usual=usual), set=pick, **clear)

    def _pick_own(self, picked, *, field, from_above):
        """Give the section the value picked of its own, or give the field back to the value from above."""
        set_own = self.own_setter(field)
        if picked == from_above:
            set_own(None)
        else:
            set_own(picked)

    def fade_field(self, field):
        return fade_field(branch=self, place=self._place, field=field)

    def listens(self):
        return messages.MSG_WIZARD_LISTEN_SECTION.format(number=self._place + FIRST_SECTION_NUMBER, name=self.name()), self._place, None

    def role_field(self):
        """Return the field of what the answering player does in the section: the plan's, marked as the plan's, until the section is given
        its own from a list, and Bksp gives the section back to the plan."""
        choices = self.get_choices()
        page = self.get_page()
        place = self._place
        ways = choices.interplay().ways_beside()
        way = choices.section(place).role()
        own = choices.section(place).has_own_role()
        chosen = page.choosing(lambda picked: choices.section(place).set_own_role(None if picked == labels.MSG_WIZARD_FROM_PLAN else picked))

        def to_plan():
            chosen(labels.MSG_WIZARD_FROM_PLAN)
        return ChoiceField(page=page, label=labels.MSG_WIZARD_SECTION_ROLE_LABEL.format(player=choices.player(choices.interplay().answered_by()).title()), choices=[labels.MSG_WIZARD_FROM_PLAN, *ways],
                           current=way if own else labels.MSG_WIZARD_FROM_PLAN, shown=way if own else marks.MSG_WIZARD_ROLE_FROM_PLAN.format(way=way), set=chosen,
                           clear=to_plan if own else None, clear_what=legends.MSG_FROM_PLAN_WHAT)

    def plays_setter(self, role):
        """Return what has a player play in the section or sit it out, refusing to leave the section with nobody."""
        choices = self.get_choices()
        page = self.get_page()
        place = self._place

        def set_plays(on):
            try:
                page.choosing(lambda wanted: choices.section(place).set_plays(role=role, on=wanted))(on)
            except ValueError as problem:
                page.refuse(str(problem))
        return set_plays

    # A section is one of a list, the form's.

    def adds(self):
        return True

    def add(self, kind):
        """Put a new section of a kind at the end of the form, as A does on any row of a list."""
        self.get_choices().get_song_form().add_section(place=len(self.get_choices().get_song_form().form_sections()), kind=kind)

    def insert(self, kind):
        """Put a new section of a kind before this one, as insert does on Arrange."""
        self.get_choices().get_song_form().add_section(place=self._place, kind=kind)

    def kinds_to_add(self):
        return self.get_choices().get_song_form().section_kinds()

    def is_listed(self):
        return True

    def copy(self):
        self.get_choices().section(self._place).copy()

    def remove(self):
        self.get_choices().section(self._place).remove()

    def shift(self, offset):
        return self.get_choices().section(self._place).move(offset=offset)
