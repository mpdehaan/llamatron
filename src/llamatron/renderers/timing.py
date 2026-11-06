# llamatron: a Python language and framework for producing MIDI clips.
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

"""Works out when each note in a clip plays, for renderers to write out."""

from fractions import Fraction

from llamatron.chord import Chord
from llamatron.held import Held, is_phrase
from llamatron.midi import MAX_VELOCITY
from llamatron.note import Degree, Note, Rest

# A beat is a quarter note, which matches how MIDI and Live measure both time and tempo.
BEATS_PER_WHOLE_NOTE = 4
# A note with no velocity of its own plays as loud as MIDI allows.
VELOCITY = MAX_VELOCITY
# Where a clip starts.
START = Fraction(0)

MSG_DEGREE_NEEDS_SCALE = '{degree!r} needs a scale, but the clip, scene and song have none'
MSG_NOT_A_POSITION = 'expected a Note, Chord or Rest, got {value!r}'
# How far a note with glide runs into the next one, in fractions of a whole note.
GLIDE_OVERLAP = Fraction(1, 128)


def _degree_to_note(position, scale):
    """Return a Note for a Degree, leaving anything else as it is."""
    if not isinstance(position, Degree):
        return position
    if scale is None:
        raise ValueError(MSG_DEGREE_NEEDS_SCALE.format(degree=position))
    return position.to_note(scale)


def _sounding_notes(position):
    """Return {MIDI number: note} for one position in a clip, keeping the longest of any pitch."""
    # A clip's list can be appended to directly, so its contents are checked again here.
    if isinstance(position, Rest):
        return {}
    if isinstance(position, Note):
        return {position.midi_number: position}
    if isinstance(position, Chord):
        notes = {}
        for note in position.notes:
            if note.midi_number not in notes or note.length > notes[note.midi_number].length:
                notes[note.midi_number] = note
        return notes
    raise ValueError(MSG_NOT_A_POSITION.format(value=position))


def _glide_end(note, end, following):
    """Return when a note ends, running into what follows if it glides to a different pitch."""
    if note.glide and following and note.midi_number not in following:
        return end + GLIDE_OVERLAP
    return end


def timed_events(clip, scale):
    """Return a clip's notes as (start, end, MIDI number, velocity), and the clip's total length.

    Times are exact fractions of a whole note. This is where lengths and degrees are
    finally settled, as late as possible. Notes are cut off at the end of the clip.
    """
    positions = clip.resolved_notes()
    # Placing the positions checks each one, so an invalid one is reported before its length is read.
    slots = _slots(positions, scale)
    clip_length = _clip_length(clip, positions)

    timed = []
    for place, (slot_start, sounding_notes) in enumerate(slots):
        start = min(slot_start, clip_length)
        following = _what_follows(slots, place)
        for midi_number, note in sounding_notes.items():
            end = _glide_end(note, slot_start + Fraction(note.length), following)
            end = min(end, clip_length)
            if end > start:
                velocity = VELOCITY if note.velocity is None else note.velocity
                timed.append((start, end, midi_number, velocity))
    return timed, clip_length


def _slots(positions, scale):
    """Return when each position starts and the notes it sounds by MIDI number, in time order.

    A Held's sound is placed at its own start, with a held phrase's parts one after another from
    there, while the next position starts after the Held's length. Sorting by start keeps
    positions that start together in the clip's order.
    """
    slots = []
    start = START
    for position in positions:
        _place(position, start, scale, slots)
        start += Fraction(position.length)
    return sorted(slots, key=lambda slot: slot[0])


def _place(position, start, scale, slots):
    """Add the slots a position sounds, starting at a time, including everything a Held holds."""
    if not isinstance(position, Held):
        slots.append((start, _sounding_notes(_degree_to_note(position, scale))))
        return
    if not is_phrase(position.sound):
        _place(position.sound, start, scale, slots)
        return
    for part in position.sound:
        _place(part, start, scale, slots)
        start += Fraction(part.length)


def _clip_length(clip, positions):
    """Return how long a clip lasts: its own length if it has one, or else all its positions end to end."""
    if clip.length is not None:
        return Fraction(clip.length)
    return sum((Fraction(position.length) for position in positions), START)


def _what_follows(slots, place):
    """Return the notes the slot after a place sounds, or none if it's the last."""
    following = place + 1
    return slots[following][1] if following < len(slots) else {}


# How often a slide sends a new CC value, in fractions of a whole note, where a format can't ramp.
SLIDE_STEP = Fraction(1, 64)


def control_points(clip, length):
    """Return each CC number's values as (time, value, slide) points, in time order.

    Points at or after the clip's length are left out, and a later value at the same time as an
    earlier one replaces it.
    """
    points = {}
    for item in clip.controls:
        time = Fraction(item.time)
        if time >= length:
            continue
        lane = points.setdefault(item.number, [])
        if lane and lane[-1][0] == time:
            lane.pop()
        lane.append((time, item.value, item.slide))
    return points


def control_events(clip, length):
    """Return a clip's CC values as (time, CC number, value), with slides written out as steps.

    A slide ramps in a straight line to the next value for the same number, sending a value every
    SLIDE_STEP, and a slide with nothing after it holds.
    """
    events = []
    for number, lane in control_points(clip, length).items():
        for place, (time, value, slide) in enumerate(lane):
            events.append((time, number, value))
            following = place + 1
            if slide and following < len(lane):
                end, target, _ = lane[following]
                events += _slide_steps(number, time, value, end, target)
    return sorted(events)


def _slide_steps(number, start, value, end, target):
    """Return the values a slide sends between two points, every SLIDE_STEP, leaving out repeats of the same value."""
    steps, sent = [], value
    now = start + SLIDE_STEP
    while now < end:
        ramped = _value_on_the_way(start, value, end, target, now)
        if ramped != sent:
            steps.append((now, number, ramped))
            sent = ramped
        now += SLIDE_STEP
    return steps


def _value_on_the_way(start, value, end, target, now):
    """Return the whole-number value a straight line from one point to the next passes through at a time."""
    return round(value + (target - value) * (now - start) / (end - start))

