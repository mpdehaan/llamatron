# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Export dialog: the kinds of export by category, Ableton Live set, MIDI, WAV and PDF, answering with the kind chosen.

MIDI has several kinds, so ENTER on it opens a flyout over the dialog, a little down and to the right, listing them, where
Up and Down move, ENTER exports the one under the cursor and ESC closes the flyout. PDF answers PDF, whose page asks what to
put in the PDFs. A flyout is not a dialog: nothing opens over the Export dialog.
"""

from llamatron.exporters.exports import ExportKind
from llamatron.interface.forms import moves
from llamatron.interface.forms.dialogs import ChoiceList, ChoiceRow
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.renderers import dialogs as dialog_renderer
from llamatron.user_strings import labels

# What the dialog answers for PDF, which is no single kind of export: its page asks what to make.
PDF = 'pdf'
MIDI = 'midi_kinds'
# Each category in the order offered, as the answer or, for MIDI, the flyout it opens.
CATEGORIES = (ExportKind.ABLETON, MIDI, ExportKind.WAV, PDF)
MIDI_KINDS = (ExportKind.STEMS, ExportKind.MIDI_FILE, ExportKind.CLIP_TREE, ExportKind.GENERAL_MIDI)


class ExportDialog(ChoiceDialog):
    """The kinds of export by category, MIDI's in a flyout, answering with the kind of export chosen, or PDF."""

    KEYS = keybindings.ExportDialog

    def __init__(self, *, title):
        super().__init__(title=title, options=labels.MSG_EXPORT_CATEGORIES)
        # Whether MIDI's flyout is open, and the cursor's place in it.
        self.flyout_open = False
        self.flyout_place = 0

    def keys(self):
        if self.flyout_open:
            return [
                self.bind(self.KEYS.CLOSE_FLYOUT, action=self.close_flyout),
                self.bind(self.KEYS.MOVE, action=self.move_in_flyout, wants_key=True),
                self.bind(self.KEYS.EXPORT, action=self.export_in_flyout),
            ]
        return super().keys()

    def choose(self):
        """Answer the category under the cursor, or open MIDI's flyout on MIDI."""
        place = self.cursor.get_place()
        if place not in self.matches():
            return
        if CATEGORIES[place] == MIDI:
            self.flyout_open = True
            self.flyout_place = 0
            return
        self.dismiss(CATEGORIES[place])

    def close_flyout(self):
        self.flyout_open = False

    def move_in_flyout(self, name):
        """Move in the flyout with Up and Down, stopping at its edges."""
        self.flyout_place = moves.moved(place=self.flyout_place, name=name, count=len(MIDI_KINDS))

    def export_in_flyout(self):
        self.dismiss(MIDI_KINDS[self.flyout_place])

    def flyout_lines(self, width):
        """Return MIDI's flyout while it is open: its heading, a blank line and its kinds, the cursor's marked."""
        if not self.flyout_open:
            return None
        rows = [ChoiceRow(text=text, under_cursor=place == self.flyout_place, heading=False) for place, text in enumerate(labels.MSG_MIDI_EXPORT_CHOICES)]
        heading = dialog_renderer.choice_lines(choices=ChoiceList(typed='', rows=(ChoiceRow(text=labels.MSG_MIDI_EXPORT_HEADING, under_cursor=False, heading=True),)), width=width)
        return [*heading, *dialog_renderer.choice_lines(choices=ChoiceList(typed='', rows=tuple(rows)), width=width)]
