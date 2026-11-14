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

"""A song's lines, found from its notes: the lead reduced to one line and split into phrases at its rests; its motion against
the research on expectation (steps, reversals after leaps, range, arching phrases, where the peak falls, how much it repeats);
how it plays the listener's prediction game, measured as IDyOM does, each note's surprise and the uncertainty before it, from
a model of melodic motion in general blended with a model of what the song has already played; how it's phrased; whether a
person could sing it; and how the bass moves."""

from collections import Counter
from math import log2
from statistics import median, pstdev

from llamatron.genres.measures.traits import Bass, BassMotion, Expectation, Melody, Phrasing, Vocal

# Notes that start within this many beats of each other start together, as the notes of a chord under a hand do.
TOGETHER = 0.06
STEP = 2
LEAP = 5
PHRASE_REST_BEATS = 0.75
# A rest of a beat or more ends a phrase, and so does a shorter rest before a note that starts a bar: fitted to the Weimar Jazz
# Database's experts, whose phrases have a median of 1.76 bars (this rule gives 1.78), where splitting at every rest as long as
# the line's usual gap gave about a bar, breaking a line at each eighth rest.
BREATH_REST_BEATS = 1.0
# How near a bar's start a note must begin, in beats, to count as starting the bar.
ON_THE_BAR = 0.05
# A pentatonic line: at most five pitch classes carry this share of its notes, and a move of up to a minor third is a step.
PENTATONIC_NOTES = 5
PENTATONIC_COVERAGE = 0.9
PENTATONIC_STEP = 3
LONG_NOTE_BEATS = 2.0
LOW_PERCENTILE = 0.05
HIGH_PERCENTILE = 0.95
MIN_PHRASE_NOTES = 4
ARCH_RISE = 2
INTERVALS = 25
LARGEST_INTERVAL = 12
CONTEXT = 2
PRIOR_WEIGHT = 2.0
SHORT_NOTE_BEATS = 1.0
SINGABLE_RANGE = 19
SINGABLE_STEPS = 0.55
VOICE_LIKE = (53, 54, 55, 86, 66, 65, 67, 57, 58, 72, 69, 70, 74, 23, 41, 22, 61, 60)
GRID = 12
HUNDREDTHS = 100
OCTAVE = 12
# A bar's figure is written on a grid of this many steps a beat, fine enough for sixteenths and triplets.
RHYTHM_GRID = 12
# A bass holding one note this many bars or more is a pedal, beneath the chords rather than following them.
PEDAL_BARS = 4


# A move of this many half steps or more, up then down again, is the leap of an oom-pah bass; and the share of such pairs that
# makes a line one.
OOM_PAH_LEAP = 5
OOM_PAH_SHARE = 0.5


def outer_line(track, *, top):
    """Return a track's notes as one line, its top or its bottom, the skyline of what sounds: of the notes that start together,
    the highest (or lowest), kept only when no note still sounding from before lies beyond it. Notes start together when they
    start within a hair of each other, since a person playing never strikes two keys at the same instant, and without that
    every note of a recorded performance was taken for the tune, both hands of it. So a part holding a tune and its
    accompaniment gives the tune as its top line and the left hand as its bottom one."""
    beyond = (lambda one, other: one.pitch > other.pitch) if top else (lambda one, other: one.pitch < other.pitch)
    line = []
    sounding = []
    notes = sorted(track.notes, key=lambda note: note.begins)
    place = 0
    while place < len(notes):
        start = notes[place].begins
        together = []
        while place < len(notes) and notes[place].begins - start <= TOGETHER:
            together.append(notes[place])
            place += 1
        outer = together[0]
        for note in together[1:]:
            if beyond(note, outer):
                outer = note
        sounding = [note for note in sounding if note.ends > start + TOGETHER]
        if not any(beyond(note, outer) for note in sounding):
            line.append(outer)
        sounding += together
    return line


def top_line(track):
    """Return a track's notes as one line, the highest of what sounds."""
    return outer_line(track, top=True)


def phrases_of(line, *, beats_per_bar=None):
    """Return a line split into phrases at its breaths: a rest of a beat or more; a shorter rest, as long as the line's usual gap,
    before a note that starts a bar (both fitted to experts' marks on transcribed solos, so that an eighth rest inside a run doesn't
    end a phrase); or a note twice as long as the usual gap and two beats or more, where a singer breathes after a phrase's long
    last note though no rest is written, as folk songs are notated."""
    phrases = []
    current = []
    gaps = [float(later.start - earlier.start) for earlier, later in zip(line, line[1:])]
    usual = median(gaps) if gaps else PHRASE_REST_BEATS
    for place, note in enumerate(line):
        current.append(note)
        following = line[place + 1] if place + 1 < len(line) else None
        gap = None if following is None else following.begins - note.ends
        starts_bar = following is not None and beats_per_bar and following.begins % float(beats_per_bar) < ON_THE_BAR
        rest = following is None or gap >= BREATH_REST_BEATS or (starts_bar and gap >= min(PHRASE_REST_BEATS, usual))
        if rest or note.length() >= max(LONG_NOTE_BEATS, 2 * usual):
            phrases.append(current)
            current = []
    if current:
        phrases.append(current)
    return phrases


