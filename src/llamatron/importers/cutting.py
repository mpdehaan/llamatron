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
"""Choosing the imported song's step size, where its scenes split, and which pattern each clip repeats, the user's design of 2026-11-10.

The rules, in the order they give way:

1. Nothing is ever cut. A scene splits only at a step where no note of any voice is held across,
   a clean step, since a clip's notes end with the clip. So the song plays every note of the
   file, for as long as the file plays it.
2. Patterns keep within the longest pattern asked for. The song is cut into phrases of whole bars
   no longer than that, each phrase a scene, and each voice's clip in a scene is the shortest
   pattern it can repeat (steps.py), so a bar played four times is one bar's pattern with a
   Repeat of 4. Where a phrase's end isn't clean, the scene ends at the clean step before it and
   a short transition scene runs to the clean step after, so that the phrases either side keep
   their length. Only where no clean step is near does a scene, and its patterns, run longer.
3. Splits fall on bar lines where they can, since the transition scenes count against a cut.
4. Then the fewest patterns, and then the fewest scenes: each phrase length is tried, a pattern
   met again is the same pattern, and scenes that come out the same one after another are one
   scene with a Repeat.

A key change, or a tempo change, splits the song first, at its step if that is clean and at the
next clean step if not, so that each scene has one key and one tempo. A key change that lands
later plays the notes before it as degrees of the key before, with accidentals, which sound the
same; a tempo change that lands later plays those notes at the tempo before, which the import
says.
"""

from dataclasses import dataclass, field
from math import ceil
from typing import NamedTuple

from llamatron.support.rational import Rational
from llamatron.importers.midi_reading import HeardNote, MidiPart, value_at
from llamatron.importers.steps import NoteStep, control_error, controls_between_steps, repeated_pattern, scene_steps

# The step sizes the import tries, longest first, down to the one that holds triplets and 32nd notes together, and
# the one it uses when none fits every note's start, moving the notes to it. Each pattern takes the longest step its
# own notes start on, so that a few triplets make only their own clips' steps short.
AUTO_STEP_SIZES = (
    Rational(1, 4), Rational(1, 8), Rational(1, 12), Rational(1, 16), Rational(1, 24), Rational(1, 32), Rational(1, 48), Rational(1, 64),
    Rational(1, 96), Rational(1, 192),
)
FALLBACK_STEP_SIZE = Rational(1, 16)
# The phrase lengths tried, in bars and then in parts of a bar, in the order a tie between them goes, the four-bar phrase first.
PHRASE_BARS = (4, 8, 2, 16, 1, 32)
PARTS_OF_A_BAR = (2, 4, 8)
# What each part of a cut costs, against one pattern: a scene, and a split away from the phrases' bar lines. A pattern
# longer than the longest asked for costs more than any number of these, since keeping within it comes first.
SCENE_COST = 0.5
OFF_THE_BAR_COST = 1
FIRST_STEP = 0
NO_REPEAT = 1
# How far a CC lane may stray from the file when no step size sends every message as the file does: a clip takes the
# longest step that keeps every lane within this, so that a recorded sweep needn't make every pattern long.
CONTROL_TOLERANCE = 4


class SceneClip(NamedTuple):
    """A clip of an imported scene: the voice that plays it, the pattern as whether it is a drum's, its step size, its steps and its CC steps, and how many times it repeats."""

    voice: int
    pattern: tuple
    repeats: int


class VoiceClip(NamedTuple):
    """A voice's clip in one scene: its step size, its steps, its pattern as (steps, CC steps), how many times it repeats, how many CC messages it can't send as the file does, and the most any is off by."""

    size: object
    found: object
    pattern: tuple
    repeats: int
    controls_moved: int
    error: int


