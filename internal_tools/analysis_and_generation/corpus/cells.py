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

"""The cells of a band's MIDI file: which channel is the kit, the bass, the chord part and the lead, and each reduced to its
commonest bar on a grid of sixteenths or of triplets. A bar is an array, a place for each step: true where a voice hits, or
the tone the bass plays there of the chord it plays under (root, third, fifth, seventh or another note) and None where it
rests. The chord part and the lead are read by rhythm alone: the lead's pitches are never read (the user's
rule for copyrighted works), and it is left out of the chords too. Only songs in common time throughout are read."""

import collections
import statistics

import mido

BEATS_PER_BAR = 4
STRAIGHT = 16
TRIPLET = 12
GRIDS = (STRAIGHT, TRIPLET)
DRUM_CHANNEL = 9
KICKS = (35, 36)
SNARES = (38, 40)
# What keeps time: the hi-hats and the rides.
TIMEKEEPERS = (42, 44, 46, 51, 53, 59)
BASS_PROGRAMS = range(32, 40)
DEFAULT_TEMPO = 500000
MICROSECONDS_IN_A_MINUTE = 60000000
REST = None
ROOT = 'root'
THIRD = 'third'
FIFTH = 'fifth'
SEVENTH = 'seventh'
OTHER = 'other'
UNKNOWN = 'unknown'
BASS_TONES = (ROOT, THIRD, FIFTH, SEVENTH, OTHER, UNKNOWN)
KIT_VOICES = ('kick', 'snare', 'time')
MAJOR_CHORD = 'major'
MINOR_CHORD = 'minor'
# A chord of a root and a fifth with no third to speak of, a power chord, which is neither major nor minor.
OPEN_CHORD = 'open'
# A third counts when it holds this share of what the root and the fifth hold.
FEWEST_THIRD = 0.15
TONES = {0: ROOT, 3: THIRD, 4: THIRD, 7: FIFTH, 10: SEVENTH, 11: SEVENTH}
MAJOR = (0, 4, 7)
MINOR = (0, 3, 7)
PITCH_CLASSES = 12
# A chord is named for a half bar only when its three notes hold this share of everything sounding.
CLEAR_CHORD = 0.6
BASS_WEIGHT = 2.0
HALF_BAR = BEATS_PER_BAR / 2
# A channel is the chord part when this share of its notes start with two others at least.
CHORDAL = 0.5
TOGETHER = 3
FEWEST_NOTES = 24
FEWEST_BARS = 8
NOT_COMMON_TIME = 'not in common time'
NO_KIT = 'no kit'
TOO_SHORT = 'too short'
UNREADABLE = 'unreadable'


class NotRead(Exception):
    """A file the cells are not taken from, with why."""

    __slots__ = ()


def song_of(path):
    """Return a MIDI file's notes by channel as (start in beats, length in beats, pitch), each channel's program, and its tempo
    in beats a minute; a file with any time signature but four four is refused."""
    try:
        midi = mido.MidiFile(path)
    except Exception as error:
        raise NotRead(UNREADABLE) from error
    notes = collections.defaultdict(list)
    programs = {}
    sounding = {}
    tempo = None
    for track in midi.tracks:
        tick = 0
        for message in track:
            tick += message.time
            beat = tick / midi.ticks_per_beat
            if message.type == 'time_signature' and (message.numerator, message.denominator) != (BEATS_PER_BAR, 4):
                raise NotRead(NOT_COMMON_TIME)
            if message.type == 'set_tempo' and tempo is None:
                tempo = message.tempo
            elif message.type == 'program_change':
                programs.setdefault(message.channel, message.program)
            elif message.type == 'note_on' and message.velocity:
                sounding[(message.channel, message.note)] = beat
            elif message.type in ('note_off', 'note_on'):
                start = sounding.pop((message.channel, message.note), None)
                if start is not None:
                    notes[message.channel].append((start, beat - start, message.note))
    for channel in notes:
        notes[channel].sort()
    return dict(notes), programs, round(MICROSECONDS_IN_A_MINUTE / (tempo or DEFAULT_TEMPO))


def off_grid(*, starts, grid):
    """Return how far a channel's starts lie from a grid's steps, on average, in steps."""
    per_beat = grid / BEATS_PER_BAR
    return statistics.fmean(abs(start * per_beat - round(start * per_beat)) for start in starts)


