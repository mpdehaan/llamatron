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
"""The File page: the set's own settings, its description, and starting a new file or saving under a new name."""

import os

from rich.text import Text

from llamatron.composition.file_format import FOLLOW_ACTION_CHOICES, OCTAVE_LABEL_CHOICES, STEP_SIZE_CHOICES
from llamatron.tui.document import Document
from llamatron.tui.drawing import LINE_BREAK, Style
from llamatron.strings.help import HELP_FILE_PAGE
from llamatron.tui.screens.notes_page import NotesPage
from llamatron.tui.screens.everywhere import open_set, save, save_as, unless_unsaved
from llamatron.tui.screens.field import ChoiceField, Field, Toggle
from llamatron.tui.screens.field_page import FieldPage
from llamatron.tui.screens.shared import octave_moved
from llamatron.tui.screens.visualizer_fields import hidden_visualizers_field, visualizer_field
from llamatron.strings.labels import MSG_NOTES_AND_OCTAVES_SECTION, MSG_VISUALIZERS_SECTION
from llamatron.strings.labels import (
    Crumb, MSG_AUTHOR_LABEL, MSG_FOLLOW_ACTION_NAMES, MSG_DEFAULT_FOLLOW_ACTION_LABEL, MSG_DEFAULT_DRUM_OCTAVE_LABEL, MSG_NOTES_LABEL, MSG_DEFAULT_OCTAVE_LABEL, MSG_DESCRIPTION_LABEL, MSG_OCTAVE_LABEL_NAMES,
    MSG_OCTAVE_LABELS_LABEL, MSG_PROTECTED_LABEL, MSG_STEP_SIZE_LABEL, MSG_TITLE_LABEL, PageName,
)
from llamatron.strings.legends import What
from llamatron.strings.marks import MSG_NONE_SHOWN, MSG_EXPORTS_AFTER_SAVING, MSG_EXPORTS_BESIDE, MSG_NOT_SAVED_YET, MSG_NOT_SET
from llamatron.strings.messages import MSG_EXPORTS_NOTE, MSG_FILE_NOTE, MSG_STARTED_NEW
from llamatron.tui import themes
from llamatron.tui import keybindings


class FilePage(FieldPage):
    """The set's title, author, description, notes and pattern settings, with its path and where it exports noted below."""

    THEME = themes.SET_FILE

    KEYS = keybindings.FilePage

    crumbs = (Crumb.FILE,)
    HELP = HELP_FILE_PAGE

    def duration(self):
        return False

    def setlist(self):
        return self.document().setlist()

    def fields(self):
        document = self.document()
        setlist = self.setlist()
        follow = ChoiceField(
            page=self, label=MSG_DEFAULT_FOLLOW_ACTION_LABEL, choices=FOLLOW_ACTION_CHOICES, current=setlist.get_default_follow_action(),
            names=[MSG_FOLLOW_ACTION_NAMES[choice] for choice in FOLLOW_ACTION_CHOICES], shown=MSG_FOLLOW_ACTION_NAMES[setlist.get_default_follow_action()],
            set=document.set_default_follow_action,
        )
        # The settings in the order the user chose: the loose ones alphabetically, then the sections, each alphabetical inside.
        return [
            self.text_field(label=MSG_AUTHOR_LABEL, current=setlist.get_author, set_text=document.set_author),
            # What a clip sends down in real-time playback when its scene is done, unless the clip says otherwise. No export reads it.
            follow,
            self.text_field(label=MSG_DESCRIPTION_LABEL, current=setlist.get_description, set_text=document.set_description),
            Field(label=MSG_NOTES_LABEL, value=self.notes_first_line, adjust=None, enter=self.edit_notes, enter_what=What.EDIT),
            Toggle(label=MSG_PROTECTED_LABEL, on=setlist.is_protected(), set=document.set_protected),
            self.text_field(label=MSG_TITLE_LABEL, current=setlist.get_title, set_text=document.set_title),
            self.heading(label=MSG_NOTES_AND_OCTAVES_SECTION, is_set=lambda: False),
            Field(label=MSG_DEFAULT_DRUM_OCTAVE_LABEL, value=lambda: setlist.shown_octave(setlist.get_default_drum_octave()),
                  adjust=lambda offset: document.set_default_drum_octave(octave_moved(octave=setlist.get_default_drum_octave(), offset=offset))),
            Field(label=MSG_DEFAULT_OCTAVE_LABEL, value=lambda: setlist.shown_octave(setlist.get_default_octave()),
                  adjust=lambda offset: document.set_default_octave(octave_moved(octave=setlist.get_default_octave(), offset=offset))),
            # How octaves are numbered on screen, each choice named with where middle C falls.
            ChoiceField(
                page=self, label=MSG_OCTAVE_LABELS_LABEL, choices=OCTAVE_LABEL_CHOICES, current=setlist.get_octave_labels(),
                names=[MSG_OCTAVE_LABEL_NAMES[choice] for choice in OCTAVE_LABEL_CHOICES], shown=MSG_OCTAVE_LABEL_NAMES[setlist.get_octave_labels()],
                set=document.set_octave_labels,
            ),
            ChoiceField(page=self, label=MSG_STEP_SIZE_LABEL, choices=STEP_SIZE_CHOICES, current=str(setlist.get_step_size()), set=document.set_default_step_size),
            self.heading(label=MSG_VISUALIZERS_SECTION, is_set=lambda: setlist.get_visualizer() is not None or bool(setlist.get_hidden_visualizers())),
            visualizer_field(page=self, current=setlist.get_visualizer(), set_name=document.set_visualizer, first=MSG_NONE_SHOWN),
            hidden_visualizers_field(page=self),
            self.button(binding=self.KEYS.SAVE, label=PageName.SAVE, action=lambda: save(self)),
            self.button(binding=self.KEYS.OPEN_SET, label=PageName.OPEN, action=lambda: open_set(self)),
        ]

    def notes(self, width):
        return [
            Text(MSG_FILE_NOTE.format(path=self.document().get_path() or MSG_NOT_SAVED_YET), style=Style.DIM),
            Text(MSG_EXPORTS_NOTE.format(where=self.exports_note()), style=Style.DIM),
        ]

    def exports_note(self):
        """Return where the current song exports: the files beside the set's file, or a note that it has to be saved first."""
        document = self.document()
        if not document.can_export():
            return MSG_EXPORTS_AFTER_SAVING
        return MSG_EXPORTS_BESIDE.format(prefix=os.path.join(document.export_directory(), document.export_name()))

    def notes_first_line(self):
        """Return the notes' first line, which is what fits on the field, or that there are none."""
        text = self.setlist().get_notes()
        return text.split(LINE_BREAK)[0].strip() or MSG_NOT_SET if text else MSG_NOT_SET

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
        self.say(MSG_STARTED_NEW)

