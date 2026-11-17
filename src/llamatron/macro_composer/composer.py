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

"""The MacroComposer: a song's input, structured data that says what to play, made into a set's data.

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

from llamatron.macro_composer.loudness import USUAL_DYNAMICS
from llamatron.macro_composer.notation import ACCENT, DEFAULT_STEP_SIZE, GHOST, HITS, LINES, LOUD, OCTAVE, SOFT, STEP, STEPS, STEP_SIZE, VELOCITY, DRUM, drum_rows, tune_rows
from llamatron.macro_composer.shaping import is_compound, role_of, shaped
from llamatron.strings.errors import ERR_NO_CLIP_FITS

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
    if HITS in part:
        return drum_rows(drum=part[DRUM], hits=part[HITS], loud=part[LOUD], soft=part.get(SOFT, part[LOUD]), step_size=part.get(STEP, DEFAULT_STEP_SIZE),
                         accent=part.get(ACCENT), ghost=part.get(GHOST))
    step = part.get(STEP, DEFAULT_STEP_SIZE)
    levels = {level: part[level] for level in (ACCENT, SOFT, GHOST) if level in part}
    return tune_rows(lines=part[LINES], octave=part[OCTAVE], velocity=part[VELOCITY], step_size=step, levels=levels)


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
    return Fraction(pattern[STEPS]) * Fraction(str(pattern.get(STEP_SIZE, DEFAULT_STEP_SIZE))) / signature


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
                raise ValueError(ERR_NO_CLIP_FITS.format(entry[SCENE], entry[BARS]))
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


def composed(*, given, version):
    """An input as a set's data."""
    signature = signature_of(given)
    patterns = {name: pattern_of(part) for name, part in given[PARTS].items()}
    scenes = [scene_of(entry=entry, bands=given.get(BANDS, {}), patterns=patterns, signature=signature) for entry in given[FORM]]
    players = players_of(scenes)
    for name in given.get(SHAPED, []):
        role = role_of(pattern=patterns[name], tracks=players.get(name, []))
        if role:
            dynamics = next((given[DYNAMICS][track] for track in players.get(name, []) if track in given.get(DYNAMICS, {})), USUAL_DYNAMICS)
            patterns[name][VELOCITY] = shaped(pattern=patterns[name], role=role, feel=given[FEEL], signature=signature, compound=is_compound(given.get(TIME_SIGNATURE)), dynamics=dynamics)
    data = {VERSION: version}
    for optional in (TITLE, DESCRIPTION, AUTHOR):
        if optional in given:
            data[optional] = given[optional]
    data.update({NOTES: given.get(NOTES, ''), REAL_TIME: True, PROTECTED: True, SCALES: given[SCALES], PATTERNS: patterns})
    data.update(given.get(GENERATORS, {}))
    if given.get(CHAINS):
        data[CHAINS] = given[CHAINS]
    data[INSTRUMENTS] = {name: instrument_of(sound) for name, sound in given[INSTRUMENTS].items()}
    song = {TEMPO: given[TEMPO], SCALE: given[SCALE], GENRE: given[GENRE]}
    for optional in (GROOVE, TIME_SIGNATURE):
        if optional in given:
            song[optional] = given[optional]
    for optional in (SUBGENRE, VARIANT):
        if given.get(optional) is not None:
            song[optional] = given[optional]
    drums = set(given.get(DRUM_TRACKS, []))
    song[TRACKS] = {track: ({DRUM: True, INSTRUMENT: instrument} if track in drums else {INSTRUMENT: instrument}) for track, instrument in given[TRACKS].items()}
    song[SCENES] = scenes
    data[SONGS] = {given[NAME]: song}
    return data
