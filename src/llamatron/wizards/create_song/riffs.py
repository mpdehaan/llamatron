# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A riff: a song's second hook, one or two bars that a rhythm player repeats exactly while the chords move the riff under the song.

A riff is written over the home chord, in eighths, as one line of notes and rests (line_edits.py): the first bar states
the figure, starting on the chord's root, and the second says the figure again with another ending, as a riff answers
itself. The Progression generator moves the line with each chord, as it moves a bass figure. A song asks for a riff
with who plays it, which kinds of section it is played in, and either a take, a number the notes are drawn from, or the
notes themselves written by hand.

A riff is drawn one of two ways. As single notes, above. Or as chords on the accents, a heavy riff: the root on the first
beat, two to four accents off the beat as two-note chords, the low root short and quiet between them or rests, the same
bar again where the riff has two, and two or three single notes at the end that lead back to the root. Its notes are the
five of the minor scale a riff keeps to, the first, the flat third, the fourth, the fifth and the flat seventh, with the
flat fifth passed through; over a scale whose third or seventh is major the two are flattened. Half of its notes or
more are the root. Its first player plays the chords, and whoever plays it besides plays its notes alone.
"""

import random

from llamatron.wizards.create_song import notation, wizard_names

# What a song says of its riff.
RIFF = 'riff'
RIFF_ROLES = 'roles'
RIFF_KINDS = 'kinds'
RIFF_TAKE = 'take'
RIFF_LINE = 'line'
FIRST_TAKE = 0
SINGLE_NOTES = 'single notes'
NOTES_WAYS = (SINGLE_NOTES, wizard_names.ACCENT_CHORDS)
MUTED_ROOTS = 'muted roots'
RESTS_BETWEEN = 'rests'
BETWEEN_WAYS = (MUTED_ROOTS, RESTS_BETWEEN)
BAR_COUNTS = (1, 2)
WITH_CHORDS_WAYS = (wizard_names.MOVES_WHOLE, wizard_names.STAYS_HOME)
RIFF_UNDER_TUNE = 'under the tune'
IN_FULL = 'in full'
LEAVES_A_GAP = 'leaves a gap'
UNDER_TUNE_WAYS = (IN_FULL, LEAVES_A_GAP)
RIFF_BARS = 2
RIFF_SEED = 'riff {} {}'
# The notes a riff is drawn from, each a degree and an octave from the player's own, with how often each is drawn: the root most, then the note under it.
HOME = (1, 0)
LADDER = ((HOME, 4), ((7, -1), 3), ((3, 0), 2), ((4, 0), 2), ((5, 0), 2), ((5, -1), 1), ((1, 1), 1))
# How long a note may last, in eighths, the shorter the likelier, and how often a place after the first is a rest.
LENGTHS = (1, 1, 2, 2, 3)
REST_SHARE = 0.2
LONGEST_REST = 2
# How many notes at the end of the second bar are drawn again, as the riff's answer.
ANSWER_NOTES = 2
TRIES = 20


def note_at(*, place, steps):
    """Return a note at a place of the ladder, a degree and an octave, lasting some steps."""
    degree, octave = place
    note = {notation.DEGREE: degree, notation.STEPS: steps}
    if octave:
        note[notation.OCTAVE] = octave
    return note


def drawn_place(*, dice, before):
    """A note of the ladder, by its share, and never the note just played a third time running."""
    places = [place for place, share in LADDER for _ in range(share) if before[-2:] != [place, place]]
    return dice.choice(places)


def riff_bar(*, dice, eighths):
    """One bar of a riff: notes and a few rests filling the bar, the first note the root."""
    bar = []
    places = []
    room = eighths
    while room:
        length = min(dice.choice(LENGTHS), room)
        if bar and length <= LONGEST_REST and dice.random() < REST_SHARE and notation.REST not in bar[-1]:
            bar.append({notation.REST: length})
        else:
            place = HOME if not bar else drawn_place(dice=dice, before=places)
            places.append(place)
            bar.append(note_at(place=place, steps=length))
        room -= length
    return bar


def answered(*, bar, dice):
    """A bar said again with its last notes drawn anew, so that the riff's second bar answers its first."""
    sounding = [count for count, note in enumerate(bar) if notation.REST not in note]
    again = [dict(note) for note in bar]
    for _ in range(TRIES):
        for count in sounding[1:][-ANSWER_NOTES:]:
            again[count] = note_at(place=drawn_place(dice=dice, before=[]), steps=bar[count][notation.STEPS])
        if again != bar:
            break
    return again


def riff_line(*, seed, take, eighths, bars=RIFF_BARS):
    """A song's riff as one line of two bars, drawn from the song's seed and the riff's take, or its first bar alone where one bar is asked for."""
    dice = random.Random(RIFF_SEED.format(seed, take))
    first = riff_bar(dice=dice, eighths=eighths)
    return first if bars == 1 else first + answered(bar=first, dice=dice)


