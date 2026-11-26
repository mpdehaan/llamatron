# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Guitarify generator: a clip's chords and notes played as a guitar plays them.

It has two halves, each of which can be off. Shape is the fretting hand: a chord is voiced again
as a hand can hold it, one note a string, on the strings of a tuning, within a few frets of a
position, above a capo; a single note stays, or becomes a power chord on the low strings, or the
chord its place in the scale builds. Strokes is the other hand: a bar of strokes, one a cell,
that follows the song's bars, played on whatever sounds at each cell. A stroke is nothing, a
strum down or up, a muted strum, the bass string, the alternate bass, or one string counted from
the highest. A strum's strings start a few milliseconds apart, fading, each gap a little loose,
and with Let ring a string sounds until it is struck again or its chord ends.

Everything is a sound of model/values/sound.py: a struck string is a held note, which sounds for its
own length while the next position starts when the next string does, so the strings of a strum
and the notes of a picked chord overlap as they do on a guitar.
"""

from fractions import Fraction
import functools

from llamatron.engine.generators.base import ClipGenerator
from llamatron.engine.parts.chords_on_notes import triad_above
from llamatron.math.length import Length
from llamatron.math.random_source import random_source
from llamatron.math.rational import Rational
from llamatron.model.schema.file_format import Approach, ChordColor, SingleNotes, Stroke, Tuning
from llamatron.model.values import midi as midi_numbers, sound as sound_values
from llamatron.model.values.sound import Sound
from llamatron.music_theory.fundamentals import intervals


# Each tuning's open strings as MIDI numbers, the lowest string first.
OPEN_STRINGS = {
    Tuning.STANDARD: (40, 45, 50, 55, 59, 64),
    Tuning.DROP_D: (38, 45, 50, 55, 59, 64),
    Tuning.OPEN_G: (38, 43, 50, 55, 59, 62),
    Tuning.OPEN_D: (38, 45, 50, 54, 57, 62),
    Tuning.DADGAD: (38, 45, 50, 55, 57, 62),
}
# The string each single-string stroke picks, counted from the highest.
STRING_OF = {Stroke.STRING_1: 1, Stroke.STRING_2: 2, Stroke.STRING_3: 3, Stroke.STRING_4: 4}

# A hand reaches this many frets from its position, the position's fret among them.
REACH = 4
OPEN_POSITION = 0
# What a string a shape leaves unplayed is counted as when two shapes of one cost are compared: below every fret.
UNPLAYED_STRING = -1
# A power chord: the root, the fifth above and the octave.
POWER_CHORD = (0, 7, 12)
FIFTH = 7
# The steps of a scale from a chord's root to its third and its fifth.
# How a voicing is scored, lower being better: each note of the chord no string plays (the root costing most and the fifth least,
# since a hand short of strings leaves the fifth out first), the bass not being the root, a silent string between two that sound,
# each silent string, and each fret of distance from the position, the least of all.
MISSING_NOTE_COST = 1000
MISSING_ROOT_COST = 1500
MISSING_FIFTH_COST = 600
WRONG_BASS_COST = 400
INSIDE_MUTE_COST = 300
MUTED_STRING_COST = 40
FRET_COST = 1
# A muted stroke sounds for this share of its cell, at this share of its loudness; where a bar has accents, a stroke without one is played at this share.
MUTE_LENGTH = Rational(1, 4)
MUTE_VELOCITY = Rational(1, 2)
UNACCENTED_VELOCITY = Rational(4, 5)
# A stab and a muted bass note sound for this share of their cell, whatever Let ring says: the silence after is the point.
SHORT_LENGTH = Rational(1, 2)
# A muted bass note without an accent plays at this share: the body of a riff, louder than a scratch.
MUTED_BASS_VELOCITY = Rational(4, 5)
# A squeal sounds this far above the chord's lowest note.
SQUEAL_ABOVE = 2 * intervals.HALF_STEPS_PER_OCTAVE
OCTAVE_ABOVE = (intervals.HALF_STEPS_PER_OCTAVE,)
# A double stop adds the note this far below.
FOURTH_BELOW = 5
# A chord's third is this far above its lowest note, minor or major.
THIRDS = (3, 4)
# What each color puts in the third's place, in half steps above the lowest note, and the ninth a color adds.
THIRD_MOVED_TO = {ChordColor.SUS_2: 2, ChordColor.SUS_4: 5}
NINTH_ABOVE = 14
# A chord approached from a fret away is played there for this long, or half its length where it is shorter.
APPROACH_LENGTH = Rational(1, 16)
APPROACH_FROM = {Approach.FROM_BELOW: -1, Approach.FROM_ABOVE: 1}
# The strokes that stop short of their cell, each with the share of the cell it sounds for.
SHORT_STROKES = {Stroke.MUTE: MUTE_LENGTH, Stroke.STAB: SHORT_LENGTH, Stroke.MUTED_BASS: SHORT_LENGTH, Stroke.SQUEAL: SHORT_LENGTH}
# A velocity a note has none of its own is taken as, to make it softer from.
FULL_VELOCITY = 127
LOWEST_VELOCITY = 1
PERCENT = 100
# A gap of so many milliseconds is that share of a whole note, which lasts four beats.
MILLISECONDS_PER_WHOLE_NOTE_AT_ONE_BEAT_A_MINUTE = 240000
TEMPO_DENOMINATOR = 1000
# A strum takes at most this share of the time until the next stroke, however wide its spread.
WIDEST_STRUM = Rational(1, 2)
NO_TIME = Rational(0)
# A strum's strings start on a grid this fine, in ticks to a whole note: far finer than an ear tells, and coarse enough that every length stays an exact fraction.
STRUM_TICKS = 19200
# What an event of the strokes is: notes struck at a time, or a position passed on as it came.
STRUCK = 0
PASSED_ON = 1


class Guitarify(ClipGenerator):
    """Plays a clip's chords and notes as a guitar does: shaped onto strings, then struck by a bar of strokes."""

    __slots__ = (
        '_shape', '_open', '_position', '_single_notes', '_color', '_approach', '_strokes', '_bar', '_accents', '_cell', '_let_ring', '_gap', '_fade', '_loose_timing', '_upstroke',
        '_seed', '_offset',
    )

    def __init__(self, *, shape, tuning, position, capo, strings, single_notes, strokes, bar, accents, cell, let_ring, spread, fade, loose_timing, upstroke,
                 tempo, color=ChordColor.AS_WRITTEN, approach=Approach.OFF, seed=None, continuation=None):
        """shape and strokes switch the halves on; tuning, position, capo, strings and single_notes are Shape's; bar, accents, cell (a length in whole notes), let_ring, spread (milliseconds between strings), fade and loose_timing (percentages) and upstroke (how many top strings an upstroke catches, or None for all) are the strokes'; tempo is the scene's, which turns the spread into time."""
        self._shape = shape
        self._open = tuple(pitch + capo for pitch in OPEN_STRINGS[tuning][-strings:])
        self._position = position
        self._single_notes = single_notes
        # How every chord is voiced, and how the strokes reach a new chord.
        self._color = color
        self._approach = approach
        self._strokes = strokes and bool(bar)
        self._bar = tuple(bar)
        self._accents = tuple(accents) + (False,) * (len(self._bar) - len(accents))
        self._cell = Rational(cell)
        self._let_ring = let_ring
        gap = Fraction(spread) * Fraction(tempo).limit_denominator(TEMPO_DENOMINATOR) / MILLISECONDS_PER_WHOLE_NOTE_AT_ONE_BEAT_A_MINUTE
        self._gap = Rational(gap.numerator, gap.denominator)
        self._fade = fade
        self._loose_timing = loose_timing
        self._upstroke = upstroke
        self._seed = seed
        # How far into the song's bars the clip starts, so that the bar of strokes follows them.
        self._offset = NO_TIME
        if continuation is not None:
            self._offset = Rational(continuation.offset)

    def _generate(self, clip):
        scale = clip.get_scale()
        sounds = [self._shaped_position(sound=sound, scale=scale) for sound in clip.resolved_sounds()]
        if self._strokes:
            sounds = self._struck(sounds)
        return sounds, clip.get_length()

    # Shape: the fretting hand.

    def _shaped_position(self, *, sound, scale):
        """Return one position with what it plays settled into notes and, with Shape on, shaped; a rest and anything that can't be settled as they are."""
        kind = sound[sound_values.KIND]
        if kind == sound_values.HELD:
            return (sound_values.HELD, sound[sound_values.LENGTH], self._shaped(sound=sound[sound_values.HELD_SOUND], scale=scale))
        if kind in (sound_values.NOTE, sound_values.CHORD, sound_values.DEGREE):
            return self._shaped(sound=sound, scale=scale)
        return sound

    def _shaped(self, *, sound, scale):
        """Return a note, chord or degree as Shape plays it."""
        if sound[sound_values.KIND] == sound_values.DEGREE:
            if scale is None:
                return sound
            sound = Sound.settled(sound, scale)
        if not self._shape:
            return sound
        if sound[sound_values.KIND] == sound_values.CHORD and len(sound[sound_values.NOTES]) > 1:
            return self._voiced(sound)
        note = sound
        if sound[sound_values.KIND] == sound_values.CHORD:
            note = sound[sound_values.NOTES][0]
        if self._single_notes == SingleNotes.POWER_CHORD:
            return self._power_chord(note)
        if self._single_notes == SingleNotes.SCALE_CHORD and scale is not None:
            above = triad_above(note=note, scale=scale)
            if above:
                return self._voiced(Sound.chord_above(note, above))
        if self._single_notes == SingleNotes.OCTAVE and note[sound_values.MIDI] + intervals.HALF_STEPS_PER_OCTAVE <= midi_numbers.MAX_MIDI_NUMBER:
            return Sound.chord_above(note, OCTAVE_ABOVE)
        if self._single_notes == SingleNotes.THIRD_ABOVE and scale is not None:
            above = triad_above(note=note, scale=scale)
            if above and note[sound_values.MIDI] + above[0] <= midi_numbers.MAX_MIDI_NUMBER:
                return Sound.chord_above(note, above[:1])
        if self._single_notes == SingleNotes.DOUBLE_STOP and note[sound_values.MIDI] >= FOURTH_BELOW:
            return Sound.chord([_moved(note=note, midi=note[sound_values.MIDI] - FOURTH_BELOW), note])
        return sound

    def _colored(self, notes):
        """Return a chord's notes, lowest first, as the color voices them: a ninth added, or the third moved or left out; a chord with no third keeps its notes."""
        if self._color == ChordColor.AS_WRITTEN:
            return notes
        root = notes[0]
        if self._color == ChordColor.ADD_9:
            ninth = root[sound_values.MIDI] + NINTH_ABOVE
            if ninth > midi_numbers.MAX_MIDI_NUMBER:
                return notes
            return [*notes, _moved(note=root, midi=ninth)]
        colored = []
        for note in notes:
            above = (note[sound_values.MIDI] - root[sound_values.MIDI]) % intervals.HALF_STEPS_PER_OCTAVE
            if above not in THIRDS:
                colored.append(note)
            elif self._color in THIRD_MOVED_TO:
                colored.append(_moved(note=note, midi=note[sound_values.MIDI] - above + THIRD_MOVED_TO[self._color]))
        return colored

    def _power_chord(self, note):
        """Return a single note as a power chord on the low strings: its root on the lowest string that can play it, the fifth and the octave above."""
        lowest = self._open[0]
        if self._position != OPEN_POSITION:
            lowest += self._position
        root = lowest + (note[sound_values.MIDI] - lowest) % intervals.HALF_STEPS_PER_OCTAVE
        notes = []
        for above in POWER_CHORD:
            if root + above <= midi_numbers.MAX_MIDI_NUMBER:
                notes.append(_moved(note=note, midi=root + above))
        return Sound.chord(notes)

    def _voiced(self, chord):
        """Return a chord as a hand holds it on the strings: its root first, then the rest from the lowest string up, every note as long and as loud as the chord's own."""
        notes = self._colored(sorted(chord[sound_values.NOTES], key=_pitch_of))
        classes = tuple(sorted({note[sound_values.MIDI] % intervals.HALF_STEPS_PER_OCTAVE for note in notes}))
        root = notes[0][sound_values.MIDI] % intervals.HALF_STEPS_PER_OCTAVE
        pitches = best_voicing(strings=self._open, position=self._position, classes=classes, root=root)
        if not pitches:
            return chord
        by_class = {note[sound_values.MIDI] % intervals.HALF_STEPS_PER_OCTAVE: note for note in reversed(notes)}
        return Sound.chord([_moved(note=by_class[pitch % intervals.HALF_STEPS_PER_OCTAVE], midi=pitch) for pitch in pitches])

    # Strokes: the other hand.

    def _struck(self, sounds):
        """Return the positions the bar of strokes makes of the shaped ones."""
        events = []
        time = NO_TIME
        before = None
        for place, sound in enumerate(sounds):
            length = Length.rational(sound[sound_values.LENGTH])
            played = sound
            if sound[sound_values.KIND] == sound_values.HELD:
                played = sound[sound_values.HELD_SOUND]
            if played[sound_values.KIND] in (sound_values.NOTE, sound_values.CHORD):
                end = time + self._sounding_length(sound=sound, played=played, length=length)
                strokes = self._strokes_on(played=played, start=time, end=end, place=place)
                pitches = _pitches_of(played)
                if self._approach != Approach.OFF and before is not None and pitches != before:
                    strokes = self._approached(played=played, strokes=strokes, start=time, end=end)
                before = pitches
                events.extend(strokes)
            elif played[sound_values.KIND] != sound_values.REST:
                events.append((time, PASSED_ON, sound, time + length))
            time += length
        return _positions(events=events, total=time)

    def _approached(self, *, played, strokes, start, end):
        """Return a new chord's strokes with the chord first played a fret away: every note of it for a moment, and whatever was struck in that moment struck after it."""
        moment = min(APPROACH_LENGTH, (end - start) / 2)
        lands = start + moment
        from_fret = APPROACH_FROM[self._approach]
        strings = [played]
        if played[sound_values.KIND] == sound_values.CHORD:
            strings = played[sound_values.NOTES]
        if not _all_in_range(strings=strings, from_fret=from_fret):
            return strokes
        events = [(start, STRUCK, Sound.with_length(_moved(note=note, midi=note[sound_values.MIDI] + from_fret), Length.of(moment)), lands) for note in strings]
        for begins, kind, note, stops in strokes:
            if begins < lands:
                begins = begins + moment
                if stops <= begins:
                    continue
                note = Sound.with_length(note, Length.of(stops - begins))
            events.append((begins, kind, note, stops))
        return events

    def _sounding_length(self, *, sound, played, length):
        """Return how long what a position plays sounds: its own length when it is held past its place, and its place's otherwise."""
        if sound[sound_values.KIND] == sound_values.HELD and played[sound_values.LENGTH] is not None:
            return Length.rational(played[sound_values.LENGTH])
        return length

    def _strokes_on(self, *, played, start, end, place):
        """Return the events of the strokes that fall while one note or chord sounds, from start to end."""
        strings = [played]
        if played[sound_values.KIND] == sound_values.CHORD:
            strings = sorted(played[sound_values.NOTES], key=_pitch_of)
        struck = []
        for time, cell in self._cells(start=start, end=end):
            stroke = self._bar[cell]
            if stroke != Stroke.NOTHING:
                struck.append((time, stroke, self._accents[cell], self._strings_of(stroke=stroke, strings=strings)))
        any_accent = any(self._accents)
        events = []
        for index, (time, stroke, accent, chosen) in enumerate(struck):
            following = end
            if index + 1 < len(struck):
                following = struck[index + 1][0]
            delays = self._delays(count=len(chosen), room=following - time, seed_place=place * len(self._bar) + index)
            for string, (note, delay) in enumerate(zip(chosen, delays)):
                stops = self._stops(note=note, index=index, struck=struck, end=end, following=following)
                if stroke in SHORT_STROKES:
                    stops = min(stops, time + self._cell * SHORT_STROKES[stroke])
                begins = time + delay
                if stops <= begins:
                    continue
                accented = None
                if any_accent:
                    accented = accent
                share = stroke_share(stroke=stroke, accented=accented, fade=self._fade, string=string, count=len(chosen))
                events.append((begins, STRUCK, _softened(note=Sound.with_length(note, Length.of(stops - begins)), share=share), stops))
        return events

    def _cells(self, *, start, end):
        """Return (time, cell of the bar) for where a sound starts and for every cell that starts while it sounds; the bar follows the song's bars."""
        whole = self._offset + start
        number = whole // self._cell
        found = []
        if number * self._cell == whole:
            time = start
        else:
            # A sound that starts inside a cell is struck there as that cell's stroke, and the cells after it follow.
            found.append((start, int(number) % len(self._bar)))
            number += 1
            time = number * self._cell - self._offset
        while time < end:
            found.append((time, int(number) % len(self._bar)))
            number += 1
            time += self._cell
        return found

    def _strings_of(self, *, stroke, strings):
        """Return the notes a stroke strikes, in the order it strikes them, from a chord's notes given lowest first."""
        if stroke in (Stroke.DOWN, Stroke.MUTE, Stroke.STAB):
            return list(strings)
        if stroke == Stroke.UP:
            top = strings
            if self._upstroke is not None:
                top = strings[-self._upstroke:]
            return list(reversed(top))
        if stroke in (Stroke.BASS, Stroke.MUTED_BASS):
            return strings[:1]
        if stroke == Stroke.SQUEAL:
            high = strings[0][sound_values.MIDI] + SQUEAL_ABOVE
            if high > midi_numbers.MAX_MIDI_NUMBER:
                return strings[-1:]
            return [_moved(note=strings[0], midi=high)]
        if stroke == Stroke.ALT_BASS:
            fifth = (strings[0][sound_values.MIDI] + FIFTH) % intervals.HALF_STEPS_PER_OCTAVE
            fifths = [note for note in strings[1:] if note[sound_values.MIDI] % intervals.HALF_STEPS_PER_OCTAVE == fifth]
            return fifths[:1] or strings[1:2] or strings[:1]
        # A string the chord lacks is the nearest it has.
        return [strings[max(len(strings) - STRING_OF[stroke], 0)]]

    def _delays(self, *, count, room, seed_place):
        """Return how much later than the stroke each of its strings starts: nothing for the first, and a gap more for each after, loose by the seed, all within the room the stroke has."""
        delays = [NO_TIME]
        if count < 2 or self._gap <= NO_TIME:
            return delays * count
        seed = None
        if self._seed is not None:
            seed = self._seed + seed_place
        chooser = random_source(seed)
        for _ in range(count - 1):
            loose = NO_TIME
            if self._loose_timing:
                loose = Rational(round(chooser.uniform(-self._loose_timing, self._loose_timing)), PERCENT)
            delays.append(delays[-1] + self._gap * (1 + loose))
        widest = room * WIDEST_STRUM
        if delays[-1] > widest:
            delays = [delay * widest / delays[-1] for delay in delays]
        return [_on_the_grid(delay) for delay in delays]

    def _stops(self, *, note, index, struck, end, following):
        """Return when a struck string stops sounding: with Let ring, when a later stroke strikes the same pitch or the chord ends, and otherwise at the next stroke."""
        if not self._let_ring:
            return following
        for time, _, _, chosen in struck[index + 1:]:
            if _holds_pitch(notes=chosen, pitch=note[sound_values.MIDI]):
                return time
        return end


