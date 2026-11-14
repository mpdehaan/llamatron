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
"""Importing a MIDI file from the main screen: the file picker in the home directory, the import dialog, and the song added, the user's design of 2026-11-10.

M on the main screen, or Enter on its Import cell, opens the Open page showing MIDI files,
starting in the home directory, since a MIDI file may be anywhere on the computer. Enter on a
file reads it and asks with the import dialog; Import adds the song to the set as one edit, makes
it current, goes back to the main screen, and says what it made and every warning in a dialog
with one OK button. A file that can't be read is
told in a dialog, and the picker stays.
"""

import os

from llamatron.importers.midi_import import MidiImport
from llamatron.strings.errors import ERR_CANT_IMPORT_TITLE, ERR_CANT_READ_MIDI
from llamatron.strings.importing import MSG_IMPORTED
from llamatron.strings.labels import Crumb
from llamatron.tui.dialogs.import_dialog import ImportDialog
from llamatron.tui.dialogs.imported_dialog import ImportedDialog
from llamatron.tui.screens.open_page import OpenPage
from llamatron.tui.screens.shared import MIDI_SUFFIXES

# What reading a MIDI file can raise: mido raises these for a file that isn't MIDI or stops short, and the import its own
# MidiImportProblem, a ValueError, for one with no notes.
UNREADABLE = (OSError, ValueError, EOFError, KeyError, IndexError)


def home_folder():
    """Return the directory the import's picker starts in: the home directory."""
    return os.path.expanduser('~')


def import_midi(page):
    """Show the file picker for a MIDI file to import, over the page."""
    picker = OpenPage(holder=page.holder, then=None, suffixes=MIDI_SUFFIXES, folder=home_folder(), crumbs=(Crumb.IMPORT_MIDI,))
    picker.chosen = lambda path: offer_import(page=picker, path=path)
    page.show_page(picker)


def offer_import(*, page, path):
    """Read a MIDI file and ask how to import it, or say why it can't be read."""
    name = os.path.basename(path)
    try:
        midi_import = MidiImport.from_path(path)
    except UNREADABLE as problem:
        page.tell(ERR_CANT_IMPORT_TITLE, ERR_CANT_READ_MIDI.format(file=name, problem=problem))
        return
    dialog = ImportDialog(midi_import=midi_import, setlist=page.document().setlist(), song_name=os.path.splitext(name)[0])
    page.ask(dialog=dialog, then=lambda imported: finish_import(page=page, imported=imported))


def finish_import(*, page, imported):
    """Add what the import made to the set, make the song current, go back to the main screen, and say what was made and what had to change, on the status line and in a dialog with one OK button."""
    page.document().import_song(imported.song)
    page.go_back()
    page.say(MSG_IMPORTED.format(name=imported.song.name, tracks=imported.tracks, patterns=imported.patterns, scenes=imported.scenes))
    page.app.push_screen(ImportedDialog(imported))
