# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The File page: the set's own settings, its description, and starting a new file or saving under a new name."""

import os
from rich.text import Text

from llamatron.composition import file_format
from llamatron.strings import help as help_text, labels, legends, marks, messages
from llamatron.tui import drawing, keybindings, themes
from llamatron.tui.document import Document
from llamatron.tui.drawing import Style
from llamatron.tui.screens.set.notes_page import NotesPage
from llamatron.tui.screens.set.visualizer_fields import hidden_visualizers_field, visualizer_field
from llamatron.tui.screens.shared.everywhere import open_set, save, save_as, unless_unsaved
from llamatron.tui.screens.shared.field import ChoiceField, Field, Toggle
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.shared import octave_moved


class FilePage(FieldPage):
    """The set's title, author, description, notes and pattern settings, with its path and where it exports noted below."""

    THEME = themes.SET_FILE

    KEYS = keybindings.FilePage

    crumbs = (labels.Crumb.FILE,)
    HELP = help_text.HELP_FILE_PAGE

    def duration(self):
        return False

    def get_setlist(self):
        return self.document().get_setlist()

    def fields(self):
        document = self.document()
        setlist = self.get_setlist()
        follow = ChoiceField(
            page=self, label=labels.MSG_DEFAULT_FOLLOW_ACTION_LABEL, choices=file_format.FOLLOW_ACTION_CHOICES, current=setlist.get_default_follow_action(),
            names=[labels.MSG_FOLLOW_ACTION_NAMES[choice] for choice in file_format.FOLLOW_ACTION_CHOICES], shown=labels.MSG_FOLLOW_ACTION_NAMES[setlist.get_default_follow_action()],
            set=lambda advance: document.change(document.get_setlist().set_default_follow_action, advance),
        )
        # The settings in their order: the loose ones alphabetically, then the sections, each alphabetical inside.
        return [
            self.text_field(label=labels.MSG_AUTHOR_LABEL, current=setlist.get_author, set_text=lambda text: document.change(document.get_setlist().set_author, text)),
            # What a clip sends down in real-time playback when its scene is done, unless the clip says otherwise. No export reads it.
            follow,
            self.text_field(label=labels.MSG_DESCRIPTION_LABEL, current=setlist.get_description, set_text=lambda text: document.change(document.get_setlist().set_description, text)),
            Field(label=labels.MSG_NOTES_LABEL, value=self.notes_first_line, adjust=None, enter=self.edit_notes, enter_what=legends.What.EDIT),
            Toggle(label=labels.MSG_PROTECTED_LABEL, on=setlist.is_protected(), set=lambda value: document.change(document.get_setlist().set_protected, value)),
            self.text_field(label=labels.MSG_TITLE_LABEL, current=setlist.get_title, set_text=lambda text: document.change(document.get_setlist().set_title, text)),
            self.heading(label=labels.MSG_NOTES_AND_OCTAVES_SECTION, is_set=lambda: False),
            Field(label=labels.MSG_DEFAULT_DRUM_OCTAVE_LABEL, value=lambda: setlist.shown_octave(setlist.get_default_drum_octave()),
                  adjust=lambda offset: document.change(document.get_setlist().set_default_drum_octave, octave_moved(octave=setlist.get_default_drum_octave(), offset=offset))),
            Field(label=labels.MSG_DEFAULT_OCTAVE_LABEL, value=lambda: setlist.shown_octave(setlist.get_default_octave()),
                  adjust=lambda offset: document.change(document.get_setlist().set_default_octave, octave_moved(octave=setlist.get_default_octave(), offset=offset))),
            # How octaves are numbered on screen, each choice named with where middle C falls.
            ChoiceField(
                page=self, label=labels.MSG_OCTAVE_LABELS_LABEL, choices=file_format.OCTAVE_LABEL_CHOICES, current=setlist.get_octave_labels(),
                names=[labels.MSG_OCTAVE_LABEL_NAMES[choice] for choice in file_format.OCTAVE_LABEL_CHOICES], shown=labels.MSG_OCTAVE_LABEL_NAMES[setlist.get_octave_labels()],
                set=lambda labels: document.change(document.get_setlist().set_octave_labels, labels),
            ),
            ChoiceField(page=self, label=labels.MSG_STEP_SIZE_LABEL, choices=file_format.STEP_SIZE_CHOICES, current=str(setlist.get_step_size()), set=lambda step_size: document.change(document.get_setlist().set_step_size, step_size)),
            self.heading(label=labels.MSG_VISUALIZERS_SECTION, is_set=lambda: setlist.get_visualizer() is not None or bool(setlist.get_hidden_visualizers())),
            visualizer_field(page=self, current=setlist.get_visualizer(), set_name=lambda name: document.change(document.get_setlist().set_visualizer, name), first=marks.MSG_NONE_SHOWN),
            hidden_visualizers_field(page=self),
            self.button(binding=self.KEYS.SAVE, label=labels.PageName.SAVE, action=lambda: save(self)),
            self.button(binding=self.KEYS.OPEN_SET, label=labels.PageName.OPEN, action=lambda: open_set(self)),
        ]

    def remarks(self, width):
        return [
            Text(messages.MSG_FILE_NOTE.format(path=self.document().get_path() or marks.MSG_NOT_SAVED_YET), style=Style.DIM),
            Text(messages.MSG_EXPORTS_NOTE.format(where=self.exports_note()), style=Style.DIM),
        ]

    def exports_note(self):
        """Return where the current song exports: the files beside the set's file, or a note that it has to be saved first."""
        document = self.document()
        if not document.can_export():
            return marks.MSG_EXPORTS_AFTER_SAVING
        return marks.MSG_EXPORTS_BESIDE.format(prefix=os.path.join(document.export_directory(), document.export_name()))

    def notes_first_line(self):
        """Return the notes' first line, which is what fits on the field, or that there are none."""
        text = self.get_setlist().get_notes()
        return text.split(drawing.LINE_BREAK)[0].strip() or marks.MSG_NOT_SET if text else marks.MSG_NOT_SET

    def edit_notes(self):
        """Open the Notes page editing, so that Enter on the field starts typing and Tab comes back; a protected set's opens for reading."""
        self.show_page(NotesPage(self.holder, editing=True))

    def page_keys(self):
        return [
            self.bind(self.KEYS.NEW, action=self.new),
            self.bind(self.KEYS.SAVE_AS, action=lambda: save_as(self)),
        ]

    def new(self):
        unless_unsaved(self, then=self.start_new)

    def start_new(self):
        self.holder.set_document(Document())
        self.say(messages.MSG_STARTED_NEW)

