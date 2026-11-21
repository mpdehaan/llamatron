# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""What every page can do: save the set, open another, export the current song, undo, redo, help and about, and the main screen's quit.

These keys work on every page, and they're kept out of every page's footer so that it shows only
the page's own keys: the F1 dialog lists them all, and so does the main screen's menu. Each works
on the page it was pressed on, which shows the dialogs and the status line. The page passes
itself in. Quit is Q on the main screen alone, and lives here because it asks the same questions.
"""

import os

from llamatron.composition.song_file_error import SongFileError
from llamatron.exporters import exports
from llamatron.exporters.exports import ExportKind
from llamatron.tui.dialogs import quit_dialog
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.corrections_dialog import CorrectionsDialog
from llamatron.tui.dialogs.quit_dialog import QuitDialog
from llamatron.tui.document import Document
from llamatron.tui.screens.shared import shared
from llamatron.tui.silent_instruments import warn_of_silent_instruments
from llamatron.tui.uses import loop_error_lines
from llamatron.user_strings import errors, labels, marks, messages as messages_text

# Where Save as starts when the set has no file yet.
DEFAULT_SAVE_FOLDER = 'songs'
DEFAULT_SAVE_NAME = 'untitled.yml'
# How the quit dialog's title says there's something to lose.
UNSAVED_TITLE = '{title} ({note})'


def everywhere_actions(page):
    """Return what each key that works everywhere does on a page, by its binding."""
    if page.app.is_drafting():
        # A draft is no set of its own: it is neither saved nor exported, and nothing is opened over the set behind it.
        def refused():
            page.refuse(errors.ERR_NOT_WHILE_DRAFTING)
        return {
            page.KEYS.SAVE: refused, page.KEYS.OPEN_SET: refused, page.KEYS.EXPORT: refused, page.KEYS.WIZARD: refused,
            page.KEYS.UNDO: lambda: undo(page), page.KEYS.REDO: lambda: redo(page), page.KEYS.HELP: page.show_help, page.KEYS.ABOUT: page.show_about,
            page.KEYS.SILENCE: lambda: silence(page), page.KEYS.QUIT_NOW: page.app.exit,
        }
    return {
        page.KEYS.SAVE: lambda: save(page), page.KEYS.OPEN_SET: lambda: open_set(page), page.KEYS.EXPORT: lambda: export(page),
        page.KEYS.UNDO: lambda: undo(page), page.KEYS.REDO: lambda: redo(page), page.KEYS.HELP: page.show_help, page.KEYS.ABOUT: page.show_about,
        page.KEYS.SILENCE: lambda: silence(page), page.KEYS.QUIT_NOW: page.app.exit, page.KEYS.WIZARD: lambda: page.holder.show_wizard(page),
    }


def everywhere_keys(page):
    """Return the keys every page has, in the order the F1 dialog and the main screen list them."""
    actions = everywhere_actions(page)
    return [page.bind(binding, action=actions[binding]) for binding in page.KEYS.EVERYWHERE]


def everywhere_key(*, page, binding):
    """Return one of the keys every page has, for the main screen, which draws a cell for Save, Open and Export."""
    return page.bind(binding, action=everywhere_actions(page)[binding])


def silence(page):
    """The emergency stop: silence every channel the instruments use on every connected device, and say what was silenced."""
    page.app.pattern_preview().stop()
    page.say(page.app.transport.silence_everything())


def quit_key(page):
    """Return the key that quits, which only the main screen has."""
    return page.bind(page.KEYS.QUIT, action=lambda: quit_program(page))


# Undo and redo, which work on the set from any page.

def undo(page):
    """Take back the last edit, saying what it touched, or that there is nothing to undo."""
    step_history(page, step=page.document().undo, done=messages_text.MSG_UNDONE, nothing=messages_text.MSG_NOTHING_TO_UNDO)


def redo(page):
    """Put back the last undone edit, saying what it touched, or that there is nothing to redo."""
    step_history(page, step=page.document().redo, done=messages_text.MSG_RESTORED, nothing=messages_text.MSG_NOTHING_TO_REDO)


def step_history(page, *, step, done, nothing):
    """Move the set one step through its history and bring the open pages along.

    Every open page remembers what its cursor is on first, and puts the cursor back on it after,
    so that an undo doesn't move it. A page whose thing the step renamed goes on showing it under
    its other name. A page whose thing the step took away, like the settings page of a track whose
    adding was undone, can't be shown, so the tracker goes back to the page it was opened from,
    and the status line says so.
    """
    if not page.steps_history():
        page.say(page.history_refusal())
        return
    app = page.holder
    pages = app.pages()
    places = [open_page.remember_place() for open_page in pages]
    change = step()
    if change is None:
        page.say(nothing)
        return
    status = done.format(what=change.words)
    for index, open_page in enumerate(pages):
        open_page.follow_renames(change.renames)
        if not open_page.still_exists():
            status = messages_text.MSG_BACK_FROM.format(status=status, page=marks.MSG_CRUMB_SEPARATOR.join(open_page.crumb_trail()))
            app.go_back_to(pages[index - 1])
            break
        open_page.restore_place(places[index])
    page.say(status)


# Saving.

def save(page, *, then=None):
    """Save the set where it came from, or ask where, and then call then if it was saved.

    Nothing is written when the file already holds the set, and the status line says so. A file
    that something else has changed since it was opened or saved here is only written over after
    asking, so that the other change isn't lost by accident. A protected set's file, like the
    demos', is never written over: saving offers to save a copy under another name instead.
    """
    document = page.document()
    path = document.get_path()
    if not path:
        save_as(page, then=then)
        return
    if document.file_is_protected():
        messages = [messages_text.MSG_PROTECTED_EXPLAINED.format(path=path), messages_text.MSG_PROTECTED_SAVE_COPY_QUESTION]
        page.confirm(title=messages_text.MSG_PROTECTED_TITLE, lines=messages, then=lambda: save_as(page, then=then))
        return
    # The file is read once for both questions about it.
    held = document.file_now()
    if document.file_holds_this_set(held=held):
        page.say(messages_text.MSG_FILE_UNCHANGED.format(path=path))
        if then is not None:
            then()
    elif document.file_changed_elsewhere(held=held):
        question = messages_text.MSG_FILE_CHANGED_ELSEWHERE_QUESTION.format(path=path)
        page.confirm(title=messages_text.MSG_FILE_CHANGED_ELSEWHERE_TITLE, lines=[question], then=lambda: write(page, path=path, then=then))
    else:
        write(page, path=path, then=then)


def save_as(page, *, then=None):
    """Ask for a file to save the set as, adding .yml if the name has no suffix, and asking before replacing another file."""
    document = page.document()
    default = document.get_path() or os.path.join(DEFAULT_SAVE_FOLDER, DEFAULT_SAVE_NAME)

    def chosen(path):
        path = path.strip()
        if not path:
            return
        if not path.endswith(shared.SONG_SUFFIXES):
            path += shared.SONG_SUFFIX
        if document.file_is_protected(path=path):
            page.tell(messages_text.MSG_PROTECTED_TITLE, messages_text.MSG_PROTECTED_EXPLAINED.format(path=path), messages_text.MSG_PROTECTED_CHOOSE_ANOTHER_NAME)
        elif path != document.get_path() and os.path.exists(path):
            page.confirm(title=messages_text.MSG_REPLACE_FILE_TITLE, lines=[messages_text.MSG_REPLACE_FILE_QUESTION.format(path=path)], then=lambda: write(page, path=path, then=then, as_copy=True))
        else:
            write(page, path=path, then=then, as_copy=True)
    page.ask_text(title=messages_text.MSG_SAVE_AS_PROMPT, value=default, then=chosen)


def write(page, *, path, then=None, as_copy=False):
    """Write the set to path, as the user's own copy when they chose the name, and explain a failure."""
    try:
        if as_copy:
            page.document().save_as(path)
        else:
            page.document().save(path=path)
    except OSError as error:
        page.tell(errors.ERR_CANT_SAVE_TITLE, errors.ERR_CANT_SAVE.format(path=path, error=error.strerror))
        return
    except SongFileError as error:
        page.tell(errors.ERR_CANT_SAVE_TITLE, str(error))
        return
    page.say(messages_text.MSG_SAVED.format(path=path))
    if then is not None:
        then()


