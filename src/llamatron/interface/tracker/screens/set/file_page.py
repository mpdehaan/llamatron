# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The File page: the File/Global presenter's form (interface/pages/file_global.py) shown on a page of its own, with the
buttons and the Notes page only the tracker can give it: starting a new file, opening one, saving, saving under a new name."""

from rich.text import Text

from llamatron.interface.forms.nodes import Button
from llamatron.interface.pages.file_global import FileGlobalPresenter
from llamatron.interface.tracker import keybindings, themes
from llamatron.interface.tracker.document import Document
from llamatron.interface.tracker.drawing import Style
from llamatron.interface.tracker.screens.set.notes_page import NotesPage
from llamatron.interface.tracker.screens.shared.everywhere import open_set, save, save_as, unless_unsaved
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.user_strings import help as help_text, labels, legends, messages


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

    def presenter(self):
        """Return what the page shows, for the set as it is now."""
        return FileGlobalPresenter(page=self, document=self.document(), buttons=self.buttons(), edit_notes=self.edit_notes)

    def fields(self):
        return self.presenter().form()

    def buttons(self):
        """Return the page's buttons, in order: New, Open, Save and Save As."""
        return [
            Button(label=labels.MSG_NEW_SET_BUTTON, enter=self.new, enter_what=legends.MSG_NEW_WHAT),
            self.button(binding=self.KEYS.OPEN_SET, label=labels.PageName.OPEN, action=lambda: open_set(self)),
            self.button(binding=self.KEYS.SAVE, label=labels.PageName.SAVE, action=lambda: save(self)),
            Button(label=labels.MSG_SAVE_AS_BUTTON, enter=lambda: save_as(self), enter_what=legends.MSG_SAVE_AS_WHAT),
        ]

    def remarks(self, width):
        return [Text(line, style=Style.DIM) for line in self.presenter().remarks()]

    def edit_notes(self):
        """Open the Notes page editing, so that Enter on the field starts typing and Tab comes back; a protected set's opens for reading."""
        self.show_page(NotesPage(self.holder, editing=True))

    def new(self):
        unless_unsaved(self, then=self.start_new)

    def start_new(self):
        self.holder.set_document(Document())
        self.say(messages.MSG_STARTED_NEW)