@dataclass(slots=True, kw_only=True)
class CutScene:
    """A scene of the imported song: the steps it starts and ends at, its key and tempo, its clips, and how many times it plays."""

    start: int
    end: int
    key: object
    tempo: int
    clips: list
    repeat: int = NO_REPEAT

    def same_music(self, other):
        """Return whether another scene plays exactly what this one does, so that the two can be one scene played twice."""
        return (self.end - self.start, self.key, self.tempo, self.clips) == (other.end - other.start, other.key, other.tempo, other.clips)


@dataclass(slots=True, kw_only=True)
class Cut:
    """How the song was cut: its scenes, the patterns they use in the order first met, and what had to change."""

    scenes: list
    patterns: list
    lengths_changed: int = 0
    too_low: int = 0
    controls_moved: int = 0
    long_patterns: int = 0
    cost: tuple = field(default=())


def step_size_for(parts):
    """Return the longest step size every note starts on, and whether there was one: if not, the fallback, which the notes are moved to."""
    size = longest_step_for({note.start for part in parts for note in part.notes})
    return (size, True) if size is not None else (FALLBACK_STEP_SIZE, False)


def longest_step_for(times):
    """Return the longest of the step sizes tried that every time falls on, or None when none does."""
    for size in AUTO_STEP_SIZES:
        if all((time / size).is_whole() for time in times):
            return size
    return None


def grid_for(*, voices, step_size):
    """Return the grid scenes split on: the notes' step size, or a shorter one the CC messages need, so that a clip can take a step a CC needs.

    That is the longest step every CC message falls on, or, for messages that fall on none, as a
    recorded sweep's do, the longest that keeps every lane within CONTROL_TOLERANCE of the file.
    """
    times = {control.time for voice in voices for control in voice.controls}
    controls = longest_step_for(times)
    if controls is None and times:
        near = [size for size in AUTO_STEP_SIZES if most_off(voices=voices, step_size=size) <= CONTROL_TOLERANCE]
        controls = near[0] if near else AUTO_STEP_SIZES[-1]
    return step_size if controls is None or controls >= step_size else controls


def most_off(*, voices, step_size):
    """Return the most any voice's CC message differs from the value its lane holds at the start of the step it falls in, on a grid of this step size."""
    error = 0
    for voice in voices:
        held = {}
        step_start = None
        for control in voice.controls:
            start = int(control.time / step_size) * step_size
            if start != step_start:
                step_start = start
                at_start = dict(held)
            if control.time == start:
                at_start[control.number] = control.value
            error = max(error, abs(control.value - at_start.get(control.number, control.value)))
            held[control.number] = control.value
    return error


def snapped(*, parts, step_size):
    """Return the parts with every note moved whole to the nearest step, and how many notes moved."""
    moved = 0
    snapped_parts = []
    for part in parts:
        notes = []
        for note in part.notes:
            start = round(note.start / step_size) * step_size
            if start != note.start:
                moved += 1
            notes.append(HeardNote(start, note.end + start - note.start, note.pitch, note.velocity))
        snapped_parts.append(MidiPart(name=part.name, channel=part.channel, notes=sorted(notes), controls=part.controls))
    return snapped_parts, moved


def bar_lines(*, time_signatures, end, holding=None):
    """Return when each bar starts, in whole notes, and then when the bar the song ends in ends, which is where the song ends.

    The song ends with the bar its last note ends in, and goes on past holding, the time of its
    last CC message, which a scene must still hold.
    """
    lines = []
    time = Rational(0)
    while not lines or time < end or (holding is not None and time <= holding):
        lines.append(time)
        beats, unit = value_at(changes=time_signatures, time=time)
        time += Rational(beats, unit)
    lines.append(time)
    return lines


