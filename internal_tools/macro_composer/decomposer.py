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

"""A set's data written as a MacroComposer input, so that an existing song can be read, changed and composed again.

Each pattern becomes the plainest part that composes back to the same pattern: a tune's lines, a drum's hits, or, where a
pattern holds something neither can say, the pattern as written. Where a part's velocities are a few plain values moved by
the rhythm, the part is written plain and listed under shaped with the song's feel, which is found by trying each.
"""

from collections import Counter
from fractions import Fraction

from composer import (AUTHOR, BANDS, BARS, CHAINS, DESCRIPTION, DEVICE, DRUM_TRACKS, FEEL, FLUIDSYNTH, FORM, GENERATORS, GENRE, GM_SOUND, GROOVE,
                      INSTRUMENT, INSTRUMENTS, LOOP, NAME, NOTES, ONCE, PART, PARTS, PATTERN, PATTERNS, PLAY, PROTECTED, RAW, REAL_TIME, REPEAT, SCALE,
                      SCALES, SCENE, SCENES, SETTINGS, SHAPED, SONGS, TEMPO, TIME_SIGNATURE, TITLE, TRACKS, VERSION, WITH, bars_of, pattern_of,
                      players_of, scene_of, signature_of)
from notation import DEFAULT_STEP_SIZE, DRUM, HITS, LINES, LOUD, NotWritable, OCTAVE, SOFT, STEP, STEP_SIZE, VELOCITY, drum_hits, kept_rows, tune_lines
from shaping import FEELS, is_compound, role_of, shaped, unshaped

SONG_SETTINGS = (TEMPO, SCALE, GENRE, GROOVE, TIME_SIGNATURE, TRACKS, SCENES)
SET_SETTINGS = (VERSION, TITLE, DESCRIPTION, AUTHOR, NOTES, REAL_TIME, PROTECTED, SCALES, PATTERNS, CHAINS, INSTRUMENTS, SONGS)
CLIP_SETTINGS = (PATTERN, REPEAT, LOOP, CHAINS)
BAND = 'band'
# A band is what at least this share of the scenes play alike, when that is at least this many tracks.
BAND_SHARE = Fraction(1, 2)
SMALLEST_BAND = 2

ERR_ONE_SONG = 'a MacroComposer input holds one song, and the set holds {}'


def normal(pattern):
    """A pattern with only the rows that say anything and its step size written, so that two can be compared."""
    rows = {name: value for name, value in pattern.items() if not isinstance(value, list)}
    rows.setdefault(STEP_SIZE, DEFAULT_STEP_SIZE)
    rows[STEP_SIZE] = str(rows[STEP_SIZE])
    rows.update(kept_rows({name: value for name, value in pattern.items() if isinstance(value, list)}))
    return rows


def written_part(*, pattern, signature, velocities=None):
    """A pattern as a tune's or a drum's part, or NotWritable."""
    step = str(pattern.get(STEP_SIZE, DEFAULT_STEP_SIZE))
    if pattern.get(DRUM):
        drum, hits, loud, soft = drum_hits(pattern=pattern, velocities=velocities)
        part = {DRUM: drum, STEP: step, LOUD: loud}
        if soft != loud:
            part[SOFT] = soft
        part[HITS] = hits
        return part
    lines, octave, velocity = tune_lines(pattern=pattern, bar=int(signature / Fraction(step)), velocities=velocities)
    return {STEP: step, OCTAVE: octave, VELOCITY: velocity, LINES: lines}


def written_out(part):
    """How many of a part's notes write their velocity out, which a plainer part has fewer of."""
    return sum(1 for line in part.get(LINES, []) for note in line if VELOCITY in note)


def plain_part(*, pattern, signature):
    """A pattern as a part that composes back to it with no shaping, or None."""
    try:
        part = written_part(pattern=pattern, signature=signature)
    except (NotWritable, KeyError, ValueError):
        return None
    return part if normal(pattern_of(part)) == normal(pattern) else None


def shaped_part(*, pattern, signature, role, feel, compound):
    """A pattern as a plain part that the feel shapes back into it, or None."""
    if not role or not pattern.get(VELOCITY):
        return None
    before = unshaped(pattern=pattern, role=role, feel=feel, signature=signature, compound=compound)
    try:
        part = written_part(pattern=pattern, signature=signature, velocities=before)
    except (NotWritable, KeyError, ValueError):
        return None
    again = pattern_of(part)
    again[VELOCITY] = shaped(pattern=again, role=role, feel=feel, signature=signature, compound=compound)
    return part if normal(again) == normal(pattern) else None


def better(*, shaped_one, plain_one):
    """Whether the shaped part says the pattern more plainly than the plain part does."""
    if shaped_one is None:
        return False
    return plain_one is None or written_out(shaped_one) < written_out(plain_one)


def parts_for(*, patterns, players, signature, feel, compound):
    """Every pattern as a part under one feel, and the names of the parts the feel shapes."""
    parts = {}
    shaped_names = []
    for name, pattern in patterns.items():
        plain_one = plain_part(pattern=pattern, signature=signature)
        role = role_of(pattern=pattern, tracks=players.get(name, []))
        shaped_one = shaped_part(pattern=pattern, signature=signature, role=role, feel=feel, compound=compound)
        if better(shaped_one=shaped_one, plain_one=plain_one):
            parts[name] = shaped_one
            shaped_names.append(name)
        else:
            parts[name] = plain_one or {RAW: pattern}
    return parts, shaped_names


