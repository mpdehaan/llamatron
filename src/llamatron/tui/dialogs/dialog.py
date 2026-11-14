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

"""What every dialog has in common: a box in the middle of the screen, with its keys inside it."""

from rich.text import Text
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Static

from llamatron.strings.messages import MSG_DELETE_TITLE
from llamatron.tui.drawing import Box, legend, LINE_BREAK, NOTHING, SELECTOR, SPACE, Style
from llamatron.tui.key_table import pressed_key, quits_at_once, BindsKeys
from llamatron.tui import keybindings


DIALOG_ID = 'dialog'
DIALOG_VIEW_ID = 'dialog-view'
DIALOG_VIEW_SELECTOR = SELECTOR.format(id=DIALOG_VIEW_ID)
DIALOG_SELECTOR = SELECTOR.format(id=DIALOG_ID)
# The widest a dialog is, and the margin around it.
DIALOG_WIDTH = 70
DIALOG_MARGIN = 4
# How far down and to the right a flyout's box is drawn from its dialog's, so that the two read as a stack (the user's design).
FLYOUT_SHIFT = 2


class Dialog(BindsKeys, ModalScreen):
    """A box in the middle of the screen, with its keys inside it."""

    KEYS = keybindings.Dialog

    title = NOTHING
    # Whether the keys are listed under the dialog: a dialog whose one button names its key leaves the list off.
    shows_legend = True

    def compose(self):
        with Container(id=DIALOG_ID):
            yield Static(id=DIALOG_VIEW_ID)

    def on_mount(self):
        self.draw()

    def on_resize(self):
        self.draw()

    def keys(self):
        return []

    def key_table(self):
        return self.in_order(self.keys())

    def lines(self, width):
        return []

    def heading(self, width):
        """Return the dialog's top line, in red for a question about deleting, the user's design, so that it isn't answered by habit."""
        return Text(self.title, style=Style.DELETE_TITLE if self.title == MSG_DELETE_TITLE else Style.BOLD)

    def draw(self):
        if not self.is_attached or not self.query(DIALOG_VIEW_SELECTOR):
            return
        width = min(self.app.size.width - DIALOG_MARGIN, self.wanted_width())
        inner = width - DIALOG_MARGIN
        result = [self.heading(inner), Text(NOTHING)]
        result += self.lines(inner)
        if self.shows_legend:
            result += [Text(NOTHING), *self.legend_lines(inner)]
        boxed = self.boxed(lines=result, width=width)
        over = self.flyout_lines(inner)
        size = self.app.size
        across, down = 0, 0
        if over is not None:
            # The flyout's box is as tall as the dialog's, whatever it holds, or shorter by what a short console has no room for.
            closed_top = (size.height - len(boxed)) // 2
            short_of = max(closed_top + FLYOUT_SHIFT + len(boxed) - size.height, 0)
            over = [*over, *[Text(NOTHING)] * len(result)][:len(result) - short_of]
            closed = len(boxed)
            boxed = self.stacked(under=boxed, over=self.boxed(lines=over, width=width))
            # The box is centred, so a box that has grown would move the dialog back: the box, with the view inside it, is moved forward by as much, and the dialog
            # stays where it was. Moving the view alone would push its last column and line out of the box that holds it.
            across = (size.width - width) // 2 - (size.width - width - FLYOUT_SHIFT) // 2
            down = (size.height - closed) // 2 - (size.height - len(boxed)) // 2
        self.query_one(DIALOG_SELECTOR, Container).styles.offset = (across, down)
        self.query_one(DIALOG_VIEW_SELECTOR, Static).update(Text(LINE_BREAK).join(boxed))

    def wanted_width(self):
        """Return how wide the dialog is where the console has the room."""
        return DIALOG_WIDTH

    def legend_lines(self, width):
        """Return the lines listing the keys under the dialog."""
        return legend(keys=self.keys(), width=width)

    def flyout_lines(self, width):
        """Return the lines of the flyout open over this dialog, or None: a flyout is drawn as a box of the dialog's size over it, a little down and to the right."""
        return None

    def boxed(self, *, lines, width):
        """Return lines inside a heavy box of a width."""
        inner = width - DIALOG_MARGIN
        boxed = [Text(Box.HEAVY_TOP_LEFT + Box.HEAVY_RULE * (width - 2) + Box.HEAVY_TOP_RIGHT)]
        for line in lines:
            framed = Text(Box.HEAVY_BAR + SPACE)
            framed.append_text(line)
            framed.append(SPACE * max(inner - line.cell_len, 0))
            framed.append(SPACE + Box.HEAVY_BAR)
            boxed.append(framed)
        boxed.append(Text(Box.HEAVY_BOTTOM_LEFT + Box.HEAVY_RULE * (width - 2) + Box.HEAVY_BOTTOM_RIGHT))
        return boxed

    def stacked(self, *, under, over):
        """Return one box drawn over another of the same width, FLYOUT_SHIFT down and to the right, covering what lies under it."""
        result = []
        for row in range(max(len(under), len(over) + FLYOUT_SHIFT)):
            if row < FLYOUT_SHIFT:
                line = under[row].copy()
                line.append(SPACE * FLYOUT_SHIFT)
            else:
                line = under[row][:FLYOUT_SHIFT] if row < len(under) else Text(SPACE * FLYOUT_SHIFT)
                line.append_text(over[row - FLYOUT_SHIFT])
            result.append(line)
        return result

    def takes_text(self):
        """Return whether typed characters go into text in this dialog, as a prompt's value and a picker's search do, rather than acting as its keys."""
        return False

    def on_key(self, event):
        event.stop()
        event.prevent_default()
        name = pressed_key(event)
        if name is None:
            return
        if quits_at_once(name):
            self.app.exit()
            return
        table = self.keys()
        for item in table:
            if name in item.keys:
                item.press(name)
                if self.is_attached:
                    self.draw()
                return
        self.other_key(event)

    def other_key(self, event):
        pass
