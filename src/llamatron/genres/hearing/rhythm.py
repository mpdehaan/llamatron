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

"""A song's rhythm, found from its notes: its drums sorted into the kit's voices by General MIDI's drum notes, each bar written
as a groove on a grid of twelve steps a beat, the grooves it plays most, the bars that break from them at phrase ends as fills
and what kind, the voice that keeps time; and its groove: how swung its offbeats are, how far ahead of or behind the grid its
notes fall, how many of its drum hits are ghost notes, and its feel."""

from collections import Counter
from statistics import median

from llamatron.genres.measures.comparing import groove_gap
from llamatron.genres.measures.drum_patterns import COMMON_STEPS_PER_BEAT, DrumPattern, Voice
from llamatron.genres.measures.traits import Drums, Feel, FillKind, Groove

# General MIDI's drum notes, by the voice they're sorted into; any other drum note is percussion.
VOICE_OF_NOTE = {
    35: Voice.KICK, 36: Voice.KICK, 38: Voice.SNARE, 40: Voice.SNARE, 37: Voice.RIM, 39: Voice.CLAP, 42: Voice.HATS, 44: Voice.HATS,
    46: Voice.OPEN_HAT, 51: Voice.RIDE, 53: Voice.RIDE, 59: Voice.RIDE, 49: Voice.CRASH, 52: Voice.CRASH, 55: Voice.CRASH, 57: Voice.CRASH,
    41: Voice.TOMS, 43: Voice.TOMS, 45: Voice.TOMS, 47: Voice.TOMS, 48: Voice.TOMS, 50: Voice.TOMS,
}
GROOVES_KEPT = 3
FILL_GAP = 0.35
PHRASE_BARS = 4
GHOST_SHARE = 0.55
STRONG = 2
SOFT = 1
STRAIGHT_SWING = 0.5
OFFBEAT_LOW = 0.4
OFFBEAT_HIGH = 0.8
SHUFFLE_SWING = 0.6
HUNDREDTHS = 100
TIMEKEEPERS = (Voice.HATS, Voice.RIDE, Voice.CRASH, Voice.TOMS, Voice.PERCUSSION)


# Words in a drum track's name that say which voice it plays, since a drum track may play any note: a drum rack or a
# sampler maps notes as it likes, and llamatron's drum tracks are often one voice each, named for it.
VOICE_WORDS = (
    (('kick', 'bass drum', 'bd', 'boom'), Voice.KICK), (('snare', 'sd', 'snap'), Voice.SNARE), (('clap',), Voice.CLAP),
    (('rim', 'stick', 'cross'), Voice.RIM), (('open',), Voice.OPEN_HAT), (('hat', 'hh', 'hihat', 'shaker', 'tick'), Voice.HATS),
    (('ride',), Voice.RIDE), (('crash', 'cymbal', 'splash', 'china'), Voice.CRASH), (('tom', 'timpani'), Voice.TOMS),
)
MIXED_KIT_PITCHES = 3


def voice_named(name):
    """Return the voice a drum track's name says it plays, or None."""
    words = (name or '').lower()
    for keys, voice in VOICE_WORDS:
        if any(key in words for key in keys):
            return voice
    return None


def voice_by_rhythm(*, track, beats_per_bar):
    """Return the voice a one-voice drum track plays judged by where its hits fall: on the downbeats the kick, on two and
    four the backbeat, and dense the timekeeper."""
    places = [note.begins % beats_per_bar for note in track.notes]
    if not places:
        return Voice.PERCUSSION
    downbeats = sum(1 for place in places if place in (0.0, 2.0)) / len(places)
    backbeats = sum(1 for place in places if place in (1.0, 3.0)) / len(places)
    offbeats = sum(1 for place in places if place % 1) / len(places)
    if offbeats >= 0.4:
        return Voice.HATS
    if backbeats > downbeats:
        return Voice.SNARE
    return Voice.KICK


def track_voices(*, track, beats_per_bar):
    """Return how to sort a drum track's hits into voices: by its name when it names a voice, by General MIDI's drum notes
    when it plays a kit's worth of them, and otherwise by where its hits fall in the bar."""
    named = voice_named(track.name)
    if named is not None:
        return lambda pitch: named
    pitches = {note.pitch for note in track.notes}
    if len(pitches) >= MIXED_KIT_PITCHES or pitches <= set(VOICE_OF_NOTE):
        return lambda pitch: VOICE_OF_NOTE.get(pitch, Voice.PERCUSSION)
    judged = voice_by_rhythm(track=track, beats_per_bar=beats_per_bar)
    return lambda pitch: judged


def drum_hits(performance):
    """Return every drum hit as (time in beats, voice, velocity), each track's voices found from its name, its notes or its
    rhythm."""
    hits = []
    for track in performance.drums():
        voice_of = track_voices(track=track, beats_per_bar=float(performance.beats_per_bar))
        hits += [(note.begins, voice_of(note.pitch), note.velocity) for note in track.notes]
    return hits


