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

"""Works out when each note in a clip plays, for exporters to write out."""

from typing import NamedTuple

from llamatron.composition.file_format import StrumDirection
from llamatron.support.length import ZERO, Length
from llamatron.support.random_source import random_source
from llamatron.support.rational import Rational
from llamatron.music.midi import MAX_VELOCITY
from llamatron.music.sound import CHORD, DEGREE, GLIDE, HELD, HELD_SOUND, KIND, LENGTH, MIDI, NOTE, NOTES, PARTS, PHRASE, REST, Sound
from llamatron.music.sound import VELOCITY as NOTE_VELOCITY
from llamatron.strings.errors import ERR_DEGREE_NEEDS_SCALE, ERR_TIMING_NOT_A_POSITION

# A beat is a quarter note, which matches how MIDI and Live measure both time and tempo.
BEATS_PER_WHOLE_NOTE = 4
# A note with no velocity of its own plays as loud as MIDI allows.
VELOCITY = MAX_VELOCITY

# How far a note with glide runs into the next one, in fractions of a whole note.
GLIDE_OVERLAP = Rational(1, 128)
# A note that starts with its chord, and one a strum leaves as loud as it was.
ZERO_DELAY = Rational(0)
NO_FADING = Rational(0)
PERCENT = 100
MIN_FADED_VELOCITY = 1


class NoteEvent(NamedTuple):
    """One note as it plays: when it starts and ends, in whole notes from the clip's start, its MIDI number and velocity."""

    start: Rational
    end: Rational
    midi_number: int
    velocity: int


class ControlPoint(NamedTuple):
    """One point of a CC lane: a value sent at a time, sliding to the lane's next point if slide is set."""

    time: Rational
    value: int
    slide: bool


class ControlEvent(NamedTuple):
    """One CC value as it's sent: at a time, on a CC number."""

    time: Rational
    number: int
    value: int


def _degree_to_note(*, position, scale):
    """Return the note a degree plays in a scale, leaving anything else as it is."""
    if position[KIND] != DEGREE:
        return position
    if scale is None:
        raise ValueError(ERR_DEGREE_NEEDS_SCALE.format(degree=Sound.position(position)))
    return Sound.settled(position, scale)


def _sounding_notes(position):
    """Return {MIDI number: note} for one position in a clip, keeping the longest of any pitch."""
    kind = position[KIND]
    if kind == REST:
        return {}
    if kind == NOTE:
        return {position[MIDI]: position}
    if kind == CHORD:
        notes = {}
        for note in position[NOTES]:
            if note[MIDI] not in notes or Length.less(notes[note[MIDI]][LENGTH], note[LENGTH]):
                notes[note[MIDI]] = note
        return notes
    raise ValueError(ERR_TIMING_NOT_A_POSITION.format(value=Sound.position(position)))


def _glide_end(*, note, end, following):
    """Return when a note ends, running into what follows if it glides to a different pitch."""
    if note[GLIDE] and following and note[MIDI] not in following:
        return end + GLIDE_OVERLAP
    return end


