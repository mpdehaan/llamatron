# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A song made into the PrintedSong the PDF export draws, read as a lead sheet is from a MIDI file of the song.

The tracks chosen are played from the song's own render, so that every chain, groove and draw prints as it plays, and merged
into one track, whatever llamatron's tracks hold: a lead sheet thinks of one tune and the chords under it, and the hands of
a piece may each hold some of both. The tune is that track's skyline, the highest note at each moment, each note ending where
the next begins, a low cluster the top line drops into while the tune rests cut off. The chords are estimated from all of
its notes a bar or half bar at a time (music_theory/harmony/chord_estimate.py), or at As played heard a beat at a time as
Scene View hears them (music_theory/harmony/heard_chords.py), named in the key of the scene playing. A song whose scenes set
their Section has a section wherever that setting changes; any other has one at every scene, a scene played again in a row
counted rather than repeated. Every track that plays pitched notes is chosen by default, the drums never.
"""

from typing import NamedTuple

from llamatron.engine.realizer.song_realizer import SongRealizer
from llamatron.engine.timing.timing import timed_events
from llamatron.exporters.pdf.printed_song import KeyStart, PrintedChord, PrintedNote, PrintedSong, SectionStart
from llamatron.music_theory.analysis import roles
from llamatron.music_theory.fundamentals import intervals
from llamatron.music_theory.harmony import chord_estimate
from llamatron.music_theory.harmony.heard_chords import beat_chords, chord_texts

# A low cluster is cut from the tune where enough notes fall in it: at least so many, the cluster an octave or more below the
# tune's middle, a fourth or more below the tune's lowest note, holding no more than this share of the notes.
FEWEST_FOR_A_CLUSTER = 16
FEWEST_IN_A_CLUSTER = 4
MOST_IN_A_CLUSTER = 0.4
CLUSTER_GAP = 5
CLUSTER_DEPTH = 12
OCTAVE = intervals.HALF_STEPS_PER_OCTAVE


class TrackNotes(NamedTuple):
    """A track's notes over the whole song as PrintedNotes, its name, and whether it is a drums track."""

    name: str
    drum: bool
    notes: tuple


class MergedNote(NamedTuple):
    """A note of the merged track as heard_chords reads it, in whole notes from its scene's start."""

    start: object
    end: object
    pitch: int
    drum: bool


class HeardNotes(NamedTuple):
    """A scene's notes as heard_chords reads them, with how long the scene lasts and its beat, in whole notes."""

    notes: list
    length: object
    beat: object


class RenderedSong(NamedTuple):
    """A song's render: its grid, when each row starts, and the song's scene each row plays."""

    grid: object
    starts: list
    scenes: list


class _RolePart(NamedTuple):
    """A track as the roles of music_theory/analysis/roles.py read it: its name, whether it is drums, its notes in beats."""

    name: str
    drum: bool
    notes: tuple


def rendered(song):
    """Return a song's render as a RenderedSong, the one the other exports use."""
    realizer = SongRealizer(song)
    grid = realizer.render()
    scenes = [written.get_scene() for written in realizer.get_scenes()]
    return RenderedSong(grid=grid, starts=grid.row_starts(), scenes=scenes)


def track_notes(render):
    """Return every track's notes over the whole song (TrackNotes), each clip's laid at its row's start, in track order."""
    grid = render.grid
    tracks = []
    for column in grid.get_columns():
        notes = []
        for row, start in zip(grid.get_rows(), render.starts):
            clip = grid.get_clip(row=row, column=column)
            if clip is None:
                continue
            events, _ = timed_events(clip=clip, scale=grid.scale_at(row=row, column=column))
            notes += [PrintedNote(start=start + event.start, end=start + event.end, pitch=event.midi_number) for event in events]
        tracks.append(TrackNotes(name=column.get_name(), drum=column.is_drum(), notes=tuple(sorted(notes))))
    return tracks