def grid_of(starts):
    """Return the grid a song's starts fit best: sixteenths, or triplets for a shuffle or a swing."""
    return min(GRIDS, key=lambda grid: off_grid(starts=starts, grid=grid))


def place_of(*, start, grid):
    """Return the bar a note starts in and its step in the bar."""
    step = round(start * grid / BEATS_PER_BAR)
    return step // grid, step % grid


def mask_of(*, steps, grid):
    """Return a bar as an array, true at each step hit."""
    return tuple(step in steps for step in range(grid))


def commonest(bars):
    """Return the commonest bar of a part and the share of its bars that are that bar, or nothing where it plays none."""
    if not bars:
        return None, 0.0
    cell, count = collections.Counter(bars).most_common(1)[0]
    return cell, round(count / len(bars), 2)


def kit_bars(*, notes, grid):
    """Return a kit's bars, each an array for its kick, its snare and its timekeeper, true at the steps hit."""
    bars = collections.defaultdict(lambda: (set(), set(), set()))
    for start, _, pitch in notes:
        bar, step = place_of(start=start, grid=grid)
        for voice, pitches in enumerate((KICKS, SNARES, TIMEKEEPERS)):
            if pitch in pitches:
                bars[bar][voice].add(step)
    return [tuple(mask_of(steps=voice, grid=grid) for voice in bars[bar]) for bar in sorted(bars) if any(bars[bar])]


def polyphony_of(notes):
    """Return the share of a channel's notes that start together with two others at least."""
    together = collections.Counter(round(start * STRAIGHT / BEATS_PER_BAR) for start, _, _ in notes)
    return sum(count for count in together.values() if count >= TOGETHER) / len(notes)


def roles_of(*, notes, programs):
    """Return the channels of the bass, the chord part and the lead, each None where the song has none: the bass by its
    program, the chord part the busiest channel that plays chords, the lead the busiest of the rest."""
    pitched = {channel: found for channel, found in notes.items() if channel != DRUM_CHANNEL and len(found) >= FEWEST_NOTES}
    basses = [channel for channel in pitched if programs.get(channel) in BASS_PROGRAMS]
    bass = max(basses, key=lambda channel: len(pitched[channel]), default=None)
    rest = {channel: found for channel, found in pitched.items() if channel != bass}
    chordal = [channel for channel in rest if polyphony_of(rest[channel]) >= CHORDAL]
    chords = max(chordal, key=lambda channel: len(rest[channel]), default=None)
    lines = [channel for channel in rest if channel not in chordal and programs.get(channel) not in BASS_PROGRAMS]
    lead = max(lines, key=lambda channel: len(rest[channel]), default=None)
    return bass, chords, lead


