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

"""A song's shape over time, found from its notes: how its energy rises and falls bar by bar, how many parts play at once, how
much two lines take turns, how much of its material returns, and where it jumps from one state to another with nothing to
prepare the jump (the sawtooth the user hears when scenes change without the music that would join them)."""

from dataclasses import dataclass

from llamatron.genres.measures.comparing import stretched
from llamatron.genres.measures.traits import Energy, Role, Texture

ARC_POINTS = 10
TOP_LEVEL = 10
JUMP = 0.35
# The share of the lowest and of the highest notes left out of a song's span.
SPAN_EDGE = 0.05
PREPARED_RISE = 0.12
SMOOTHING = 2


@dataclass(slots=True, kw_only=True, frozen=True)
class Shape:
    """What a song's shape shows beyond the traits: its energy bar by bar, from 0 to 1; the bars where it jumps with nothing
    preparing the jump, counted from 0; how often the energy turns from rising to falling and back, per eight bars; and the
    share of its bars that differ from every bar before them."""

    energy: tuple
    jumps: tuple
    turns: float
    variety: float


def bar_energy(*, performance):
    """Return each bar's energy, from 0 to 1: how many notes play, how loud, and how many parts."""
    bars = performance.bars()
    counts = [0] * bars
    loudness = [0] * bars
    parts = [set() for _ in range(bars)]
    for track in performance.tracks:
        for note in track.notes:
            bar = min(bars - 1, performance.bar_of(note.begins))
            counts[bar] += 1
            loudness[bar] += note.velocity
            parts[bar].add(track.name)
    raw = [(loudness[bar] / 127) * (1 + len(parts[bar])) for bar in range(bars)]
    smooth = [sum(raw[max(0, bar - SMOOTHING + 1):bar + 1]) / len(raw[max(0, bar - SMOOTHING + 1):bar + 1]) for bar in range(bars)]
    top = max(smooth, default=0) or 1
    return [level / top for level in smooth], parts


def energy_of(levels):
    """Return the song's energy as a trait: its arc at ten points and how far its quietest and loudest stand apart."""
    if not levels:
        return Energy(arc=(), contrast=None)
    ordered = sorted(levels)
    low = ordered[int(0.1 * (len(ordered) - 1))]
    high = ordered[int(0.9 * (len(ordered) - 1))]
    return Energy(arc=tuple(round(level * TOP_LEVEL, 1) for level in stretched(values=levels, count=ARC_POINTS)), contrast=round(high - low, 3))


def span_of(performance):
    """Return how wide a song's notes range, in half steps, from its low notes to its high ones, the few lowest and highest left
    out so that one stray note doesn't set it."""
    pitches = sorted(note.pitch for track in performance.melodic() for note in track.notes)
    if not pitches:
        return None
    return float(pitches[int(len(pitches) * (1 - SPAN_EDGE))] - pitches[int(len(pitches) * SPAN_EDGE)])


def texture_of(*, performance, roles, parts):
    """Return how many parts play at once and how much the lead and another line take turns."""
    average = sum(len(playing) for playing in parts) / len(parts) if parts else 0
    lead = next((track for track, role in roles.items() if role == Role.LEAD), None)
    others = [track for track, role in roles.items() if role in (Role.COUNTER, Role.HARMONY, Role.PAD) and track is not lead]
    turns = 0.0
    if lead is not None and others:
        turns = max(alternation(performance=performance, first=lead, second=other) for other in others)
    notes = sum(len(track.notes) for track in performance.tracks if not track.drum)
    return Texture(parts=round(average, 2), call_and_response=round(turns, 3), density=round(notes / float(performance.length), 2) if performance.length else 0.0,
                   span=span_of(performance))


def alternation(*, performance, first, second):
    """Return the share of bars where one of two lines plays and the other rests, turning from one to the other."""
    playing_first = {performance.bar_of(note.begins) for note in first.notes}
    playing_second = {performance.bar_of(note.begins) for note in second.notes}
    alone = [1 if bar in playing_first and bar not in playing_second else 2 if bar in playing_second and bar not in playing_first else 0
             for bar in range(performance.bars())]
    changes = sum(1 for earlier, later in zip(alone, alone[1:]) if earlier and later and earlier != later)
    either = sum(1 for each in alone if each) or 1
    return min(1.0, 2 * changes / either)


def bar_signatures(performance):
    """Return each bar's content apart from its place in the song: every note's track, place in the bar and pitch."""
    bars = performance.bars()
    signatures = [[] for _ in range(bars)]
    for track in performance.tracks:
        for note in track.notes:
            bar = min(bars - 1, performance.bar_of(note.begins))
            signatures[bar].append((track.name, round((note.begins - bar * float(performance.beats_per_bar)) * 12), note.pitch))
    return [tuple(sorted(signature)) for signature in signatures]


def familiarity_of(performance):
    """Return the share of bars whose content has been heard before in the song."""
    seen = set()
    heard = 0
    signatures = [signature for signature in bar_signatures(performance) if signature]
    for signature in signatures:
        heard += signature in seen
        seen.add(signature)
    return round(heard / len(signatures), 3) if signatures else 0.0


def shape_of(*, levels, performance):
    """Return the song's shape: its energy, its unprepared jumps, how often it turns, and its variety."""
    jumps = []
    for bar in range(1, len(levels)):
        change = levels[bar] - levels[bar - 1]
        if abs(change) >= JUMP:
            before = levels[max(0, bar - 3):bar]
            prepared = len(before) >= 2 and (before[-1] - before[0]) * change > 0 and abs(before[-1] - before[0]) >= PREPARED_RISE
            if not prepared:
                jumps.append(bar)
    blocks = [sum(levels[start:start + 4]) / len(levels[start:start + 4]) for start in range(0, len(levels), 4)]
    directions = [1 if later > earlier else -1 for earlier, later in zip(blocks, blocks[1:]) if later != earlier]
    turns = sum(1 for earlier, later in zip(directions, directions[1:]) if earlier != later)
    signatures = [signature for signature in bar_signatures(performance) if signature]
    return Shape(energy=tuple(round(level, 3) for level in levels), jumps=tuple(jumps), turns=round(turns / max(1, len(levels) / 8), 2),
                 variety=round(len(set(signatures)) / len(signatures), 3) if signatures else 0.0)
