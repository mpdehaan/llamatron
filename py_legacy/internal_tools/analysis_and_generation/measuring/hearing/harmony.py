# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A song's harmony and keys, found from its notes: the key of each window of bars by Krumhansl and Kessler's key profiles (the
standard way of finding a key from how long each pitch class sounds), the chord on each beat by matching its pitch classes
against chord shapes, and from those the chords as numbers of the key (the Nashville and Roman-numeral view), how long a chord
lasts, the qualities and borrowed chords it uses (modal interchange), its loops, and where and how it changes key."""

from collections import Counter
from dataclasses import dataclass
from measuring.measures.traits import Harmony, Modulation

from llamatron.music_theory.analysis import keys
from llamatron.music_theory.analysis.chords import chord_of

PITCH_CLASSES = 12
MAJOR = keys.MAJOR
MINOR = keys.MINOR
KEY_WINDOW_BARS = 8
# How much a note may overlap the next and still count as one line, in beats.
OVERLAP_ALLOWED = 0.05
NUMERALS = ('I', 'bII', 'II', 'bIII', 'III', 'IV', 'bV', 'V', 'bVI', 'VI', 'bVII', 'VII')
MAJOR_SCALE = (0, 2, 4, 5, 7, 9, 11)
MINOR_SCALE = (0, 2, 3, 5, 7, 8, 10)
MINOR_QUALITIES = ('m', 'm7', 'dim', 'm7b5')
ENOUGH_SHARE = 0.08
LOOP_LENGTH = 4
LOOPS_KEPT = 3
LOOP_JOIN = ' '
# A loop is kept when it is heard at least this share of the times the most played loop is.
LOOP_SHARE = 0.3
PHRASE_BARS = 4
# How much more a run of chords starting a phrase counts, when a loop is named by one of its rotations.
PHRASE_START_WEIGHT = 100
MOST_QUALITIES = 5
RELATIVE_MINOR_BELOW = 3
FIFTH = 7


@dataclass(slots=True, kw_only=True, frozen=True)
class Key:
    """A key: its tonic's pitch class and whether it's major or minor."""

    tonic: int
    mode: str


def key_of(weights):
    """Return the key whose profile best matches how long each pitch class sounds (music_theory/analysis/keys.py)."""
    fit = keys.best_key(weights)
    return Key(tonic=fit.tonic, mode=fit.mode)


def harmonic_notes(*, performance, roles, lead):
    """Return the notes that make the harmony: every melodic track's but the lead's, or the lead's too when it plays alone."""
    notes = [note for track in performance.melodic() if track is not lead for note in track.notes]
    return notes or (list(lead.notes) if lead is not None else [])


