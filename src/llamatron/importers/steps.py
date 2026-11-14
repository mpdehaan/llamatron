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
"""A voice's notes as a pattern's steps, and the shortest pattern a clip can repeat to play them.

Every note starts on a step. A note that lasts whole steps is its step and ties on the steps
after it, as the piano roll writes one, and a note that doesn't is its step with an exact gate.
A step is a NoteStep, TIED, or None for an empty step.

A clip plays one pattern some number of times, and a note held over from one pass to the next is
a tie at the start of the pattern, which holds the note the pass before ended with, and is
silence on the first pass, where nothing came before. So a clip's notes are one pattern
repeated when every pass but the first is the same steps, and the first is the same with the
ties at its start left empty, and no gate runs past the end of a pass, since a pass cuts it.

A voice's CC lanes are read as the value in force at the start of each step. Each pass of a
pattern says each lane's value at its first step, and then each change at the step it happens,
so that a pass sounds the same wherever it plays; a run of steps whose values lie on a straight
line, as a slide sends them, is one value with Slide on, ramping to the value at the run's end.
A value that comes and goes between two steps is not heard, which the comparison would show.
"""

from bisect import bisect_right
from typing import NamedTuple

from llamatron.composition.checks import fraction_text
from llamatron.composition.limits import MAX_GATE
from llamatron.exporters.timing import SLIDE_STEP, value_on_the_way
from llamatron.importers.keys import degree_of, drum_note_of
from llamatron.support.rational import Rational

# What a step holds when it ties the note before it on.
TIED = 'tied'


class NoteStep(NamedTuple):
    """A step that plays: its degree, or a drum's letter, its accidental, octave and chord symbol, its gate as a file writes it or None for whole steps, and its velocity."""

    degree: object
    accidental: object
    octave: int
    chord: object
    gate: object
    velocity: int


class ControlStep(NamedTuple):
    """A step's CC values, one for each of the voice's lanes or None for a lane with nothing new, and whether the step slides them."""

    values: tuple
    slide: bool


class SceneSteps(NamedTuple):
    """One voice's steps across a scene, with the gated notes as the steps they start and end at, each CC lane's value in force at each step, whether a lane changes in the scene, and what had to change."""

    steps: list
    gated: list
    lanes: tuple
    changes: bool
    # Notes longer than a gate can be that don't last whole steps, which are held for the whole steps they last.
    lengths_changed: int
    # Notes too low to be written as a degree in any octave a pattern holds, which are left out.
    too_low: int


def scene_steps(*, voice, start, end, key, step_size):
    """Return a voice's steps from step start to step end, in a key, where every note starts on a step and none crosses either end."""
    steps = [None] * (end - start)
    gated = []
    lengths_changed = 0
    too_low = 0
    for played in voice.played:
        first = played.start / step_size
        if not start <= first < end:
            continue
        place = int(first) - start
        written = drum_note_of(played.pitches[0]) if voice.drum else degree_of(pitch=played.pitches[0], key=key)
        if written is None:
            too_low += 1
            continue
        degree, accidental, octave = written
        length = (played.end - played.start) / step_size
        gate = None
        if not length.is_whole():
            if played.end - played.start <= MAX_GATE:
                gate = fraction_text(played.end - played.start)
                gated.append((place, place + length))
            else:
                lengths_changed += 1
        steps[place] = NoteStep(degree, accidental, octave, played.chord, gate, played.velocity)
        if gate is None:
            for tied in range(place + 1, place + max(int(length), 1)):
                steps[tied] = TIED
    lanes = tuple(lane_values(voice=voice, number=number, start=start, end=end, step_size=step_size) for number in voice.lanes)
    changes = any(lane_changes(values=values, before=value_in_force(voice=voice, number=number, time=start * step_size, before=True)) for number, values in zip(voice.lanes, lanes))
    return SceneSteps(steps=steps, gated=gated, lanes=lanes, changes=changes, lengths_changed=lengths_changed, too_low=too_low)