def timed_events(*, clip, scale, grooved=True):
    """Return a clip's notes as NoteEvents, and the clip's total length.

    Times are exact fractions of a whole note. This is where lengths and degrees are
    finally settled, as late as possible. Notes are cut off at the end of the clip. The
    clip's groove, if it has one, moves each note's start and keeps its gate, so that a
    delayed note ends later too; grooved=False reads the notes where the grid puts them,
    which is what a grab wants, since grooves only change timing.
    """
    positions = clip.resolved_sounds()
    slots = _slots(positions=positions, scale=scale)
    clip_length = _clip_length(clip=clip, positions=positions)
    groove = clip.get_groove() if grooved else None
    # A strum, like a groove, only changes timing, so a grab reads the notes without it too.
    strum = clip.get_strum() if grooved else None
    nudge = clip.get_nudge() if grooved else None
    strummed = 0

    timed = []
    for place, (slot_start, sounding_notes) in enumerate(slots):
        onset = _grooved_time(time=slot_start, groove=groove)
        if nudge is not None:
            onset = max(onset + nudge.moved(slot_start), ZERO_DELAY)
        following = _what_follows(slots=slots, place=place)
        strings = [(midi_number, note, ZERO_DELAY, NO_FADING) for midi_number, note in sounding_notes.items()]
        if strum is not None and len(strings) > 1:
            strings = _strummed(notes=sounding_notes, strum=strum, time=slot_start, count=strummed, place=place)
            strummed += 1
        for midi_number, note, delay, fading in strings:
            start = min(onset + delay, clip_length)
            end = _glide_end(note=note, end=onset + Length.rational(note[LENGTH]), following=following)
            end = min(end, clip_length)
            if end > start:
                velocity = VELOCITY if note[NOTE_VELOCITY] is None else note[NOTE_VELOCITY]
                timed.append(NoteEvent(start, end, midi_number, _faded(velocity=velocity, fading=fading)))
    handed = clip.get_handed()
    if handed:
        timed.extend(_handed_events(notes=handed, groove=groove, nudge=nudge, clip_length=clip_length))
        timed.sort(key=_start_of)
    return timed, clip_length


def _handed_events(*, notes, groove, nudge, clip_length):
    """Return the notes a Hocket hands a clip as NoteEvents, each moved by the clip's groove and its rushes and drags as the clip's own notes are, keeping its length, and cut at the clip's end."""
    events = []
    for note in notes:
        onset = _grooved_time(time=note.start, groove=groove)
        if nudge is not None:
            onset = max(onset + nudge.moved(note.start), ZERO_DELAY)
        start = min(onset, clip_length)
        end = min(onset + (note.end - note.start), clip_length)
        if end > start:
            events.append(NoteEvent(start, end, note.midi_number, note.velocity))
    return events


def _start_of(event):
    return event.start


def _strummed(*, notes, strum, time, count, place):
    """Return a chord's notes as a strum plays them: each with how much later it starts than the first and how far through the strum it is, from 0 to 1.

    Down is low to high and up high to low; by the beat is down on a beat and up between, down
    up alternates from the clip's first chord. An upstroke that catches only the top strings
    leaves the rest out. Each gap is the strum's, varied by its loose timing from its seed.
    """
    pitches = sorted(notes)
    if strum.direction == StrumDirection.BY_THE_BEAT:
        down = ((time + strum.offset) / strum.beat).denominator == 1
    elif strum.direction == StrumDirection.DOWN_UP:
        down = (count + strum.chords_before) % 2 == 0
    else:
        down = strum.direction == StrumDirection.DOWN
    if not down:
        pitches = pitches[::-1]
        if strum.upstroke_count is not None:
            pitches = pitches[:strum.upstroke_count]
    chooser = random_source(strum.seed + place)
    result = []
    delay = ZERO_DELAY
    last = max(len(pitches) - 1, 1)
    for string, midi_number in enumerate(pitches):
        if string:
            loose = Rational(round(chooser.uniform(-strum.loose_timing, strum.loose_timing)), PERCENT) if strum.loose_timing else ZERO_DELAY
            delay = delay + strum.gap * (1 + loose)
        result.append((midi_number, notes[midi_number], delay, Rational(string * strum.fade, last * PERCENT)))
    return result


def _faded(*, velocity, fading):
    """Return a velocity made quieter by a share of itself, never below 1."""
    return max(round(velocity * (1 - fading)), MIN_FADED_VELOCITY) if fading else velocity


def _grooved_time(*, time, groove):
    """Return when something at a time plays once the clip's groove has moved it, or the time itself with no groove."""
    return time if groove is None else groove.moved(time)


