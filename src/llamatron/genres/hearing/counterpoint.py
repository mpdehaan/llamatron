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

"""How a song's lines move against one another, found from its notes: between every pair of melodic lines, at each moment both
move, whether they move in contrary, oblique, similar or parallel motion, how often they move in parallel fifths or octaves,
and how independent their rhythms are. The measures of counterpoint, kept as measures of every style, not a rule for all."""

from bisect import bisect_right

from llamatron.genres.measures.traits import VoiceLeading

PERFECT_INTERVALS = (0, 7)
OCTAVE = 12
PER_HUNDRED = 100
MIN_NOTES = 8


def line_of(track):
    """Return a track's notes as one line of (start, pitch), the highest note of each onset."""
    highest = {}
    for note in track.notes:
        if note.begins not in highest or note.pitch > highest[note.begins]:
            highest[note.begins] = note.pitch
    return sorted(highest.items())


def pitch_at(*, line, time, starts):
    """Return the pitch a line sounds at a time: its latest onset at or before the time."""
    place = bisect_right(starts, time) - 1
    return line[place][1] if place >= 0 else None


def motions(*, upper, lower):
    """Return the motions between two lines at each onset of either where both have sounded: (kind counts, parallels, together, apart)."""
    upper_starts = [start for start, _ in upper]
    lower_starts = [start for start, _ in lower]
    onsets = sorted(set(upper_starts) | set(lower_starts))
    contrary = oblique = similar = parallel_perfect = together = 0
    previous = None
    for time in onsets:
        high = pitch_at(line=upper, time=time, starts=upper_starts)
        low = pitch_at(line=lower, time=time, starts=lower_starts)
        if high is None or low is None:
            continue
        both = time in upper_starts and time in lower_starts
        together += both
        if previous is not None:
            high_move = high - previous[0]
            low_move = low - previous[1]
            if high_move == 0 and low_move == 0:
                pass
            elif high_move == 0 or low_move == 0:
                oblique += 1
            elif (high_move > 0) != (low_move > 0):
                contrary += 1
            else:
                similar += 1
                interval = (high - low) % OCTAVE
                if interval in PERFECT_INTERVALS and (previous[0] - previous[1]) % OCTAVE == interval:
                    parallel_perfect += 1
        previous = (high, low)
    return contrary, oblique, similar, parallel_perfect, together, len(onsets)


def voice_leading_of(performance):
    """Return how the song's melodic lines move against one another, or None with fewer than two lines."""
    lines = [line_of(track) for track in performance.melodic()]
    lines = [line for line in lines if len(line) >= MIN_NOTES]
    if len(lines) < 2:
        return None
    contrary = oblique = similar = parallel_perfect = together = onsets = 0
    for place, first in enumerate(lines):
        for second in lines[place + 1:]:
            upper, lower = (first, second) if sum(pitch for _, pitch in first) / len(first) >= sum(pitch for _, pitch in second) / len(second) else (second, first)
            counts = motions(upper=upper, lower=lower)
            contrary += counts[0]
            oblique += counts[1]
            similar += counts[2]
            parallel_perfect += counts[3]
            together += counts[4]
            onsets += counts[5]
    moving = contrary + oblique + similar
    if not moving:
        return None
    return VoiceLeading(contrary=round(contrary / moving, 3), oblique=round(oblique / moving, 3), parallels=round(parallel_perfect / moving * PER_HUNDRED, 2),
                        independence=round(1 - together / onsets, 3) if onsets else 0.0)