def _on_the_grid(time):
    """Return a time moved to the nearest tick of the grid a strum's strings start on, so that every length stays exact."""
    return Rational(round(time * STRUM_TICKS), STRUM_TICKS)


def _pitch_of(note):
    return note[sound_values.MIDI]


def _pitches_of(played):
    """Return the pitches a note or chord plays, to tell one chord from the next."""
    if played[sound_values.KIND] != sound_values.CHORD:
        return (played[sound_values.MIDI],)
    pitches = [note[sound_values.MIDI] for note in played[sound_values.NOTES]]
    return tuple(sorted(pitches))


def _moved(*, note, midi):
    """Return a note at another pitch, spelled as Sound.half_step spells it, everything else kept."""
    return Sound.half_step(note, midi - note[sound_values.MIDI])


def _softened(*, note, share):
    """Return a note at a share of its loudness, never silent; a note with no velocity of its own is taken as full."""
    if share == 1:
        return note
    velocity = note[sound_values.VELOCITY]
    if velocity is None:
        velocity = FULL_VELOCITY
    softer = max(round(velocity * share), LOWEST_VELOCITY)
    return (sound_values.NOTE, note[sound_values.LENGTH], note[sound_values.MIDI], softer, note[sound_values.GLIDE], note[sound_values.NAME])


