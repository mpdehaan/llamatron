# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The File/Global page as a presenter: the set's own settings in three tabs, its buttons, and what is said under them.

Settings holds what the file says about the set, its default follow action and its protection; Notes & Octaves the default
octaves, how octaves are numbered and the step size; Visualizers the mode Arrange shows first and the modes it hides. Under the
settings, where the set's file is and where the current song exports.
"""

import os

from llamatron.interface.forms.nodes import ChoiceField, Field, octave_moved, TextField, Toggle
from llamatron.interface.forms.tab_box import Tab, TabBox, TabColumn
from llamatron.interface.pages.visualizer_fields import hidden_visualizers_field, visualizer_field
from llamatron.model.schema import file_format
from llamatron.user_strings import labels, legends, marks, messages

# What ends the notes' first line, which is what fits on the field.
LINE_BREAK = '\n'


class FileGlobalPresenter:
    """What the File/Global page shows and does, for the set a document holds: page is what its fields ask through, buttons the
    page's own buttons, which the tracker makes since they are its actions, and edit_notes opens the Notes page."""

    __slots__ = ('_page', '_document', '_buttons', '_edit_notes')

    def __init__(self, *, page, document, buttons, edit_notes):
        self._page = page
        self._document = document
        self._buttons = buttons
        self._edit_notes = edit_notes

    def form(self):
        """Return the page's form: a tab box of its settings, each tab one column in its order, alphabetically, then the buttons."""
        return [
            TabBox(tabs=[
                Tab(label=labels.MSG_SETTINGS_TAB, columns=[TabColumn(heading=None, fields=self.settings_fields())]),
                Tab(label=labels.MSG_NOTES_AND_OCTAVES_TAB, columns=[TabColumn(heading=None, fields=self.notes_and_octaves_fields())]),
                Tab(label=labels.MSG_VISUALIZERS_TAB, columns=[TabColumn(heading=None, fields=self.visualizer_fields())]),
            ]),
            *self._buttons,
        ]

    def settings_fields(self):
        """Return the Settings tab's fields: what the file says about the set, its default follow action and its protection."""
        document = self._document
        setlist = document.get_setlist()
        # What a clip sends down in real-time playback when its scene is done, unless the clip says otherwise. No export reads it.
        follow = ChoiceField(
            page=self._page, label=labels.MSG_DEFAULT_FOLLOW_ACTION_LABEL, choices=file_format.FOLLOW_ACTION_CHOICES, current=setlist.get_default_follow_action(),
            names=[labels.MSG_FOLLOW_ACTION_NAMES[choice] for choice in file_format.FOLLOW_ACTION_CHOICES], shown=labels.MSG_FOLLOW_ACTION_NAMES[setlist.get_default_follow_action()],
            set=lambda advance: document.change_set(document.get_setlist().set_default_follow_action, advance),
        )
        # What describes the set, in the order a reader meets it, then how the set behaves.
        return [
            TextField(page=self._page, label=labels.MSG_TITLE_LABEL, current=setlist.get_title, set_text=lambda text: document.change_set(document.get_setlist().set_title, text)),
            TextField(page=self._page, label=labels.MSG_AUTHOR_LABEL, current=setlist.get_author, set_text=lambda text: document.change_set(document.get_setlist().set_author, text)),
            TextField(page=self._page, label=labels.MSG_DESCRIPTION_LABEL, current=setlist.get_description, set_text=lambda text: document.change_set(document.get_setlist().set_description, text)),
            Field(label=labels.MSG_NOTES_LABEL, value=self.notes_first_line, adjust=None, enter=self._edit_notes, enter_what=legends.What.EDIT),
            follow,
            Toggle(label=labels.MSG_PROTECTED_LABEL, on=setlist.is_protected(), set=lambda value: document.change_set(document.get_setlist().set_protected, value)),
        ]

    def visualizer_fields(self):
        """Return the Visualizers tab's fields: the mode Arrange shows first, and the modes it hides."""
        document = self._document
        current = self._document.get_setlist().get_visualizer()
        return [
            visualizer_field(page=self._page, current=current, set_name=lambda name: document.change_set(document.get_setlist().set_visualizer, name), first=marks.MSG_NONE_SHOWN),
            hidden_visualizers_field(page=self._page),
        ]

    def notes_and_octaves_fields(self):
        """Return the Notes & Octaves tab's fields: the default octaves, how octaves are numbered, and the step size."""
        document = self._document
        setlist = document.get_setlist()
        return [
            Field(label=labels.MSG_DEFAULT_DRUM_OCTAVE_LABEL, value=lambda: setlist.shown_octave(setlist.get_default_drum_octave()),
                  adjust=lambda offset: document.change_set(document.get_setlist().set_default_drum_octave, octave_moved(octave=setlist.get_default_drum_octave(), offset=offset))),
            Field(label=labels.MSG_DEFAULT_OCTAVE_LABEL, value=lambda: setlist.shown_octave(setlist.get_default_octave()),
                  adjust=lambda offset: document.change_set(document.get_setlist().set_default_octave, octave_moved(octave=setlist.get_default_octave(), offset=offset))),
            # How octaves are numbered on screen, each choice named with where middle C falls.
            ChoiceField(
                page=self._page, label=labels.MSG_OCTAVE_LABELS_LABEL, choices=file_format.OCTAVE_LABEL_CHOICES, current=setlist.get_octave_labels(),
                names=[labels.MSG_OCTAVE_LABEL_NAMES[choice] for choice in file_format.OCTAVE_LABEL_CHOICES], shown=labels.MSG_OCTAVE_LABEL_NAMES[setlist.get_octave_labels()],
                set=lambda labels: document.change_set(document.get_setlist().set_octave_labels, labels),
            ),
            ChoiceField(page=self._page, label=labels.MSG_STEP_SIZE_LABEL, choices=file_format.STEP_SIZE_CHOICES, current=str(setlist.get_step_size()), set=lambda step_size: document.change_set(document.get_setlist().set_step_size, step_size)),
        ]

    def remarks(self):
        """Return what is said under the settings: where the set's file is, and where the current song exports."""
        return [
            messages.MSG_FILE_NOTE.format(path=self._document.get_path() or marks.MSG_NOT_SAVED_YET),
            messages.MSG_EXPORTS_NOTE.format(where=self.exports_note()),
        ]

    def exports_note(self):
        """Return where the current song exports: the files beside the set's file, or a note that it has to be saved first."""
        document = self._document
        if not document.can_export():
            return marks.MSG_EXPORTS_AFTER_SAVING
        return marks.MSG_EXPORTS_BESIDE.format(prefix=os.path.join(document.export_directory(), document.export_name()))

    def notes_first_line(self):
        """Return the notes' first line, which is what fits on the field, or that there are none."""
        text = self._document.get_setlist().get_notes()
        first = text.split(LINE_BREAK)[0].strip()
        return first or marks.MSG_NONE_SHOWN
