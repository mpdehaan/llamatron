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
"""The song wizard's page, the user's design: a tree of the song's parts at the left, and at the right the fields of the part under the cursor.

The cursor is in the tree or in the fields. In the tree, Up and Down move, Left and Right
close and open a branch, the fields of the branch under the cursor show dim, and ENTER or Tab
moves into them. In the fields the keys are a settings page's, and ESC or Tab moves back to the
tree. ESC in the tree closes the wizard, asking first when anything was chosen. Nothing in the
set changes until the Create button, which adds the song with all it uses as one change, so
that one undo takes it away again, and shows Arrange on it.

The page knows nothing of any one branch (branch.py): it draws what the branches say.
"""

from rich.text import Text

from llamatron.composition.naming import new_name
from llamatron.macro_composer.wizard_choices import WizardChoices
from llamatron.strings.help import HELP_WIZARD_PAGE
from llamatron.strings.errors import ERR_WIZARD_CHOOSE_START
from llamatron.strings.labels import Crumb, MSG_WIZARD_CAPTION, MSG_WIZARD_REPLACE_CAPTION
from llamatron.strings.marks import MSG_WIZARD_BRANCH_CLOSED, MSG_WIZARD_BRANCH_OPEN, MSG_WIZARD_EDITED_BRANCH
from llamatron.strings.messages import MSG_WIZARD_CLOSE_QUESTION, MSG_WIZARD_CLOSE_TITLE, MSG_WIZARD_CREATED, MSG_WIZARD_NOTHING_TO_UNDO, MSG_WIZARD_REPLACED, MSG_WIZARD_SONG_NAME_PROMPT
from llamatron.strings.names import MSG_NEW_SONG_WORD
from llamatron.support.version import VERSION
from llamatron.tui import keybindings, themes
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.drawing import Box, cursor_mark, INDENT, NOTHING, SPACE, Style
from llamatron.tui.key_table import cursor_moved
from llamatron.tui.keys import Key
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.wizard.band_branch import BandBranch
from llamatron.tui.screens.wizard.create_branch import CreateBranch
from llamatron.tui.screens.wizard.form_branch import FormBranch
from llamatron.tui.screens.wizard.genre_branch import GenreBranch
from llamatron.tui.screens.wizard.start_branch import StartBranch
from llamatron.tui.screens.wizard.starts import FROM_LAST, REPLACING

# How wide the tree is, with its cursor's mark, and the least the fields beside it are given.
TREE_WIDTH = 24
LEAST_FIELDS_WIDTH = 20
# Where the fields' cursor is while the cursor is in the tree: on no field.
NO_PLACE = -1
FIRST_PLACE = 0
# The line and the space between the tree and the fields.
DIVIDER = Box.BAR + SPACE


