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
"""The wizard's Hooks branch, under Composition: whether the song has a hook, which is made apart from the melody style, and a picture of the hook."""

from rich.text import Text

from llamatron.macro_composer import line_edits
from llamatron.macro_composer.wizard_choices import HOOK_PARTS, WizardChoices
from llamatron.strings.labels import MSG_WIZARD_GROUP_HOOK_KIND, MSG_WIZARD_GROUP_HOOK_SAID, MSG_WIZARD_GROUP_RIFF, MSG_WIZARD_NEW_RIFF_BUTTON, MSG_WIZARD_RIFF_NOTES_LABEL, MSG_WIZARD_RIFF_NOTES_TITLE, MSG_WIZARD_RIFF_PLAYED_BY_LABEL, MSG_WIZARD_RIFF_PLAYERS_JOINED, MSG_WIZARD_RIFF_SAID_LABEL, MSG_WIZARD_INTRO_HOOK_LABEL, MSG_WIZARD_NOBODY, MSG_WIZARD_HOOK_PART_LABELS, MSG_WIZARD_PICK, MSG_WIZARD_PICK_SHOWN, MSG_WIZARD_NEW_HOOK_BUTTON, MSG_WIZARD_HOOK_LABEL, MSG_WIZARD_HOOK_NOTES_LABEL, MSG_WIZARD_HOOK_NOTES_OWN, MSG_WIZARD_HOOK_NOTES_TITLE, MSG_WIZARD_HOOK_NOTES_WIZARD, MSG_WIZARD_HOOK_OFF, MSG_WIZARD_HOOK_ON, MSG_WIZARD_HOOKS_BRANCH
from llamatron.strings.legends import KeyName, MSG_TUNE_USUAL_WHAT, MSG_WIZARD_EDIT_NOTES_WHAT, MSG_WIZARD_NEW_HOOK_WHAT
from llamatron.strings.marks import MSG_WIZARD_HOOK_BAR_LINE, MSG_WIZARD_HOOK_CELL, MSG_WIZARD_HOOK_FLOOR, MSG_WIZARD_HOOK_FLOOR_BAR, MSG_WIZARD_HOOK_GAP, MSG_WIZARD_HOOK_ROW
from llamatron.strings.messages import MSG_WIZARD_LISTEN_RIFF, MSG_WIZARD_RIFF_SAID, MSG_WIZARD_HOOK_MADE, MSG_WIZARD_HOOK_OWN, MSG_WIZARD_LISTEN_HOOK
from llamatron.tui.drawing import INDENT, Style
from llamatron.tui.note_names import note_shown
from llamatron.tui.dialogs.tune_dialog import TuneDialog
from llamatron.tui.screens.shared.field import Button, ChoiceField, Field, Toggle
from llamatron.tui.screens.wizard.song_ways_branch import SongWaysBranch

# A step of the picture is two cells wide where the hook fits so, and one where it is long.
WIDE_STEP = 2
NARROW_STEP = 1
# The cells the picture leaves for a note's name and its edges.
ROOM_BESIDE = 8


def hook_notes_field(*, choices, page, label):
    """Return the field of the hook's notes, the wizard's until they are written by hand: ENTER opens the hook's line in the Tune dialog and keeps the line
    the dialog answers with as the hook's own notes, and Bksp gives the wizard's back. The Hooks panel shows it, and so does every section that says the hook."""
    own = choices.hook_is_own()

    def edit_notes():
        usual = WizardChoices.from_data(choices.to_data())
        usual.set_hook_line(None)
        dialog = TuneDialog(title=MSG_WIZARD_HOOK_NOTES_TITLE, line=choices.hook_line(), steps_in_bar=choices.hook_notes()[1], pitch_of_place=choices.pitch_of_place, usual=usual.hook_line())
        page.ask(dialog=dialog, then=page.choosing(lambda line: choices.set_hook_line(None if line == line_edits.tidied(usual.hook_line()) else line)))
    return Field(label=label, value=lambda: MSG_WIZARD_HOOK_NOTES_OWN if own else MSG_WIZARD_HOOK_NOTES_WIZARD, enter=edit_notes, enter_what=MSG_WIZARD_EDIT_NOTES_WHAT,
                 clear=(lambda: page.choosing(lambda nothing: choices.set_hook_line(None))(None)) if own else None, clear_what=MSG_TUNE_USUAL_WHAT)


