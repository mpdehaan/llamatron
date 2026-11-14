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
"""The fields that choose visualizer modes, the user's design: the mode Arrange's visualizer key shows first, on the Set File page and the Song page, the song's over the set's, and the Set File page's Hide Visualizers section."""

from llamatron.composition.file_format import VISUALIZER_NAMES
from llamatron.strings.labels import MSG_HIDE_VISUALIZERS_LABEL, MSG_VISUALIZER_LABEL
from llamatron.strings.legends import What
from llamatron.strings.marks import MSG_DETAILS_LIST_SEPARATOR, MSG_NONE_SHOWN
from llamatron.tui.dialogs.pick_many_dialog import PickManyDialog
from llamatron.tui.screens.field import ChoiceField, Field
from llamatron.visualizers.modes import mode_called


def visualizer_field(*, page, current, set_name, first):
    """Return the field that chooses the mode shown first: first, the words for none of its own, then every mode by its name on screen."""
    choices = [first, *VISUALIZER_NAMES]
    names = [first, *[mode_called(name).NAME for name in VISUALIZER_NAMES]]
    shown = first if current is None else mode_called(current).NAME
    return ChoiceField(
        page=page, label=MSG_VISUALIZER_LABEL, choices=choices, current=current or first, names=names, shown=shown,
        set=lambda choice: set_name(None if choice == first else choice),
    )


def hidden_visualizers_field(*, page):
    """Return the field of the modes left out of the visualizer key: their names, or (none), and Enter opening a list where each
    can be picked, the user's design of one field rather than a section of toggles."""
    setlist = page.document().setlist()

    def shown():
        hidden = setlist.get_hidden_visualizers()
        return MSG_DETAILS_LIST_SEPARATOR.join(mode_called(name).NAME for name in hidden) if hidden else MSG_NONE_SHOWN

    def pick():
        def chosen(names):
            for name in VISUALIZER_NAMES:
                page.document().set_visualizer_hidden(name=name, hidden=name in names)
        dialog = PickManyDialog(title=MSG_HIDE_VISUALIZERS_LABEL, options=list(VISUALIZER_NAMES), names=[mode_called(name).NAME for name in VISUALIZER_NAMES],
                                picked=setlist.get_hidden_visualizers())
        page.ask(dialog=dialog, then=chosen)
    return Field(label=MSG_HIDE_VISUALIZERS_LABEL, value=shown, enter=pick, enter_what=What.CHOOSE)
