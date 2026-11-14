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

"""How a song's parts are spaced in pitch, found from its notes: how far the bass sits below the lead, how often parts playing
at once crowd the same register, how often close intervals sound together low down where they turn to mud, and how often the
accompaniment sounds above the lead and masks it, the arranger's checks."""

from bisect import bisect_left
from statistics import median

from llamatron.genres.measures.traits import Role, Spacing

LOW_REGISTER = 48
MUDDY_INTERVAL = 4
HOLE = 24
LOWER_QUARTER = 0.25
UPPER_QUARTER = 0.75


def usual_range(track):
    pitches = sorted(note.pitch for note in track.notes)
    return pitches[int(LOWER_QUARTER * (len(pitches) - 1))], pitches[int(UPPER_QUARTER * (len(pitches) - 1))]


def sounding_by_beat(*, tracks, beats):
    """Return the pitches sounding at the start of each beat, one pass over the notes."""
    result = [[] for _ in range(beats)]
    for track in tracks:
        for note in track.notes:
            first = max(0, int(-(-note.begins // 1)))
            for beat in range(first, min(beats, int(-(-note.ends // 1)))):
                if note.begins <= beat < note.ends:
                    result[beat].append(note.pitch)
    return result


def sounding_at_starts(*, tracks, times):
    """Return the pitches sounding at each of some times, by the time, one pass over the notes for each track."""
    wanted = sorted(set(times))
    result = {time: [] for time in wanted}
    for track in tracks:
        for note in track.notes:
            for time in wanted_between(times=wanted, low=note.begins, high=note.ends):
                result[time].append(note.pitch)
    return result


def wanted_between(*, times, low, high):
    """Return the times from a sorted list at or after low and before high."""
    return times[bisect_left(times, low):bisect_left(times, high)]


def spacing_of(*, performance, roles):
    """Return how the song's parts are spaced, or None for a song with fewer than two melodic parts."""
    melodic = performance.melodic()
    if len(melodic) < 2:
        return None
    lead = next((track for track, role in roles.items() if role == Role.LEAD), None)
    bass = next((track for track, role in roles.items() if role == Role.BASS), None)
    gap = median(note.pitch for note in lead.notes) - median(note.pitch for note in bass.notes) if lead is not None and bass is not None else None
    ranges = [usual_range(track) for track in melodic]
    pairs = [(first, second) for place, first in enumerate(ranges) for second in ranges[place + 1:]]
    crowded = sum(1 for first, second in pairs if min(first[1], second[1]) - max(first[0], second[0]) > 0) / len(pairs)
    beats = int(float(performance.length))
    muddy = 0
    hollow = 0
    by_beat = sounding_by_beat(tracks=melodic, beats=beats)
    for beat in range(beats):
        sounding = sorted(set(by_beat[beat]))
        low = [pitch for pitch in sounding if pitch < LOW_REGISTER]
        if any(0 < higher - lower <= MUDDY_INTERVAL for lower, higher in zip(low, low[1:])):
            muddy += 1
        if any(higher - lower > HOLE for lower, higher in zip(sounding, sounding[1:])):
            hollow += 1
    masked = 0
    if lead is not None:
        others = [track for track in melodic if track is not lead and roles.get(track) != Role.BASS]
        heard = sounding_at_starts(tracks=others, times=[note.begins for note in lead.notes])
        for note in lead.notes:
            if any(pitch > note.pitch for pitch in heard[note.begins]):
                masked += 1
    return Spacing(bass_to_lead=gap, crowding=round(crowded, 3), mud=round(muddy / beats, 3) if beats else 0.0,
                   masking=round(masked / len(lead.notes), 3) if lead is not None and lead.notes else 0.0, hollow=round(hollow / beats, 3) if beats else 0.0)
