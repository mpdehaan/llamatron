# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A set's data written as a song wizard input, so that an existing song can be read, changed and composed again.

Each pattern becomes the plainest part that composes back to the same pattern: a tune's lines, a drum's hits, or, where a
pattern holds something neither can say, the pattern as written. Where a part's velocities are a few plain values moved by
the rhythm, the part is written plain and listed under shaped with the song's feel, which is found by trying each.
"""

from collections import Counter
from fractions import Fraction

from llamatron.music_theory.composing import notation, shaping
from llamatron.music_theory.composing.notation import drum_hits, kept_rows, NotWritable
from llamatron.music_theory.composing.shaping import is_compound, role_of, shaped, unshaped
from llamatron.user_strings import errors
from llamatron.wizards.create_song import composer
from llamatron.wizards.create_song.composer import bars_of, pattern_of, players_of, scene_of, signature_of
from llamatron.wizards.create_song.tune_reading import tune_lines

SET_SETTINGS = (composer.VERSION, composer.TITLE, composer.DESCRIPTION, composer.AUTHOR, composer.NOTES, composer.REAL_TIME, composer.PROTECTED, composer.SCALES, composer.PATTERNS, composer.CHAINS, composer.INSTRUMENTS, composer.SONGS)
CLIP_SETTINGS = (composer.PATTERN, composer.REPEAT, composer.LOOP, composer.CHAINS)
BAND = 'band'
# A band is what at least this share of the scenes play alike, when that is at least this many tracks.
BAND_SHARE = Fraction(1, 2)
SMALLEST_BAND = 2



def normal(pattern):
    """A pattern with only the rows that say anything and its step size written, so that two can be compared: its group is
    left out, since a group says only where the Patterns page lists a pattern."""
    rows = {name: value for name, value in pattern.items() if not isinstance(value, list) and name != notation.GROUP}
    rows.setdefault(notation.STEP_SIZE, notation.DEFAULT_STEP_SIZE)
    rows[notation.STEP_SIZE] = str(rows[notation.STEP_SIZE])
    rows.update(kept_rows({name: value for name, value in pattern.items() if isinstance(value, list)}))
    return rows


def written_part(*, pattern, signature, velocities=None):
    """A pattern as a tune's or a drum's part, or NotWritable."""
    step = str(pattern.get(notation.STEP_SIZE, notation.DEFAULT_STEP_SIZE))
    if pattern.get(notation.DRUM):
        drum, hits, loud, soft = drum_hits(pattern=pattern, velocities=velocities)
        part = {notation.DRUM: drum, notation.STEP: step, notation.LOUD: loud}
        if soft != loud:
            part[notation.SOFT] = soft
        part[notation.HITS] = hits
        return part
    lines, octave, velocity = tune_lines(pattern=pattern, bar=int(signature / Fraction(step)), velocities=velocities)
    return {notation.STEP: step, notation.OCTAVE: octave, notation.VELOCITY: velocity, notation.LINES: lines}


def written_out(part):
    """How many of a part's notes write their velocity out, which a plainer part has fewer of."""
    return sum(1 for line in part.get(notation.LINES, []) for note in line if notation.VELOCITY in note)


def plain_part(*, pattern, signature):
    """A pattern as a part that composes back to it with no shaping, or None."""
    try:
        part = written_part(pattern=pattern, signature=signature)
    except (NotWritable, KeyError, ValueError):
        return None
    return part if normal(pattern_of(part)) == normal(pattern) else None


def shaped_part(*, pattern, signature, role, feel, compound):
    """A pattern as a plain part that the feel shapes back into it, or None."""
    if not role or not pattern.get(notation.VELOCITY):
        return None
    before = unshaped(pattern=pattern, role=role, feel=feel, signature=signature, compound=compound)
    try:
        part = written_part(pattern=pattern, signature=signature, velocities=before)
    except (NotWritable, KeyError, ValueError):
        return None
    again = pattern_of(part)
    again[notation.VELOCITY] = shaped(pattern=again, role=role, feel=feel, signature=signature, compound=compound)
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
            parts[name] = plain_one or {composer.RAW: pattern}
    return parts, shaped_names


def played_of(clip):
    """A set's clip as what a track plays, without its timing: a part's name where the clip only loops it."""
    played = {composer.PART: clip[composer.PATTERN]}
    if clip.get(composer.CHAINS):
        played[composer.CHAINS] = list(clip[composer.CHAINS])
    others = {name: value for name, value in clip.items() if name not in CLIP_SETTINGS}
    if others:
        played[composer.SETTINGS] = others
    return played


def timed(*, played, clip):
    """What a track plays with the clip's own timing written."""
    played = dict(played)
    if composer.REPEAT in clip:
        played[composer.REPEAT] = clip[composer.REPEAT]
    elif not clip.get(composer.LOOP):
        played[composer.ONCE] = True
    return played


def short(played):
    return played[composer.PART] if list(played) == [composer.PART] else played


def scene_bars(*, scene, patterns, signature):
    for clip in scene[composer.TRACKS].values():
        if composer.REPEAT in clip:
            return clip[composer.REPEAT] * bars_of(pattern=patterns[clip[composer.PATTERN]], signature=signature)
    return None


