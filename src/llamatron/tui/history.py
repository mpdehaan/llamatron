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
"""The undo history: snapshots of the set's data, one per edit, walked back by undo and forward by redo.

The history knows nothing about pages, fields or what an edit was. The document hands it the
set's data after each key press or dialog answer that changed something (`record`), and it keeps
the data as it was before, as one undo step. Undo hands back the step before, redo the one after,
and the document puts the set back from it. A snapshot's data is shared, never copied: the
document hands over the data its objects keep (kept_data), in which every piece that an edit
didn't touch is the same piece as in the snapshot before, so a step costs the size of the edit and
not of the set. Nothing may change a snapshot's data, neither here nor where it's handed back,
and a history that checks (the tests' do) keeps a copy of its own of each snapshot and raises
StaleAnswer if one differs when it's handed back. The steps are a ring: past the depth, the
oldest is dropped without a word. It's held in memory only, and never written to a file.

`describe_change` puts the difference between two snapshots into words for the status line, like
`pattern (bass)` or `song (verse): scene 2`, by finding the first section that differs, and
`renamed_items` finds what a step renamed, so that a page showing the renamed thing can follow it.
"""

import collections
import copy
from dataclasses import dataclass
from typing import NamedTuple

from llamatron.support.ordered_data import same_in_order
from llamatron.composition.file_format import ScaleSetting, SceneSetting, Section, SetlistSetting, SongSetting
from llamatron.composition.sections import SETLIST_SECTIONS, SONG_SECTIONS
from llamatron.composition.naming import is_default_scale_name
from llamatron.strings.errors import ERR_CHANGED_SNAPSHOT
from llamatron.support.memory import StaleAnswer
from llamatron.strings.messages import MSG_CHANGED_IN_SONG, MSG_CHANGED_NAMED, MSG_CHANGED_SCENE, MSG_CHANGED_THE_SET, MSG_CHANGED_WORDS

# How many edits can be undone. A snapshot holds only the data of what its edit changed and shares
# the rest with its neighbours, so a full history is a little more than the set itself.
HISTORY_DEPTH = 100
# Scenes are shown counted from 1, as the Arrange page numbers them.
FIRST_SCENE_NUMBER = 1


@dataclass(slots=True, kw_only=True, frozen=True)
class Snapshot:
    """The set's data at one moment, and which song was current then. The data is shared with other snapshots and is never changed."""

    data: dict
    song: str


@dataclass(slots=True, kw_only=True)
class Change:
    """What one undo or redo did: words for the status line, and what it renamed, by section, as old name to new."""

    words: str
    renames: dict


class Proof(NamedTuple):
    """A snapshot's data and a copy of it made when the history kept it, which a history that checks compares when the snapshot is handed back."""

    data: dict
    copy: dict


