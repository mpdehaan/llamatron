# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Importing a MIDI file from the main screen: the file picker in the home directory, the import dialog, and the song added.

M on the main screen, or Enter on its Import cell, opens the Open page showing MIDI files,
starting in the home directory, since a MIDI file may be anywhere on the computer. Enter on a
file reads it and asks with the import dialog; Import adds the song to the set as one edit, makes
it current, goes back to the main screen, and says what it made and every warning in a dialog
with one OK button. A file that can't be read is
told in a dialog, and the picker stays.
"""

import os

from llamatron.importers.midi_import import MidiImport
from llamatron.interface.tracker.dialogs.import_dialog import ImportDialog
from llamatron.interface.tracker.dialogs.imported_dialog import ImportedDialog
from llamatron.interface.tracker.screens.set.open_page import OpenPage
from llamatron.interface.tracker.screens.shared import shared
from llamatron.user_strings import errors, importing, labels

# What reading a MIDI file can raise: mido raises these for a file that isn't MIDI or stops short, and the import its own
# MidiImportProblem, a ValueError, for one with no notes.
UNREADABLE = (OSError, ValueError, EOFError, KeyError, IndexError)


def home_folder():
    """Return the directory the import's picker starts in: the home directory."""
    return os.path.expanduser('~')


def import_midi(page):
    """Show the file picker for a MIDI file to import, over the page."""
    picker = OpenPage(holder=page.holder, then=None, suffixes=shared.MIDI_SUFFIXES, folder=home_folder(), crumbs=(labels.Crumb.IMPORT_MIDI,))
    picker.chosen = lambda path: offer_import(page=picker, path=path)
    page.show_page(picker)


def offer_import(*, page, path):
    """Read a MIDI file and ask how to import it, or say why it can't be read."""
    name = os.path.basename(path)
    try:
        midi_import = MidiImport.from_path(path)
    except UNREADABLE as problem:
        page.tell(errors.ERR_CANT_IMPORT_TITLE, errors.ERR_CANT_READ_MIDI.format(file=name, problem=problem))
        return
    dialog = ImportDialog(midi_import=midi_import, setlist=page.document().get_setlist(), song_name=os.path.splitext(name)[0])
    page.ask(dialog=dialog, then=lambda imported: finish_import(page=page, imported=imported))


def finish_import(*, page, imported):
    """Add what the import made to the set, make the song current, go back to the main screen, and say what was made and what had to change, on the status line and in a dialog with one OK button."""
    page.document().import_song(imported.song)
    page.go_back()
    page.say(importing.MSG_IMPORTED.format(name=imported.song.name, tracks=imported.tracks, patterns=imported.patterns, scenes=imported.scenes))
    page.app.push_screen(ImportedDialog(imported))
