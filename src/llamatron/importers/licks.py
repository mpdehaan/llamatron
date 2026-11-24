# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Import Wizard's licks: a cut song rewritten as the fewest short licks it is built from, each clip a list of them.

A person learns a song best as short figures put together, and none is easy to learn past four bars, so a lick is 1 to
MOST_BARS bars, a hard limit, and too many licks to remember is as bad as licks too long. Each track's clips are cut into
bars. The cost of a track's licks is the bars of music they hold, plus LICK_PRICE bars for each lick and ENTRY_PRICE bars
for each entry of a clip's list; a run of bars heard in two places or more is tried as a lick of its own, every clip cut
again into the cheapest list, and kept where the cost goes down, so A A A C becomes A, A, A, C, while a pair heard once
stays inside its pattern (the user's design). Every note plays as the cut played it: a bar a gate rings out of, or a slide
runs out of, is never cut from the next; a bar that begins by tying on a note is a lick only where the same note is held
into it; each lick states its CC values at its first step, so it plays alike wherever it is listed.
"""

from typing import NamedTuple

from llamatron.importers import cutting, steps as steps_values
from llamatron.importers.cutting import CutScene, SceneClip
from llamatron.importers.steps import ControlStep, NoteStep
from llamatron.math.rational import Rational

MOST_BARS = 4
LICK_PRICE = 2
ENTRY_PRICE = Rational(1, 4)
# What a lick's first step holds where it begins by tying on what no note is held into, at a clip's start.
NOTHING_HELD = None


class Bar(NamedTuple):
    """One bar of a track's clip: its steps and CC steps at the track's finest step size, the note a tie at its start holds
    on, or NOTHING_HELD, and whether a gate or a slide runs out of it into the next, which keeps the two together."""

    steps: tuple
    controls: tuple
    held: object
    joined: bool


def licked(*, cut, bar):
    """Return a cut with each track's clips rewritten as lists of licks, bar long in whole notes, or the cut as it is for a
    song whose bars are not all one length."""
    clips_by_voice = {}
    for place, scene in enumerate(cut.scenes):
        for clip in scene.clips:
            clips_by_voice.setdefault(clip.voice, []).append((place, clip))
    licked_clips = {}
    for clips in clips_by_voice.values():
        for (place, clip), pieces in zip(clips, track_licks(clips=[clip for _, clip in clips], bar=bar)):
            licked_clips[(place, clip.voice)] = pieces
    scenes = []
    for place, scene in enumerate(cut.scenes):
        clips = []
        for clip in scene.clips:
            pieces = licked_clips[(place, clip.voice)]
            clips.append(clip if pieces is None else SceneClip(clip.voice, pieces, cutting.NO_REPEAT))
        scenes.append(CutScene(
            start=scene.start, end=scene.end, key=scene.key, tempo=scene.tempo, clips=clips, repeat=scene.repeat,
            material=scene.material, letter=scene.letter, families=scene.families,
        ))
    return cutting.Cut(
        scenes=scenes, patterns=cutting.patterns_of(scenes), lengths_changed=cut.lengths_changed, too_low=cut.too_low,
        controls_moved=cut.controls_moved, long_patterns=cut.long_patterns, cost=cut.cost,
    )


def track_licks(*, clips, bar):
    """Return each of a track's clips as the licks it plays, each a pattern as a clip lists it, or None for a clip left as
    it is, where its patterns don't fall in whole bars."""
    fine = min(pattern[1] for clip in clips for pattern in clip.patterns)
    per_bar = bar / fine
    if not per_bar.is_whole():
        return [None] * len(clips)
    drum = clips[0].patterns[0][0]
    bars_of_clips = [clip_bars(clip=clip, fine=fine, per_bar=int(per_bar), bar=bar) for clip in clips]
    vocabulary = chosen_licks(bars_of_clips)
    licks = []
    for bars in bars_of_clips:
        if bars is None:
            licks.append(None)
            continue
        _, pieces = cheapest_list(bars=bars, vocabulary=vocabulary)
        licks.append(tuple(coarsened(drum=drum, piece=piece, fine=fine) for piece in pieces))
    return licks


def clip_bars(*, clip, fine, per_bar, bar):
    """Return a clip's bars (Bar), its patterns played in turn as often as it repeats them, or None where they don't fill
    whole bars."""
    steps, controls = [], []
    for _ in range(clip.repeats):
        for _, size, pattern_steps, pattern_controls in clip.patterns:
            finer_steps, finer_controls = at_finer_steps(steps=pattern_steps, controls=pattern_controls, factor=int(size / fine))
            steps += finer_steps
            controls += finer_controls
    if len(steps) % per_bar:
        return None
    bars = []
    held = NOTHING_HELD
    in_force = None
    rung = rung_bar_lines(steps=steps, per_bar=per_bar, fine=fine)
    for start in range(0, len(steps), per_bar):
        bar_steps = tuple(steps[start:start + per_bar])
        stated, in_force = stated_controls(controls=controls[start:start + per_bar], in_force=in_force)
        joined = start + per_bar in rung or slides_on(controls[start:start + per_bar])
        bars.append(Bar(steps=bar_steps, controls=stated, held=held if bar_steps[0] == steps_values.TIED else NOTHING_HELD, joined=joined))
        held = last_held(steps=bar_steps, held=held)
    return bars


def at_finer_steps(*, steps, controls, factor):
    """Return a pattern's steps and CC steps at a step size factor times finer: a step's note on its first part and ties on
    the rest where it lasts the whole step, a tie or an empty step held over every part, its CC step on its first part."""
    finer_steps, finer_controls = [], []
    for step, control in zip(steps, controls):
        rest = None
        if step == steps_values.TIED or (isinstance(step, NoteStep) and step.gate is None):
            rest = steps_values.TIED
        finer_steps += [step, *[rest] * (factor - 1)]
        finer_controls += [control, *[None] * (factor - 1)]
    return finer_steps, finer_controls


def stated_controls(*, controls, in_force):
    """Return a bar's CC steps with every lane's value stated on its first step, the value in force there where the bar sends
    none, so that a lick plays alike wherever it is listed, and the values in force after it."""
    controls = list(controls)
    if in_force is not None:
        first = controls[0]
        values = list(first.values) if first is not None else [None] * len(in_force)
        for lane, value in enumerate(in_force):
            if values[lane] is None:
                values[lane] = value
        controls[0] = ControlStep(tuple(values), first.slide if first is not None else False)
    for control in controls:
        if control is not None:
            in_force = in_force_after(control=control, in_force=in_force)
    return tuple(controls), in_force


def in_force_after(*, control, in_force):
    """Return each lane's value in force after a CC step: its own where it sends one, else the one before."""
    known = list(in_force or [None] * len(control.values))
    for lane, value in enumerate(control.values):
        if value is not None:
            known[lane] = value
    return tuple(known)


def rung_bar_lines(*, steps, per_bar, fine):
    """Return the bar lines, as the steps they fall on, that a gate rings across, every one a long gate passes and not only
    the first, so that no cut shortens a note held by its gate."""
    rung = set()
    for place, step in enumerate(steps):
        if isinstance(step, NoteStep) and step.gate is not None:
            end = place + Rational(str(step.gate)) / fine
            line = (place // per_bar + 1) * per_bar
            while line < end:
                rung.add(line)
                line += per_bar
    return rung


def slides_on(controls):
    """Return whether a CC slide in a bar runs on to a value after it: its last CC step slides."""
    sent = [control for control in controls if control is not None]
    return bool(sent) and sent[-1].slide


def last_held(*, steps, held):
    """Return the note a bar's last step holds on into the next: its last note, where every step after it ties it on."""
    for step in reversed(steps):
        if isinstance(step, NoteStep):
            return step
        if step != steps_values.TIED:
            return NOTHING_HELD
    return held


def chosen_licks(bars_of_clips):
    """Return the runs of bars chosen as licks of their own: each run heard in two places or more, tried in turn, the most
    heard and longest first, and kept where every clip cut again makes the track's cost go down."""
    heard = {}
    for bars in bars_of_clips:
        for run in runs_of(bars or []):
            heard[run] = heard.get(run, 0) + 1
    tried = sorted((run for run, count in heard.items() if count > 1), key=lambda run: -heard[run] * len(run))
    vocabulary = set()
    clips = [bars for bars in bars_of_clips if bars is not None]
    best = track_cost(clips=clips, vocabulary=vocabulary)
    for run in tried:
        cost = track_cost(clips=clips, vocabulary=vocabulary | {run})
        if cost < best:
            vocabulary.add(run)
            best = cost
    return vocabulary


def runs_of(bars):
    """Return every run of 1 to MOST_BARS bars of a clip that a lick could be: none ending on a bar a gate or slide runs out
    of, nor beginning just after one, where the clip goes on."""
    runs = []
    for length in range(1, MOST_BARS + 1):
        for start in range(len(bars) - length + 1):
            end = start + length
            if (start and bars[start - 1].joined) or (end < len(bars) and bars[end - 1].joined):
                continue
            runs.append(tuple(bars[start:end]))
    return runs


def track_cost(*, clips, vocabulary):
    """Return what a track's licks cost: every clip's cheapest list, and each lick of the vocabulary any list uses."""
    used = set()
    cost = Rational(0)
    for bars in clips:
        clip_cost, pieces = cheapest_list(bars=bars, vocabulary=vocabulary)
        cost += clip_cost
        used.update(piece for piece in pieces if piece in vocabulary)
    return cost + sum(len(piece) + LICK_PRICE for piece in used)


def cheapest_list(*, bars, vocabulary):
    """Return the cheapest list of pieces a clip's bars play as and its cost, each piece 1 to MOST_BARS bars and never cut
    from a bar a gate or slide runs into, but for bars held together longer than that, which are one piece whatever its
    length: a lick of the vocabulary costs its entry, any other piece its bars and price too."""
    best = [(Rational(0), [])] + [(None, None)] * len(bars)
    for end in range(1, len(bars) + 1):
        for length in range(1, end + 1):
            start = end - length
            # Past MOST_BARS only bars held together all through are one piece, so no longer piece ends here once one isn't.
            if length > MOST_BARS and length > 1 and not bars[start].joined:
                break
            # A piece never ends on a bar a gate or slide runs out of, nor begins just after one; inside it, such bars are kept whole.
            if best[start][0] is None or bars[end - 1].joined and end < len(bars):
                continue
            if start and bars[start - 1].joined:
                continue
            if length > MOST_BARS and not all(bar.joined for bar in bars[start:end - 1]):
                continue
            piece = tuple(bars[start:end])
            cost = best[start][0] + ENTRY_PRICE + (0 if piece in vocabulary else length + LICK_PRICE)
            if best[end][0] is None or cost < best[end][0]:
                best[end] = (cost, best[start][1] + [piece])
    return best[-1]


def coarsened(*, drum, piece, fine):
    """Return a lick as a pattern a clip lists, (drum, step size, steps, CC steps), at the longest step size its steps fit:
    every step's note, tie or rest on a step of it, the parts after a note it lasts tied and after a gated note or a rest
    empty, and no CC step between."""
    steps = [step for bar in piece for step in bar.steps]
    controls = [control for bar in piece for control in bar.controls]
    for size in cutting.AUTO_STEP_SIZES:
        factor = size / fine
        if size < fine or not factor.is_whole() or len(steps) % int(factor):
            continue
        fitted = fitted_steps(steps=steps, controls=controls, factor=int(factor))
        if fitted is not None:
            return (drum, size, *fitted)
    return (drum, fine, tuple(steps), tuple(controls))


def fitted_steps(*, steps, controls, factor):
    """Return steps and CC steps at a step size factor times coarser, or None where they don't fit it."""
    coarse_steps, coarse_controls = [], []
    for start in range(0, len(steps), factor):
        first = steps[start]
        rest = steps[start + 1:start + factor]
        if any(control is not None for control in controls[start + 1:start + factor]):
            return None
        held = first == steps_values.TIED or (isinstance(first, NoteStep) and first.gate is None)
        if any(step != (steps_values.TIED if held else None) for step in rest):
            return None
        coarse_steps.append(first)
        coarse_controls.append(controls[start])
    return tuple(coarse_steps), tuple(coarse_controls)