def keys_by_window(*, performance, notes):
    """Return the key of each window of bars, in order."""
    window = float(performance.beats_per_bar) * KEY_WINDOW_BARS
    count = int(-(-float(performance.length) // window))
    keys = []
    for weights in weights_by_span(notes=notes, span=window, count=count):
        keys.append(key_of(weights) if any(weights) else (keys[-1] if keys else None))
    return keys


def numeral(*, chord, key):
    """Return a chord as a number of the key: its degree's Roman numeral, lower case for a minor chord, with its quality."""
    root, quality = chord
    name = NUMERALS[(root - key.tonic) % PITCH_CLASSES]
    if quality in MINOR_QUALITIES:
        name = name.lower()
    return name if quality in ('M', 'm') else name + quality.lstrip('mM') if quality not in ('M7', 'm7') else name + '7' if quality == 'm7' else name + 'M7'


def is_borrowed(*, chord, key):
    scale = MAJOR_SCALE if key.mode == MAJOR else MINOR_SCALE
    return (chord[0] - key.tonic) % PITCH_CLASSES not in scale


def weights_by_span(*, notes, span, count):
    """Return how long each pitch class sounds in each span of beats, one pass over the notes."""
    result = [[0.0] * PITCH_CLASSES for _ in range(count)]
    for note in notes:
        first = max(0, int(note.begins // span))
        last = min(count - 1, int(note.ends // span))
        for place in range(first, last + 1):
            overlap = min(note.ends, (place + 1) * span) - max(note.begins, place * span)
            if overlap > 0:
                result[place][note.pitch % PITCH_CLASSES] += overlap
    return result


def chords_by_beat(*, performance, notes):
    """Return the chord on each beat, None where nothing sounds."""
    beats = int(float(performance.length))
    return [chord_of(weights) for weights in weights_by_span(notes=notes, span=1.0, count=beats)]


def is_lone_melody(performance):
    """Return whether a performance is a single line: one part, never two notes at once, as a folk song or a transcribed solo."""
    melodic = performance.melodic()
    if len(melodic) != 1:
        return False
    notes = melodic[0].notes
    return all(later.begins >= earlier.ends - OVERLAP_ALLOWED for earlier, later in zip(notes, notes[1:]))


def starts_a_phrase(*, beat, performance):
    """Return whether a beat starts a phrase: a whole number of four-bar phrases after the start of its scene, or of the song."""
    scene = max((start for start in performance.scene_starts if start <= beat), default=0)
    return (beat - float(scene)) % (float(performance.beats_per_bar) * PHRASE_BARS) == 0


def loops_of(*, numerals, changes, performance):
    """Return the song's chord loops, the most played first: every run of four chord changes, a loop and its rotations counted
    as one, since a loop going round is heard from each of its chords in turn, and named as it is written, by the rotation
    that most often starts a phrase. A run heard far less than the most played, as where one section's loop runs into the
    next's, is left out."""
    counts = Counter()
    starts = {}
    for place in range(max(0, len(numerals) - LOOP_LENGTH + 1)):
        run = tuple(numerals[place:place + LOOP_LENGTH])
        same = min(run[turn:] + run[:turn] for turn in range(LOOP_LENGTH))
        counts[same] += 1
        seen = starts.setdefault(same, Counter())
        seen[run] += PHRASE_START_WEIGHT if starts_a_phrase(beat=changes[place], performance=performance) else 1
    most = max(counts.values(), default=0)
    return [LOOP_JOIN.join(starts[same].most_common(1)[0][0]) for same, count in counts.most_common() if count >= most * LOOP_SHARE]


def harmony_of(*, performance, roles, lead):
    """Return the song's harmony as a trait and its keys by window. A lone melody has keys but no chords of its own, so its
    progressions, chord qualities and harmonic rhythm are left unknown rather than guessed from the tune."""
    notes = harmonic_notes(performance=performance, roles=roles, lead=lead)
    keys = keys_by_window(performance=performance, notes=notes)
    if is_lone_melody(performance):
        return Harmony(progressions=None, qualities=None, modes=tuple(dict.fromkeys(key.mode for key in keys if key is not None)), beats_per_chord=None,
                       borrowed=None), keys
    chords = chords_by_beat(performance=performance, notes=notes)
    window = int(float(performance.beats_per_bar)) * KEY_WINDOW_BARS
    changes = []
    numerals = []
    borrowed = Counter()
    qualities = Counter()
    previous = None
    for beat, chord in enumerate(chords):
        key = keys[min(len(keys) - 1, beat // window)] if keys else None
        if chord is None or key is None:
            continue
        qualities[chord[1]] += 1
        if chord != previous:
            changes.append(beat)
            numerals.append(numeral(chord=chord, key=key))
            if is_borrowed(chord=chord, key=key):
                borrowed[numeral(chord=chord, key=key)] += 1
        previous = chord
    sounding = sum(1 for chord in chords if chord is not None)
    beats_per_chord = sounding / len(changes) if changes else float(performance.length)
    total = sum(qualities.values()) or 1
    common_qualities = tuple(quality for quality, count in qualities.most_common(MOST_QUALITIES) if count / total >= ENOUGH_SHARE)
    loops = loops_of(numerals=numerals, changes=changes, performance=performance)
    modes = tuple(dict.fromkeys(key.mode for key in keys if key is not None))
    changed = len(numerals) or 1
    return Harmony(progressions=tuple(loops[:LOOPS_KEPT]), qualities=common_qualities, modes=modes,
                   beats_per_chord=round(beats_per_chord, 2),
                   borrowed=tuple(name for name, count in borrowed.most_common(MOST_QUALITIES) if count / changed >= ENOUGH_SHARE / 2),
                   chromatic=chromatic_of(performance=performance, keys=keys)), keys


def fifths_between(*, old, new):
    """Return how far apart two tonics are round the circle of fifths, from 0 to 6."""
    steps = ((new - old) * FIFTH) % PITCH_CLASSES
    return min(steps, PITCH_CLASSES - steps)


def travel_of(keys):
    """Return how far a song's keys wander: the fifths between one window's tonic and the next's, on average over the windows
    where the tonic moves, and none where it never does. A move to the dominant is one, a move a third away three or four."""
    moves = [fifths_between(old=old.tonic, new=new.tonic) for old, new in zip(keys, keys[1:]) if new.tonic != old.tonic]
    return round(sum(moves) / len(moves), 2) if moves else 0.0


def chromatic_of(*, performance, keys):
    """Return the share of a song's sounding time spent on notes outside the scale of the key of their window."""
    window = float(performance.beats_per_bar) * KEY_WINDOW_BARS
    outside = 0.0
    total = 0.0
    for track in performance.melodic():
        for note in track.notes:
            key = keys[min(len(keys) - 1, int(note.begins // window))] if keys else None
            if key is None:
                continue
            length = note.ends - note.begins
            total += length
            if (note.pitch - key.tonic) % PITCH_CLASSES not in (MAJOR_SCALE if key.mode == MAJOR else MINOR_SCALE):
                outside += length
    return round(outside / total, 3) if total else None


def modulation_of(*, keys, chords_before=None):
    """Return how the song changes key: whether it does, and the moves, each in half steps up, kept only when the new key holds
    for two windows, so that a passing borrowed chord doesn't count, and only when the tonic moves, since a turn between a key's
    major and minor, or to its relative, keeps the same home."""
    moves = []
    steady = [key for key in keys if key is not None]
    for place in range(1, len(steady) - 1):
        old = steady[place - 1]
        new = steady[place]
        if new.tonic != old.tonic and steady[place + 1] == new and not relative(old=old, new=new):
            moves.append((new.tonic - old.tonic) % PITCH_CLASSES)
    return Modulation(often=1.0 if moves else 0.0, moves=tuple(dict.fromkeys(moves)), where=None, reached=None, travel=travel_of(steady))


def relative(*, old, new):
    """Return whether two keys share their notes, a major key and its relative minor, which is a change of center, not of key."""
    if old.mode == new.mode:
        return False
    major, minor = (old, new) if old.mode == MAJOR else (new, old)
    return (major.tonic - minor.tonic) % PITCH_CLASSES == RELATIVE_MINOR_BELOW