class HooksBranch(SongWaysBranch):
    """The Hook switch, shown where a hook changes the song, and under it a picture of the hook's notes; the hook's kind,
    its variations, listening and editing are to come."""

    __slots__ = ()

    def name(self):
        return MSG_WIZARD_HOOKS_BRANCH

    def traits(self):
        return []

    def offers_a_hook(self):
        return self.choices().is_ready() and self.choices().can_have_hook()

    def summary(self):
        if not self.offers_a_hook():
            return None
        return MSG_WIZARD_HOOK_ON if self.choices().has_hook() else MSG_WIZARD_HOOK_OFF

    def fields(self):
        # The buttons come last, as a page draws them, so that the cursor walks the fields in the order they show.
        fields = [*self.hook_fields(), *self.riff_fields()]
        return [field for field in fields if not isinstance(field, Button)] + [field for field in fields if isinstance(field, Button)]

    def grouped(self, *, label, fields, is_set):
        """Return a group of the panel's fields under a heading that opens and closes, or nothing for a group with no fields."""
        return [self.page().heading(label=label, is_set=is_set), *fields] if fields else []

    def riff_fields(self):
        """Return the group of the song's riff, its second hook: who plays it, nobody until chosen, and then where it is played, its notes and another take."""
        choices = self.choices()
        page = self.page()
        offered = choices.riff_players_offered()
        if not offered:
            return []

        def refusing(setter):
            def set_way(value):
                try:
                    page.choosing(setter)(value)
                except ValueError as problem:
                    page.refuse(str(problem))
            return set_way
        titles = {MSG_WIZARD_RIFF_PLAYERS_JOINED.join(choices.role_title(role) for role in players): players for players in offered}
        now = next((title for title, players in titles.items() if players == choices.get_riff_players()), MSG_WIZARD_NOBODY)
        fields = [ChoiceField(page=page, label=MSG_WIZARD_RIFF_PLAYED_BY_LABEL, choices=[MSG_WIZARD_NOBODY, *titles], current=now, set=refusing(lambda title: choices.set_riff(players=titles.get(title))))]
        if choices.has_riff():
            own = choices.riff_is_own()

            def edit_notes():
                usual = WizardChoices.from_data(choices.to_data())
                usual.set_riff_line(None)
                dialog = TuneDialog(title=MSG_WIZARD_RIFF_NOTES_TITLE, line=choices.riff_line(), steps_in_bar=choices.riff_steps_in_bar(), pitch_of_place=choices.riff_pitch_of_place, usual=usual.riff_line())
                page.ask(dialog=dialog, then=refusing(lambda line: choices.set_riff_line(None if line == line_edits.tidied(usual.riff_line()) else line)))
            fields += [ChoiceField(page=page, label=MSG_WIZARD_RIFF_SAID_LABEL, choices=choices.riff_said_offered(), current=choices.get_riff_said(),
                                   set=refusing(lambda said: choices.set_riff(players=choices.get_riff_players(), said=said))),
                       Field(label=MSG_WIZARD_RIFF_NOTES_LABEL, value=lambda: MSG_WIZARD_HOOK_NOTES_OWN if own else MSG_WIZARD_HOOK_NOTES_WIZARD, enter=edit_notes, enter_what=MSG_WIZARD_EDIT_NOTES_WHAT,
                             clear=(lambda: refusing(lambda nothing: choices.set_riff_line(None))(None)) if own else None, clear_what=MSG_TUNE_USUAL_WHAT),
                       Button(label=MSG_WIZARD_NEW_RIFF_BUTTON, key_name=KeyName.ENTER, enter=lambda: page.choosing(lambda nothing: choices.new_riff())(None), enter_what=MSG_WIZARD_NEW_HOOK_WHAT)]
        return self.grouped(label=MSG_WIZARD_GROUP_RIFF, fields=fields, is_set=choices.has_riff)

    def hook_fields(self):
        if not self.offers_a_hook():
            return []
        choices = self.choices()
        switch = Toggle(label=MSG_WIZARD_HOOK_LABEL, on=choices.has_hook(), set=self.page().choosing(choices.set_hook))
        if not choices.has_hook():
            return [switch]
        # Another hook is made and every other line of the song is left as it was.
        new_hook = Button(label=MSG_WIZARD_NEW_HOOK_BUTTON, key_name=KeyName.ENTER, enter=lambda: self.page().choosing(lambda nothing: choices.new_hook())(None), enter_what=MSG_WIZARD_NEW_HOOK_WHAT)
        # In a planned song the hook is of a kind, each part the wizard's pick until a person chooses it.
        kind = [self.part_field(part) for part in choices.hook_parts()] if choices.has_song_plan() else []
        said = self.grouped(label=MSG_WIZARD_GROUP_HOOK_SAID, fields=self.intro_hook_fields(), is_set=lambda: choices.get_intro_hook() is not None)
        kinds = self.grouped(label=MSG_WIZARD_GROUP_HOOK_KIND, fields=kind, is_set=lambda: any(choices.hook_part_is_chosen(part) for part in choices.hook_parts()))
        if choices.hook_line() is None:
            return [switch, *kinds, *said, new_hook]
        # The hook's notes are the wizard's until they are written by hand; then the notes are the hook, whatever its kind was, until Bksp gives them back.
        own = choices.hook_is_own()
        notes = hook_notes_field(choices=choices, page=self.page(), label=MSG_WIZARD_HOOK_NOTES_LABEL)
        return [switch, notes, *([] if own else kinds), *said, *([] if own else [new_hook])]

    def intro_hook_fields(self):
        """Return the field of who says the hook in the intro, before anybody sings it, where somebody can."""
        choices = self.choices()
        players = choices.intro_hook_players()
        if not players:
            return []
        titles = {choices.role_title(role): role for role in players}
        now = choices.get_intro_hook()
        return [ChoiceField(page=self.page(), label=MSG_WIZARD_INTRO_HOOK_LABEL, choices=[MSG_WIZARD_NOBODY, *titles], current=MSG_WIZARD_NOBODY if now is None else choices.role_title(now),
                            set=self.page().choosing(lambda title: choices.set_intro_hook(titles.get(title))))]

    def part_field(self, part):
        """Return the field of one part of the hook's kind, its contour, its rhythm or its odd detail: the wizard's pick, said to be so, or the one
        chosen from the list, whose first entry gives the part back to the wizard."""
        choices = self.choices()
        now = choices.hook_kind()[part]
        chosen = choices.hook_part_is_chosen(part)
        return ChoiceField(page=self.page(), label=MSG_WIZARD_HOOK_PART_LABELS[part], choices=[MSG_WIZARD_PICK, *HOOK_PARTS[part]], current=now if chosen else MSG_WIZARD_PICK,
                           shown=now if chosen else MSG_WIZARD_PICK_SHOWN.format(value=now),
                           set=self.page().choosing(lambda value: choices.set_hook_part(part=part, value=None if value == MSG_WIZARD_PICK else value)))

    def listens(self):
        choices = self.choices()
        if not self.offers_a_hook() or not choices.has_hook() or choices.hook_scene() is None or choices.tune_player() is None:
            # With no hook to hear, the riff is heard where the song has one: the first section that plays it, its first player alone.
            if choices.riff_scene() is None:
                return None
            return MSG_WIZARD_LISTEN_RIFF, choices.riff_scene(), choices.get_riff_players()[0]
        return MSG_WIZARD_LISTEN_HOOK, choices.hook_scene(), choices.tune_player()

    def notes(self, width):
        """Return the picture of the hook while the song has one, with who plays it; else what a branch with nothing to choose says."""
        if not self.offers_a_hook() and not self.choices().riff_players_offered():
            return super().notes(width)
        choices = self.choices()
        hook = choices.hook_notes()
        lines = []
        if hook is not None:
            made = (MSG_WIZARD_HOOK_OWN if choices.hook_is_own() else MSG_WIZARD_HOOK_MADE).format(player=choices.role_title(choices.tune_player()))
            lines += [Text(), *(Text(INDENT + line) for line in picture_of(hook=hook, width=width)), Text(INDENT + made, style=Style.DIM)]
        riff = choices.riff_notes()
        if riff is not None:
            # The riff's picture under the hook's, with who plays it.
            said = MSG_WIZARD_RIFF_SAID.format(players=MSG_WIZARD_RIFF_PLAYERS_JOINED.join(choices.role_title(role) for role in choices.get_riff_players()))
            lines += [Text(), *(Text(INDENT + line) for line in picture_of(hook=riff, width=width)), Text(INDENT + said, style=Style.DIM)]
        return lines


