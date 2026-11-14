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

"""Which part each track of a song plays, found from its notes alone: the drums by their kit, the bass as the lowest line, the
lead as the line that moves most like a melody above the rest, pads as long chords, harmony and rhythm parts as shorter chords,
and counter lines as the other single lines. A track's name is never read, since nothing about the set is assumed."""

from dataclasses import dataclass
from statistics import median

from llamatron.genres.measures.traits import Role

LOW_REGISTER = 55
CHORDAL = 1.6
LONG_NOTE_BEATS = 1.5
STEP = 2
SINGING_DENSITY = 10
SPARSEST = 0.5
SPARSE_SHARE = 0.3
# What a line's score keeps however little of the song it plays in, its presence counting on top of this.
ALWAYS_COUNTS = 0.3
VARIETY_ENOUGH = 12
RHYTHMS_ENOUGH = 4


@dataclass(slots=True, kw_only=True, frozen=True)
class TrackShape:
    """What a track's notes look like: its median pitch, how many notes sound at once on average, how long a note lasts, how
    many notes it plays a bar, how many different pitches it uses, the share of its moves that are steps, how many different
    note lengths it plays, and its presence, the share of the song's bars it plays in."""

    track: object
    pitch: float
    polyphony: float
    note_beats: float
    density: float
    variety: int
    steps: float
    rhythms: int
    presence: float


def shape_of(*, track, bars, beats_per_bar):
    """Return a melodic track's shape."""
    notes = track.notes
    starts = {}
    for note in notes:
        starts[note.start] = starts.get(note.start, 0) + 1
    highest = {}
    for note in notes:
        if note.start not in highest or note.pitch > highest[note.start]:
            highest[note.start] = note.pitch
    line = [highest[start] for start in sorted(highest)]
    moves = [later - earlier for earlier, later in zip(line, line[1:]) if later != earlier]
    steps = sum(1 for move in moves if abs(move) <= STEP) / len(moves) if moves else 0.0
    return TrackShape(track=track, pitch=median(note.pitch for note in notes), polyphony=sum(starts.values()) / len(starts),
                      note_beats=median(note.length() for note in notes), density=len(starts) / bars, variety=len({note.pitch for note in notes}),
                      steps=steps, rhythms=len({round(note.length() * 4) for note in notes}),
                      presence=min(1.0, len({int(float(note.start) // float(beats_per_bar)) for note in notes}) / max(bars, 1)))


def singing_share(density):
    """Return how far a line's density, its notes a bar, is one a voice could sing, from SPARSE_SHARE to 1: wholly up to
    SINGING_DENSITY, then less the busier it is, with no cliff, so that a line a note over the limit isn't thrown out for a
    quieter inner voice; a line with hardly a note in a bar counts least."""
    if density < SPARSEST:
        return SPARSE_SHARE
    return max(SPARSE_SHARE, min(1.0, SINGING_DENSITY / density))


def melody_score(shape):
    """Return how much a single line looks like the song's melody: it moves mostly by step among many pitches, in varied
    rhythm, above the bass, at a density a voice could sing, through most of the song, since the tune is the line that is nearly
    always there and an inner voice comes and goes; an arpeggiated sequence, all leaps in even notes, scores low."""
    singing = singing_share(shape.density)
    return min(shape.variety, VARIETY_ENOUGH) * (0.2 + shape.steps) * min(shape.rhythms, RHYTHMS_ENOUGH) * (shape.pitch / LOW_REGISTER) * singing * (ALWAYS_COUNTS + shape.presence)


def roles_of(performance):
    """Return each sounding track's role, by the track."""
    roles = {track: Role.DRUMS for track in performance.drums()}
    shapes = [shape_of(track=track, bars=performance.bars(), beats_per_bar=performance.beats_per_bar) for track in performance.melodic()]
    if not shapes:
        return roles
    singles = [shape for shape in shapes if shape.polyphony < CHORDAL]
    low = [shape for shape in singles if shape.pitch < LOW_REGISTER]
    bass = min(low, key=lambda shape: shape.pitch) if low else None
    if bass is not None:
        roles[bass.track] = Role.BASS
    lines = [shape for shape in singles if shape is not bass]
    lead = max(lines, key=melody_score) if lines else None
    if lead is None:
        chords = [shape for shape in shapes if shape is not bass]
        lead = max(chords, key=lambda shape: shape.pitch) if chords else None
    if lead is not None:
        roles[lead.track] = Role.LEAD
    for shape in shapes:
        if shape.track in roles:
            continue
        if shape.polyphony >= CHORDAL:
            roles[shape.track] = Role.PAD if shape.note_beats >= LONG_NOTE_BEATS else Role.HARMONY
        else:
            roles[shape.track] = Role.COUNTER
    return roles


def tracks_in_role(*, roles, role):
    return [track for track, its_role in roles.items() if its_role == role]