@functools.cache
def best_voicing(*, strings, position, classes, root):
    """Return the pitches of the best way to hold a chord, the lowest string first, or an empty tuple when no string can play any of
    it: strings are the open strings' pitches, position the hand's, classes the chord's pitch classes and root its root's. Remembered
    for the run, since it follows from those alone and every clip of a song holds the same few chords, where each clip worked them
    out again."""
    choices = []
    for open_pitch in strings:
        frets = [fret for fret in _frets(position) if (open_pitch + fret) % intervals.HALF_STEPS_PER_OCTAVE in classes and open_pitch + fret <= midi_numbers.MAX_MIDI_NUMBER]
        choices.append([None, *frets])
    best = None
    for held in _every_way(choices):
        if all(fret is None for fret in held):
            continue
        score = _cost(strings=strings, held=held, classes=classes, root=root)
        if best is None or score < best[0]:
            best = (score, held)
    if best is None:
        return ()
    pitches = []
    for open_pitch, fret in zip(strings, best[1]):
        if fret is not None:
            pitches.append(open_pitch + fret)
    return tuple(pitches)


@functools.cache
def stroke_share(*, stroke, accented, fade, string, count):
    """Return the share of its velocity a note of a stroke keeps: a mute and an unaccented muted bass quieter, an unaccented stroke
    quieter in a bar with accents, accented being None in a bar with none, and each string after the first faded by a further
    share of fade when the stroke strikes count strings. Remembered for the run, since a bar's few strokes come round on every
    chord, where every note of every stroke worked its share out again."""
    share = Rational(1)
    if stroke == Stroke.MUTE:
        share = share * MUTE_VELOCITY
    if stroke == Stroke.MUTED_BASS:
        if not accented:
            share = share * MUTED_BASS_VELOCITY
    elif accented is False and stroke != Stroke.SQUEAL:
        share = share * UNACCENTED_VELOCITY
    if fade and count > 1:
        share = share * (1 - Rational(fade * string, PERCENT * (count - 1)))
    return share