def _slots(*, positions, scale):
    """Return when each position starts and the notes it sounds by MIDI number, in time order.

    A held sound is placed at its own start, with a held phrase's parts one after another from
    there, while the next position starts after the held length. Sorting by start keeps
    positions that start together in the clip's order. The starts are added up as pairs and
    each slot's is a Rational, which is what the exporters are given.
    """
    slots = []
    start = ZERO
    for position in positions:
        _place(position=position, start=start, scale=scale, slots=slots)
        start = Length.add(start, position[LENGTH])
    return sorted(slots, key=_slot_start)


def _slot_start(slot):
    return slot[0]


def _place(*, position, start, scale, slots):
    """Add the slots a position sounds, starting at a time, including everything a held sound holds."""
    kind = position[KIND]
    if kind == HELD:
        _place(position=position[HELD_SOUND], start=start, scale=scale, slots=slots)
    elif kind == PHRASE:
        for part in position[PARTS]:
            _place(position=part, start=start, scale=scale, slots=slots)
            start = Length.add(start, part[LENGTH])
    else:
        slots.append((Length.rational(start), _sounding_notes(_degree_to_note(position=position, scale=scale))))


def _clip_length(*, clip, positions):
    """Return how long a clip lasts: its own length if it has one, or else all its positions end to end."""
    if clip.get_length() is not None:
        return Rational(clip.get_length())
    return Length.rational(Length.total([position[LENGTH] for position in positions]))


def _what_follows(*, slots, place):
    """Return the notes the slot after a place sounds, or none if it's the last."""
    following = place + 1
    return slots[following][1] if following < len(slots) else {}


# How often a slide sends a new CC value, in fractions of a whole note, where a format can't ramp.
SLIDE_STEP = Rational(1, 64)


def control_points(*, clip, length):
    """Return each CC number's values as ControlPoints, in time order.

    Points at or after the clip's length are left out, and a later value at the same time as an
    earlier one replaces it. The clip's groove moves each point with the step it was set on.
    """
    points = {}
    groove = clip.get_groove()
    for item in clip.get_controls():
        time = _grooved_time(time=Rational(item.get_time()), groove=groove)
        if time >= length:
            continue
        lane = points.setdefault(item.get_number(), [])
        if lane and lane[-1].time == time:
            lane.pop()
        lane.append(ControlPoint(time, item.get_value(), item.get_slide()))
    return points


def control_events(*, clip, length):
    """Return a clip's CC values as ControlEvents, with slides written out as steps.

    A slide ramps in a straight line to the next value for the same number, sending a value every
    SLIDE_STEP, and a slide with nothing after it holds.
    """
    events = []
    for number, lane in control_points(clip=clip, length=length).items():
        for place, point in enumerate(lane):
            events.append(ControlEvent(point.time, number, point.value))
            following = place + 1
            if point.slide and following < len(lane):
                events += _slide_steps(number=number, point=point, following=lane[following])
    return sorted(events)


def _slide_steps(*, number, point, following):
    """Return the values a slide sends between a point and the one after it, every SLIDE_STEP, leaving out repeats of the same value."""
    steps = []
    sent = point.value
    now = point.time + SLIDE_STEP
    while now < following.time:
        ramped = value_on_the_way(start=point.time, value=point.value, end=following.time, target=following.value, now=now)
        if ramped != sent:
            steps.append(ControlEvent(now, number, ramped))
            sent = ramped
        now += SLIDE_STEP
    return steps


def value_on_the_way(*, start, value, end, target, now):
    """Return the whole-number value a straight line from one point to the next passes through at a time."""
    return round(value + (target - value) * (now - start) / (end - start))


def as_note(*, position, scale):
    """Return a note, or a degree settled into the note it plays in a scale, which a grab reads."""
    return _degree_to_note(position=position, scale=scale)


def clip_end(*, clip, positions):
    """Return how long a clip lasts, its own length or its positions end to end, where every note is cut off."""
    return _clip_length(clip=clip, positions=positions)
