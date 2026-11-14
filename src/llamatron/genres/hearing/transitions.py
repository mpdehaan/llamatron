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

"""How a song moves from one scene to the next, the sawtooth the user hears when a song jumps from one state to another with
nothing to join them: at each scene's start, which the render knows, how abrupt the change is (energy, register, density and
how the harmony moves) and what prepares it (a fill, a pickup stepping across the bar line, a dominant resolving into the new
section, a drop-out, a build towards the new level), as songwriters and arrangers join sections."""

from dataclasses import dataclass

from llamatron.genres.hearing.harmony import PITCH_CLASSES, chord_of, weights_by_span

WINDOW_BARS = 2
REGISTER_SCALE = 12
# How much each measure counts in a change's abruptness: energy, register, density and harmony.
ABRUPT_WEIGHTS = (0.4, 0.2, 0.2, 0.2)
FILL_RISE = 1.5
DROP_SHARE = 0.25
BUILD_SHARE = 0.5
STEP = 2
ABRUPT = 0.4
PREPARED = 0.5
DOMINANT = 7
SMOOTH_MOVES = {0: 0.0, 5: 0.1, 7: 0.1, 2: 0.3, 10: 0.3, 1: 0.5, 11: 0.5, 3: 0.6, 4: 0.6, 8: 0.6, 9: 0.6, 6: 1.0}


class Sign:
    """What prepares a change of scene."""

    FILL = 'fill'
    PICKUP = 'pickup'
    DOMINANT = 'dominant'
    DROP_OUT = 'drop-out'
    BUILD = 'build'


@dataclass(slots=True, kw_only=True, frozen=True)
class Transition:
    """One change of scene: the bar it falls on, counted from 0; how abrupt it is, from 0 seamless to 1 a jump in everything;
    how well it's prepared, from 0 to 1; and the signs that prepare it."""

    bar: int
    abrupt: float
    prepared: float
    signs: tuple

    def is_unprepared_jump(self):
        return self.abrupt >= ABRUPT and self.prepared < PREPARED


def notes_between(*, tracks, start, end):
    return [note for track in tracks for note in track.notes if start <= note.begins < end]


def notes_sounding(*, tracks, start, end):
    """Return the notes sounding at any moment between two times, held notes included."""
    return [note for track in tracks for note in track.notes if note.begins < end and note.ends > start]


def mean_pitch(notes):
    return sum(note.pitch for note in notes) / len(notes) if notes else None


def transition_at(*, performance, start, levels):
    """Return the change at one scene's start."""
    bar_beats = float(performance.beats_per_bar)
    bar = performance.bar_of(start)
    window = WINDOW_BARS * bar_beats
    melodic = performance.melodic()
    before = notes_between(tracks=melodic, start=start - window, end=start)
    after = notes_between(tracks=melodic, start=start, end=start + window)
    energy_before = sum(levels[max(0, bar - WINDOW_BARS):bar]) / max(1, len(levels[max(0, bar - WINDOW_BARS):bar]))
    energy_after = sum(levels[bar:bar + WINDOW_BARS]) / max(1, len(levels[bar:bar + WINDOW_BARS]))
    energy = abs(energy_after - energy_before)
    pitch_before = mean_pitch(before)
    pitch_after = mean_pitch(after)
    register = min(1.0, abs(pitch_after - pitch_before) / REGISTER_SCALE) if pitch_before is not None and pitch_after is not None else 0.0
    density = abs(len(after) - len(before)) / max(len(after), len(before), 1)
    last = chord_of(weights_by_span(notes=[note for note in before if note.ends > start - 1], span=1.0, count=int(start) + 1)[int(start) - 1]) if start >= 1 else None
    first = chord_of(weights_by_span(notes=after, span=1.0, count=int(start) + 1)[int(start)])
    harmony = SMOOTH_MOVES[(first[0] - last[0]) % PITCH_CLASSES] if last is not None and first is not None else 0.0
    abrupt = sum(measure * weight for measure, weight in zip((energy, register, density, harmony), ABRUPT_WEIGHTS))
    signs = []
    drums = performance.drums()
    hits_last_beat = len(notes_between(tracks=drums, start=start - 1, end=start))
    hits_average = len(notes_between(tracks=drums, start=start - window, end=start - 1)) / max(1.0, window - 1)
    if drums and hits_last_beat >= FILL_RISE * max(hits_average, 1.0):
        signs.append(Sign.FILL)
    crossing = [note for note in before if note.begins >= start - 0.5]
    if crossing and after:
        landing = min(after, key=lambda note: note.begins)
        if any(abs(landing.pitch - note.pitch) <= STEP for note in crossing):
            signs.append(Sign.PICKUP)
    if last is not None and first is not None and (last[0] - first[0]) % PITCH_CLASSES == DOMINANT:
        signs.append(Sign.DOMINANT)
    last_beat = notes_sounding(tracks=performance.tracks, start=start - 1, end=start)
    first_beat = notes_sounding(tracks=performance.tracks, start=start, end=start + 1)
    if first_beat and len(last_beat) <= DROP_SHARE * len(first_beat):
        signs.append(Sign.DROP_OUT)
    lead_in = levels[max(0, bar - 4):bar]
    if len(lead_in) >= 2 and energy_after > energy_before and lead_in[-1] - lead_in[0] >= BUILD_SHARE * (energy_after - lead_in[0]) > 0:
        signs.append(Sign.BUILD)
    prepared = min(1.0, len(signs) * 0.5) if abrupt > 0 else 1.0
    return Transition(bar=bar, abrupt=round(abrupt, 3), prepared=round(prepared, 3), signs=tuple(signs))


def transitions_of(*, performance, levels):
    """Return every change of scene after the first scene, in order."""
    return tuple(transition_at(performance=performance, start=start, levels=levels) for start in performance.scene_starts[1:]
                 if 0 < start < float(performance.length))
