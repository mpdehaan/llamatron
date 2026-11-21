# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The fields that choose visualizer modes: the mode Arrange's visualizer key shows first, on the File/Global page and the Song page, the song's over the set's, and the File/Global page's Hide Visualizers section."""

from llamatron.composition import file_format
from llamatron.tui.dialogs.pick_many_dialog import PickManyDialog
from llamatron.tui.screens.shared.field import ChoiceField, Field
from llamatron.user_strings import labels, legends, marks
from llamatron.visualizers.modes import mode_called


def visualizer_field(*, page, current, set_name, first):
    """Return the field that chooses the mode shown first: first, the words for none of its own, then every mode by its name on screen."""
    choices = [first, *file_format.VISUALIZER_NAMES]
    names = [first, *[mode_called(name).NAME for name in file_format.VISUALIZER_NAMES]]
    shown = first if current is None else mode_called(current).NAME
    return ChoiceField(
        page=page, label=labels.MSG_VISUALIZER_LABEL, choices=choices, current=current or first, names=names, shown=shown,
        set=lambda choice: set_name(None if choice == first else choice),
    )


def hidden_visualizers_field(*, page):
    """Return the field of the modes left out of the visualizer key: their names, or (none), and Enter opening a list where each
    can be picked: one field rather than a section of toggles."""
    setlist = page.document().get_setlist()

    def shown():
        hidden = setlist.get_hidden_visualizers()
        return marks.MSG_DETAILS_LIST_SEPARATOR.join(mode_called(name).NAME for name in hidden) if hidden else marks.MSG_NONE_SHOWN

    def pick():
        def chosen(names):
            for name in file_format.VISUALIZER_NAMES:
                page.document().change(page.document().get_setlist().set_visualizer_hidden, name=name, hidden=name in names)
        dialog = PickManyDialog(title=labels.MSG_HIDE_VISUALIZERS_LABEL, options=list(file_format.VISUALIZER_NAMES), names=[mode_called(name).NAME for name in file_format.VISUALIZER_NAMES],
                                picked=setlist.get_hidden_visualizers())
        page.ask(dialog=dialog, then=chosen)
    return Field(label=labels.MSG_HIDE_VISUALIZERS_LABEL, value=shown, enter=pick, enter_what=legends.What.CHOOSE)