def whole(number):
    return int(number) if number.denominator == 1 else float(number)


def entry_of(*, scene, patterns, signature, band):
    """A set's scene as an entry of the form, with its bars and loops where that says the same and each clip's timing where it does not."""
    plays = {track: played_of(clip) for track, clip in scene[composer.TRACKS].items()}
    settings = {name: value for name, value in scene.items() if name not in (composer.NAME, composer.TRACKS)}
    bars = scene_bars(scene=scene, patterns=patterns, signature=signature)
    uses_band = bool(band) and all(track in plays and short(plays[track]) == played for track, played in band.items())
    for with_band in ([True, False] if uses_band else [False]):
        entry = {composer.SCENE: scene[composer.NAME]}
        if bars is not None:
            entry[composer.BARS] = whole(bars)
        if with_band:
            entry[composer.WITH] = [BAND]
        entry[composer.PLAY] = {track: short(played) for track, played in plays.items() if not (with_band and track in band)}
        if settings:
            entry[composer.SETTINGS] = settings
        try:
            if bars is not None and scene_of(entry=entry, bands={BAND: band or {}}, patterns=patterns, signature=signature)[composer.TRACKS] == scene[composer.TRACKS]:
                return entry
        except ValueError:
            pass
    entry = {composer.SCENE: scene[composer.NAME], composer.PLAY: {track: short(timed(played=plays[track], clip=clip)) for track, clip in scene[composer.TRACKS].items()}}
    if settings:
        entry[composer.SETTINGS] = settings
    return entry


def band_of(scenes):
    """What most scenes play alike, as a band for the form to reuse, or nothing."""
    counts = Counter()
    for scene in scenes:
        for track, clip in scene[composer.TRACKS].items():
            played = short(played_of(clip))
            if isinstance(played, str):
                counts[(track, played)] += 1
    kept = {}
    for (track, played), count in counts.items():
        if count >= BAND_SHARE * len(scenes) and track not in kept:
            kept[track] = played
    return kept if len(kept) >= SMALLEST_BAND else {}


def instrument_sound(instrument):
    if instrument == {composer.DEVICE: composer.FLUIDSYNTH}:
        return None
    if set(instrument) == {composer.DEVICE, composer.GM_SOUND} and instrument[composer.DEVICE] == composer.FLUIDSYNTH:
        return instrument[composer.GM_SOUND]
    return instrument


def decomposed(data):
    """A set's data as an input."""
    if len(data[composer.SONGS]) != 1:
        raise ValueError(errors.ERR_ONE_SONG.format(len(data[composer.SONGS])))
    (name, song), = data[composer.SONGS].items()
    signature = signature_of(song)
    compound = is_compound(song.get(composer.TIME_SIGNATURE))
    players = players_of(song[composer.SCENES])
    tried = {feel: parts_for(patterns=data[composer.PATTERNS], players=players, signature=signature, feel=feel, compound=compound) for feel in shaping.FEELS}
    feel = max(shaping.FEELS, key=lambda each: len(tried[each][1]))
    parts, shaped_names = tried[feel]
    given = {composer.NAME: name}
    for optional in (composer.TITLE, composer.DESCRIPTION, composer.AUTHOR):
        if optional in data:
            given[optional] = data[optional]
    given.update({composer.GENRE: song[composer.GENRE], composer.NOTES: data.get(composer.NOTES, ''), composer.SCALES: data[composer.SCALES], composer.SCALE: song[composer.SCALE], composer.TEMPO: song[composer.TEMPO]})
    for optional in (composer.TIME_SIGNATURE, composer.GROOVE, composer.SUBGENRE, composer.VARIANT):
        if optional in song:
            given[optional] = song[optional]
    if shaped_names:
        given[composer.FEEL] = feel
        given[composer.SHAPED] = shaped_names
    given[composer.INSTRUMENTS] = {instrument: instrument_sound(settings) for instrument, settings in data[composer.INSTRUMENTS].items()}
    given[composer.TRACKS] = {track: settings[composer.INSTRUMENT] for track, settings in song[composer.TRACKS].items()}
    given[composer.DRUM_TRACKS] = [track for track, settings in song[composer.TRACKS].items() if settings.get(notation.DRUM)]
    generators = {section: value for section, value in data.items() if section not in SET_SETTINGS}
    if generators:
        given[composer.GENERATORS] = generators
    if data.get(composer.CHAINS):
        given[composer.CHAINS] = data[composer.CHAINS]
    given[composer.PARTS] = parts
    band = band_of(song[composer.SCENES])
    given[composer.FORM] = [entry_of(scene=scene, patterns=data[composer.PATTERNS], signature=signature, band=band) for scene in song[composer.SCENES]]
    if any(BAND in entry.get(composer.WITH, []) for entry in given[composer.FORM]):
        given[composer.BANDS] = {BAND: band}
    return given


def same_music(*, one, other):
    """Whether two sets' data play the same: everything but the version, with each pattern compared by the rows that say anything."""
    def comparable(data):
        kept = {name: value for name, value in data.items() if name != composer.VERSION}
        kept[composer.PATTERNS] = {name: normal(pattern) for name, pattern in data[composer.PATTERNS].items()}
        return kept
    return comparable(one) == comparable(other)
