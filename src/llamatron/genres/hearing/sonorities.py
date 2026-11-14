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

"""What sounds together, measured the way writing about the classical periods describes them: how much of a song is chords
struck at once, how many of its chords hold four notes or more (sevenths and ninths, common in romantic and impressionist music
and rare in the baroque), how often a chord moves to the same chord higher or lower (planing, parallel chords), how much of it
lies in a whole-tone scale, and how far the left hand reaches within a bar (a baroque bass line stays close, a romantic
accompaniment spreads wide under the pedal). Each was
kept because it moved the same way, period by period, in typeset scores and in recorded performances alike; what did not
(an Alberti bass counted note by note, trills, a steady stream of equal notes) was left out. None reads a melody."""

from statistics import median

from llamatron.genres.hearing.lines import TOGETHER

PITCH_CLASSES = 12
FEWEST_IN_A_CHORD = 3
RICH_CHORD = 4
WHOLE_TONE_SCALES = (frozenset((0, 2, 4, 6, 8, 10)), frozenset((1, 3, 5, 7, 9, 11)))
# A window is in a whole-tone scale when this share of its sounding time lies in one.
MOSTLY = 0.9
WINDOW_BEATS = 8.0
# Middle C, below which a note is the left hand's.
HANDS_SPLIT = 60
PLACES = 3
RICH = 'rich'
PLANING = 'planing'
WHOLE_TONE = 'whole_tone'
CHORDAL = 'chordal'
BAR_SPAN = 'bar_span'


def struck_together(notes):
    """Return notes in groups struck together, within a hair of each other, in time order."""
    groups = []
    for note in sorted(notes, key=lambda note: note.begins):
        if groups and note.begins - groups[-1][0].begins <= TOGETHER:
            groups[-1].append(note)
        else:
            groups.append([note])
    return groups


def pitches_of(group):
    return sorted({note.pitch for note in group})


def planing_of(groups):
    """Return the share of moves from one chord to the next that carry the same chord, interval for interval, to another pitch."""
    moves = 0
    parallel = 0
    before = None
    for group in groups:
        pitches = pitches_of(group)
        if len(pitches) < FEWEST_IN_A_CHORD:
            before = None
            continue
        shape = tuple(pitch - pitches[0] for pitch in pitches)
        if before is not None:
            moves += 1
            parallel += before[0] == shape and before[1] != pitches[0]
        before = (shape, pitches[0])
    return round(parallel / moves, PLACES) if moves else None


def whole_tone_of(*, notes, length):
    """Return the share of a song's windows whose sounding time lies mostly in one whole-tone scale."""
    windows = 0
    found = 0
    place = 0
    while place * WINDOW_BEATS < length:
        start = place * WINDOW_BEATS
        end = start + WINDOW_BEATS
        weights = [0.0] * PITCH_CLASSES
        for note in notes:
            if note.begins < end and note.ends > start:
                weights[note.pitch % PITCH_CLASSES] += min(note.ends, end) - max(note.begins, start)
        total = sum(weights)
        if total > 0:
            windows += 1
            found += max(sum(weights[pitch] for pitch in scale) for scale in WHOLE_TONE_SCALES) / total >= MOSTLY
        place += 1
    return round(found / windows, PLACES) if windows else None


def bar_span_of(*, notes, beats_per_bar, length):
    """Return how far the notes below middle C usually reach within one bar, in half steps, or None where few bars hold two."""
    spans = []
    low = [note for note in notes if note.pitch < HANDS_SPLIT]
    bar = 0
    while bar * beats_per_bar < length:
        pitches = [note.pitch for note in low if bar * beats_per_bar <= note.begins < (bar + 1) * beats_per_bar]
        if len(pitches) > 1:
            spans.append(max(pitches) - min(pitches))
        bar += 1
    return float(median(spans)) if spans else None


def sonorities_of(performance):
    """Return what sounds together in a song, by the measure's field: nothing for a song with no pitched notes."""
    notes = [note for track in performance.melodic() for note in track.notes]
    if not notes:
        return {}
    groups = struck_together(notes)
    chords = [pitches_of(group) for group in groups if len(pitches_of(group)) >= FEWEST_IN_A_CHORD]
    rich = sum(1 for chord in chords if len({pitch % PITCH_CLASSES for pitch in chord}) >= RICH_CHORD)
    length = float(performance.length)
    return {RICH: round(rich / len(chords), PLACES) if chords else None, PLANING: planing_of(groups), CHORDAL: round(len(chords) / len(groups), PLACES),
            WHOLE_TONE: whole_tone_of(notes=notes, length=length),
            BAR_SPAN: bar_span_of(notes=notes, beats_per_bar=float(performance.beats_per_bar), length=length)}