def played_of(clip):
    """A set's clip as what a track plays, without its timing: a part's name where the clip only loops it."""
    played = {PART: clip[PATTERN]}
    if clip.get(CHAINS):
        played[CHAINS] = list(clip[CHAINS])
    others = {name: value for name, value in clip.items() if name not in CLIP_SETTINGS}
    if others:
        played[SETTINGS] = others
    return played


def timed(*, played, clip):
    """What a track plays with the clip's own timing written."""
    played = dict(played)
    if REPEAT in clip:
        played[REPEAT] = clip[REPEAT]
    elif not clip.get(LOOP):
        played[ONCE] = True
    return played


def short(played):
    return played[PART] if list(played) == [PART] else played


def scene_bars(*, scene, patterns, signature):
    for clip in scene[TRACKS].values():
        if REPEAT in clip:
            return clip[REPEAT] * bars_of(pattern=patterns[clip[PATTERN]], signature=signature)
    return None


def whole(number):
    return int(number) if number.denominator == 1 else float(number)


def entry_of(*, scene, patterns, signature, band):
    """A set's scene as an entry of the form, with its bars and loops where that says the same and each clip's timing where it does not."""
    plays = {track: played_of(clip) for track, clip in scene[TRACKS].items()}
    settings = {name: value for name, value in scene.items() if name not in (NAME, TRACKS)}
    bars = scene_bars(scene=scene, patterns=patterns, signature=signature)
    uses_band = bool(band) and all(track in plays and short(plays[track]) == played for track, played in band.items())
    for with_band in ([True, False] if uses_band else [False]):
        entry = {SCENE: scene[NAME]}
        if bars is not None:
            entry[BARS] = whole(bars)
        if with_band:
            entry[WITH] = [BAND]
        entry[PLAY] = {track: short(played) for track, played in plays.items() if not (with_band and track in band)}
        if settings:
            entry[SETTINGS] = settings
        try:
            if bars is not None and scene_of(entry=entry, bands={BAND: band or {}}, patterns=patterns, signature=signature)[TRACKS] == scene[TRACKS]:
                return entry
        except ValueError:
            pass
    entry = {SCENE: scene[NAME], PLAY: {track: short(timed(played=plays[track], clip=clip)) for track, clip in scene[TRACKS].items()}}
    if settings:
        entry[SETTINGS] = settings
    return entry


def band_of(scenes):
    """What most scenes play alike, as a band for the form to reuse, or nothing."""
    counts = Counter()
    for scene in scenes:
        for track, clip in scene[TRACKS].items():
            played = short(played_of(clip))
            if isinstance(played, str):
                counts[(track, played)] += 1
    kept = {}
    for (track, played), count in counts.items():
        if count >= BAND_SHARE * len(scenes) and track not in kept:
            kept[track] = played
    return kept if len(kept) >= SMALLEST_BAND else {}


def instrument_sound(instrument):
    if instrument == {DEVICE: FLUIDSYNTH}:
        return None
    if set(instrument) == {DEVICE, GM_SOUND} and instrument[DEVICE] == FLUIDSYNTH:
        return instrument[GM_SOUND]
    return instrument


def decomposed(data):
    """A set's data as an input."""
    if len(data[SONGS]) != 1:
        raise ValueError(ERR_ONE_SONG.format(len(data[SONGS])))
    (name, song), = data[SONGS].items()
    signature = signature_of(song)
    compound = is_compound(song.get(TIME_SIGNATURE))
    players = players_of(song[SCENES])
    tried = {feel: parts_for(patterns=data[PATTERNS], players=players, signature=signature, feel=feel, compound=compound) for feel in FEELS}
    feel = max(FEELS, key=lambda each: len(tried[each][1]))
    parts, shaped_names = tried[feel]
    given = {NAME: name}
    for optional in (TITLE, DESCRIPTION, AUTHOR):
        if optional in data:
            given[optional] = data[optional]
    given.update({GENRE: song[GENRE], NOTES: data.get(NOTES, ''), SCALES: data[SCALES], SCALE: song[SCALE], TEMPO: song[TEMPO]})
    for optional in (TIME_SIGNATURE, GROOVE):
        if optional in song:
            given[optional] = song[optional]
    if shaped_names:
        given[FEEL] = feel
        given[SHAPED] = shaped_names
    given[INSTRUMENTS] = {instrument: instrument_sound(settings) for instrument, settings in data[INSTRUMENTS].items()}
    given[TRACKS] = {track: settings[INSTRUMENT] for track, settings in song[TRACKS].items()}
    given[DRUM_TRACKS] = [track for track, settings in song[TRACKS].items() if settings.get(DRUM)]
    generators = {section: value for section, value in data.items() if section not in SET_SETTINGS}
    if generators:
        given[GENERATORS] = generators
    if data.get(CHAINS):
        given[CHAINS] = data[CHAINS]
    given[PARTS] = parts
    band = band_of(song[SCENES])
    given[FORM] = [entry_of(scene=scene, patterns=data[PATTERNS], signature=signature, band=band) for scene in song[SCENES]]
    if any(BAND in entry.get(WITH, []) for entry in given[FORM]):
        given[BANDS] = {BAND: band}
    return given


def same_music(*, one, other):
    """Whether two sets' data play the same: everything but the version, with each pattern compared by the rows that say anything."""
    def comparable(data):
        kept = {name: value for name, value in data.items() if name != VERSION}
        kept[PATTERNS] = {name: normal(pattern) for name, pattern in data[PATTERNS].items()}
        return kept
    return comparable(one) == comparable(other)