def lane_changes(*, values, before):
    """Return whether a lane's values at each step change anywhere, from the value it held before the first."""
    return any(earlier != later for earlier, later in zip([before, *values], values))


def value_in_force(*, voice, number, time, before=False):
    """Return the value a voice's CC number holds at a time, or just before it, or None before it is first sent."""
    value = None
    for control in voice.controls:
        if control.time > time or (before and control.time == time):
            break
        if control.number == number:
            value = control.value
    return value


def lane_values(*, voice, number, start, end, step_size):
    """Return the value a voice's CC number holds at the start of each step from step start to step end, None before it is first sent."""
    sent = [control for control in voice.controls if control.number == number]
    times = [control.time for control in sent]
    values = []
    for step in range(start, end):
        place = bisect_right(times, step * step_size)
        values.append(sent[place - 1].value if place else None)
    return values


def pass_controls(*, lanes, begin, length):
    """Return each step's ControlStep for one pass of a pattern from step begin, or None for a step with nothing to send.

    Each lane says its value at the pass's first step and then each change. Slide ramps every lane
    that has a value on its step to that lane's next value, so a step slides only when each lane
    with a value there either changes no more in the pass or lies on a straight line to a value
    two steps or more on, and then each of those lanes keeps only its run's first and last value.
    """
    if not lanes:
        return (None,) * length
    points = [[None] * length for _ in lanes]
    for lane, values in enumerate(lanes):
        for place in range(length):
            value = values[begin + place]
            if value is not None and (place == 0 or values[begin + place - 1] != value):
                points[lane][place] = value
    slides = [False] * length
    for place in range(length):
        holding = [lane for lane in range(len(lanes)) if points[lane][place] is not None]
        runs = {lane: straight_run(values=lanes[lane], begin=begin + place, last=begin + length - 1) for lane in holding}
        steady = [lane for lane in holding if runs[lane] is None and not any(value is not None for value in points[lane][place + 1:])]
        if not any(run is not None for run in runs.values()) or len(steady) + sum(1 for run in runs.values() if run is not None) < len(holding):
            continue
        for lane, run in runs.items():
            if run is not None:
                for between in range(place + 1, run - begin):
                    points[lane][between] = None
                points[lane][run - begin] = lanes[lane][run]
        slides[place] = True
    steps = []
    for place in range(length):
        values = tuple(points[lane][place] for lane in range(len(lanes)))
        steps.append(None if all(value is None for value in values) else ControlStep(values, slides[place]))
    return tuple(steps)


def straight_run(*, values, begin, last):
    """Return the furthest step up to last that a slide from step begin reaches, two steps on or more, with every step between on its straight line, or None."""
    for end in range(last, begin + 1, -1):
        if values[end] is None or values[end] == values[begin]:
            continue
        if all(values[step] == value_on_the_way(start=Rational(begin), value=values[begin], end=Rational(end), target=values[end], now=Rational(step)) for step in range(begin, end + 1)):
            return end
    return None


def controls_between_steps(*, voice, start, end, step_size, controls):
    """Return how many of a voice's CC messages from step start to step end the pattern's CC steps, repeated, can't send as the file does.

    A message on a step is sent there. One between steps is sent only when it lies on a slide, at
    a SLIDE_STEP from the slide's start, with the value the slide passes through there, since that
    is where and what an export sends; any other moves to a step, or is lost to a later one.
    """
    length = len(controls)
    begin = start * step_size
    count = 0
    for control in voice.controls:
        if not begin <= control.time < end * step_size:
            continue
        offset = (control.time - begin) / step_size
        if offset.is_whole():
            continue
        place = offset - int(offset) // length * length
        if not on_a_slide(controls=controls, lane=voice.lanes.index(control.number), place=place, value=control.value, step_size=step_size):
            count += 1
    return count + slides_astray(voice=voice, start=start, end=end, step_size=step_size, controls=controls)