class History:
    """The undo steps, the redo steps, and the snapshot the set matches now."""

    __slots__ = ('_now', '_undo', '_redo', '_proofs')

    def __init__(self, *, depth=HISTORY_DEPTH, checks=False):
        self._now = None
        self._undo = collections.deque(maxlen=depth)
        self._redo = []
        # In a history that checks, a copy of each snapshot's data, by the data's identity, to prove that what is shared was never changed.
        self._proofs = {} if checks else None

    def reset(self, snapshot):
        """Start again from a snapshot, as when a set is opened: nothing to undo or redo."""
        if self._proofs is not None:
            self._proofs.clear()
        self._now = self._kept(snapshot)
        self._undo.clear()
        self._redo.clear()

    def note_song(self, name):
        """Note which song is current, which isn't an edit, so that an undo goes back to the song the edit was made in."""
        if self._now is not None:
            self._now = Snapshot(data=self._now.data, song=name)

    def _kept(self, snapshot):
        """Return a snapshot to keep, as it was given: a history that checks copies its data aside first."""
        if self._proofs is not None:
            self._proofs[id(snapshot.data)] = Proof(data=snapshot.data, copy=copy.deepcopy(snapshot.data))
        return snapshot

    def _handed_back(self, snapshot):
        """Return a kept snapshot to hand back, as it is: a history that checks raises StaleAnswer if its data was changed since it was kept."""
        if self._proofs is not None and self._proofs[id(snapshot.data)].copy != snapshot.data:
            raise StaleAnswer(ERR_CHANGED_SNAPSHOT)
        return snapshot

    def record(self, snapshot, *, continues=False):
        """Keep the step from the current snapshot to this one, and return whether anything changed.

        A step that continues the previous one, like a second digit typed into the same cell,
        replaces where the previous step ended rather than adding a step of its own. Any new step
        drops the redo steps, as everywhere.
        """
        if snapshot.song == self._now.song and same_in_order(first=snapshot.data, second=self._now.data):
            return False
        if not (continues and self._undo):
            self._undo.append(self._now)
        self._now = self._kept(snapshot)
        self._redo.clear()
        return True

    def depth(self):
        """Return how many steps are kept, which is HISTORY_DEPTH except in tests."""
        return self._undo.maxlen

    def can_undo(self):
        return bool(self._undo)

    def can_redo(self):
        return bool(self._redo)

    def undo(self):
        """Return the snapshot before the last step, or None when there is nothing to undo."""
        if not self._undo:
            return None
        self._redo.append(self._now)
        self._now = self._undo.pop()
        return self._handed_back(self._now)

    def redo(self):
        """Return the snapshot after the last undone step, or None when there is nothing to redo."""
        if not self._redo:
            return None
        self._undo.append(self._now)
        self._now = self._redo.pop()
        return self._handed_back(self._now)

    def now(self):
        """Return the snapshot the set matches now."""
        return self._handed_back(self._now)


# Putting a change into words.

def describe_change(*, leaving, arriving):
    """Return words for the first difference between two snapshots' data, for the status line.

    The names come from the snapshot being left first, so that undoing an added track names the
    track that goes away, and undoing a deleted one names the track that comes back.
    """
    for section in SETLIST_SECTIONS:
        name = _differing_name(section=section, leaving=leaving.data, arriving=arriving.data)
        if name is None:
            continue
        if section == Section.SONGS:
            return MSG_CHANGED_IN_SONG.format(song=name, what=_describe_song_change(leaving=leaving.data[Section.SONGS].get(name), arriving=arriving.data[Section.SONGS].get(name)))
        return MSG_CHANGED_NAMED.format(kind=MSG_CHANGED_WORDS[section], name=name)
    for setting in SETTINGS_OF_THE_SET:
        if leaving.data.get(setting) != arriving.data.get(setting):
            return MSG_CHANGED_WORDS[setting]
    return MSG_CHANGED_THE_SET


# The set's own settings, in the order a difference is looked for.
SETTINGS_OF_THE_SET = [
    SetlistSetting.TITLE, SetlistSetting.AUTHOR, SetlistSetting.DESCRIPTION, SetlistSetting.NOTES, SetlistSetting.STEP_SIZE,
    SetlistSetting.DEFAULT_OCTAVE, SetlistSetting.DEFAULT_DRUM_OCTAVE, SetlistSetting.OCTAVE_LABELS, SetlistSetting.PROTECTED,
]
# A song's own settings, likewise.
SETTINGS_OF_A_SONG = [SongSetting.TEMPO, SongSetting.TIME_SIGNATURE, SongSetting.SCALE, SongSetting.SEED, SongSetting.GROOVE]


