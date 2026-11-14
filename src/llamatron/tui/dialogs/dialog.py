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
        width = min(self.app.size.width - DIALOG_MARGIN, DIALOG_WIDTH)
        inner = width - DIALOG_MARGIN
        result = [self.heading(inner), Text(NOTHING)]
        result += self.lines(inner)
        if self.shows_legend:
            result += [Text(NOTHING), *legend(keys=self.legend_keys(), width=inner)]
        boxed = self.boxed(lines=result, width=width)
        over = self.flyout_lines(inner)
        view = self.query_one(DIALOG_VIEW_SELECTOR, Static)
        if over is not None:
            # The flyout's box is as tall as the dialog's, whatever it holds.
            over = [*over, *[Text(NOTHING)] * len(result)][:len(result)]
            boxed = self.stacked(under=boxed, over=self.boxed(lines=over, width=width), width=width)
        # The view is centred, so a view grown by the shift would move the dialog back half of it: the view is moved forward by as much, and the dialog stays where it was.
        shift = FLYOUT_SHIFT // 2 if over is not None else 0
        view.styles.offset = (shift, shift)
        view.update(Text(LINE_BREAK).join(boxed))

    def legend_keys(self):
        """Return the keys listed under the dialog, which are its keys unless a flyout has taken them."""
        return self.keys()

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

    def stacked(self, *, under, over, width):
        """Return one box drawn over another of the same size, FLYOUT_SHIFT down and to the right, covering what lies under it."""
        result = []
        for row in range(len(under) + FLYOUT_SHIFT):
            line = under[row][:FLYOUT_SHIFT] if row < len(under) else Text(SPACE * FLYOUT_SHIFT)
            if row < FLYOUT_SHIFT:
                line = under[row].copy()
                line.append(SPACE * FLYOUT_SHIFT)
            else:
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