def track_roles(*, tracks, signature):
    """Return the role each track's notes play (music_theory/analysis/roles.py), by its name, a track playing no notes having
    none, and the parts in beats the roles were read from."""
    beat = signature.beat_length()
    parts = []
    for track in tracks:
        notes = tuple(_in_beats(note=note, beat=beat) for note in track.notes)
        parts.append(_RolePart(name=track.name, drum=track.drum, notes=notes))
    length = max((note.end for part in parts for note in part.notes), default=0)
    bars = max(1, int(length // signature.get_beats()) + 1)
    found = roles.roles_of(parts=parts, bars=bars, beats_per_bar=signature.get_beats())
    return {part.name: found.get(part) for part in parts}, parts, bars


def default_tracks(tracks):
    """Return the names of the tracks a PDF takes by default: every track that plays pitched notes, the drums never."""
    return {track.name for track in tracks if not track.drum and track.notes}


def printed_song(*, song, title, tracks, level=chord_estimate.DEFAULT_CHORD_LEVEL):
    """Return a song as the PDF export prints it, the named tracks merged into one and read as a lead sheet: the tune its
    skyline, the chords estimated at a level (chord_estimate.ChordLevel)."""
    render = rendered(song)
    merged = merged_notes(render=render, names=tracks)
    keys = key_starts(song=song, render=render)
    melody = without_low_cluster(top_line(merged))
    printed = PrintedSong(
        title=title, melody=tuple(melody), chords=(), keys=tuple(keys), sections=tuple(section_starts(song=song, render=render)),
        signature=song.get_time_signature(), tempo=song.get_tempo(), length=render.grid.song_length(),
    )
    return PrintedSong(
        title=printed.title, melody=printed.melody, chords=tuple(lead_sheet_chords(printed=printed, merged=merged, render=render, level=level)),
        keys=printed.keys, sections=printed.sections, signature=printed.signature, tempo=printed.tempo, length=printed.length,
    )


def merged_notes(*, render, names):
    """Return the named tracks' notes over the whole song merged into one, the drums aside, in order."""
    merged = []
    for track in track_notes(render):
        if track.name in names and not track.drum:
            merged += track.notes
    return sorted(merged)


def top_line(notes):
    """Return notes merged into one line: at each moment the highest note struck then, each ending where the next begins if
    it sounds that long."""
    highest = {}
    for note in notes:
        if note.start not in highest or note.pitch > highest[note.start].pitch:
            highest[note.start] = note
    line = [highest[start] for start in sorted(highest)]
    merged = []
    for note, following in zip(line, line[1:] + [None]):
        if following is not None and note.end > following.start:
            note = note._replace(end=following.start)
        merged.append(note)
    return merged


def without_low_cluster(line):
    """Return a tune's line without the low cluster it drops into where the tune rests and a bass or an accompaniment is the
    highest note, as a MIDI file's melody often does: a separate group of low pitches, a fourth or more below the rest and
    an octave or more below the tune's middle, holding a minority of its notes."""
    pitches = sorted(note.pitch for note in line)
    if len(pitches) < FEWEST_FOR_A_CLUSTER:
        return line
    middle = pitches[len(pitches) // 2]
    distinct = sorted(set(pitches))
    cutoff = None
    for low, high in zip(distinct, distinct[1:]):
        if high > middle:
            break
        if high - low >= CLUSTER_GAP and low <= middle - CLUSTER_DEPTH:
            cutoff = high
    if cutoff is None:
        return line
    below = sum(1 for pitch in pitches if pitch < cutoff)
    if not FEWEST_IN_A_CLUSTER <= below <= MOST_IN_A_CLUSTER * len(pitches):
        return line
    return [note for note in line if note.pitch >= cutoff]


def lead_sheet_chords(*, printed, merged, render, level):
    """Return the chords under the tune: estimated a bar or half bar at a time, or at As played heard a beat at a time."""
    if level == chord_estimate.ChordLevel.AS_PLAYED:
        return heard_chords(printed=printed, merged=merged, render=render)
    bars = [(start, min(start + printed.bar_length(), printed.length)) for start in printed.bar_starts()]
    music = chord_estimate.Music(notes=tuple(merged), tune=frozenset(doubled_tune(merged=merged, melody=printed.melody)))
    estimated = chord_estimate.estimated_chords(music=music, bars=bars, scale_at=printed.key_at, level=level)
    return [_printed(chord=chord, scale=printed.key_at(chord.start)) for chord in estimated]


def doubled_tune(*, merged, melody):
    """Return the tune's notes and every note that doubles one at an octave, struck with it, as a right hand playing the
    tune in octaves does, so that the doubling counts as the tune and not as the chord."""
    struck = {(note.start, note.pitch % OCTAVE) for note in melody}
    return [note for note in merged if (note.start, note.pitch % OCTAVE) in struck]


def heard_chords(*, printed, merged, render):
    """Return the chord heard on each beat of each row, a chord heard on beats in a row joined into one while its numeral
    holds."""
    beat = printed.signature.beat_length()
    chords = []
    for row, start in zip(render.grid.get_rows(), render.starts):
        length = render.grid.row_length(row)
        notes = [MergedNote(start=note.start - start, end=note.end - start, pitch=note.pitch, drum=False) for note in merged if note.end > start and note.start < start + length]
        for found in beat_chords(notes=HeardNotes(notes=notes, length=length, beat=beat), scale=printed.key_at(start)):
            name, numeral = found.name, found.numeral
            chord = PrintedChord(start=start + found.start, end=start + found.start + beat, name=name, numeral=numeral, root=found.root, symbol=found.symbol, bass=found.bass)
            if chords and chords[-1].end == chord.start and (chords[-1].name, chords[-1].numeral) == (name, numeral):
                chord = chords.pop()._replace(end=chord.end)
            chords.append(chord)
    return chords


def key_starts(*, song, render):
    """Return where each key begins: the first row, and every row whose scene's scale differs from the row before's."""
    keys = []
    for scene, start in zip(render.scenes, render.starts):
        scale = _scene_scale(song=song, scene=scene)
        if scale is not None and (not keys or keys[-1].scale != scale):
            keys.append(KeyStart(start=start, scale=scale))
    return keys


def section_starts(*, song, render):
    """Return where each section begins: where the scenes' Section setting changes, named after it, in a song whose scenes
    set it; else at every scene, named after it, a row playing the same clips as the row before counted as a time more."""
    if any(scene.get_section() is not None for scene in render.scenes):
        return _sections_by_setting(render)
    sections = []
    before = None
    for scene, start in zip(render.scenes, render.starts):
        music = _clips_of(song=song, scene=scene)
        if sections and music == before:
            sections[-1] = sections[-1]._replace(times=sections[-1].times + 1)
        else:
            sections.append(SectionStart(start=start, name=scene.get_name()))
        before = music
    return sections


def _sections_by_setting(render):
    """Return a section wherever the scenes' Section setting changes, named after it, a scene that sets none carrying on the
    section before."""
    sections = []
    for scene, start in zip(render.scenes, render.starts):
        if scene.get_section() is not None and (not sections or sections[-1].name != scene.get_section()):
            sections.append(SectionStart(start=start, name=scene.get_section()))
    return sections


def _clips_of(*, song, scene):
    """Return what a scene plays, each track's patterns in turn, so that two scenes playing alike compare equal."""
    played = []
    for track in song.get_track_names():
        clip_slot = scene.get_clip_slot(track)
        if clip_slot is not None:
            played.append((track, tuple(clip_slot.get_pattern_names())))
    return tuple(played)


def _printed(*, chord, scale):
    """Return an estimated chord as printed, named and numbered in its scale."""
    name, numeral = chord_texts(root=chord.root, symbol=chord.symbol, scale=scale)
    return PrintedChord(start=chord.start, end=chord.end, name=name, numeral=numeral, root=chord.root, symbol=chord.symbol, bass=None)


def _in_beats(*, note, beat):
    """Return a note with its times in beats rather than whole notes."""
    return note._replace(start=note.start / beat, end=note.end / beat)


def _scene_scale(*, song, scene):
    """Return the NamedScale a scene plays in: the one most of its clips with a scale of their own take, else its own, else
    the song's, or None."""
    counts = {}
    for track in song.get_track_names():
        clip_slot = scene.get_clip_slot(track)
        if clip_slot is not None and clip_slot.get_scale_name():
            counts[clip_slot.get_scale_name()] = counts.get(clip_slot.get_scale_name(), 0) + 1
    name = scene.get_scale_name() or song.get_scale_name()
    if counts:
        name = max(counts, key=counts.get)
    if name is None:
        return None
    return song.get_setlist().get_named_scale(name)
