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
from llamatron.macro_composer.melody import LINE_NOTES
from llamatron.macro_composer.song_plan import ENERGY, FADES, HIGHEST_ENERGY, LOWEST_ENERGY, NOT_AT_ALL, RISES, ROOT_OF_PLACE, SETUP, TEMPO_END_OF_PLACE, TEMPO_OF_PLACE, TYPE_OF_PLACE
from llamatron.macro_composer.wizard_choices import LEAVES_AS_JOIN, LINE_IS_HOOK, LINE_OWN, SCALE_TYPES, SHAPE_OF_SECTION, chords_as_text
from llamatron.music.note import ROOT_NAMES
from llamatron.tui.dialogs.lines_dialog import LinesDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.screens.shared.field import ChoiceField, Field, NumberField, Toggle
from llamatron.tui.screens.wizard.branch import Branch, gauge_shown
from llamatron.tui.screens.wizard.hooks_branch import hook_notes_field

# What two sections of one name are told apart by: the section's number in the form and its name.
SECTION_KEY = '{number} {name}'
# Sections are counted from 1, as they are shown.
FIRST_SECTION_NUMBER = 1


# The numbers a section can be given of its own, each with its range, and the choices of each field chosen from a list.
NUMBERS_OF_SECTION = {ENERGY: (LOWEST_ENERGY, HIGHEST_ENERGY), TEMPO_OF_PLACE: (limits.MIN_TEMPO, limits.MAX_TEMPO), TEMPO_END_OF_PLACE: (limits.MIN_TEMPO, limits.MAX_TEMPO)}
CHOICES_OF_SECTION = {LEAVES: list(LEAVES_AS_JOIN), SETUP: [NOT_AT_ALL], ROOT_OF_PLACE: list(ROOT_NAMES), TYPE_OF_PLACE: list(SCALE_TYPES)}


# The groups of what a section is given of its own, in the order they show, each with its fields in order.
OWN_GROUPS = ((labels.MSG_WIZARD_GROUP_HARMONY, (CHORDS, ROOT_OF_PLACE, TYPE_OF_PLACE)),
              (labels.MSG_WIZARD_GROUP_SHAPE, (SHAPE_OF_SECTION, RISES, FADES, TEMPO_OF_PLACE, TEMPO_END_OF_PLACE)),
              (labels.MSG_WIZARD_GROUP_JOINS, (LEAVES, SETUP)))


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
        says_hook = choices.hook_line() is not None and any(line[LINE_IS_HOOK] for line in choices.section_lines(place))
        hook = [hook_notes_field(choices=choices, page=page, label=labels.MSG_WIZARD_SECTION_HOOK_LABEL)] if says_hook else []
        groups = [(labels.MSG_WIZARD_GROUP_TUNE, [*self.lines_fields(), *hook, *([self.role_field()] if choices.section_has_role(place) else [])], lambda: self.has_own_lines() or self.has_own_role() or (says_hook and choices.hook_is_own())),
                  *[(label, [self.own_field(field) for field in own if field in of_group], self.own_checker(of_group)) for label, of_group in OWN_GROUPS],
                  (labels.MSG_WIZARD_GROUP_PLAYERS, players, lambda: sorted(plays) != sorted(usual))]
        for label, inside, is_set in groups:
            if inside:
                fields += [page.heading(label=label, is_set=is_set), *inside]
        return fields

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

    def lines_fields(self):
        """Return the field that says how many lines the section's tune has and how many are a person's own, where the section has a tune; ENTER opens the lines."""
        choices = self.choices()
        lines = choices.section_lines(self._place)
        if not any(line[LINE_NOTES] is not None for line in lines):
            return []
        own = sum(1 for line in lines if line[LINE_OWN])
        said = marks.MSG_LINES_COUNT_OWN.format(count=len(lines), own=own) if own else marks.MSG_LINES_COUNT.format(count=len(lines))
        return [Field(label=labels.MSG_WIZARD_LINES_LABEL, value=lambda: said, enter=self.edit_lines, enter_what=legends.MSG_WIZARD_EDIT_LINES_WHAT)]

    def edit_lines(self):
        choices = self.choices()
        page = self.page()
        place = self._place

        def set_line(*, line, field, value):
            try:
                page.choosing(lambda given: choices.set_section_line(place=place, line=line, field=field, value=given))(value)
            except ValueError as problem:
                return str(problem)
            return None
        section = choices.section_labels()[place]
        dialog = LinesDialog(title=labels.MSG_WIZARD_LINES_TITLE.format(section=section), lines=lambda: choices.section_lines(place), set_line=set_line, steps_in_bar=choices.tune_steps_in_bar(),
                             pitch_of_place=choices.pitch_of_place, title_of_player=choices.role_title, notes_title=labels.MSG_WIZARD_LINE_NOTES_TITLE.format(line='{line}', section=section),
                             listen=lambda: page.problem_listening(what=self.listens()[0], index=place, track=choices.tune_player()), stop_listening=page.app.made_preview().stop)
        page.ask(dialog=dialog, then=lambda nothing: None)

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