def intervals_of(phrase):
    return [later.pitch - earlier.pitch for earlier, later in zip(phrase, phrase[1:])]


def percentile(*, values, share):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * (len(ordered) - 1)))]


def bar_figures(*, line, beats_per_bar):
    """Return the line's figure in each bar it plays in: its intervals and its rhythm within the bar, apart from where it starts,
    so that a figure repeated, or repeated a step higher, counts as the same; bars of a single note are left out."""
    bars = {}
    for note in line:
        bars.setdefault(int(note.begins // beats_per_bar), []).append(note)
    figures = []
    for bar, notes in sorted(bars.items()):
        if len(notes) < 2:
            continue
        intervals = tuple(later.pitch - earlier.pitch for earlier, later in zip(notes, notes[1:]))
        rhythm = tuple(round((note.begins - bar * beats_per_bar) * RHYTHM_GRID) for note in notes)
        figures.append((intervals, rhythm))
    return figures


def melody_of(*, line, beats_per_bar):
    """Return the lead's motion as a trait."""
    phrases = phrases_of(line, beats_per_bar=beats_per_bar)
    moves = [interval for phrase in phrases for interval in intervals_of(phrase)]
    if not moves:
        return Melody(steps=None, reversals=None, range=None, phrase_bars=None, arches=None, peak=None, repetition=None, density=None), phrases
    steps = sum(1 for move in moves if abs(move) <= STEP) / len(moves)
    turns = []
    for phrase in phrases:
        motion = intervals_of(phrase)
        for leap, after in zip(motion, motion[1:]):
            if abs(leap) >= LEAP:
                turns.append(after != 0 and (after > 0) != (leap > 0))
    pitches = [note.pitch for note in line]
    shaped = [phrase for phrase in phrases if len(phrase) >= MIN_PHRASE_NOTES]
    arches = []
    peaks = []
    for phrase in shaped:
        highest = max(range(len(phrase)), key=lambda place: phrase[place].pitch)
        peaks.append(highest / (len(phrase) - 1))
        top = phrase[highest].pitch
        arches.append(0 < highest < len(phrase) - 1 and top - phrase[0].pitch >= ARCH_RISE and top - phrase[-1].pitch >= ARCH_RISE)
    figures = bar_figures(line=line, beats_per_bar=float(beats_per_bar))
    seen = set()
    repeats = 0
    for figure in figures:
        repeats += figure in seen
        seen.add(figure)
    lengths = [(phrase[-1].ends - phrase[0].begins) / float(beats_per_bar) for phrase in phrases]
    span = (line[-1].ends - line[0].begins) or 1.0
    return Melody(steps=round(steps, 3), reversals=round(sum(turns) / len(turns), 3) if turns else None, density=round(len(line) / span, 2),
                  range=percentile(values=pitches, share=HIGH_PERCENTILE) - percentile(values=pitches, share=LOW_PERCENTILE), phrase_bars=round(median(lengths), 2),
                  arches=round(sum(arches) / len(arches), 3) if arches else None, peak=round(sum(peaks) / len(peaks), 3) if peaks else None,
                  repetition=round(repeats / len(figures), 3) if figures else None), phrases


def prior(interval, *, previous):
    """Return how likely a melodic interval is in melody in general: small intervals far likelier than large ones (pitch
    proximity), and after a leap a turn back the other way likelier (post-skip reversal), the odds of Huron and Narmour."""
    weight = 2.0 ** (-abs(interval) / 2.0)
    if previous is not None and abs(previous) >= LEAP and interval != 0 and (interval > 0) != (previous > 0):
        weight *= 2.0
    return weight


def predicted(*, history, counts):
    """Return the odds of every next interval: the general model blended with what the song has played after the same
    context, the song's weight growing with how often it has heard that context."""
    previous = history[-1] if history else None
    odds = {interval: prior(interval, previous=previous) for interval in range(-LARGEST_INTERVAL, LARGEST_INTERVAL + 1)}
    total = sum(odds.values())
    general = {interval: weight / total for interval, weight in odds.items()}
    heard = counts.get(tuple(history[-CONTEXT:]), Counter())
    seen = sum(heard.values())
    if not seen:
        return general
    return {interval: (PRIOR_WEIGHT * general[interval] + heard[interval]) / (PRIOR_WEIGHT + seen) for interval in general}


def expectation_of(*, phrases, line, bars_heard):
    """Return how the lead plays the prediction game: each note's surprise (its information content, in bits, as a share of
    the most an interval can carry) and the uncertainty before it (the entropy of the odds, as a share of the most), the
    surprise's spread, and how much of the song's material returns."""
    counts = {}
    surprises = []
    uncertainties = []
    most = log2(INTERVALS)
    for phrase in phrases:
        history = []
        for interval in intervals_of(phrase):
            interval = max(-LARGEST_INTERVAL, min(LARGEST_INTERVAL, interval))
            odds = predicted(history=history, counts=counts)
            surprises.append(-log2(max(odds[interval], 1e-9)) / most)
            uncertainties.append(-sum(chance * log2(chance) for chance in odds.values() if chance > 0) / most)
            counts.setdefault(tuple(history[-CONTEXT:]), Counter())[interval] += 1
            history.append(interval)
    if not surprises:
        return Expectation(surprise=None, contrast=None, familiarity=bars_heard, uncertainty=None)
    return Expectation(surprise=round(sum(surprises) / len(surprises), 3), contrast=round(min(1.0, pstdev(surprises) * 2), 3),
                       familiarity=bars_heard, uncertainty=round(sum(uncertainties) / len(uncertainties), 3))


def phrasing_of(*, line, phrases, length):
    """Return how the lead is phrased."""
    if len(line) < MIN_PHRASE_NOTES:
        return None
    sounding = sum((phrase[-1].ends - phrase[0].begins) for phrase in phrases)
    span = (line[-1].ends - line[0].begins) or 1.0
    densities = [len(phrase) / max(0.25, (phrase[-1].ends - phrase[0].begins)) for phrase in phrases]
    mean_density = sum(densities) / len(densities)
    lengths = Counter(round(note.length() * 4) for note in line)
    offbeats = sum(1 for note in line if round(note.begins * 2) != note.begins * 2) / len(line)
    velocities = [note.velocity for note in line]
    looseness = sum(abs(round(note.begins * GRID) - note.begins * GRID) / GRID for note in line) / len(line) * HUNDREDTHS
    arcs = []
    for phrase in phrases:
        if len(phrase) >= MIN_PHRASE_NOTES:
            half = len(phrase) // 2
            rising = max(note.pitch for note in phrase[:half + 1]) < max(note.pitch for note in phrase[half:])
            releasing = phrase[-1].pitch < max(note.pitch for note in phrase)
            arcs.append(rising and releasing)
    return Phrasing(space=round(max(0.0, 1 - sounding / span), 3), burstiness=round(min(1.0, pstdev(densities) / mean_density) if mean_density else 0.0, 3),
                    rhythmic_variety=round(min(1.0, (len(lengths) / 8 + offbeats) / 2), 3), dynamics=round((max(velocities) - min(velocities)) / 127, 3),
                    looseness=round(looseness, 2), arc=round(sum(arcs) / len(arcs), 3) if arcs else 0.0)


def leaning(*, value, good, bad):
    """Return how far a value leans from bad (0) to good (1), on a straight line between them and held to that span."""
    if good == bad:
        return 1.0
    return max(0.0, min(1.0, (value - bad) / (good - bad)))


def is_pentatonic(line):
    """Return whether a line keeps to an anhemitonic pentatonic scale: five pitch classes or fewer carry nearly all its notes, and
    no two of them lie a half step apart."""
    counts = {}
    for note in line:
        counts[note.pitch % OCTAVE] = counts.get(note.pitch % OCTAVE, 0) + 1
    main = sorted(counts, key=lambda pitch_class: -counts[pitch_class])[:PENTATONIC_NOTES]
    covered = sum(counts[pitch_class] for pitch_class in main) / len(line)
    return covered >= PENTATONIC_COVERAGE and all((one - other) % OCTAVE not in (1, OCTAVE - 1) for one in main for other in main if one != other)


def sung_steps(*, line, melody):
    """Return the share of moves a singer hears as steps: two half steps or fewer, or in a pentatonic line, where a minor third is
    a step of the scale, three or fewer, so that a pentatonic tune isn't heard as a leaping one (the user's many lenses)."""
    if not is_pentatonic(line):
        return melody.steps
    moves = [abs(later.pitch - earlier.pitch) for earlier, later in zip(line, line[1:]) if later.pitch != earlier.pitch]
    return sum(1 for move in moves if move <= PENTATONIC_STEP) / len(moves) if moves else melody.steps


def vocal_of(*, line, melody, phrases, sound, beats_per_bar):
    """Return how singable the lead is, a spectrum: a voice's range, steps as a singer hears them, breaths and a voice-like sound
    each lean it towards a song's tune, and the share of short, syllable-like notes says how it would be sung."""
    if not line or melody.steps is None:
        return Vocal(singable=0.0, range=None, syllabic=None, breath_bars=None, carriers=(sound,) if sound else ())
    syllabic = sum(1 for note in line if note.length() <= SHORT_NOTE_BEATS) / len(line)
    breath_bars = median((phrase[-1].ends - phrase[0].begins) / float(beats_per_bar) for phrase in phrases)
    within_voice = leaning(value=melody.range, good=SINGABLE_RANGE - 7, bad=SINGABLE_RANGE + 12)
    by_step = leaning(value=sung_steps(line=line, melody=melody), good=SINGABLE_STEPS + 0.2, bad=SINGABLE_STEPS - 0.35)
    breathing = leaning(value=abs(breath_bars - 2), good=1, bad=5)
    voiced = 1.0 if sound is None or sound in VOICE_LIKE else 0.6
    singable = within_voice * by_step * (0.5 + 0.5 * breathing) * voiced
    return Vocal(singable=round(singable, 3), range=melody.range, syllabic=round(syllabic, 3), breath_bars=round(breath_bars, 2), carriers=(sound,) if sound else ())


def bass_of(*, track, performance):
    """Return how the bass moves, or that there is none."""
    if track is None:
        return Bass(motion=BassMotion.NONE, notes_per_bar=0)
    line = top_line(track)
    reach = max(note.pitch for note in line) - min(note.pitch for note in line) if line else None
    per_bar = len(line) / performance.bars()
    moves = [later.pitch - earlier.pitch for earlier, later in zip(line, line[1:])]
    if not moves:
        return Bass(motion=BassMotion.SUSTAINED, notes_per_bar=round(per_bar, 2), reach=reach)
    repeats = sum(1 for move in moves if move == 0) / len(moves)
    octaves = sum(1 for move in moves if abs(move) == OCTAVE) / len(moves)
    small = sum(1 for move in moves if 0 < abs(move) <= 3) / len(moves)
    offbeat = sum(1 for note in line if place_off_beat(note)) / len(line)
    beats = float(performance.beats_per_bar)
    if per_bar <= 2.2:
        motion = BassMotion.SUSTAINED
    elif alternation(moves) >= OOM_PAH_SHARE:
        motion = BassMotion.OOM_PAH
    elif octaves >= 0.3:
        motion = BassMotion.OCTAVES
    elif repeats >= 0.6:
        motion = BassMotion.PEDAL if per_bar >= 6 and held_bars(line=line, beats=beats) >= PEDAL_BARS else BassMotion.ROOTS
    elif abs(per_bar - beats) <= 0.8 and small >= 0.5:
        motion = BassMotion.WALKING
    elif offbeat >= 0.4:
        motion = BassMotion.SYNCOPATED
    elif per_bar >= 6 and repeats < 0.3 and small + sum(1 for move in moves if 3 < abs(move) <= 5) / len(moves) >= 0.6:
        motion = BassMotion.BOOGIE
    elif repeats >= 0.35:
        motion = BassMotion.ROOTS
    else:
        motion = BassMotion.RIFF
    return Bass(motion=motion, notes_per_bar=round(per_bar, 2), reach=reach)


def alternation(moves):
    """Return the share of a bass line's pairs of moves that leap up and straight back down by a fourth or more, the oom and pah
    of a ragtime or stride left hand, a march's tuba against its afterbeats."""
    pairs = list(zip(moves, moves[1:]))
    if not pairs:
        return 0.0
    return sum(1 for up, down in pairs if (up >= OOM_PAH_LEAP and down <= -OOM_PAH_LEAP) or (up <= -OOM_PAH_LEAP and down >= OOM_PAH_LEAP)) / len(pairs)


def bottom_line(track):
    """Return a track's notes as one line, the lowest note of each onset, a piano's left hand heard as its bass."""
    return outer_line(track, top=False)


def held_bars(*, line, beats):
    """Return how many bars the bass usually stays on one note before it moves, the median over its runs of a repeated note:
    a pedal holds through the chord changes, a root bass moves with them."""
    runs = []
    start = line[0]
    for earlier, later in zip(line, line[1:]):
        if later.pitch != earlier.pitch:
            runs.append((earlier.ends - start.begins) / beats)
            start = later
    runs.append((line[-1].ends - start.begins) / beats)
    return median(runs)


def place_off_beat(note):
    return note.begins % 1 != 0