# Exporting the current song.

def unless_unsaved(page, *, then):
    """Call then, after asking if the set has unsaved changes that it would lose."""
    if page.document().is_dirty():
        page.confirm(title=messages_text.MSG_UNSAVED_TITLE, lines=[messages_text.MSG_UNSAVED_CONTINUE], then=then)
    else:
        then()


def open_file(*, page, path, then):
    """Open a set file for a page and pass the document to a function, after asking about any values that have to be corrected.

    A file that holds values that can't be used, each with an allowed value near it, opens only
    after the Corrections dialog is answered Yes. Any other problem is told in a dialog, and
    nothing is opened.
    """
    try:
        document, corrections = Document.load_or_correct(path)
    except SongFileError as error:
        page.tell(errors.ERR_CANT_OPEN_TITLE, str(error))
        return
    if corrections:
        offer_corrected(page=page, document=document, corrections=corrections, then=then)
    else:
        then(document)


def offer_corrected(*, page, document, corrections, then):
    """Ask whether to open a set whose file's values had to be corrected, listing them, and pass the document on if the answer is yes."""
    dialog = CorrectionsDialog(file=document.get_file_name(), corrections=[correction.described() for correction in corrections])
    page.ask(dialog=dialog, then=lambda yes: then(document))


def open_set(page):
    """Show the Open page to pick a set file, unless unsaved changes say otherwise, and come back here with it open."""
    # Imported here because open_page.py descends from Page, which imports this module.
    from llamatron.tui.screens.set.open_page import OpenPage

    def opened(document):
        page.holder.set_document(document)
        page.say(document.conversion_note() or messages_text.MSG_OPENED.format(path=document.get_path()))
        warn_of_silent_instruments(page=page, document=document)
    unless_unsaved(page, then=lambda: page.show_page(OpenPage(holder=page.holder, then=opened)))


