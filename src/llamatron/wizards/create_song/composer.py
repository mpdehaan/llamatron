# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The song wizard: a song's input, structured data that says what to play, made into a set's data.

The input decides the music and the composer decides nothing: it turns each part into a pattern, shapes the velocity of the
parts the input lists by the song's feel, lays the form out as scenes and writes the set's sections. An input holds:

    name, title, description, author, genre, notes      what the song is called and what its notes say
    scales, scale, tempo, time_signature, groove        as a set's song has them
    feel, shaped                                        the style's feel, and the parts whose velocity the feel shapes
    dynamics                                            how far the feel moves a track's notes, where a track says: 0 not at all, 5 as usual, 10 twice as far
    instruments                                         each instrument's General MIDI sound number, or its settings
    tracks, drum_tracks                                 each track's instrument in order, and which tracks are drums
    generators, chains                                  as a set has them
    parts                                               each part: a tune's lines, a drum's hits, or a pattern as written
    bands                                               named groups of what tracks play, for the form to reuse
    form                                                the scenes in order, each with its bars and what plays
"""

from fractions import Fraction

from llamatron.model.objects import naming, sections
from llamatron.user_strings import errors, labels, names
from llamatron.wizards.create_song import loudness, notation
from llamatron.wizards.create_song.notation import drum_rows, tune_rows
from llamatron.wizards.create_song.shaping import is_compound, role_of, shaped

# The fields of an input.
NAME = 'name'
TITLE = 'title'
DESCRIPTION = 'description'
AUTHOR = 'author'
GENRE = 'genre'
SUBGENRE = 'subgenre'
VARIANT = 'variant'
NOTES = 'notes'
SCALES = 'scales'
SCALE = 'scale'
TEMPO = 'tempo'
TIME_SIGNATURE = 'time_signature'
GROOVE = 'groove'
FEEL = 'feel'
SHAPED = 'shaped'
DYNAMICS = 'dynamics'
INSTRUMENTS = 'instruments'
TRACKS = 'tracks'
DRUM_TRACKS = 'drum_tracks'
GENERATORS = 'generators'
CHAINS = 'chains'
PARTS = 'parts'
BANDS = 'bands'
FORM = 'form'
# The fields of a part that is a pattern as written, of a scene and of what a track plays.
RAW = 'raw'
MUTED_TRACKS = 'muted_tracks'
MUTE = 'mute'
SCENE = 'scene'
BARS = 'bars'
WITH = 'with'
PLAY = 'play'
SETTINGS = 'settings'
PART = 'part'
REPEAT = 'repeat'
ONCE = 'once'
# The names a set file uses.
VERSION = 'version'
REAL_TIME = 'real_time'
PROTECTED = 'protected'
PATTERNS = 'patterns'
SONGS = 'songs'
SCENES = 'scenes'
PATTERN = 'pattern'
LOOP = 'loop'
INSTRUMENT = 'instrument'
DEVICE = 'device'
GM_SOUND = 'gm_sound'
FLUIDSYNTH = '*FluidSynth'
WHOLE_BAR = '1'



def signature_of(given):
    return Fraction(str(given.get(TIME_SIGNATURE, WHOLE_BAR)))


def pattern_of(part):
    """A part as a pattern, before any shaping."""
    if RAW in part:
        return dict(part[RAW])
    if notation.HITS in part:
        return drum_rows(drum=part[notation.DRUM], hits=part[notation.HITS], loud=part[notation.LOUD], soft=part.get(notation.SOFT, part[notation.LOUD]), step_size=part.get(notation.STEP, notation.DEFAULT_STEP_SIZE),
                         accent=part.get(notation.ACCENT), ghost=part.get(notation.GHOST))
    step = part.get(notation.STEP, notation.DEFAULT_STEP_SIZE)
    levels = {level: part[level] for level in (notation.ACCENT, notation.SOFT, notation.GHOST) if level in part}
    return tune_rows(lines=part[notation.LINES], octave=part[notation.OCTAVE], velocity=part[notation.VELOCITY], step_size=step, levels=levels)


def clip_of(played):
    """What a track plays in a scene, as a set's clip: a part's name loops, and a mapping says more."""
    if isinstance(played, str):
        return {PATTERN: played, LOOP: True}
    clip = {PATTERN: played[PART]}
    if REPEAT in played:
        clip[REPEAT] = played[REPEAT]
    elif not played.get(ONCE):
        clip[LOOP] = True
    if played.get(CHAINS):
        clip[CHAINS] = list(played[CHAINS])
    clip.update(played.get(SETTINGS, {}))
    return clip


def bars_of(*, pattern, signature):
    return Fraction(pattern[notation.STEPS]) * Fraction(str(pattern.get(notation.STEP_SIZE, notation.DEFAULT_STEP_SIZE))) / signature


def scene_of(*, entry, bands, patterns, signature):
    """A scene of the form as a set's scene: the first clip that divides the scene's bars evenly times the scene, the others loop."""
    plays = {}
    for band in entry.get(WITH, []):
        plays.update(bands[band])
    plays.update(entry.get(PLAY, {}))
    clips = {track: clip_of(played) for track, played in plays.items()}
    if BARS in entry and not any(REPEAT in clip for clip in clips.values()):
        for clip in clips.values():
            repeats = Fraction(entry[BARS]) / bars_of(pattern=patterns[clip[PATTERN]], signature=signature)
            if repeats.denominator == 1 and clip.get(LOOP):
                del clip[LOOP]
                clip[REPEAT] = int(repeats)
                break
        else:
            # A scene whose every clip plays once needs none to time it, where one of them lasts as long as the scene.
            lasting = [clip for clip in clips.values() if LOOP not in clip and bars_of(pattern=patterns[clip[PATTERN]], signature=signature) == entry[BARS]]
            if not lasting:
                raise ValueError(errors.ERR_NO_CLIP_FITS.format(entry[SCENE], entry[BARS]))
    return {NAME: entry[SCENE], **entry.get(SETTINGS, {}), TRACKS: clips}


def instrument_of(given):
    if isinstance(given, dict):
        return dict(given)
    return {DEVICE: FLUIDSYNTH} if given is None else {DEVICE: FLUIDSYNTH, GM_SOUND: given}


def players_of(scenes):
    """The tracks that play each pattern."""
    players = {}
    for scene in scenes:
        for track, clip in scene[TRACKS].items():
            players.setdefault(clip[PATTERN], []).append(track)
    return {pattern: sorted(set(tracks)) for pattern, tracks in players.items()}


def names_apart(*, generators, chains):
    """Return the generators, by section, and the chains, with names no two share, since a set file lists every generator, the
    chains among them, in one list: generators of two kinds that share a name each take their kind's word, as kick rush beside
    kick drag, and a chain that shares a generator's name takes the word chain, as guitar player chain, which runs the
    Musician guitar player. Every chain's steps and every clip follow."""
    plain = [name for items in generators.values() for name in items]
    clashing = {name for name in plain if _times_named(name=name, names=plain) > 1}
    taken = plain + list(chains)
    renamed = {}
    apart = {}
    for section, items in generators.items():
        kind = sections.GENERATOR_KINDS[section]
        apart[section] = {}
        for name, settings in items.items():
            if name in clashing:
                renamed[(kind, name)] = naming.unique_name(base=names.MSG_NAMED_FOR_KIND.format(name=name, word=labels.MSG_KIND_WORDS[kind]), taken=taken)
                taken.append(renamed[(kind, name)])
            apart[section][renamed.get((kind, name), name)] = settings
    held = [name for items in apart.values() for name in items]
    chains_renamed = {}
    for name in chains:
        if naming.is_taken(name=name, taken=held):
            chains_renamed[name] = naming.unique_name(base=names.MSG_NAMED_FOR_KIND.format(name=name, word=names.MSG_CHAIN_WORD), taken=taken)
            taken.append(chains_renamed[name])
    return apart, {chains_renamed.get(name, name): _steps_renamed(steps=steps, renamed=renamed) for name, steps in chains.items()}, chains_renamed