# A heavy riff: its seed, the chord of an accent, how short a muted root is, and the notes an accent is drawn from, each a
# degree and an octave from the player's own, with how often each is drawn.
HEAVY_SEED = 'heavy riff {} {}'
POWER_CHORD = 'pow'
GATE = 'gate'
MUTED_GATE = '1/2'
ACCENT_LADDER = ((HOME, 2), ((3, 0), 2), ((4, 0), 2), ((5, 0), 1), ((7, -1), 2))
FEWEST_ACCENTS = 2
MOST_ACCENTS = 4
# The degrees flattened over a scale that has them major, and the fifth flattened in passing.
FLATTENED = (3, 7)
FLAT_FIFTH = (5, 0, notation.FLAT)
# The single notes a riff ends on, which lead back to the root.
TAILS = (((4, 0), (3, 0)), ((3, 0), (7, -1)), ((5, -1), (7, -1)), ((5, 0), (4, 0), (3, 0)), ((4, 0), (3, 0), (7, -1)), ((5, 0), FLAT_FIFTH, (4, 0)))





def with_gap(*, bar, eighths):
    """Return a bar whose second half is left empty, for the voice."""
    half = eighths // 2
    kept = []
    at = 0
    for note in bar:
        if at >= half:
            break
        # A note that would ring into the gap is cut off where the gap starts.
        length = min(note.get(notation.REST, note.get(notation.STEPS)), half - at)
        kept.append(_lasting(note=note, length=length))
        at += length
    kept.append({notation.REST: eighths - at})
    return kept


def _lasting(*, note, length):
    """Return a copy of a note or a rest lasting a length."""
    lasting = dict(note)
    if notation.REST in note:
        lasting[notation.REST] = length
    else:
        lasting[notation.STEPS] = length
    return lasting








def line_of(*, riff, seed, eighths, flattened=()):
    """Return the notes of a song's riff: those written by hand, or those drawn the way the riff says."""
    if riff.get(RIFF_LINE):
        return [dict(note) for note in riff[RIFF_LINE]]
    take = riff.get(RIFF_TAKE, FIRST_TAKE)
    bars = riff.get(wizard_names.RIFF_BAR_COUNT, RIFF_BARS)
    if riff.get(wizard_names.RIFF_NOTES, SINGLE_NOTES) == SINGLE_NOTES:
        return riff_line(seed=seed, take=take, eighths=eighths, bars=bars)
    between = riff.get(wizard_names.RIFF_BETWEEN, MUTED_ROOTS)
    gap = riff.get(RIFF_UNDER_TUNE, IN_FULL) == LEAVES_A_GAP
    # Imported here, since the heavy riffs read this module's names.
    from llamatron.wizards.create_song.heavy_riffs import heavy_line
    return heavy_line(seed=seed, take=take, eighths=eighths, bars=bars, between=between, flattened=flattened, gap=gap)


def bars_of(*, line, eighths):
    """Return how many bars a riff's line lasts."""
    total = 0
    for note in line:
        total += note.get(notation.REST, note.get(notation.STEPS))
    return total // eighths


def single(line):
    """A riff's notes alone, with no chords, as a second player plays the riff under the first."""
    return [notation.without_fields(entry=note, fields=(notation.CHORD,)) for note in line]


def accent_bars(*, line, eighths):
    """Where a riff's accents fall, as a drum's bars of hits in eighths: a kick follows them."""
    hits = []
    for note in line:
        length = note.get(notation.REST, note.get(notation.STEPS))
        hits += [notation.LOUD if note.get(notation.LEVEL) == wizard_names.ACCENT else notation.NONE] + [notation.NONE] * (length - 1)
    return [hits[start:start + eighths] for start in range(0, len(hits), eighths)]



def split_bars(*, line, eighths):
    """A riff's line bar by bar, or None where a note is held over a bar line."""
    bars = [[]]
    room = eighths
    for note in line:
        length = note.get(notation.REST, note.get(notation.STEPS))
        if not room:
            bars.append([])
            room = eighths
        if length > room:
            return None
        bars[-1].append(dict(note))
        room -= length
    return bars


def is_home(chord):
    return chord.get(notation.DEGREE) == HOME[0] and not chord.get(notation.ACCIDENTAL)


def bars_played(*, chords, bars, count, stays):
    """Return which bar of a riff each bar of a section plays: the riff round and round, or, where the riff stays on the home
    chord, begun again wherever the home chord returns and None over every other chord, which is held. A riff asked to stay
    goes round and round all the same in a section where the home chord fills fewer than half the bars or never lasts the
    whole riff."""
    round_again = [bar % count for bar in range(bars)]
    if not stays:
        return round_again
    played = []
    run = 0
    for bar in range(bars):
        if is_home(chords[bar % len(chords)]):
            played.append(run % count)
            run += 1
        else:
            played.append(None)
            run = 0
    # A riff is at home only in a section that mostly is, with room to say the whole riff: elsewhere it moves with each chord.
    if _stays_at_home(played=played, count=count, bars=bars):
        return played
    return round_again


def _stays_at_home(*, played, count, bars):
    """Return whether a riff that would stay at home does: the home chord fills half the bars or more, with room to say the whole riff."""
    at_home = 0
    for bar in played:
        if bar is not None:
            at_home += 1
    if 2 * at_home < bars:
        return False
    whole_riff = list(range(count))
    for bar in range(bars):
        if played[bar:bar + count] == whole_riff:
            return True
    return False


def held_bar(*, eighths, chord):
    """Return a bar of the chord held, where a riff that stays at home gives way."""
    note = {notation.DEGREE: HOME[0], notation.STEPS: eighths}
    if chord:
        note[notation.CHORD] = POWER_CHORD
    return [note]
