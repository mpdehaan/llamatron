# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""What Scene View shows of one scene: every track's notes laid over each other, as played or as written, and the chord heard on each beat.

Played is the song's own render, the one the exports and real-time playback use, so it shows what
every chain, groove, strum, shape and register does; a song with no seed draws its random parts
afresh, so it is one take. Written renders a copy of the set with everything taken out that works
after the patterns are read: every chain, shape, strum and groove, and the steps'
probability and the rows that read the registers, so that each note shows as its pattern writes it.
A clip whose pattern reads the registers is marked either way, since what the registers do to it
depends on the whole song before it: its notes are drawn apart, never mixed in.

The chord on each beat is found from these notes by music_theory/harmony/heard_chords.py.
"""

from typing import NamedTuple

from llamatron.engine.realizer.as_written import as_written
from llamatron.engine.realizer.song_realizer import SongRealizer
from llamatron.engine.timing.timing import timed_events
from llamatron.interface.forms.text import tempo_text
from llamatron.user_strings import marks

class SceneNote(NamedTuple):
    """A note of the scene: its track's place in the song, when it starts and ends in whole notes from the scene's start, its pitch, whether it's a drum's, and whether its clip reads the registers."""

    track: int
    start: object
    end: object
    pitch: int
    drum: bool
    marked: bool


class SceneNotes(NamedTuple):
    """A scene's notes, the song's track names by place, which tracks read the registers, how long the scene lasts in whole notes, and its beat and bar."""

    names: tuple
    notes: list
    marked_tracks: set
    length: object
    beat: object
    bar: object


def marked_tracks(*, song, index):
    """Return the names of the tracks whose clip in a scene plays a pattern whose statements read the draws."""
    scene = song.get_scenes()[index]
    marked = set()
    for name in song.get_track_names():
        clip_slot = scene.get_clip_slot(name)
        if clip_slot is not None and song.get_setlist().get_pattern(clip_slot.get_pattern_name()).has_any_statement():
            marked.add(name)
    return marked


def scene_notes(*, song, index, written, seed=None):
    """Return a scene's notes as played, the song's render, or as written, its patterns alone, with its rows laid end to end from the scene's start, its random parts drawn afresh, or from a seed where one is given, so that a tool can repeat it."""
    rendered = as_written(song) if written else song
    realizer = SongRealizer(rendered, seed=seed, looping_scenes_go_round=True)
    grid = realizer.render()
    rows = grid.get_rows()
    starts = grid.row_starts()
    places = realizer.realization().rows_of_scene(index)
    names = tuple(song.get_track_names())
    marked = marked_tracks(song=song, index=index)
    origin = starts[places[0]] if places else 0
    notes = []
    end = origin
    for place in places:
        row = rows[place]
        end = max(end, starts[place] + grid.row_length(row))
        for column in grid.get_columns():
            clip = grid.get_clip(row=row, column=column)
            if clip is None or column.get_name() not in names:
                continue
            track = names.index(column.get_name())
            events, _ = timed_events(clip=clip, scale=grid.scale_at(row=row, column=column))
            for event in events:
                notes.append(SceneNote(track=track, start=starts[place] - origin + event.start, end=starts[place] - origin + event.end, pitch=event.midi_number,
                                       drum=column.is_drum(), marked=column.get_name() in marked))
    signature = song.get_time_signature()
    return SceneNotes(names=names, notes=notes, marked_tracks={names.index(name) for name in marked}, length=end - origin,
                      beat=signature.beat_length(), bar=signature.bar_length())


class Effective(NamedTuple):
    """What a scene plays with in the end, and where each comes from, since overrides can confuse: its tempo, scale and groove, each with its source, and each track whose clip takes a scale of its own."""

    tempo: str
    tempo_source: str
    scale: object
    scale_source: str
    groove: str
    groove_source: str
    clip_scales: dict


SONG_SOURCE = marks.MSG_SCENE_VIEW_FROM_SONG
SCENE_SOURCE = marks.MSG_SCENE_VIEW_FROM_SCENE
NO_GROOVE = marks.MSG_SCENE_VIEW_NO_GROOVE


def effective_values(*, song, index):
    """Return the tempo, scale and groove a scene plays with and where each comes from, and the tracks whose clips take scales of their own."""
    scene = song.get_scenes()[index]
    tempo = tempo_text(scene.tempo_in(song.get_tempo()))
    tempo_source = SCENE_SOURCE if scene.has_own_tempo() else SONG_SOURCE
    if scene.has_tempo_ramp():
        tempo, tempo_source = marks.MSG_SCENE_VIEW_TEMPO_RAMPS.format(tempo=tempo), SCENE_SOURCE
    scale_name = scene.get_scale_name() or song.get_scale_name()
    scale_source = SCENE_SOURCE if scene.get_scale_name() else SONG_SOURCE
    choice = scene.get_groove_choice()
    if choice is None:
        groove, groove_source = song.get_groove_name(), SONG_SOURCE
    else:
        groove, groove_source = (NO_GROOVE if choice is False else choice), SCENE_SOURCE
    clip_scales = {}
    for name in song.get_track_names():
        clip_slot = scene.get_clip_slot(name)
        if clip_slot is not None and clip_slot.get_scale_name() and clip_slot.get_scale_name() != scale_name:
            clip_scales[name] = clip_slot.get_scale_name()
    return Effective(tempo=tempo, tempo_source=tempo_source, scale=scale_name, scale_source=scale_source, groove=groove, groove_source=groove_source,
                     clip_scales=clip_scales)
