# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Which part each of a piece's parts plays, found from its notes alone: the drums by their kit, the bass as the lowest line,
the melody as the line that behaves most like one, pads as long chords, harmony as shorter chords, and counter lines as the
other single lines. A part's name is never read.

The melody is not simply the highest line, which in a nocturne may be the left hand's arpeggio and in a quartet passes between
the instruments: a line scores as a melody by moving mostly by step among many pitches, in varied rhythm, at a pace a voice
could sing, through most of the piece, its height above the bass one clue among these. A part is anything hashable with a name, whether
it is drums, and notes, each with a start and an end in beats and a pitch."""

from statistics import median
from typing import NamedTuple

# The parts a piece's parts play.
MELODY = 'lead'
HARMONY = 'harmony'
BASS = 'bass'
PAD = 'pad'
COUNTER = 'counter'
DRUMS = 'drums'
# A line whose middle note is below this MIDI number may be the bass.
LOW_REGISTER = 55
# A part playing this many notes at once on average plays chords.
CHORDAL = 1.6
# Chords this long, in beats, are a pad.
LONG_NOTE_BEATS = 1.5
# A move this many half steps or fewer is a step.
STEP = 2
# A line playing up to this many notes a bar could be sung; a busier one counts less, and one this sparse least of all.
SINGING_DENSITY = 10
SPARSEST = 0.5
SPARSE_SHARE = 0.3
# What a line's score keeps however little of the piece it plays in, its presence counting on top of this.
ALWAYS_COUNTS = 0.3
# How many different pitches and note lengths are enough for a line to be as varied as a melody needs.
VARIETY_ENOUGH = 12
RHYTHMS_ENOUGH = 4
# What a line's share of steps counts from, so that a line all leaps still scores a little.
STEPS_FLOOR = 0.2
# Note lengths are told apart to a quarter of a beat.
LENGTHS_PER_BEAT = 4


class PartShape(NamedTuple):
    """What a part's notes look like: its middle pitch, how many notes sound at once on average, how long its middle note
    lasts in beats, how many notes it plays a bar, how many different pitches it uses, the share of its moves that are steps,
    how many different note lengths it plays, and its presence, the share of the piece's bars it plays in."""

    part: object
    pitch: float
    polyphony: float
    note_beats: float
    density: float
    variety: int
    steps: float
    rhythms: int
    presence: float


def roles_of(*, parts, bars, beats_per_bar):
    """Return the role each part that plays notes plays, by the part, for a piece of so many bars of so many beats."""
    roles = {part: DRUMS for part in parts if part.drum and part.notes}
    shapes = [shape_of(part=part, bars=bars, beats_per_bar=beats_per_bar) for part in parts if not part.drum and part.notes]
    if not shapes:
        return roles
    singles = [shape for shape in shapes if shape.polyphony < CHORDAL]
    bass = lowest_line(singles)
    if bass is not None:
        roles[bass.part] = BASS
    melody = melody_among(shapes=shapes, singles=singles, bass=bass)
    if melody is not None:
        roles[melody.part] = MELODY
    for shape in shapes:
        if shape.part not in roles:
            roles[shape.part] = other_role(shape)
    return roles


def shape_of(*, part, bars, beats_per_bar):
    """Return what a part's notes look like (PartShape)."""
    notes = part.notes
    at_once = {}
    highest = {}
    for note in notes:
        at_once[note.start] = at_once.get(note.start, 0) + 1
        highest[note.start] = max(highest.get(note.start, note.pitch), note.pitch)
    line = [highest[start] for start in sorted(highest)]
    moves = [later - earlier for earlier, later in zip(line, line[1:]) if later != earlier]
    steps = 0.0
    if moves:
        steps = sum(1 for move in moves if abs(move) <= STEP) / len(moves)
    bars_played = {int(float(note.start) // float(beats_per_bar)) for note in notes}
    return PartShape(
        part=part, pitch=median(note.pitch for note in notes), polyphony=sum(at_once.values()) / len(at_once),
        note_beats=median(float(note.end - note.start) for note in notes), density=len(at_once) / bars,
        variety=len({note.pitch for note in notes}), steps=steps,
        rhythms=len({round(float(note.end - note.start) * LENGTHS_PER_BEAT) for note in notes}),
        presence=min(1.0, len(bars_played) / max(bars, 1)),
    )


def lowest_line(singles):
    """Return the lowest single line in the bass register, or None."""
    low = [shape for shape in singles if shape.pitch < LOW_REGISTER]
    if not low:
        return None
    return min(low, key=lambda shape: shape.pitch)


def melody_among(*, shapes, singles, bass):
    """Return the shape of the line most like a melody, or where every part plays chords, the highest of them, or None."""
    lines = [shape for shape in singles if shape is not bass]
    if lines:
        return max(lines, key=melody_score)
    chords = [shape for shape in shapes if shape is not bass]
    if chords:
        return max(chords, key=lambda shape: shape.pitch)
    return None


def other_role(shape):
    """Return the role of a part that is neither the bass nor the melody: a pad or harmony for chords, a counter line otherwise."""
    if shape.polyphony < CHORDAL:
        return COUNTER
    if shape.note_beats >= LONG_NOTE_BEATS:
        return PAD
    return HARMONY


def singing_share(density):
    """Return how far a line's density, its notes a bar, is one a voice could sing, from SPARSE_SHARE to 1: wholly up to
    SINGING_DENSITY, then less the busier it is, with no cliff, so that a line a note over the limit isn't thrown out for a
    quieter inner voice; a line with hardly a note in a bar counts least."""
    if density < SPARSEST:
        return SPARSE_SHARE
    return max(SPARSE_SHARE, min(1.0, SINGING_DENSITY / density))


def melody_score(shape):
    """Return how much a single line behaves like the piece's melody: it moves mostly by step among many pitches, in varied
    rhythm, above the bass, at a density a voice could sing, through most of the piece, since the tune is the line nearly always
    there and an inner voice comes and goes; an arpeggiated sequence, all leaps in even notes, scores low."""
    variety = min(shape.variety, VARIETY_ENOUGH)
    rhythms = min(shape.rhythms, RHYTHMS_ENOUGH)
    height = shape.pitch / LOW_REGISTER
    return variety * (STEPS_FLOOR + shape.steps) * rhythms * height * singing_share(shape.density) * (ALWAYS_COUNTS + shape.presence)


def parts_in_role(*, roles, role):
    """Return the parts that play a role."""
    return [part for part, its_role in roles.items() if its_role == role]