def chords_of(*, notes, bass, lead):
    """Return the chord of each half bar as (root, major, minor or open), from every pitched channel but the lead, the bass
    counted double; a half bar whose notes name no chord clearly has none."""
    weights = collections.defaultdict(lambda: [0.0] * PITCH_CLASSES)
    for channel, found in notes.items():
        if channel in (DRUM_CHANNEL, lead):
            continue
        weight = BASS_WEIGHT if channel == bass else 1.0
        for start, length, pitch in found:
            half = int(start // HALF_BAR)
            while half * HALF_BAR < start + length:
                overlap = min(start + length, (half + 1) * HALF_BAR) - max(start, half * HALF_BAR)
                weights[half][pitch % PITCH_CLASSES] += weight * overlap
                half += 1
    return {half: chord for half, chord in ((half, chord_of(weight)) for half, weight in weights.items()) if chord is not None}


def chord_of(weights):
    total = sum(weights)
    if not total:
        return None
    scored = [(sum(weights[(root + interval) % PITCH_CLASSES] for interval in shape) + weights[root] / 2, root, shape is MINOR)
              for root in range(PITCH_CLASSES) for shape in (MAJOR, MINOR)]
    score, root, minor = max(scored)
    if score - weights[root] / 2 < CLEAR_CHORD * total:
        return None
    third = weights[(root + (MINOR if minor else MAJOR)[1]) % PITCH_CLASSES]
    if third < FEWEST_THIRD * (weights[root] + weights[(root + MAJOR[2]) % PITCH_CLASSES]):
        return root, OPEN_CHORD
    return root, MINOR_CHORD if minor else MAJOR_CHORD


def tone_of(*, pitch, chord):
    """Return what a bass note is of the chord it plays under: its root, third, fifth, seventh or another note."""
    if chord is None:
        return UNKNOWN
    return TONES.get((pitch - chord[0]) % PITCH_CLASSES, OTHER)


def bass_bars(*, notes, chords, grid):
    """Return a bass's bars, each an array of the tone that starts at each step or None, and for each tone an array of how
    often it started at each step."""
    bars = collections.defaultdict(lambda: [REST] * grid)
    tally = {tone: [0] * grid for tone in BASS_TONES}
    for start, _, pitch in notes:
        bar, step = place_of(start=start, grid=grid)
        tone = tone_of(pitch=pitch, chord=chords.get(int(round(start * grid / BEATS_PER_BAR) * BEATS_PER_BAR / grid // HALF_BAR)))
        bars[bar][step] = tone
        tally[tone][step] += 1
    return [tuple(bars[bar]) for bar in sorted(bars)], tally


def rhythm_bars(*, notes, grid, fewest=1):
    """Return a part's bars by rhythm alone, each an array true at the steps where notes start, as many at least as asked."""
    bars = collections.defaultdict(collections.Counter)
    for start, _, _ in notes:
        bar, step = place_of(start=start, grid=grid)
        bars[bar][step] += 1
    found = {bar: {step for step, count in steps.items() if count >= fewest} for bar, steps in bars.items()}
    return [mask_of(steps=found[bar], grid=grid) for bar in sorted(found) if found[bar]]


def cells_of(path):
    """Return a file's cells as plain data: its tempo and grid, the kit's, bass's and chord part's commonest bars with the share
    of bars each holds, the bass's tones by step, the lead's rhythm, each part's program, and how many bars the song has."""
    notes, programs, tempo = song_of(path)
    kit = notes.get(DRUM_CHANNEL, [])
    if len(kit) < FEWEST_NOTES:
        raise NotRead(NO_KIT)
    bars = int(max(start for found in notes.values() for start, _, _ in found) // BEATS_PER_BAR) + 1
    if bars < FEWEST_BARS:
        raise NotRead(TOO_SHORT)
    grid = grid_of([start for start, _, _ in kit])
    bass, chord_part, lead = roles_of(notes=notes, programs=programs)
    result = {'tempo': tempo, 'grid': grid, 'bars': bars}
    result['kit'], result['kit_share'] = commonest(kit_bars(notes=kit, grid=grid))
    for voice, name in enumerate(KIT_VOICES):
        result[name], _ = commonest([bar[voice] for bar in kit_bars(notes=kit, grid=grid)])
    if bass is not None:
        chords = chords_of(notes=notes, bass=bass, lead=lead)
        found, tally = bass_bars(notes=notes[bass], chords=chords, grid=grid)
        result['bass'], result['bass_share'] = commonest(found)
        result['bass_rhythm'], _ = commonest([tuple(step is not REST for step in bar) for bar in found])
        result['bass_tones'] = tally
        result['bass_program'] = programs.get(bass)
        result['bass_bars'] = round(len(found) / bars, 2)
        kinds = collections.Counter(kind for _, kind in chords.values())
        thirds = kinds[MAJOR_CHORD] + kinds[MINOR_CHORD]
        result['minor'] = round(kinds[MINOR_CHORD] / thirds, 2) if thirds else None
        result['open'] = round(kinds[OPEN_CHORD] / len(chords), 2) if chords else None
    if chord_part is not None:
        found = rhythm_bars(notes=notes[chord_part], grid=grid, fewest=2)
        result['chords'], result['chords_share'] = commonest(found)
        result['chords_program'] = programs.get(chord_part, 0)
        result['chords_bars'] = round(len(found) / bars, 2)
    if lead is not None:
        found = rhythm_bars(notes=notes[lead], grid=grid)
        result['lead_program'] = programs.get(lead, 0)
        result['lead_bars'] = round(len(found) / bars, 2)
        result['lead_starts'] = round(len(notes[lead]) / max(len(found), 1), 1)
        result['lead_length'] = round(statistics.median(length for _, length, _ in notes[lead]), 2)
    result['programs'] = sorted({programs.get(channel, 0) for channel in notes if channel != DRUM_CHANNEL})
    return result
