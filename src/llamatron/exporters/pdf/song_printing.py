# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A song made into the PrintedSong the PDF export draws, from the song's own render, so that every chain, groove and draw
prints as it plays.

The tracks chosen as the melody are merged into one line: where they overlap, the highest note struck at a moment is printed,
and a note still sounding when the next is struck ends there. The tracks chosen as the chords are heard together, one chord a
beat as Scene View hears it (music_theory/harmony/heard_chords.py), in the key of the scene playing, and a chord heard on
beats in a row is one chord. A song whose scenes set their Section has a section wherever that setting changes; any other has
one wherever the key changes. Each track's default part is the role its notes play (music_theory/analysis/roles.py): the
melody, the chords for harmony and pads, and left out for the rest.
"""

from statistics import median
from typing import NamedTuple

from llamatron.engine.realizer.song_realizer import SongRealizer
from llamatron.engine.timing.timing import timed_events
from llamatron.exporters.pdf.printed_song import KeyStart, PrintedChord, PrintedNote, PrintedSong, SectionStart
from llamatron.music_theory.analysis import roles
from llamatron.music_theory.fundamentals import intervals
from llamatron.music_theory.harmony import chord_charts
from llamatron.music_theory.harmony.heard_chords import beat_chords, chord_texts


class PrintedPart:
    """The part a track plays in a PDF: the melody, the chords, or left out."""

    MELODY = 'melody'
    CHORDS = 'chords'
    LEFT_OUT = 'left_out'


PRINTED_PARTS = (PrintedPart.MELODY, PrintedPart.CHORDS, PrintedPart.LEFT_OUT)
# A line heard in fewer than this share of the bars is too seldom there to be the tune, which the highest chords then carry.
LEAST_MELODY_PRESENCE = 0.25
# The part each role a track's notes play takes by default.
PARTS_OF_ROLES = {roles.MELODY: PrintedPart.MELODY, roles.HARMONY: PrintedPart.CHORDS, roles.PAD: PrintedPart.CHORDS}


class TrackNotes(NamedTuple):
    """A track's notes over the whole song as PrintedNotes, its name, and whether it is a drums track."""

    name: str
    drum: bool
    notes: tuple


class ChordNote(NamedTuple):
    """A note of the chord tracks as heard_chords reads it, in whole notes from its scene's start."""

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


