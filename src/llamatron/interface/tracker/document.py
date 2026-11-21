# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The set being edited in the text UI: a Setlist, which of its songs is current, where it's saved, and what's unsaved.

The document holds the set as composition objects and changes it only through their methods,
which check every value. What's left here is what the set doesn't know: the file it came from,
whether it has unsaved changes, which song the pages are working on, how long that song lasts
(Lengths), the undo history and exporting, and what the pages worked out from the set,
kept in one Memory until what each answer came from changes. Nothing here draws
anything, and nothing is saved or exported unless one of those methods is called.

The history is kept in memory only, never in the set or its file. Every edit goes through
`changed()`, which only notes that something changed; the app calls `record_edit()` after each
key press and each dialog answer, so that one key press is one undo step however many setters it
ran, and typing another digit into the same cell `continue_edit()`s the step before.

Document's methods are grouped by subject in interface/tracker/document_parts, one class each, which Document
is made of: DocumentFiles (opening, saving, exporting), DocumentUndo, NamedEdits (renaming,
copying, deleting, moving and sorting anything with a name), SetEdits (what the whole set
shares), SongEdits (the current song) and PatternEdits. What's in this module is what they all
work on: the set, the current song, the note that something changed, and the answers remembered
until it does.
"""

from llamatron.caching.memory import Memory
from llamatron.caching.revised import ChangeMark, Revised
from llamatron.interface.tracker.document_parts import files
from llamatron.interface.tracker.document_parts.files import DocumentFiles, file_data
from llamatron.interface.tracker.document_parts.named_edits import NamedEdits
from llamatron.interface.tracker.document_parts.pattern_edits import PatternEdits
from llamatron.interface.tracker.document_parts.set_edits import SetEdits
from llamatron.interface.tracker.document_parts.song_edits import SongEdits
from llamatron.interface.tracker.document_parts.undo import DocumentUndo
from llamatron.interface.tracker.history import History
from llamatron.interface.tracker.lengths import Lengths, measured
from llamatron.interface.tracker.uses import uses_of
from llamatron.model.objects.setlist import Setlist
from llamatron.user_strings import names


# The key the current song's estimate is remembered by.
MEASURED_KEY = 'measured'


class Document(Revised, DocumentFiles, DocumentUndo, NamedEdits, SetEdits, SongEdits, PatternEdits):
    """One set, along with which song is current, where it's saved and whether it has unsaved changes.

    The document has a revision of its own, which moves with every change to the set and every
    change of the current song, so an answer worked out from anything in the set is remembered
    `on=(document,)`. An answer that no pattern's own contents can change, like what uses a scale
    or which scales a pattern plays under, is remembered `on=(document.get_outside_patterns(),)`, which
    typing into a pattern leaves alone, and an answer about one pattern's contents names that
    pattern.
    """

    __slots__ = ('_setlist', '_current', '_path', '_dirty', '_memory', '_outside_patterns', '_saved_data', '_clean_data', '_history', '_edited', '_continues')

    def __init__(self, *, setlist=None, path=None, saved_data=files.NOT_READ):
        """Hold a set, or a new one, saved at path if it has one.

        Saving writes every setting a new set has, even where a file left it out. A set from a
        file with no songs gets an empty one, so that there is always a current song. saved_data
        is what the file at path holds, from whoever has just read it; left out, the file is read.
        """
        self._setlist = Setlist.new() if setlist is None else setlist
        self._setlist.fill_in_defaults()
        if not self._setlist.get_song_names():
            self._setlist.add_new_song(names.MSG_DEFAULT_SONG_NAME)
        self._current = self._setlist.first_song_name()
        self._path = path
        self._dirty = False
        # What the pages worked out from the set, each answer kept until what it was worked out from changes.
        self._memory = Memory()
        # The revision of everything but the patterns' own contents: it moves with every change except one made by a pattern's own method.
        self._outside_patterns = ChangeMark()
        self.note_change()
        # What the file held when it was opened or last saved, so that a change made to it by
        # something else can be noticed before it's written over.
        self._saved_data = (None if path is None else file_data(path)) if saved_data is files.NOT_READ else saved_data
        # What the set was when it was opened or last saved, so that undoing back to it reads as saved.
        self._clean_data = self._own_data()
        self._history = History(checks=self._memory.checks())
        self._edited = False
        self._continues = False
        self._history.reset(self._snapshot())

    def get_setlist(self):
        """Return the set. Pages read it through this, and change it only through this document's methods."""
        return self._setlist

    def song(self):
        """Return the current song, which the Arrange, Tracks and Registers pages work on and X exports."""
        return self._setlist.get_song(self._current)

    def get_current_song_name(self):
        return self._current

    def select_song(self, name):
        """Make another of the set's songs current, which changes nothing in the file."""
        self._setlist.get_song(name)
        self._current = name
        self._forget()
        # Picking a song isn't an edit, so the history's idea of the current song follows it, unless an
        # edit is under way, like deleting the current song, which an undo should bring back as current.
        if not self._edited:
            self._history.note_song(name)

    def changed(self, *, inside_a_pattern=False):
        """Note that the set changed, so that it needs saving, what was worked out from it is worked out again and the edit is recorded.

        inside_a_pattern says the change was made by a pattern's own method, which can only have
        changed that pattern's contents, so what was worked out from everything else is kept.
        """
        self._dirty = True
        self._forget(inside_a_pattern=inside_a_pattern)
        self._edited = True

    def _forget(self, *, inside_a_pattern=False):
        """Move the document's revision on, since the set or the current song changed, and the revision of everything outside the patterns unless only a pattern's contents did."""
        self.note_change()
        if not inside_a_pattern:
            self._outside_patterns.note_change()

    def get_outside_patterns(self):
        """Return what an answer is remembered on when no pattern's own contents can change it: its revision moves with every change but one inside a pattern."""
        return self._outside_patterns

    def get_memory(self):
        """Return the one memory of what was worked out from the set, which the pages and their parts keep their own answers in too."""
        return self._memory

    def uses(self, *, section, name):
        """Return the uses of a named item of a section, worded for a page, remembered until the set changes, since the list pages count them for every row on every key."""
        return self.remembered(
            key=(Document.uses.__name__, section, name), on=(self._outside_patterns,),
            compute=lambda: uses_of(setlist=self._setlist, section=section, name=name),
        )

    def remembered(self, *, key, on, compute):
        """Return the answer to a question about the set, worked out by compute the first time it's asked since anything in on changed.

        on is what the answer is worked out from: this document for anything in the set,
        outside_patterns() for what no pattern's contents can change, or the objects themselves,
        like a pattern and the set whose step size it takes.
        """
        return self._memory.remembered(key=key, on=on, compute=compute)

    def lengths(self):
        """Return how long everything in the current song lasts, which measures the song only when a scene's or a clip's length is asked for."""
        return Lengths(song=self.song(), measure=self._measured)

    def _measured(self):
        """Return the current song's estimate, taken when first asked for and kept until the set changes."""
        return self.remembered(key=MEASURED_KEY, on=(self,), compute=lambda: measured(self.song()))

    def change_pattern(self, method, *arguments, **named):
        """Make one change to a pattern through one of its methods, a pattern found by pattern(name), note it as a change inside
        that pattern, which what is known of everything else outlives, and return what the method returned."""
        result = method(*arguments, **named)
        self.changed(inside_a_pattern=True)
        return result

    def change_set(self, method, *arguments, **named):
        """Make one change to anything of the set but a pattern's own contents through its method, note it, and return what the method returned."""
        result = method(*arguments, **named)
        self.changed(inside_a_pattern=False)
        return result

    def set_setting(self, *, holder, name, value):
        """Set one setting of anything in the set that holds settings, by the setting's file name, or None to leave it out and use its default.

        The holder checks the value as reading a file does, against the current song where the setting names something of it.
        """
        self.change_set(holder.set_written, name=name, value=value, song=self.song())