class WizardPage(FieldPage):
    """The song wizard: a tree of branches beside the fields of the branch under the cursor."""

    THEME = themes.WIZARD

    KEYS = keybindings.WizardPage

    HELP = HELP_WIZARD_PAGE

    crumbs = (Crumb.WIZARD,)

    def __init__(self, holder):
        super().__init__(holder)
        self._choices = WizardChoices()
        self._song_name = new_name(word=MSG_NEW_SONG_WORD, taken=self.document().song_names())
        self._changed = False
        # What the current song kept of the run that made it, the way of starting chosen where one is asked for, and whether a new take is wanted.
        self._last = self.document().song().get_wizard_choices()
        self._start = None
        self._new_take = False
        self._open = set()
        self.tree_place = FIRST_PLACE
        self.in_fields = False

    # What the branches read and change.

    def choices(self):
        return self._choices

    def song_name(self):
        return self._song_name

    def choosing(self, setter):
        """Return a setter that also notes that something was chosen, so that closing the wizard asks before the choices are lost."""
        def chosen(value):
            setter(value)
            self._changed = True
        return chosen

    def ask_song_name(self):
        self.ask_name(title=MSG_WIZARD_SONG_NAME_PROMPT, value=self._song_name, taken=self.document().song_names(), then=self.choosing(self.name_song))

    def name_song(self, name):
        self._song_name = name

    # How the run starts, asked when the current song was made by the wizard.

    def asks_how_to_start(self):
        return self._last is not None

    def start(self):
        """Return the way of starting chosen, or None before one is."""
        return self._start

    def start_with(self, start):
        """Start the run one of the four ways: from the choices the current song kept or from none, a new song or the current song replaced."""
        self._start = start
        self._choices = WizardChoices.from_data(self._last) if start in FROM_LAST else WizardChoices()
        self._new_take = False
        document = self.document()
        self._song_name = document.current_song_name() if self.replaces() else new_name(word=MSG_NEW_SONG_WORD, taken=document.song_names())
        self._changed = True

    def replaces(self):
        """Return whether Create replaces the current song, where otherwise a song is added."""
        return self._start in REPLACING

    def starts_from_last(self):
        return self._start in FROM_LAST

    def wants_new_take(self):
        return self._new_take

    def want_new_take(self, wanted):
        self._new_take = wanted
        self._changed = True

    def refusal_of(self, branch):
        """Return why the cursor cannot move into a branch's fields yet, or None when it can: a way of starting comes before all else."""
        if self.asks_how_to_start() and self._start is None and branch.waits_for_start():
            return ERR_WIZARD_CHOOSE_START
        return branch.refusal()

    def has_choices_to_lose(self):
        return self._changed

    # The tree.

    def roots(self):
        """Return the tree's top branches, in the order a song is thought through."""
        start = [StartBranch(page=self)] if self.asks_how_to_start() else []
        return [*start, GenreBranch(page=self), BandBranch(page=self), FormBranch(page=self), CreateBranch(page=self)]

    def rows(self):
        """Return the branches the tree shows, each with how deep it is: every top branch, and the branches under each open one."""
        rows = []
        for root in self.roots():
            rows.append((0, root))
            if root.key() in self._open:
                rows += [(1, child) for child in root.children()]
        return rows

    def row(self):
        """Return the depth and the branch under the tree's cursor, the cursor held within the tree, which a choice can shorten."""
        rows = self.rows()
        self.tree_place = max(min(self.tree_place, len(rows) - 1), FIRST_PLACE)
        return rows[self.tree_place]

    def branch(self):
        return self.row()[1]

    def shows_children(self, branch):
        """Return whether a branch of the tree is open, showing the branches under it."""
        return branch.key() in self._open

    def move_in_tree(self, name):
        self.tree_place = cursor_moved(place=self.tree_place, name=name, count=len(self.rows()))

    def fold(self, name):
        """Open the branch under the cursor with Right and close it with Left; Left on a branch inside another goes to the branch that holds it."""
        depth, branch = self.row()
        if name == Key.RIGHT:
            if branch.children():
                self._open.add(branch.key())
            return
        if depth:
            while self.rows()[self.tree_place][0]:
                self.tree_place -= 1
            return
        self._open.discard(branch.key())

    def into_fields(self):
        """Move the cursor into the fields of the branch under it, onto the first field that does something, or say why not yet."""
        branch = self.branch()
        if self.refusal_of(branch):
            self.refuse(self.refusal_of(branch))
            return
        self.in_fields = True
        fields = self.shown_fields()
        self.place = next((place for place, field in enumerate(fields) if field.enter or field.adjust), FIRST_PLACE)

    def to_tree(self):
        self.in_fields = False

    # The fields, a settings page's, of the branch under the tree's cursor.

    def fields(self):
        return self.branch().fields()

    def notes(self, width):
        return self.branch().notes(width)

    def field(self):
        """Return the field under the cursor, or None while the cursor is in the tree."""
        return super().field() if self.in_fields else None

    def keys(self):
        if self.in_fields:
            # A settings page's keys, but for ESC, which goes back to the tree here and not from the page.
            return [self.bind(self.KEYS.TO_TREE, action=self.to_tree), *super().keys()[1:]]
        depth, branch = self.row()
        result = [self.bind(self.KEYS.CLOSE, action=self.go_back), self.bind(self.KEYS.TREE, action=self.move_in_tree, wants_key=True)]
        if depth or branch.children():
            result.append(self.bind(self.KEYS.FOLD, action=self.fold, wants_key=True))
        if self.refusal_of(branch) or branch.can_be_edited():
            result.append(self.bind(self.KEYS.INTO_FIELDS, action=self.into_fields))
        return result

    # Closing, and undo, which has nothing to act on here.

    def go_back(self):
        """Close the wizard, which loses every choice, the user's design, so it asks first when anything was chosen."""
        if not self.has_choices_to_lose():
            super().go_back()
            return

        def answered(yes):
            if yes:
                FieldPage.go_back(self)
        self.ask(dialog=ConfirmDialog(title=MSG_WIZARD_CLOSE_TITLE, messages=[MSG_WIZARD_CLOSE_QUESTION]), then=answered)

    def steps_history(self):
        return False

    def why_no_history(self):
        return MSG_WIZARD_NOTHING_TO_UNDO

    # Create.

    def create(self):
        """Make the song from the choices, add it to the set with all it uses as one change, and show Arrange on it, the user's design."""
        if not self.starts_from_last() or self._new_take:
            # A song from scratch and a new take each roll the dice afresh; a run from the last settings keeps the seed, so that what was not changed stays.
            self._choices.forget_seed()
        made = self._choices.made_setlist(name=self._song_name, version=VERSION)
        document = self.document()
        replaces = self.replaces()
        if replaces:
            name = document.replace_with_made_song(made)
        elif document.current_song_is_untouched():
            # A song nothing was done to, as a new set's, is filled in place of a song added beside it, the user's design.
            name = document.replace_with_made_song(made, new=self._song_name)
        else:
            name = document.add_made_song(made)
        self.holder.show_arrange_on_new_song()
        self.say((MSG_WIZARD_REPLACED if replaces else MSG_WIZARD_CREATED).format(name=name))

    # Drawing.

    def caption(self):
        return (MSG_WIZARD_REPLACE_CAPTION if self.replaces() else MSG_WIZARD_CAPTION).format(name=self._song_name)

    def tree_lines(self):
        """Return the tree's lines: each branch after its cursor's mark, indented by its depth, with its open or closed mark, its note dim,
        and at the line's end the mark of the branch whose fields hold the cursor."""
        lines = []
        for place, (depth, branch) in enumerate(self.rows()):
            under_cursor = place == self.tree_place
            line = Text(no_wrap=True)
            line.append(cursor_mark(under_cursor and not self.in_fields))
            line.append(INDENT * depth)
            if branch.children():
                line.append((MSG_WIZARD_BRANCH_OPEN if self.shows_children(branch) else MSG_WIZARD_BRANCH_CLOSED) + SPACE)
            else:
                line.append(INDENT)
            line.append(branch.name(), style=Style.DIM if self.refusal_of(branch) else (Style.BOLD if under_cursor else Style.PLAIN))
            if branch.note():
                line.append(SPACE + branch.note(), style=Style.DIM)
            line.truncate(TREE_WIDTH - 2)
            line.pad_right(TREE_WIDTH - 2 - len(line.plain))
            line.append((MSG_WIZARD_EDITED_BRANCH if under_cursor and self.in_fields else SPACE) + SPACE)
            lines.append(line)
        return lines

    def field_lines(self, *, width, height):
        """Return the right side's lines: the branch's title, then its fields as a settings page draws them, all dim while the cursor is in the tree."""
        place = self.place
        if not self.in_fields:
            self.place = NO_PLACE
        lines = [Text(SPACE + self.branch().title(), style=Style.BOLD), *FieldPage.body(self, width=width, height=max(height - 1, 1))]
        self.place = place
        if not self.in_fields:
            for line in lines:
                line.stylize(Style.DIM)
        return lines

    def body(self, *, width, height):
        tree = self.window_of_tree(lines=self.tree_lines(), height=height)
        fields = self.field_lines(width=max(width - TREE_WIDTH - len(DIVIDER), LEAST_FIELDS_WIDTH), height=height)
        lines = []
        for place in range(max(len(tree), len(fields), height)):
            line = Text(no_wrap=True)
            line.append_text(tree[place] if place < len(tree) else Text(SPACE * TREE_WIDTH))
            line.append(DIVIDER, style=Style.DIM)
            line.append_text(fields[place] if place < len(fields) else Text(NOTHING))
            lines.append(line)
        return lines

    def window_of_tree(self, *, lines, height):
        """Return the tree's lines that fit the height, scrolled so that the branch under the cursor shows, a long form having more sections than a console has lines."""
        if len(lines) <= height:
            return lines
        first = max(min(self.tree_place - height // 2, len(lines) - height), FIRST_PLACE)
        return lines[first:first + height]
