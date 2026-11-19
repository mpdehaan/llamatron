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

"""A section of the wizard's form: its kind, how long it lasts and who plays in it; it can be copied, removed and moved."""

from llamatron.composition import limits
from llamatron.strings import labels, legends, marks, messages
from llamatron.macro_composer.arranger import CHORDS
from llamatron.macro_composer.joins import LEAVES
from llamatron.macro_composer.song_plan import ENERGY, FADE_LEVEL, FADE_OVER, FADED, FADES, LOUDEST_FADE_LEVEL, HIGHEST_ENERGY, LOWEST_ENERGY, NOT_AT_ALL, RISES, ROOT_OF_PLACE, SETUP, TEMPO_END_OF_PLACE, TEMPO_OF_PLACE, TYPE_OF_PLACE
from llamatron.macro_composer.wizard_choices import LEAVES_AS_JOIN, LINE_OWN, SCALE_TYPES, SHAPE_OF_SECTION, chords_as_text
from llamatron.music.note import ROOT_NAMES
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.screens.shared.field import ChoiceField, Field, NumberField, Toggle, gauge_shown
from llamatron.tui.screens.wizard.branch import Branch

# What two sections of one name are told apart by: the section's number in the form and its name.
SECTION_KEY = '{number} {name}'
# Sections are counted from 1, as they are shown.
FIRST_SECTION_NUMBER = 1


# The numbers a section can be given of its own, each with its range, and the choices of each field chosen from a list.
NUMBERS_OF_SECTION = {ENERGY: (LOWEST_ENERGY, HIGHEST_ENERGY), TEMPO_OF_PLACE: (limits.MIN_TEMPO, limits.MAX_TEMPO), TEMPO_END_OF_PLACE: (limits.MIN_TEMPO, limits.MAX_TEMPO)}
CHOICES_OF_SECTION = {LEAVES: list(LEAVES_AS_JOIN), SETUP: [NOT_AT_ALL], ROOT_OF_PLACE: list(ROOT_NAMES), TYPE_OF_PLACE: list(SCALE_TYPES)}


# The groups of what a section is given of its own, in the order they show, each with its fields in order.
OWN_GROUPS = ((labels.MSG_WIZARD_GROUP_HARMONY, (CHORDS, ROOT_OF_PLACE, TYPE_OF_PLACE)),
              (labels.MSG_WIZARD_GROUP_SHAPE, (SHAPE_OF_SECTION, RISES, FADES, FADE_LEVEL, FADE_OVER, TEMPO_OF_PLACE, TEMPO_END_OF_PLACE)),
              (labels.MSG_WIZARD_GROUP_JOINS, (LEAVES, SETUP)))