def _frets(position):
    """Return the frets a hand at a position reaches, the open string among them in the open position."""
    if position == OPEN_POSITION:
        return range(REACH)
    return range(position, position + REACH)


def _cost(*, strings, held, classes, root):
    """Return how poor a way of holding a chord is, lower being better, with the way itself last so that two equal ways always choose the same."""
    sounding = [place for place, fret in enumerate(held) if fret is not None]
    pitches = [strings[place] + held[place] for place in sounding]
    played = {pitch % intervals.HALF_STEPS_PER_OCTAVE for pitch in pitches}
    cost = sum(_missing_cost(missing=missing, root=root) for missing in set(classes) - played)
    if pitches[0] % intervals.HALF_STEPS_PER_OCTAVE != root:
        cost += WRONG_BASS_COST
    cost += INSIDE_MUTE_COST * (sounding[-1] - sounding[0] + 1 - len(sounding))
    cost += MUTED_STRING_COST * (len(held) - len(sounding))
    cost += FRET_COST * sum(held[place] for place in sounding)
    frets = []
    for fret in held:
        if fret is None:
            fret = UNPLAYED_STRING
        frets.append(fret)
    return (cost, tuple(frets))


def _missing_cost(*, missing, root):
    """Return what leaving one note of a chord out costs: the root most, the fifth least."""
    if missing == root:
        return MISSING_ROOT_COST
    if missing == (root + FIFTH) % intervals.HALF_STEPS_PER_OCTAVE:
        return MISSING_FIFTH_COST
    return MISSING_NOTE_COST