def default_parts(*, tracks, signature):
    """Return the part each track plays by default, by its name: the role its notes play, as PARTS_OF_ROLES gives it."""
    beat = signature.beat_length()
    parts = []
    for track in tracks:
        notes = tuple(_in_beats(note=note, beat=beat) for note in track.notes)
        parts.append(_RolePart(name=track.name, drum=track.drum, notes=notes))
    length = max((note.end for part in parts for note in part.notes), default=0)
    bars = max(1, int(length // signature.get_beats()) + 1)
    found = roles.roles_of(parts=parts, bars=bars, beats_per_bar=signature.get_beats())
    chosen = {part.name: PARTS_OF_ROLES.get(found.get(part), PrintedPart.LEFT_OUT) for part in parts}
    melody = [part for part in parts if found.get(part) == roles.MELODY]
    if melody and roles.shape_of(part=melody[0], bars=bars, beats_per_bar=signature.get_beats()).presence < LEAST_MELODY_PRESENCE:
        chosen[melody[0].name] = PrintedPart.LEFT_OUT
        _melody_from_chords(chosen=chosen, parts=parts, found=found)
    return chosen


def printed_song(*, song, title, parts, level=chord_charts.DEFAULT_CHORD_LEVEL):
    """Return a song as the PDF export prints it, its tracks playing the parts given by name (PrintedPart), any track not
    named left out, its chords printed at a level (chord_charts.ChordLevel)."""
    render = rendered(song)
    tracks = track_notes(render)
    melody = top_line([note for track in tracks if parts.get(track.name) == PrintedPart.MELODY for note in track.notes])
    chord_tracks = {track.name for track in tracks if parts.get(track.name) == PrintedPart.CHORDS}
    keys = key_starts(song=song, render=render)
    return PrintedSong(
        title=title, melody=tuple(melody), chords=tuple(chords_heard(song=song, render=render, names=chord_tracks, level=level, melody=melody)), keys=tuple(keys),
        sections=tuple(section_starts(render=render, keys=keys)), signature=song.get_time_signature(), tempo=song.get_tempo(),
        length=render.grid.song_length(),
    )


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


def key_starts(*, song, render):
    """Return where each key begins: the first row, and every row whose scene's scale differs from the row before's."""
    keys = []
    for scene, start in zip(render.scenes, render.starts):
        scale = _scene_scale(song=song, scene=scene)
        if scale is not None and (not keys or keys[-1].scale != scale):
            keys.append(KeyStart(start=start, scale=scale))
    return keys


def section_starts(*, render, keys):
    """Return where each section begins: where the scenes' Section setting changes, named after it, in a song whose scenes
    set it; else where the key changes, named after the first scene of the section."""
    sections = []
    named = any(scene.get_section() is not None for scene in render.scenes)
    key_times = {key.start for key in keys}
    before = None
    for scene, start in zip(render.scenes, render.starts):
        if scene is before:
            continue
        before = scene
        if named and scene.get_section() is not None and (not sections or sections[-1].name != scene.get_section()):
            sections.append(SectionStart(start=start, name=scene.get_section()))
        elif not named and (not sections or start in key_times):
            sections.append(SectionStart(start=start, name=scene.get_name()))
    return sections


def chords_heard(*, song, render, names, level, melody):
    """Return the chords the named tracks play together, heard a beat at a time in each row's key and printed at a level
    (music_theory/harmony/chord_charts.py), the melody's notes supplying a power chord's third."""
    grid = render.grid
    beat = grid.get_time_signature().beat_length()
    span = chord_charts.chord_span(grid.get_time_signature())
    chords = []
    for row, start, scene in zip(grid.get_rows(), render.starts, render.scenes):
        scale = _scene_scale(song=song, scene=scene)
        length = grid.row_length(row)
        heard = HeardNotes(notes=_row_notes(grid=grid, row=row, names=names), length=length, beat=beat)
        beats = [chord_charts.HeardBeat(start=found.start, root=found.root, symbol=found.symbol, bass=found.bass) for found in beat_chords(notes=heard, scale=scale)]
        sounding = _melody_at_beats(melody=melody, start=start, length=length, beat=beat)
        charted = chord_charts.charted_chords(beats=beats, stretch=chord_charts.Stretch(length=length, beat=beat, span=span), level=level, melody=sounding)
        chords += [_printed(chord=chord, start=start, scale=scale) for chord in charted]
    return _joined_across_rows(chords)


def _melody_from_chords(*, chosen, parts, found):
    """Make the highest of the parts playing chords the melody, its top line the tune, as a pianist's right hand plays it."""
    chordal = [part for part in parts if chosen[part.name] == PrintedPart.CHORDS]
    if chordal:
        highest = max(chordal, key=lambda part: median(note.pitch for note in part.notes))
        chosen[highest.name] = PrintedPart.MELODY


def _melody_at_beats(*, melody, start, length, beat):
    """Return the pitch classes the melody sounds at the start of each beat of a row, by the beat's start from the row's."""
    sounding = {}
    for note in melody:
        if note.end <= start or note.start >= start + length:
            continue
        first = max(note.start - start, 0 * beat)
        place = (first // beat) * beat
        if place < first:
            place += beat
        while place < min(note.end - start, length):
            sounding.setdefault(place, set()).add(note.pitch % intervals.HALF_STEPS_PER_OCTAVE)
            place += beat
    return sounding


def _printed(*, chord, start, scale):
    """Return a chart's chord as printed, named and numbered in its scale, placed from its row's start."""
    name, numeral = chord_texts(root=chord.root, symbol=chord.symbol, scale=scale, bass=chord.bass)
    return PrintedChord(start=start + chord.start, end=start + chord.end, name=name, numeral=numeral, root=chord.root, symbol=chord.symbol, bass=chord.bass)


def _joined_across_rows(chords):
    """Return chords with one that carries on, end to end and unchanged in name and numeral, into the next row joined."""
    runs = []
    for chord in chords:
        if runs and runs[-1].end == chord.start and (runs[-1].name, runs[-1].numeral) == (chord.name, chord.numeral):
            chord = runs.pop()._replace(end=chord.end)
        runs.append(chord)
    return runs


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


def _row_notes(*, grid, row, names):
    """Return the notes the named tracks play in a row, as ChordNotes from the row's start."""
    notes = []
    for column in grid.get_columns():
        clip = grid.get_clip(row=row, column=column)
        if clip is None or column.get_name() not in names:
            continue
        events, _ = timed_events(clip=clip, scale=grid.scale_at(row=row, column=column))
        notes += [ChordNote(start=event.start, end=event.end, pitch=event.midi_number, drum=column.is_drum()) for event in events]
    return notes