def fade_field(*, branch, place, field):
    """Return a field of a section's fade, named for the fade's way: the switch, Fade in where the section opens the song and
    Fade out where the section closes it; the level, the velocity the fade starts from or ends at; or the
    bars the fade takes, the first of the section for a fade in and the last for a fade out. The level and the bars show what a fade takes until they are given, and Bksp gives each back."""
    choices = branch.choices()
    page = branch.page()
    label = labels.MSG_WIZARD_FADE_LABELS[choices.fade_way(place)][field]
    own = choices.section_own(place=place, field=field)

    def set_own(value):
        try:
            page.choosing(lambda wanted: choices.set_section_own(place=place, field=field, value=wanted))(value)
        except ValueError as problem:
            page.refuse(str(problem))
    if field == FADES:
        return Toggle(label=label, on=bool(own), set=set_own)
    usual = choices.section_from_plan(place=place, field=field)
    lowest, highest = (FADED, LOUDEST_FADE_LEVEL) if field == FADE_LEVEL else (FIRST_SECTION_NUMBER, choices.section_bars(place))
    now = usual if own is None else min(own, highest)
    said = labels.MSG_WIZARD_FADE_VELOCITY.format(value=now) if field == FADE_LEVEL else labels.MSG_WIZARD_FADE_ONE_BAR if now == 1 else labels.MSG_WIZARD_FADE_BARS.format(value=now)
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
        return self.choices().section_labels()[self._place]

    def fields(self):
        choices = self.choices()
        page = self.page()
        place = self._place
        kinds = choices.section_kinds()
        fields = [ChoiceField(page=page, label=labels.MSG_WIZARD_KIND_LABEL, choices=kinds, current=choices.section_kind(place),
                              set=page.choosing(lambda kind: choices.set_section_kind(place=place, kind=kind)))]
        lengths = choices.bars_offered(place)
        if len(lengths) > 1:
            fields.append(ChoiceField(page=page, label=labels.MSG_WIZARD_BARS_LABEL, choices=lengths, names=[str(bars) for bars in lengths], current=choices.section_bars(place),
                                      set=page.choosing(lambda bars: choices.set_section_bars(place=place, bars=bars))))
        else:
            # A held section, or one whose parts fill only its usual length, shows its bars and takes no key.
            fields.append(Field(label=labels.MSG_WIZARD_BARS_LABEL, value=lambda: choices.section_bars(place)))
        own = choices.section_own_fields(place)
        fields += [self.own_field(field) for field in own if field == ENERGY]
        plays = choices.section_plays(place)
        usual = choices.section_usually_plays(place)
        players = [Toggle(label=choices.role_title(role), on=role in plays, set=self.plays_setter(role)) for role in choices.roles_in() if role in choices.roles_shown()]
        # The rest in groups, the same on every section and in the order a section is shaped; a group with nothing to offer in this section is left out.
        groups = [(labels.MSG_WIZARD_GROUP_TUNE, [*self.own_lines_fields(), *([self.role_field()] if choices.section_has_role(place) else [])], lambda: self.has_own_lines() or self.has_own_role()),
                  *[(label, [self.own_field(field) for field in own if field in of_group], self.own_checker(of_group)) for label, of_group in OWN_GROUPS],
                  (labels.MSG_WIZARD_GROUP_PLAYERS, players, lambda: sorted(plays) != sorted(usual))]
        for label, inside, is_set in groups:
            if inside:
                fields += [page.heading(label=label, is_set=is_set), *inside]
        return fields

    def own_lines_fields(self):
        """Return the field that says how many of the section's lines a person gave notes, a breath or an early note of their own, in
        a song made before tunes were patterns; Bksp gives every line back to the wizard. A tune's notes are now edited on the
        panel of its kind of section, so a section with no such line has no such field."""
        choices = self.choices()
        place = self._place
        own = {count: line[LINE_OWN] for count, line in enumerate(choices.section_lines(place)) if line[LINE_OWN]}
        if not own:
            return []

        def give_back(nothing):
            for count, given in own.items():
                for field in given:
                    choices.set_section_line(place=place, line=count, field=field, value=None)
        return [Field(label=labels.MSG_WIZARD_LINES_LABEL, value=lambda: marks.MSG_LINES_COUNT_OWN.format(count=len(choices.section_lines(place)), own=len(own)),
                      clear=lambda: self.page().choosing(give_back)(None), clear_what=legends.MSG_TUNE_USUAL_WHAT)]

    def has_own_lines(self):
        return any(line[LINE_OWN] for line in self.choices().section_lines(self._place))

    def has_own_role(self):
        choices = self.choices()
        return choices.section_has_role(self._place) and choices.section_role_is_own(self._place)

    def own_checker(self, of_group):
        """Return what says whether the section was given anything of its own for a group's fields."""
        choices = self.choices()
        return lambda: any(choices.section_own(place=self._place, field=field) is not None for field in of_group)

    # A section's lines, one by one, in the Lines dialog.

    # What a section of a planned song is given of its own: each field shows what the section takes and where from until it is given, and Bksp gives it back.

    def own_setter(self, field):
        """Return what gives the section a value of its own for a field, None giving the field back, and says why where the song cannot take it."""
        choices = self.choices()
        page = self.page()
        place = self._place

        def set_own(value):
            try:
                page.choosing(lambda wanted: choices.set_section_own(place=place, field=field, value=wanted))(value)
            except ValueError as problem:
                page.refuse(str(problem))
        return set_own

    def own_field(self, field):
        choices = self.choices()
        page = self.page()
        place = self._place
        if field in (FADES, FADE_LEVEL, FADE_OVER):
            return self.fade_field(field)
        own = choices.section_own(place=place, field=field)
        usual = choices.section_from_plan(place=place, field=field)
        origin = labels.MSG_WIZARD_SECTION_ORIGINS[field]
        shown = labels.MSG_WIZARD_VALUE_FROM.format(value=usual, origin=origin) if own is None else None
        label = labels.MSG_WIZARD_SECTION_OWN_LABELS[field]
        set_own = self.own_setter(field)
        clear = dict(clear=lambda: set_own(None), clear_what=origin) if own is not None else {}
        if field in NUMBERS_OF_SECTION:
            lowest, highest = NUMBERS_OF_SECTION[field]
            if field == ENERGY:
                # Energy is a gauge, as Contrast and the players' gauges are, the plan's saying so after the number.
                shown = gauge_shown(place=usual if own is None else own, lowest=lowest, highest=highest, said=shown)
            return NumberField(page=page, label=label, number=own, start=usual, shown=shown, lowest=lowest, highest=highest, set=set_own, **clear)
        if field == CHORDS:
            def ask():
                page.ask(dialog=PromptDialog(title=messages.MSG_WIZARD_SECTION_CHORDS_PROMPT, value=chords_as_text(own) if own is not None else usual, max_length=limits.MAX_NAME_LENGTH), then=set_own)
            return Field(label=label, value=lambda: shown if own is None else chords_as_text(own), enter=ask, **clear)
        if field in (RISES, FADES):
            return Toggle(label=label, on=usual if own is None else own, set=set_own, **clear)
        from_above = labels.MSG_WIZARD_FROM_ORIGIN.format(origin=origin)
        offered = choices.section_shapes(place) if field == SHAPE_OF_SECTION else CHOICES_OF_SECTION[field]
        return ChoiceField(page=page, label=label, choices=[from_above, *offered], current=from_above if own is None else own, shown=shown,
                           set=lambda picked: set_own(None if picked == from_above else picked), **clear)

    def fade_field(self, field):
        return fade_field(branch=self, place=self._place, field=field)

    def listens(self):
        return messages.MSG_WIZARD_LISTEN_SECTION.format(number=self._place + FIRST_SECTION_NUMBER, name=self.name()), self._place, None

    def role_field(self):
        """Return the field of what the answering player does in the section: the plan's, marked as the plan's, until the section is given
        its own from a list, and Bksp gives the section back to the plan."""
        choices = self.choices()
        page = self.page()
        place = self._place
        ways = choices.ways_beside()
        way = choices.section_role(place)
        own = choices.section_role_is_own(place)
        chosen = page.choosing(lambda picked: choices.set_section_role(place=place, way=None if picked == labels.MSG_WIZARD_FROM_PLAN else picked))

        def to_plan():
            chosen(labels.MSG_WIZARD_FROM_PLAN)
        return ChoiceField(page=page, label=labels.MSG_WIZARD_SECTION_ROLE_LABEL.format(player=choices.role_title(choices.answered_by())), choices=[labels.MSG_WIZARD_FROM_PLAN, *ways],
                           current=way if own else labels.MSG_WIZARD_FROM_PLAN, shown=way if own else marks.MSG_WIZARD_ROLE_FROM_PLAN.format(way=way), set=chosen,
                           clear=to_plan if own else None, clear_what=legends.MSG_FROM_PLAN_WHAT)

    def plays_setter(self, role):
        """Return what has a player play in the section or sit it out, refusing to leave the section with nobody."""
        choices = self.choices()
        page = self.page()
        place = self._place

        def set_plays(on):
            try:
                page.choosing(lambda wanted: choices.set_section_plays(place=place, role=role, on=wanted))(on)
            except ValueError as problem:
                page.refuse(str(problem))
        return set_plays

    # A section is one of a list, the form's.

    def adds(self):
        return True

    def add(self, kind):
        """Put a new section of a kind at the end of the form, as A does on any row of a list."""
        self.choices().add_section(place=len(self.choices().form_sections()), kind=kind)

    def insert(self, kind):
        """Put a new section of a kind before this one, as insert does on Arrange."""
        self.choices().add_section(place=self._place, kind=kind)

    def kinds_to_add(self):
        return self.choices().section_kinds()

    def is_listed(self):
        return True

    def copy(self):
        self.choices().copy_section(self._place)

    def remove(self):
        self.choices().remove_section(self._place)

    def move(self, offset):
        return self.choices().move_section(place=self._place, offset=offset)
