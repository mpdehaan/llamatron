# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later


"""Which scenes of a song an edit cannot change, so that a render after the edit takes them from the render before it.

A render plays the scenes in order, and what a scene plays depends on its own clips, the patterns they name and what the
scenes before it left: the registers, the draws, the drifts' walks and the random numbers drawn so far. So when nothing but
scenes and patterns changed, every scene before the first one that changed, or that names a changed pattern, plays as it
did. The render keeps, at each scene's start, the state of its random streams (a SceneCheckpoint), and the next render
starts from there.

The comparison reads the set's data as the objects keep it (Setlist.kept_data), whose unchanged parts are the very same
dictionaries from one edit to the next, so comparing two of them costs little more than finding what differs.
"""

from typing import NamedTuple

from llamatron.model.vocabulary.file_format import Section

# The first scene of a song, from which a render after an edit that could change anything starts.
FIRST_SCENE = 0


class SceneCheckpoint(NamedTuple):
    """Where a render's random streams stood as a written-out scene started: the registers' chooser and every drift."""

    register_state: tuple
    drifts: object


def first_changed_scene(*, before, after, song_name, scenes):
    """Return the place of the first scene of a song, counted from 0, that may play differently in after than in before, the set's
    data on either side of an edit; FIRST_SCENE when anything changed but the song's scenes and the set's patterns, and the
    number of scenes when none changed. scenes are the song's scenes in after, whose clips say which patterns each names."""
    if not _same_but(first=before, second=after, apart=(Section.PATTERNS, Section.SONGS)):
        return FIRST_SCENE
    song_before = before[Section.SONGS].get(song_name)
    song_after = after[Section.SONGS].get(song_name)
    if song_before is None or song_after is None or not _same_but(first=song_before, second=song_after, apart=(Section.SCENES,)):
        return FIRST_SCENE
    changed = _changed_names(first=before.get(Section.PATTERNS, {}), second=after.get(Section.PATTERNS, {}))
    old_scenes = song_before.get(Section.SCENES, [])
    new_scenes = song_after.get(Section.SCENES, [])
    for place, scene in enumerate(scenes[:len(old_scenes)]):
        if old_scenes[place] != new_scenes[place] or _names_any(scene=scene, patterns=changed):
            return place
    return min(len(old_scenes), len(new_scenes))


def changed_clips(*, before, after, song_name, scenes):
    """Return, for each scene of a song, the tracks whose clips may play differently in after than in before, the set's data
    on either side of an edit: those whose clip changed or plays or morphs to a changed pattern, or None for a scene whose own
    settings changed, which reach every clip in it. Return None when the song has a scene more or fewer. Asked only where
    first_changed_scene found nothing changed but the song's scenes and the set's patterns."""
    patterns = _changed_names(first=before.get(Section.PATTERNS, {}), second=after.get(Section.PATTERNS, {}))
    old_scenes = before[Section.SONGS][song_name].get(Section.SCENES, [])
    new_scenes = after[Section.SONGS][song_name].get(Section.SCENES, [])
    if len(old_scenes) != len(new_scenes):
        return None
    return [_scene_changes(old=old, new=new, scene=scene, patterns=patterns) for old, new, scene in zip(old_scenes, new_scenes, scenes)]


def _scene_changes(*, old, new, scene, patterns):
    """Return the tracks whose clips in one scene may play differently, or None when the scene's own settings changed."""
    if not _same_but(first=old, second=new, apart=(Section.TRACKS,)):
        return None
    tracks = _changed_names(first=old.get(Section.TRACKS, {}), second=new.get(Section.TRACKS, {}))
    for name in patterns:
        tracks.update(scene.clip_slots_naming(section=Section.PATTERNS, name=name))
    return tracks


def _names_any(*, scene, patterns):
    """Return whether a clip of a scene plays or morphs to any of the patterns named."""
    return any(scene.clip_slots_naming(section=Section.PATTERNS, name=name) for name in patterns)


def _same_but(*, first, second, apart):
    """Return whether two dictionaries of data hold the same, but for the keys apart."""
    keys = (first.keys() | second.keys()).difference(apart)
    return all(first.get(key) == second.get(key) for key in keys)


def _changed_names(*, first, second):
    """Return the names whose data differs between two sections' data, an item added or taken away among them."""
    return {name for name in first.keys() | second.keys() if first.get(name) != second.get(name)}