def bar_grooves(performance):
    """Return each bar's drums as a groove on the common grid, by the bar, leaving out bars without drums."""
    beats = int(round(float(performance.beats_per_bar)))
    steps = beats * COMMON_STEPS_PER_BEAT
    loudest = max((velocity for _, _, velocity in drum_hits(performance)), default=1)
    bars = {}
    for time, voice, velocity in drum_hits(performance):
        bar = performance.bar_of(time)
        place = min(steps - 1, round((time - bar * float(performance.beats_per_bar)) * COMMON_STEPS_PER_BEAT))
        voices = bars.setdefault(bar, {})
        line = voices.setdefault(voice, [0] * steps)
        line[place] = max(line[place], SOFT if velocity < GHOST_SHARE * loudest else STRONG)
    return {bar: DrumPattern(name=None, beats=beats, steps_per_beat=COMMON_STEPS_PER_BEAT, voices={voice: tuple(line) for voice, line in voices.items()})
            for bar, voices in bars.items()}


def pattern_key(pattern):
    return tuple(sorted(pattern.voices.items()))


def fill_kind(pattern):
    """Return what kind of fill a bar plays, from which voices crowd its last beats."""
    tail = len(next(iter(pattern.voices.values()))) // 2
    counts = {voice: sum(1 for weight in steps[tail:] if weight) for voice, steps in pattern.voices.items()}
    if counts.get(Voice.TOMS, 0) >= 3:
        return FillKind.TOM_DESCENT
    if counts.get(Voice.SNARE, 0) >= 4:
        return FillKind.SNARE_RUN
    if counts.get(Voice.CRASH, 0) >= 2:
        return FillKind.CRASH_PUNCTUATION
    return FillKind.SPARSE


def drums_of(performance):
    """Return the song's drums as a trait: its most played bars as grooves, how often a phrase ends in a fill and which kinds,
    and the voice that keeps time; or None for a song without drums."""
    grooves = bar_grooves(performance)
    if not grooves:
        return None
    counts = Counter(pattern_key(pattern) for pattern in grooves.values())
    by_key = {pattern_key(pattern): pattern for pattern in grooves.values()}
    main = [by_key[key] for key, _ in counts.most_common(GROOVES_KEPT)]
    fills = []
    before_scenes = {performance.bar_of(start) - 1 for start in performance.scene_starts[1:]}
    phrase_ends = [bar for bar in grooves if bar % PHRASE_BARS == PHRASE_BARS - 1 or bar in before_scenes]
    for bar in phrase_ends:
        if min(groove_gap(mine=grooves[bar], theirs=pattern) for pattern in main) > FILL_GAP:
            fills.append(fill_kind(grooves[bar]))
    timekeeping = Counter()
    for _, voice, _ in drum_hits(performance):
        if voice in TIMEKEEPERS:
            timekeeping[voice] += 1
    return Drums(grooves=tuple(main), fills=round(len(fills) / len(phrase_ends), 2) if phrase_ends else 0.0,
                 fill_kinds=tuple(kind for kind, _ in Counter(fills).most_common()), timekeeper=timekeeping.most_common(1)[0][0] if timekeeping else None)


def place_in_beat(time):
    return time - int(time)


def swing_of(performance):
    """Return how swung the song's offbeats are: the median place in the beat of the notes falling between its middle and its
    last quarter, 0.5 straight and about 0.67 a triplet swing."""
    places = [place_in_beat(note.begins) for track in performance.tracks for note in track.notes
              if OFFBEAT_LOW < place_in_beat(note.begins) < OFFBEAT_HIGH]
    return round(median(places), 3) if places else STRAIGHT_SWING


def push_of(performance):
    """Return how far the song's notes fall from the common grid, ahead (above 0) or behind (below 0), in hundredths of a beat;
    looseness is the mean distance either way."""
    offsets = []
    for track in performance.tracks:
        for note in track.notes:
            time = note.begins * COMMON_STEPS_PER_BEAT
            offsets.append((round(time) - time) / COMMON_STEPS_PER_BEAT)
    if not offsets:
        return 0.0, 0.0
    return round(sum(offsets) / len(offsets) * HUNDREDTHS, 2), round(sum(abs(offset) for offset in offsets) / len(offsets) * HUNDREDTHS, 2)


def ghosts_of(performance):
    """Return the share of the drum hits that are ghost notes: hits far softer than the loudest hit of the same voice in the
    same bar, as a snare's quiet notes between its backbeats are. A voice played softer than another, the hats under the snare,
    is not a ghost, and neither is a quiet section, which were once both counted."""
    hits = drum_hits(performance)
    if not hits:
        return 0.0
    bar = float(performance.beats_per_bar)
    loudest = {}
    for time, voice, velocity in hits:
        place = (int(time // bar), voice)
        loudest[place] = max(loudest.get(place, 0), velocity)
    return round(sum(1 for time, voice, velocity in hits if velocity < GHOST_SHARE * loudest[(int(time // bar), voice)]) / len(hits), 3)


def groove_of(*, performance, drums):
    """Return the song's groove as a trait."""
    swing = swing_of(performance)
    push, _ = push_of(performance)
    feel = Feel.SHUFFLE if swing >= SHUFFLE_SWING else Feel.STRAIGHT
    main = drums.main() if drums is not None else None
    if main is not None and half_time(main):
        feel = Feel.HALF_TIME
    return Groove(swing=swing, push=push, ghosts=ghosts_of(performance), feel=feel, feel_changes=None)


def half_time(pattern):
    """Return whether a groove's backbeat falls only on the third beat of four."""
    snare = pattern.voices.get(Voice.SNARE) or pattern.voices.get(Voice.CLAP) or pattern.voices.get(Voice.RIM)
    if snare is None or pattern.beats != 4:
        return False
    beat = pattern.steps_per_beat
    return snare[2 * beat] and not snare[beat] and not snare[3 * beat]