class Cutter:
    """What cuts one song: its voices on a grid of steps, the step sizes its patterns may take, the bar lines, its keys and tempos, and the longest pattern asked for."""

    __slots__ = ('_voices', '_step_size', '_clip_step_sizes', '_bars', '_keys', '_tempos', '_longest', '_end', '_blocked', '_clips_of')

    def __init__(self, *, voices, step_size, clip_step_sizes, bars, keys, tempos, longest):
        self._voices = voices
        # The grid every note starts on, where scenes split, and the step sizes a clip's pattern may take, longest first.
        self._step_size = step_size
        self._clip_step_sizes = [size for size in clip_step_sizes if (size / step_size).is_whole()] or [step_size]
        self._bars = bars
        self._keys = keys
        self._tempos = tempos
        self._longest = longest
        self._end = self.step_of(bars[-1])
        self._blocked = self.held_across()
        # Each voice's clip in a scene, worked out once whichever cuts ask for that scene.
        self._clips_of = {}

    def step_of(self, time):
        """Return a time on the grid as its step."""
        return int(time / self._step_size)

    def time_of(self, step):
        return step * self._step_size

    def held_across(self):
        """Return the steps some note is held across, which no scene can split at."""
        blocked = set()
        for voice in self._voices:
            for played in voice.played:
                first = played.start / self._step_size
                last = played.end / self._step_size
                blocked.update(range(int(first) + 1, ceil(last)))
        return blocked

    def is_clean(self, step):
        return step not in self._blocked

    def clean_after(self, step):
        """Return the first clean step at or after a step, or the song's end."""
        while step < self._end and not self.is_clean(step):
            step += 1
        return min(step, self._end)

    def boundaries(self):
        """Return the steps the song splits at whatever else, in order: its start, each key and tempo change at the first clean step from it, and its end."""
        changes = {FIRST_STEP, self._end}
        for change in [*self._keys, *self._tempos]:
            if change.time > 0:
                changes.add(self.clean_after(ceil(change.time / self._step_size)))
        return sorted(changes)

    def phrase_lengths(self):
        """Return the phrase lengths to try, in steps of the grid: whole bars, and then parts of a bar, which the cost of a long pattern chooses between."""
        bar_steps = (self._bars[1] - self._bars[0]) / self._step_size
        if not bar_steps.is_whole():
            return [self._longest]
        lengths = [int(bar_steps) * bars for bars in PHRASE_BARS]
        lengths += [int(bar_steps / parts) for parts in PARTS_OF_A_BAR if (bar_steps / parts).is_whole()]
        return lengths

    def cuts(self, length):
        """Return the steps the song splits at for phrases of a length, from its start to its end, and how many fall away from the phrases' lines."""
        cuts = []
        off = 0
        edges = self.boundaries()
        for start, end in zip(edges, edges[1:]):
            cuts.append(start)
            line = start + length
            while line < end:
                if self.is_clean(line):
                    cuts.append(line)
                    line += length
                    continue
                before = next((step for step in range(line - 1, cuts[-1], -1) if self.is_clean(step)), None)
                after = self.clean_after(line + 1)
                for step in (before, after):
                    if step is not None and cuts[-1] < step < end:
                        cuts.append(step)
                        off += 1
                # On from the first phrase line past the scene just cut, or past this line when nothing could be.
                line = start + ((max(cuts[-1], line) - start) // length + 1) * length
        cuts.append(self._end)
        return cuts, off

    def voice_clip(self, *, voice, start, end, key):
        """Return a voice's clip across the scene from grid step start to grid step end, as a VoiceClip, worked out once whichever cuts ask for it.

        The clip takes the longest step size its notes start on that also sends every CC message
        as the file does, or, when none does, the longest that keeps every lane within
        CONTROL_TOLERANCE of the file, or else the one that strays least.
        """
        place = (voice, start, end, key)
        if place not in self._clips_of:
            clips = []
            for size in self.clip_step_sizes(voice=voice, start=start, end=end):
                clips.append(self.clip_at(voice=voice, start=start, end=end, key=key, size=size))
                if not clips[-1].controls_moved:
                    break
            exact = [clip for clip in clips if not clip.controls_moved]
            near = [clip for clip in clips if clip.error <= CONTROL_TOLERANCE]
            self._clips_of[place] = exact[0] if exact else near[0] if near else min(clips, key=lambda clip: clip.error)
        return self._clips_of[place]

    def clip_at(self, *, voice, start, end, key, size):
        """Return a voice's clip across a scene at one step size."""
        ratio = size / self._step_size
        found = scene_steps(voice=self._voices[voice], start=int(start / ratio), end=int(end / ratio), key=key, step_size=size)
        pattern, repeats = repeated_pattern(steps=found.steps, gated=found.gated, lanes=found.lanes)
        first = int(start / ratio)
        last = int(end / ratio)
        moved = controls_between_steps(voice=self._voices[voice], start=first, end=last, step_size=size, controls=pattern[1])
        error = control_error(voice=self._voices[voice], start=first, end=last, step_size=size, found=found) if moved else 0
        return VoiceClip(size=size, found=found, pattern=pattern, repeats=repeats, controls_moved=moved, error=error)

    def clip_step_sizes(self, *, voice, start, end):
        """Return the step sizes a voice's clip from grid step start to grid step end can take, longest first: the scene's ends and every note's start fall on their steps."""
        begin = self.time_of(start)
        starts = [played.start - begin for played in self._voices[voice].played if start <= played.start / self._step_size < end]
        sizes = [
            size for size in self._clip_step_sizes
            if (begin / size).is_whole() and (self.time_of(end - start) / size).is_whole() and all((time / size).is_whole() for time in starts)
        ]
        return sizes or [self._step_size]

    def scenes_of(self, cuts):
        """Return the scenes between the cuts, each voice's clip the shortest pattern it repeats, with scenes that play the same one after another made one, and what changed."""
        scenes = []
        lengths_changed = 0
        too_low = 0
        controls_moved = 0
        for start, end in zip(cuts, cuts[1:]):
            key = value_at(changes=self._keys, time=self.time_of(start))
            clips = []
            for voice in range(len(self._voices)):
                clip = self.voice_clip(voice=voice, start=start, end=end, key=key)
                found = clip.found
                lengths_changed += found.lengths_changed
                too_low += found.too_low
                # A voice that plays nothing in a scene has no clip there, unless one of its CC lanes changes, which a pattern of rests then sends.
                if found.changes or any(isinstance(step, NoteStep) for step in found.steps):
                    sounds, controls = clip.pattern
                    clips.append(SceneClip(voice, (self._voices[voice].drum, clip.size, sounds, controls), clip.repeats))
                    controls_moved += clip.controls_moved
            if not clips:
                # A scene where nothing plays is a pattern of rests, which lasts as long as the scene.
                (sounds, controls), repeats = repeated_pattern(steps=[None] * (end - start), gated=[])
                clips.append(SceneClip(FIRST_STEP, (self._voices[FIRST_STEP].drum, self._step_size, sounds, controls), repeats))
            scene = CutScene(start=start, end=end, key=key, tempo=value_at(changes=self._tempos, time=self.time_of(start)), clips=clips)
            if scenes and scenes[-1].same_music(scene):
                scenes[-1].repeat += 1
            else:
                scenes.append(scene)
        return scenes, lengths_changed, too_low, controls_moved

    def cut(self, length):
        """Return the cut for phrases of a length, with what it costs."""
        cuts, off = self.cuts(length)
        scenes, lengths_changed, too_low, controls_moved = self.scenes_of(cuts)
        patterns = list(dict.fromkeys(clip.pattern for scene in scenes for clip in scene.clips))
        long_patterns = sum(1 for _, _, steps, _ in patterns if len(steps) > self._longest)
        cost = (long_patterns, len(patterns) + SCENE_COST * len(scenes) + OFF_THE_BAR_COST * off)
        return Cut(
            scenes=scenes, patterns=patterns, lengths_changed=lengths_changed, too_low=too_low, controls_moved=controls_moved,
            long_patterns=long_patterns, cost=cost,
        )

    def best_cut(self):
        """Return the cheapest cut of every phrase length tried, the first tried winning a tie."""
        return min((self.cut(length) for length in self.phrase_lengths()), key=lambda cut: cut.cost)