def _describe_song_change(*, leaving, arriving):
    """Return words for the first difference inside one song: a track, a register, a scene or a setting."""
    if leaving is None or arriving is None:
        return MSG_CHANGED_WORDS[Section.SONGS]
    for section in SONG_SECTIONS:
        name = _differing_name(section=section, leaving=leaving, arriving=arriving)
        if name is not None:
            return MSG_CHANGED_NAMED.format(kind=MSG_CHANGED_WORDS[section], name=name)
    scenes_leaving = leaving.get(Section.SCENES) or []
    scenes_arriving = arriving.get(Section.SCENES) or []
    if scenes_leaving != scenes_arriving:
        return MSG_CHANGED_SCENE.format(number=_first_differing_index(before=scenes_leaving, after=scenes_arriving) + FIRST_SCENE_NUMBER)
    for setting in SETTINGS_OF_A_SONG:
        if leaving.get(setting) != arriving.get(setting):
            return MSG_CHANGED_WORDS[setting]
    return MSG_CHANGED_WORDS[Section.SONGS]


def _differing_name(*, section, leaving, arriving):
    """Return the first name whose entry differs between two named sections, from the one being left first, or None."""
    before = leaving.get(section) or {}
    after = arriving.get(section) or {}
    for name in [*before, *after]:
        if before.get(name) != after.get(name):
            return name
    return None


def _first_differing_index(*, before, after):
    for index, (one, other) in enumerate(zip(before, after)):
        if one != other:
            return index
    return min(len(before), len(after))


# Finding renames.

def renamed_items(*, leaving, arriving):
    """Return what the step between two snapshots renamed, as {section: {old name: new name}}, with scenes by their place.

    A rename keeps an item's place and its own data and changes only its name, which tells it
    from a removal and an addition; the references a rename updates are in other items, so they
    don't get in the way. The one exception is a scale named after its root and kind, whose name
    changes with them. Tracks and scenes are looked at in the song that's current on arrival.
    """
    renames = {}
    for section in SETLIST_SECTIONS:
        _add_renames(renames, section=section, leaving=leaving.data, arriving=arriving.data)
    song_before = (leaving.data.get(Section.SONGS) or {}).get(arriving.song)
    song_after = (arriving.data.get(Section.SONGS) or {}).get(arriving.song)
    if song_before is not None and song_after is not None:
        _add_renames(renames, section=Section.TRACKS, leaving=song_before, arriving=song_after)
        scenes = _renamed_scenes(leaving=song_before.get(Section.SCENES) or [], arriving=song_after.get(Section.SCENES) or [])
        if scenes:
            renames[Section.SCENES] = scenes
    return renames


def _add_renames(renames, *, section, leaving, arriving):
    """Add the renames in one named section: the names that differ at the same place with the same data."""
    before = leaving.get(section) or {}
    after = arriving.get(section) or {}
    if len(before) != len(after):
        return
    found = {}
    for (old, old_item), (new, new_item) in zip(before.items(), after.items()):
        if old != new and _is_the_same_item(section=section, old=old, old_item=old_item, new=new, new_item=new_item):
            found[old] = new
    if found:
        renames[section] = found


def _is_the_same_item(*, section, old, old_item, new, new_item):
    """Return whether an item that changed its name at the same place is the same item: its own data is the same, or it's a scale still named after its root and kind."""
    if old_item == new_item:
        return True
    return section == Section.SCALES and _is_named_after_itself(name=old, scale=old_item) and _is_named_after_itself(name=new, scale=new_item)


def _is_named_after_itself(*, name, scale):
    return is_default_scale_name(name=name, root=scale.get(ScaleSetting.ROOT), kind=scale.get(ScaleSetting.TYPE))


def _renamed_scenes(*, leaving, arriving):
    """Return the scenes whose name alone changed, by their place, with the new name, which can be none."""
    if len(leaving) != len(arriving):
        return {}
    found = {}
    for index, (before, after) in enumerate(zip(leaving, arriving)):
        if before != after and _without_name(before) == _without_name(after):
            found[index] = after.get(SceneSetting.NAME)
    return found


def _without_name(scene):
    return {setting: value for setting, value in scene.items() if setting != SceneSetting.NAME}