def picture_of(*, hook, width):
    """Return the lines of a hook's picture: a row for each note it plays, the highest first, each note drawn as long as it
    lasts with a gap at its end so that a note played twice shows as two, a line between bars, and a floor under the rows."""
    steps, steps_in_bar, notes = hook
    step = WIDE_STEP if steps * WIDE_STEP + ROOM_BESIDE <= width else NARROW_STEP
    pitches = sorted({pitch for _, _, pitch in notes}, reverse=True)
    names = {pitch: note_shown(pitch) for pitch in pitches}
    longest = max(len(name) for name in names.values())
    lines = [MSG_WIZARD_HOOK_ROW.format(name=names[pitch], width=longest, cells=row_cells(notes=notes, pitch=pitch, steps=steps, steps_in_bar=steps_in_bar, step=step)) for pitch in pitches]
    floor = MSG_WIZARD_HOOK_FLOOR_BAR.join([MSG_WIZARD_HOOK_FLOOR * (steps_in_bar * step)] * (steps // steps_in_bar))
    return [*lines, MSG_WIZARD_HOOK_ROW.format(name=MSG_WIZARD_HOOK_GAP, width=longest, cells=MSG_WIZARD_HOOK_FLOOR_BAR + floor + MSG_WIZARD_HOOK_FLOOR_BAR)]


def row_cells(*, notes, pitch, steps, steps_in_bar, step):
    """Return one note's row of the picture: its cells filled where the hook plays the note, between bar lines."""
    cells = [MSG_WIZARD_HOOK_GAP] * (steps * step)
    for start, length, played in notes:
        if played == pitch:
            # The last cell of a note stays empty where the note has more than one, so that the next note stands apart.
            filled = max(length * step - 1, 1)
            cells[start * step:start * step + filled] = [MSG_WIZARD_HOOK_CELL] * filled
    bars = [''.join(cells[bar * steps_in_bar * step:(bar + 1) * steps_in_bar * step]) for bar in range(steps // steps_in_bar)]
    return MSG_WIZARD_HOOK_BAR_LINE + MSG_WIZARD_HOOK_BAR_LINE.join(bars) + MSG_WIZARD_HOOK_BAR_LINE