def _every_way(choices):
    """Return every way of taking one choice from each list, each a tuple in the lists' order."""
    ways = [()]
    for options in choices:
        ways = [way + (option,) for way in ways for option in options]
    return ways


def _positions(*, events, total):
    """Return a clip's positions from events in any order: each (when it starts, STRUCK or PASSED_ON, the note or the position, when it ends).

    Notes struck at one moment are one chord. Each place lasts until the next starts, and a
    struck note sounds for its own length whatever its place's, as a held sound.
    """
    groups = {}
    for start, kind, sound, end in events:
        groups.setdefault(start, []).append((kind, sound, end))
    positions = []
    time = NO_TIME
    starts = sorted(groups)
    for place, start in enumerate(starts):
        if start > time:
            positions.append(Sound.rest(Length.of(start - time)))
        following = total
        if place + 1 < len(starts):
            following = starts[place + 1]
        passed = [(sound, end) for kind, sound, end in groups[start] if kind == PASSED_ON]
        if passed:
            sound, end = passed[0]
            end = min(end, following)
            positions.append(Sound.with_length(sound, Length.of(end - start)))
            time = end
            continue
        notes = [sound for _, sound, _ in groups[start]]
        played = notes[0]
        if len(notes) > 1:
            played = Sound.chord(notes)
        positions.append((sound_values.HELD, Length.of(following - start), played))
        time = following
    if total > time:
        positions.append(Sound.rest(Length.of(total - time)))
    return positions


def _all_in_range(*, strings, from_fret):
    """Return whether every string's note moved up from a fret stays within MIDI's notes."""
    for note in strings:
        if not midi_numbers.MIN_MIDI_NUMBER <= note[sound_values.MIDI] + from_fret <= midi_numbers.MAX_MIDI_NUMBER:
            return False
    return True


def _holds_pitch(*, notes, pitch):
    """Return whether any of some notes plays a pitch."""
    for other in notes:
        if other[sound_values.MIDI] == pitch:
            return True
    return False
