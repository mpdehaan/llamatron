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
            result += [Text(NOTHING), *legend(keys=self.keys(), width=inner)]
        boxed = [Text(Box.HEAVY_TOP_LEFT + Box.HEAVY_RULE * (width - 2) + Box.HEAVY_TOP_RIGHT)]
        for line in result:
            framed = Text(Box.HEAVY_BAR + SPACE)
            framed.append_text(line)
            framed.append(SPACE * max(inner - line.cell_len, 0))
            framed.append(SPACE + Box.HEAVY_BAR)
            boxed.append(framed)
        boxed.append(Text(Box.HEAVY_BOTTOM_LEFT + Box.HEAVY_RULE * (width - 2) + Box.HEAVY_BOTTOM_RIGHT))
        self.query_one(DIALOG_VIEW_SELECTOR, Static).update(Text(LINE_BREAK).join(boxed))

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