def _step_renamed(*, step, renamed):
    kind, name = next(iter(step.items()))
    return {kind: renamed.get((kind, name), name)}


def composed(*, given, version):
    """An input as a set's data."""
    signature = signature_of(given)
    patterns = {name: pattern_of(part) for name, part in given[PARTS].items()}
    scenes = [scene_of(entry=entry, bands=given.get(BANDS, {}), patterns=patterns, signature=signature) for entry in given[FORM]]
    players = players_of(scenes)
    for name in given.get(SHAPED, []):
        role = role_of(pattern=patterns[name], tracks=players.get(name, []))
        if role:
            dynamics = next((given[DYNAMICS][track] for track in players.get(name, []) if track in given.get(DYNAMICS, {})), loudness.USUAL_DYNAMICS)
            patterns[name][notation.VELOCITY] = shaped(pattern=patterns[name], role=role, feel=given[FEEL], signature=signature, compound=is_compound(given.get(TIME_SIGNATURE)), dynamics=dynamics)
    data = {VERSION: version}
    for optional in (TITLE, DESCRIPTION, AUTHOR):
        if optional in given:
            data[optional] = given[optional]
    data.update({NOTES: given.get(NOTES, ''), REAL_TIME: True, PROTECTED: True, SCALES: given[SCALES], PATTERNS: patterns})
    generators, chains, chains_renamed = names_apart(generators=given.get(GENERATORS, {}), chains=given.get(CHAINS, {}))
    for scene in scenes:
        for clip in scene[TRACKS].values():
            if CHAINS in clip:
                clip[CHAINS] = [chains_renamed.get(chain, chain) for chain in clip[CHAINS]]
    data.update(generators)
    if chains:
        data[CHAINS] = chains
    data[INSTRUMENTS] = {name: instrument_of(sound) for name, sound in given[INSTRUMENTS].items()}
    song = {TEMPO: given[TEMPO], SCALE: given[SCALE], GENRE: given[GENRE]}
    for optional in (GROOVE, TIME_SIGNATURE):
        if optional in given:
            song[optional] = given[optional]
    for optional in (SUBGENRE, VARIANT):
        if given.get(optional) is not None:
            song[optional] = given[optional]
    drums = set(given.get(DRUM_TRACKS, []))
    song[TRACKS] = {track: ({notation.DRUM: True, INSTRUMENT: instrument} if track in drums else {INSTRUMENT: instrument}) for track, instrument in given[TRACKS].items()}
    for track in given.get(MUTED_TRACKS, []):
        song[TRACKS][track][MUTE] = True
    song[SCENES] = scenes
    data[SONGS] = {given[NAME]: song}
    return data


def _times_named(*, name, names):
    """Return how many of the names are the same name as one, capitals aside."""
    return sum(naming.same_name(one=name, other=other) for other in names)


def _steps_renamed(*, steps, renamed):
    """Return a chain's steps with each generator they name renamed as renamed says."""
    return [_step_renamed(step=step, renamed=renamed) for step in steps]
