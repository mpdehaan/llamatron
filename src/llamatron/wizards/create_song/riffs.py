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

from llamatron.wizards.create_song import melody, notation, wizard_names

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
    degree, octave = place
    return {notation.DEGREE: degree, notation.STEPS: steps, **({notation.OCTAVE: octave} if octave else {})}


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


def riff_note(*, place, steps, flattened, **more):
    """A note of a heavy riff at a place of the ladder, its third and seventh flattened where the scale has them major."""
    degree, octave, *mark = place
    note = {notation.DEGREE: degree, notation.STEPS: steps, **({notation.OCTAVE: octave} if octave else {}), **more}
    if mark or degree in flattened:
        note[notation.ACCIDENTAL] = notation.FLAT
    return note


def is_root(note):
    return note.get(notation.DEGREE) == HOME[0] and not note.get(notation.OCTAVE) and notation.ACCIDENTAL not in note


def heavy_bar(*, accents, eighths, between, flattened, tail):
    """One bar of a heavy riff: a chord at each accent, lasting to the next place where it can, the root short and quiet
    or a rest at every other place, and the tail's single notes in the bar's last places."""
    bar = []
    body = eighths - len(tail)
    at = 0
    while at < body:
        if at in accents:
            # An accent off the beat rings on through the beat after it, where nothing else starts there.
            steps = 2 if at % 2 and at + 1 < body and at + 1 not in accents else 1
            bar.append(riff_note(place=accents[at], steps=steps, flattened=flattened, **{notation.CHORD: POWER_CHORD, notation.LEVEL: wizard_names.ACCENT}))
            at += steps
        elif between == MUTED_ROOTS:
            bar.append(riff_note(place=HOME, steps=1, flattened=flattened, **{GATE: MUTED_GATE, notation.LEVEL: wizard_names.GHOST}))
            at += 1
        else:
            if bar and notation.REST in bar[-1]:
                bar[-1] = {notation.REST: bar[-1][notation.REST] + 1}
            else:
                bar.append({notation.REST: 1})
            at += 1
    return bar + [riff_note(place=place, steps=1, flattened=flattened) for place in tail]


def with_gap(*, bar, eighths):
    """A bar whose second half is left empty, for the voice."""
    kept = []
    at = 0
    for note in bar:
        length = note.get(notation.REST, note.get(notation.STEPS))
        if at >= eighths // 2:
            break
        # A note that would ring into the gap is cut off where the gap starts.
        length = min(length, eighths // 2 - at)
        kept.append({**note, **({notation.REST: length} if notation.REST in note else {notation.STEPS: length})})
        at += length
    return kept + [{notation.REST: eighths - at}]


def heavy_line(*, seed, take, eighths, bars=RIFF_BARS, between=MUTED_ROOTS, flattened=(), gap=False):
    """A song's heavy riff as one line, drawn from the song's seed and the riff's take: the bars alike but for the tail the
    last ends on, and, where a gap is asked of a riff of two bars, the first bar's second half left empty."""
    dice = random.Random(HEAVY_SEED.format(seed, take))
    tail = dice.choice(TAILS)
    # The accents fall in the same places of every bar; the last bar's give way to the tail.
    offbeats = [place for place in range(1, eighths) if place % 2]
    ladder = [place for place, share in ACCENT_LADDER for _ in range(share)]

    def made(accents):
        last = heavy_bar(accents=accents, eighths=eighths, between=between, flattened=flattened, tail=tail)
        if bars == 1:
            return last
        first = heavy_bar(accents=accents, eighths=eighths, between=between, flattened=flattened, tail=())
        return (with_gap(bar=first, eighths=eighths) if gap else first) + last
    # The accents that are left once the last bar's tail, and the gap, have taken their places.
    kept = [place for place in offbeats if place < (eighths // 2 if gap and bars > 1 else eighths - len(tail))]
    for _ in range(TRIES):
        count = dice.randint(min(FEWEST_ACCENTS, len(offbeats)), min(MOST_ACCENTS, len(offbeats)))
        accents = {0: HOME, **{place: dice.choice(ladder) for place in sorted(dice.sample(offbeats, count))}}
        line = made(accents)
        sounding = [note for note in line if notation.REST not in note]
        if any(place in accents for place in kept) and 2 * sum(is_root(note) for note in sounding) >= len(sounding):
            return line
    # An accent off the beat that is sure to be heard, and every accent on the root, which half the notes or more then are.
    return made({place: HOME for place in (0, kept[0], *accents)})


def line_of(*, riff, seed, eighths, flattened=()):
    """The notes of a song's riff: those written by hand, or those drawn the way the riff says."""
    if riff.get(RIFF_LINE):
        return [dict(note) for note in riff[RIFF_LINE]]
    take = riff.get(RIFF_TAKE, FIRST_TAKE)
    if riff.get(wizard_names.RIFF_NOTES, SINGLE_NOTES) == SINGLE_NOTES:
        return riff_line(seed=seed, take=take, eighths=eighths, bars=riff.get(wizard_names.RIFF_BAR_COUNT, RIFF_BARS))
    return heavy_line(seed=seed, take=take, eighths=eighths, bars=riff.get(wizard_names.RIFF_BAR_COUNT, RIFF_BARS), between=riff.get(wizard_names.RIFF_BETWEEN, MUTED_ROOTS),
                      flattened=flattened, gap=riff.get(RIFF_UNDER_TUNE, IN_FULL) == LEAVES_A_GAP)


def bars_of(*, line, eighths):
    """How many bars a riff's line lasts."""
    return sum(note.get(notation.REST, note.get(notation.STEPS)) for note in line) // eighths


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


def flattened_in(scale_type):
    """The degrees a heavy riff flattens over a scale: the third and the seventh where the scale has them major."""
    steps = melody.HALF_STEPS.get(scale_type, melody.HALF_STEPS[melody.MAJOR])
    return tuple(degree for degree in FLATTENED if steps[degree - 1] == melody.HALF_STEPS[melody.MAJOR][degree - 1])


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
    """Which bar of a riff each bar of a section plays: the riff round and round, or, where the riff stays on the home
    chord, begun again wherever the home chord returns and None over every other chord, which is held. A riff asked to stay
    goes round and round all the same in a section where the home chord fills fewer than half the bars or never lasts the
    whole riff."""
    round_again = [bar % count for bar in range(bars)]
    if not stays:
        return round_again
    played = []
    run = 0
    for bar in range(bars):
        home = is_home(chords[bar % len(chords)])
        played.append(run % count if home else None)
        run = run + 1 if home else 0
    # A riff is at home only in a section that mostly is, with room to say the whole riff: elsewhere it moves with each chord.
    whole = any(played[bar:bar + count] == list(range(count)) for bar in range(bars))
    return played if whole and 2 * sum(bar is not None for bar in played) >= bars else round_again


def held_bar(*, eighths, chord):
    """A bar of the chord held, where a riff that stays at home gives way."""
    return [{notation.DEGREE: HOME[0], notation.STEPS: eighths, **({notation.CHORD: POWER_CHORD} if chord else {})}]
