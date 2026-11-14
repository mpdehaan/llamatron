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

"""The Document's undo and redo: one step for each key press or dialog answer that changed the set, kept in memory only."""

import copy

from llamatron.composition.setlist import Setlist
from llamatron.strings.errors import ERR_STALE_DATA, ERR_WRONG_RESTORE
from llamatron.support.memory import StaleAnswer
from llamatron.support.ordered_data import same_in_order
from llamatron.tui.history import Change, describe_change, renamed_items, Snapshot



class DocumentUndo:
    """How Document records edits in its History and steps back and forward through them.

    It works on what Document keeps: the set, the current song's name, the history, and the marks
    that say an edit happened and whether the next one continues it.
    """

    __slots__ = ()

    # Undo and redo.

    def _snapshot(self):
        """Return the set's data as it stands, with which song is current.

        The data is what the set's objects keep (kept_data): only what changed since the last
        snapshot is built, and every other piece is the one the earlier snapshots hold. Nothing
        changes it, and a document whose memory checks proves here that what was kept is what
        the set would write now.
        """
        data = self._setlist.kept_data()
        if self._memory.checks():
            again = self._setlist.to_data()
            if data != again:
                raise StaleAnswer(ERR_STALE_DATA.format(kept=data, again=again))
        return Snapshot(data=data, song=self._current)

    def record_edit(self):
        """Keep what the set was before the changes since the last call, as one undo step, and return whether there were any.

        The app calls this after every key press and dialog answer, so a key that runs several
        setters, like deleting a track with its clips, is still one step.
        """
        continues = self._continues
        self._continues = False
        if not self._edited:
            return False
        self._edited = False
        return self._history.record(self._snapshot(), continues=continues)

    def continue_edit(self):
        """Make the next recorded edit part of the previous one, as typing another digit into the same cell is."""
        self._continues = True

    def forget_history(self):
        """Start the history again from the set as it is now, as opening a set does. Tests use it after setting a set up."""
        self._edited = False
        self._continues = False
        self._history.reset(self._snapshot())

    def can_undo(self):
        return self._history.can_undo()

    def can_redo(self):
        return self._history.can_redo()

    def undo(self):
        """Put the set back as it was before the last edit, and return the Change it made, or None if there was none."""
        return self._step_history(self._history.undo)

    def redo(self):
        """Put back the last undone edit, and return the Change it made, or None if there was none."""
        return self._step_history(self._history.redo)

    def _step_history(self, step):
        leaving = self._snapshot()
        arriving = step()
        if arriving is None:
            return None
        self._restore(arriving)
        return Change(words=describe_change(leaving=leaving, arriving=arriving), renames=renamed_items(leaving=leaving, arriving=arriving))

    def _restore(self, snapshot):
        """Put the set back as a snapshot has it, keeping the song that was current then if it still exists.

        The set reads the snapshot's data as loading does, and keeps every item whose data is
        what the snapshot holds, so an undo builds only what the edit changed. A document whose
        memory checks proves that the set is what loading the whole snapshot would have made.
        """
        self._setlist.restore(snapshot.data)
        self._setlist.fill_in_defaults()
        if self._memory.checks():
            afresh = Setlist.from_data(data=copy.deepcopy(snapshot.data))
            afresh.fill_in_defaults()
            if self._setlist.to_data() != afresh.to_data():
                raise StaleAnswer(ERR_WRONG_RESTORE.format(restored=self._setlist.to_data(), afresh=afresh.to_data()))
        self._current = snapshot.song if self._setlist.has_song(snapshot.song) else self._setlist.first_song_name()
        self._forget()
        self._edited = False
        self._dirty = not same_in_order(first=self._own_data(), second=self._clean_data)
