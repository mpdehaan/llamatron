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

from llamatron.macro_composer.wizard_choices import HOOK_PARTS
from llamatron.strings.labels import MSG_WIZARD_INTRO_HOOK_LABEL, MSG_WIZARD_NOBODY, MSG_WIZARD_HOOK_PART_LABELS, MSG_WIZARD_PICK, MSG_WIZARD_PICK_SHOWN, MSG_WIZARD_NEW_HOOK_BUTTON, MSG_WIZARD_HOOK_LABEL, MSG_WIZARD_HOOK_OFF, MSG_WIZARD_HOOK_ON, MSG_WIZARD_HOOKS_BRANCH
from llamatron.strings.legends import KeyName, MSG_WIZARD_NEW_HOOK_WHAT
from llamatron.strings.marks import MSG_WIZARD_HOOK_BAR_LINE, MSG_WIZARD_HOOK_CELL, MSG_WIZARD_HOOK_FLOOR, MSG_WIZARD_HOOK_FLOOR_BAR, MSG_WIZARD_HOOK_GAP, MSG_WIZARD_HOOK_ROW
from llamatron.strings.messages import MSG_WIZARD_HOOK_MADE, MSG_WIZARD_LISTEN_HOOK
from llamatron.tui.drawing import INDENT, Style
from llamatron.tui.note_names import note_shown
from llamatron.tui.screens.shared.field import Button, ChoiceField, Toggle
from llamatron.tui.screens.wizard.song_ways_branch import SongWaysBranch

# A step of the picture is two cells wide where the hook fits so, and one where it is long.
WIDE_STEP = 2
NARROW_STEP = 1
# The cells the picture leaves for a note's name and its edges.
ROOM_BESIDE = 8


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
        return [switch, *kind, *self.intro_hook_fields(), new_hook]

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
            return None
        return MSG_WIZARD_LISTEN_HOOK, choices.hook_scene(), choices.tune_player()

    def notes(self, width):
        """Return the picture of the hook while the song has one, with who plays it; else what a branch with nothing to choose says."""
        if not self.offers_a_hook():
            return super().notes(width)
        hook = self.choices().hook_notes()
        if hook is None:
            return []
        choices = self.choices()
        made = MSG_WIZARD_HOOK_MADE.format(player=choices.role_title(choices.tune_player()))
        return [Text(), *(Text(INDENT + line) for line in picture_of(hook=hook, width=width)), Text(INDENT + made, style=Style.DIM)]


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
