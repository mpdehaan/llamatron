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
"""The intro in the wizard: its parts, each with its bars, who plays, who says the hook and its fade in.

An intro may be one section or several, a player joining with each, as a band that starts with
the drums alone and then the bass. The panel holds how the song starts, which makes the parts,
and then a heading for each part that opens onto the part's fields. The buttons act on the part
the cursor was last on or in: they open the notes of the part's melody in the pattern editor,
play the melody's player alone and play the part with everybody in it. A part has a melody only
while a player is chosen to say the hook in it. The panel comes after the other melodies', since
the intro's melody is made from the hook and the hook from the chorus.
"""

from rich.text import Text

from llamatron.composition.checks import listed
from llamatron.macro_composer import wizard_choices
from llamatron.strings import errors, labels, legends, marks, messages
from llamatron.tui import drawing
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.drawing import Style
from llamatron.tui.screens.shared.field import Button, ChoiceField, Field, Heading, Toggle
from llamatron.tui.screens.wizard.branch import Branch
from llamatron.tui.screens.wizard.section_branch import fade_field

# What the panel is remembered by, apart from a section of the form called intro.
INTRO_MELODY_KEY = 'melody of the intro'
FIRST_PART = 1


class IntroMelodyBranch(Branch):
    """The intro: how the song starts, and each part of the intro."""

    __slots__ = ()

    def key(self):
        return INTRO_MELODY_KEY

    def name(self):
        return wizard_choices.INTRO.capitalize()

    def summary(self):
        """Return how many parts the intro has, where it has more than one, or who says the hook in it."""
        choices = self.choices()
        parts = choices.intro_parts()
        if len(parts) > 1:
            return marks.MSG_WIZARD_COUNT_SHOWN.format(count=len(parts))
        player = choices.intro_melody_player(parts[0]) if parts else None
        return choices.role_title(player) if player is not None else labels.MSG_WIZARD_NOBODY

    # The parts, each known by its number from 1 in the order they play.

    def part_label(self, number):
        return labels.MSG_WIZARD_INTRO_PART.format(number=number)

    def place_of(self, number):
        """Return the place in the form of a part by its number, or None where the intro has no such part."""
        parts = self.choices().intro_parts()
        return parts[number - FIRST_PART] if number is not None and FIRST_PART <= number <= len(parts) else None

    def part_under_cursor(self):
        """Return the number of the part whose heading the cursor is on or under, or None where the cursor is on a button or above the parts."""
        page = self.page()
        if not page.in_fields or isinstance(page.field(), Button):
            return None
        heading = page.heading_over_cursor()
        return next((number for number, _ in enumerate(self.choices().intro_parts(), start=FIRST_PART) if self.part_label(number) == heading), None)

    def part_marked(self):
        """Return the number of the part the buttons act on: the part the cursor is on or in, else the part the cursor was last
        on, else the first part somebody says the hook in, else the first; None where the intro has no part."""
        choices = self.choices()
        page = self.page()
        parts = choices.intro_parts()
        if not parts:
            return None
        under = self.part_under_cursor()
        if under is not None:
            page.marked_part = under
        if self.place_of(page.marked_part) is not None:
            return page.marked_part
        with_melody = choices.intro_melody_place()
        return parts.index(with_melody) + FIRST_PART if with_melody in parts else FIRST_PART

    def fields(self):
        choices = self.choices()
        if not choices.is_ready():
            return []
        fields = [*self.start_fields()]
        for number, place in enumerate(choices.intro_parts(), start=FIRST_PART):
            fields.append(self.part_heading(number=number, place=place))
            fields += self.part_fields(place)
        return [*fields, *self.buttons()]

    def start_fields(self):
        """Return the field of how the song starts, which makes the intro's parts; parts a person changed read as the person's own."""
        choices = self.choices()
        page = self.page()
        if not choices.starts():
            return []

        def set_start(way):
            try:
                page.choosing(choices.set_start)(way)
            except ValueError as problem:
                page.refuse(str(problem))
        start = choices.get_start()
        return [ChoiceField(page=page, label=labels.MSG_WIZARD_STARTS_LABEL, choices=choices.starts(), current=start or choices.starts()[0], shown=None if start is not None else labels.MSG_WIZARD_OWN_START, set=set_start)]

    def part_heading(self, *, number, place):
        """Return a part's heading, which says the part's bars, who plays and who says the hook, and opens onto the part's fields; Bksp deletes the part, after asking."""
        choices = self.choices()
        page = self.page()
        label = self.part_label(number)

        def said():
            bars = choices.section_bars(place)
            player = choices.intro_melody_player(place)
            melody = marks.MSG_WIZARD_PART_NO_MELODY if player is None else marks.MSG_WIZARD_PART_MELODY.format(player=choices.role_title(player))
            return marks.MSG_WIZARD_PART_ROW.format(bars=marks.MSG_WIZARD_PART_ONE_BAR if bars == 1 else marks.MSG_WIZARD_PART_BARS.format(bars=bars),
                                                    plays=listed([choices.role_title(role) for role in choices.section_plays(place) if role in choices.roles_shown()]), melody=melody)
        return Heading(label=label, is_set=lambda: True, toggle=lambda: page.toggle_section(label), said=said, clear=lambda: self.remove_part(number), clear_what=legends.What.DELETE)

    def part_fields(self, place):
        """Return a part's fields: its bars, who says the hook in it, its fade in, and a switch for each player of the band."""
        choices = self.choices()
        page = self.page()
        lengths = choices.bars_offered(place)
        if len(lengths) > 1:
            bars = ChoiceField(page=page, label=labels.MSG_WIZARD_BARS_LABEL, choices=lengths, names=[str(count) for count in lengths], current=choices.section_bars(place),
                               set=page.choosing(lambda count: choices.set_section_bars(place=place, bars=count)))
        else:
            bars = Field(label=labels.MSG_WIZARD_BARS_LABEL, value=lambda: choices.section_bars(place))
        titles = {choices.role_title(role): role for role in choices.intro_hook_players()}
        now = choices.intro_melody_player(place)
        if titles:
            melody = ChoiceField(page=page, label=labels.MSG_WIZARD_PART_MELODY_LABEL, choices=[labels.MSG_WIZARD_NOBODY, *titles], current=labels.MSG_WIZARD_NOBODY if now is None else choices.role_title(now),
                                 set=self.refusing(lambda title: choices.set_intro_melody(place=place, role=titles.get(title))))
        else:
            melody = Field(label=labels.MSG_WIZARD_PART_MELODY_LABEL, value=lambda: labels.MSG_WIZARD_NOBODY)
        fades = [fade_field(branch=self, place=place, field=field) for field in choices.fade_fields(place)]
        plays = choices.section_plays(place)
        players = [Toggle(label=choices.role_title(role), on=role in plays,
                          set=self.refusing(lambda on, role=role: choices.set_section_plays(place=place, role=role, on=on)))
                   for role in choices.roles_in() if role in choices.roles_shown()]
        return [bars, melody, *fades, *players]

    def refusing(self, setter):
        """Return a setter made through the page, which says why on the status line where the song cannot take the value."""
        page = self.page()

        def set_value(value):
            try:
                page.choosing(setter)(value)
            except ValueError as problem:
                page.refuse(str(problem))
        return set_value

    def buttons(self):
        """Return the buttons, which act on the marked part: its melody's notes in the pattern editor, its melody's player alone,
        and the part with the band; and the button that adds a part."""
        page = self.page()
        return [Button(label=labels.MSG_WIZARD_EDIT_NOTES_BUTTON, enter=self.edit_notes, enter_what=legends.MSG_WIZARD_EDIT_NOTES_WHAT, clear=self.give_back, clear_what=legends.MSG_TUNE_USUAL_WHAT),
                Button(label=labels.MSG_WIZARD_LISTEN_BUTTON, enter=self.listen_alone, enter_what=legends.MSG_LISTEN_WHAT),
                Button(label=labels.MSG_WIZARD_LISTEN_BAND_BUTTON, enter=lambda: page.listen_to(self.heard_with_band()), enter_what=legends.MSG_LISTEN_WHAT),
                Button(label=labels.MSG_WIZARD_ADD_PART_BUTTON, enter=self.add_part, enter_what=legends.What.ADD)]

    def melody_place(self):
        """Return the place of the marked part where somebody says the hook in it; else say on the status line where to choose a player, and return None."""
        number = self.part_marked()
        place = self.place_of(number)
        if place is None:
            self.page().refuse(errors.ERR_WIZARD_NO_PART)
            return None
        if self.choices().intro_melody_player(place) is None:
            self.page().refuse(errors.ERR_WIZARD_PART_NO_MELODY.format(number=number))
            return None
        return place

    def edit_notes(self):
        place = self.melody_place()
        if place is not None:
            self.page().edit_intro(place=place)

    def listen_alone(self):
        if self.melody_place() is not None:
            self.page().listen_to(self.listens())

    def give_back(self):
        """Give the marked part's notes edited by hand back to the wizard, after a question."""
        choices = self.choices()
        page = self.page()
        place = self.place_of(self.part_marked())
        if place is None or not choices.intro_is_own(place=place):
            return
        question = messages.MSG_WIZARD_TUNE_GIVE_BACK_QUESTION.format(kind=wizard_choices.INTRO)
        page.ask(dialog=ConfirmDialog(title=messages.MSG_WIZARD_TUNE_GIVE_BACK_TITLE, messages=[question], starts_on_no=True), then=page.choosing(lambda _: choices.set_intro_pattern(place=place, pattern=None)))

    def add_part(self):
        choices = self.choices()
        page = self.page()
        try:
            page.choosing(lambda _: choices.add_intro_part())(None)
        except ValueError as problem:
            page.refuse(str(problem))
            return
        page.say(messages.MSG_WIZARD_PART_ADDED.format(number=len(choices.intro_parts())))

    def remove_part(self, number):
        choices = self.choices()
        page = self.page()
        place = self.place_of(number)

        def removed(_=None):
            try:
                page.choosing(choices.remove_intro_part)(place)
            except ValueError as problem:
                page.refuse(str(problem))
                return
            page.marked_part = None
            page.say(messages.MSG_WIZARD_PART_REMOVED.format(number=number))
        page.ask(dialog=ConfirmDialog(title=messages.MSG_WIZARD_REMOVE_PART_TITLE.format(number=number), messages=[messages.MSG_WIZARD_REMOVE_PART_SAYS.format(number=number)], starts_on_no=True, deletes=True),
                 then=removed)

    def field_keys(self):
        """Return the list's key: A adds a part. Asking for the keys also marks the part the cursor is on, which the buttons then act on."""
        page = self.page()
        self.part_marked()
        return [page.bind(page.KEYS.ADD, action=self.add_part)]

    def listens_alone(self):
        return True

    def listens(self):
        """Listen plays the melody's player alone in the marked part, or nothing where nobody says the hook there."""
        choices = self.choices()
        number = self.part_marked()
        place = self.place_of(number)
        if place is None or choices.intro_melody_player(place) is None:
            return None
        return messages.MSG_WIZARD_MELODY_OF.format(kind=messages.MSG_WIZARD_INTRO_PART_NAME.format(number=number)), place, choices.intro_melody_player(place)

    def heard_with_band(self):
        """Return what Listen With Band plays: everybody in the marked part."""
        number = self.part_marked()
        place = self.place_of(number)
        return None if place is None else (messages.MSG_WIZARD_SECTION_WITH_BAND.format(kind=messages.MSG_WIZARD_INTRO_PART_NAME.format(number=number)), place, None)

    def notes(self, width):
        """Return the line under the buttons that says which part the buttons act on and whose its notes are, or how to give the part a melody."""
        choices = self.choices()
        if not choices.is_ready():
            return []
        number = self.part_marked()
        place = self.place_of(number)
        if place is None:
            said = messages.MSG_WIZARD_NO_PARTS
        elif not choices.intro_hook_players():
            said = messages.MSG_WIZARD_NO_INTRO_MELODY
        elif choices.intro_melody_player(place) is None:
            said = messages.MSG_WIZARD_PART_NO_MELODY.format(number=number)
        else:
            said = messages.MSG_WIZARD_PART_NOTES.format(number=number, notes=messages.MSG_WIZARD_NOTES_BY_HAND if choices.intro_is_own(place=place) else messages.MSG_WIZARD_HOOK_MADE)
        return [Text(drawing.INDENT + said, style=Style.DIM)]