def slides_astray(*, voice, start, end, step_size, controls):
    """Return how many slides of the pattern's CC steps, repeated from step start to step end, send a value at some SLIDE_STEP that the file doesn't hold there, as a ramp between other ends can round differently."""
    length = len(controls)
    held = {number: values_over_time(voice=voice, number=number) for number in voice.lanes}
    count = 0
    for pass_start in range(start, end, length):
        for place, step in enumerate(controls):
            if step is None or not step.slide:
                continue
            for lane, value in enumerate(step.values):
                following = next((later for later in range(place + 1, length) if controls[later] is not None and controls[later].values[lane] is not None), None)
                if value is None or following is None:
                    continue
                begin = (pass_start + place) * step_size
                finish = (pass_start + following) * step_size
                target = controls[following].values[lane]
                times, values = held[voice.lanes[lane]]
                now = begin + SLIDE_STEP
                while now < finish:
                    found = bisect_right(times, now)
                    if not found or values[found - 1] != value_on_the_way(start=begin, value=value, end=finish, target=target, now=now):
                        count += 1
                        break
                    now += SLIDE_STEP
    return count


def values_over_time(*, voice, number):
    """Return a voice's CC number's messages as their times and their values, in time order."""
    sent = [control for control in voice.controls if control.number == number]
    return [control.time for control in sent], [control.value for control in sent]


def control_error(*, voice, start, end, step_size, found):
    """Return the most any CC message from step start to step end differs from its lane's value at the start of the step it falls in, the most a clip of these steps can be off by, slides aside."""
    begin = start * step_size
    error = 0
    for control in voice.controls:
        if begin <= control.time < end * step_size:
            step = int((control.time - begin) / step_size)
            held = found.lanes[voice.lanes.index(control.number)][step]
            error = max(error, abs(control.value - (held if held is not None else control.value)))
    return error


def on_a_slide(*, controls, lane, place, value, step_size):
    """Return whether a slide in a pass's CC steps sends a value at a place between steps, counted in steps from the pass's start."""
    first = int(place)
    start = next((step for step in range(first, -1, -1) if controls[step] is not None and controls[step].values[lane] is not None), None)
    if start is None or not controls[start].slide:
        return False
    end = next((step for step in range(first + 1, len(controls)) if controls[step] is not None and controls[step].values[lane] is not None), None)
    if end is None:
        return False
    time = (place - start) * step_size
    if not (time / SLIDE_STEP).is_whole():
        return False
    ramped = value_on_the_way(start=Rational(0), value=controls[start].values[lane], end=(end - start) * step_size, target=controls[end].values[lane], now=time)
    return ramped == value


def leading_ties_cleared(steps):
    """Return a pattern's steps as its first pass plays them, with the ties at its start left empty."""
    cleared = list(steps)
    for place, step in enumerate(cleared):
        if step != TIED:
            break
        cleared[place] = None
    return cleared


def gate_crosses_a_pass(*, gated, length):
    """Return whether a gated note, as the steps it starts and ends at, would run past the end of its pass in a pattern of this length."""
    return any(finish > (begin // length + 1) * length for begin, finish in gated)


def repeated_pattern(*, steps, gated, lanes=()):
    """Return the shortest pattern a clip can repeat to play these steps and CC lanes, and how many times, as ((pattern steps, its CC steps), repeats)."""
    count = len(steps)
    for length in range(1, count + 1):
        if count % length or gate_crosses_a_pass(gated=gated, length=length):
            continue
        passes = [steps[at:at + length] for at in range(0, count, length)]
        controls = [pass_controls(lanes=lanes, begin=at, length=length) for at in range(0, count, length)]
        pattern = passes[1] if len(passes) > 1 else passes[0]
        pattern_controls = controls[1] if len(controls) > 1 else controls[0]
        if (
            all(each == pattern for each in passes[1:]) and passes[0] == leading_ties_cleared(pattern)
            and all(each == pattern_controls for each in controls)
        ):
            return (tuple(pattern), pattern_controls), len(passes)
    return (tuple(steps), pass_controls(lanes=lanes, begin=0, length=count)), 1