def export(page):
    """Ask which kind of export to write for the current song, and write it, saying where it went.

    Exports are named after the set's file and written beside it, so a set that has no file yet
    is saved first, through the Save as prompt, and the export goes on once it's saved.
    """
    if loops_block_export(page):
        return
    if not page.document().can_export():
        page.confirm(title=messages_text.MSG_SAVE_BEFORE_EXPORT_TITLE, lines=[messages_text.MSG_SAVE_BEFORE_EXPORT], then=lambda: save_as(page, then=lambda: choose_export(page)))
        return
    choose_export(page)


def choose_export(page):
    """Ask which kind of export to write for the current song, and write it."""
    title = messages_text.MSG_EXPORT_TITLE.format(name=page.document().get_current_song_name())
    page.ask(dialog=ChoiceDialog(title=title, options=labels.MSG_EXPORT_CHOICES), then=lambda place: export_chosen(page, to=exports.EXPORT_KINDS[place]))


def export_chosen(page, *, to):
    """Write the kind of export chosen. The WAV export says first that only the tracks playing through FluidSynth are in it, or that FluidSynth isn't installed."""
    if to != ExportKind.WAV:
        export_as(page, to=to)
    elif not page.app.transport.fluidsynth_installed():
        page.tell(errors.ERR_CANT_EXPORT_TITLE, errors.ERR_WAV_NEEDS_FLUIDSYNTH)
    else:
        page.confirm(title=messages_text.MSG_WAV_EXPORT_TITLE, lines=[messages_text.MSG_WAV_EXPORT_NOTE], then=lambda: export_as(page, to=to))


def loops_block_export(page):
    """Show the scenes in which every clip loops, and return whether there were any."""
    lines = loop_error_lines(page.document().song())
    if lines:
        page.tell(errors.ERR_LOOP_SCENES_TITLE, *lines)
    return bool(lines)


def export_as(page, *, to):
    """Write a kind of export, asking first the first time a Live set would be written over, since work in Live may be in it."""
    document = page.document()
    path = document.export_path(to)
    if to == ExportKind.ABLETON and document.export_exists(to) and not page.app.has_confirmed_overwrite(path):
        question = messages_text.MSG_REPLACE_EXPORT_QUESTION.format(path=path)

        def confirmed(_):
            page.app.confirm_overwrite(path)
            write_export(page, to=to)
        page.ask(dialog=ConfirmDialog(title=messages_text.MSG_REPLACE_EXPORT_TITLE, messages=[question, messages_text.MSG_EXPORT_REPLACES_LIVE_WORK]), then=confirmed)
    else:
        write_export(page, to=to)


def write_export(page, *, to):
    try:
        path = page.document().export(to)
    except SongFileError as error:
        page.tell(errors.ERR_CANT_EXPORT_TITLE, str(error))
        return
    # The status line says where it went, as it does for saving, rather than a dialog to dismiss.
    page.say(messages_text.MSG_EXPORTED.format(name=exports.EXPORT_LABELS[to], path=path))


# Quitting, which asks only when there are changes to lose.

def quit_program(page):
    """Quit, or with unsaved changes offer to quit without saving (first, since Quit is never an accident) or to save first."""
    if not page.document().is_dirty():
        page.app.exit()
        return
    title = UNSAVED_TITLE.format(title=messages_text.MSG_QUIT_TITLE, note=messages_text.MSG_QUIT_UNSAVED_NOTE)

    def chosen(answer):
        if answer == quit_dialog.SAVE_THEN_QUIT:
            save(page, then=page.app.exit)
        else:
            page.app.exit()
    page.ask(dialog=QuitDialog(title=title, messages=[messages_text.MSG_QUIT_UNSAVED_QUESTION]), then=chosen)
