# llamatron: a Python language and framework for producing MIDI clips.
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

"""Reads a song written in the YAML song format, and builds a Song from it.

A file has song settings, named scales, patterns, tracks, arps, auto_ratchets, chains and scenes. A
pattern holds one list per row, all as long as its step count, which mirrors the pattern editor:
degree, duration, accidental, octave, chord, velocity, probability, ratchet and glide. A step with
no degree is a rest, and a step with no duration uses the song's default, so every step takes time.
Octaves are absolute, and are numbered the way Live displays them. A drum pattern has note letters
instead of degrees.

A scene launches clips and has no length of its own. A clip plays its pattern repeat times and then
stays silent while the others finish, unless it has loop: true, which plays it until the longest
clip that doesn't loop has finished. At least one clip in a scene must not loop. A clip with a
repeat above 1 can morph into a second pattern across its repeats. Scales come from the scene, and
then the song. Probability is rolled here from the song's seed, so that a song always renders the
same. See the examples folder for complete songs, and raise SongFileError for anything wrong.

A clip can take its rhythm from one pattern with rhythm_from, and its notes from another with
notes_from. They match step by step, and the notes carry on across repeats and skip any rests, so
lists of different lengths drift apart. A pattern's direction sets the order its steps play in, and
a clip's direction overrides it. A pattern's source_pattern gives its grab row somewhere to take
notes from: the source moves on every step, and steps marked grab play its note. A step's
ratchet_offset moves each ratchet slice further along the scale. A step's note_add and velocity_add
add to running totals that apply from that step on, across the clip's repeats, and clear at the
pattern's accumulator_limit.
"""

import random
import re
from dataclasses import replace
from fractions import Fraction
from math import ceil

import yaml

from llamatron.chord import Chord, ChordType
from llamatron.generators.arp import Arp, ChordOrder
from llamatron.generators.blend import Blend, BlendMode
from llamatron.generators.auto_ratchet import AutoRatchet, divide
from llamatron.note import Degree, Note, Rest
from llamatron.scale import Scale, ScaleType
from llamatron.song import Clip, Scene, Song, Track


# The song settings that have defaults, as they're used when a file leaves them out.
DEFAULT_LENGTH = '1/16'
GRANULARITIES = ['1/16', '1/32', '1/64', '1/128', '1/256']
DEFAULT_OCTAVE = 3
DEFAULT_DRUM_OCTAVE = 1
DEFAULT_SEED = 1
DEFAULT_VELOCITY = 127
DEFAULT_PROBABILITY = 100
DEFAULT_RATCHET = 1

# Files and the UI number octaves the way Live displays them, where MIDI note 60 is C3. Notes in
# this project number them two higher, so that same note is C5.
LIVE_OCTAVE_OFFSET = 2
MIN_LIVE_OCTAVE, MAX_LIVE_OCTAVE = -2, 8

PATTERN_ROWS = [
    'degree', 'duration', 'accidental', 'octave', 'chord', 'velocity', 'probability', 'glide',
    'ratchet', 'ratchet_offset', 'note_add', 'velocity_add', 'grab',
]
DEFAULT_ACCUMULATOR_LIMIT = 36
MAX_OCTAVE_CHANGE = 10
FORWARD = 'forward'
DIRECTIONS = [FORWARD, 'reverse_a', 'reverse_b', 'alternate', 'pendulum', 'random', 'brownian', 'eitherway']
NOTE_LETTERS = 'ABCDEFG'
ACCIDENTALS = {'#': 1, 'b': -1}
# Chords with a fixed sound, and how many notes the ones that are built from the scale have.
FIXED_CHORDS = {
    'M': ChordType.MAJOR, 'm': ChordType.MINOR, 'M7': ChordType.MAJOR7, 'm7': ChordType.MINOR7,
    'dim': ChordType.DIMINISHED, 'sus4': ChordType.SUS4,
}
SCALE_CHORDS = {'3': 3, '7': 4}
# The generators that a chain step can use by name, and the section of a file that names them.
NAMED_GENERATORS = {'arp': 'arps', 'auto_ratchet': 'auto_ratchets'}
# Which pattern rows a grab takes, and which a clip's notes_from takes. Everything else belongs to
# the rhythm.
GRAB_ROWS = ('degree', 'accidental', 'octave', 'chord')
NOTE_ROWS = (*GRAB_ROWS, 'note_add')
CHORD_SYMBOLS = [*FIXED_CHORDS, *SCALE_CHORDS]


class SongFileError(Exception):
    """A problem with a song file, described in a way that points to where to fix it."""


# The kinds of value a generator setting can hold, and the choices that some settings have.
WHOLE, LENGTH, WHOLES = 'whole number', 'length', 'list of whole numbers'
ORDERS = {member.name.lower(): member for member in ChordOrder}
MORPH_STYLES = {member.name.lower(): member for member in BlendMode}

# Each generator's class, its settings, and which of them are required.
GENERATORS = {
    'arp': (Arp, {'step': LENGTH, 'order': ORDERS, 'seed': WHOLE}, ['step']),
    'auto_ratchet': (AutoRatchet, {'counts': WHOLES}, ['counts']),
}


def _with_sound(played, **changes):
    """Return a note or chord with changes to how every note in it plays."""
    if isinstance(played, Chord):
        return Chord([replace(note, **changes) for note in played.notes])
    return replace(played, **changes)


def _number(value, where):
    if isinstance(value, bool):
        raise SongFileError(f'{where}: expected a number, got {value!r}')
    try:
        return Fraction(str(value))
    except (ValueError, ZeroDivisionError):
        raise SongFileError(f'{where}: expected a number like 2 or 1/8, got {value!r}') from None


def _walk_order(count, direction):
    """Return the steps of a direction that repeats exactly, or None if it's chosen as it goes."""
    forward, backward = list(range(count)), list(range(count - 1, -1, -1))
    if direction == FORWARD:
        return forward
    if direction == 'reverse_a':
        return [0, *backward[:-1]]
    if direction == 'reverse_b':
        return backward
    if direction == 'alternate':
        return forward + backward
    if direction == 'pendulum':
        return forward + backward[1:-1]
    return None


class _Play:
    """Remembers where a clip is in each list of steps, carrying on across its repeats.

    Choices come from a random generator made from the song's seed, so a render is always the same.
    """

    def __init__(self, choices):
        self.choices = choices
        self.places = {}
        self.totals = {}

    def accumulate(self, kind, amount, limit):
        """Add to a running total that lasts the whole clip, and clear it if it passes its limit."""
        total = self.totals.get(kind, 0) + (amount or 0)
        if abs(total) > limit:
            total = 0
        self.totals[kind] = total
        return total

    def next(self, key, count, direction):
        """Return the next step to play from a list of count steps."""
        key = (*key, direction)
        order = _walk_order(count, direction)
        if order is not None:
            taken = self.places.get(key, 0)
            self.places[key] = taken + 1
            return order[taken % len(order)]
        if direction == 'random':
            return self.choices.randrange(count)
        if key not in self.places:
            self.places[key] = 0
            return 0
        chance = self.choices.random()
        if direction == 'brownian':
            move = 1 if chance < 0.5 else (-1 if chance < 0.75 else 0)
        else:
            move = 1 if chance < 0.5 else -1
        self.places[key] = (self.places[key] + move) % count
        return self.places[key]


class _Stanza:
    """One scene in the song, after repeats have been written out."""

    def __init__(self, number, name, scale, tempo, cells):
        self.number, self.name, self.scale = number, name, scale
        self.tempo, self.cells = tempo, cells


class _Context:
    """What's needed while writing one cell."""

    def __init__(self, stanza, cell, scale, track):
        self.stanza, self.cell, self.scale, self.track = stanza, cell, scale, track


class SongBuilder:
    """Turns the contents of a song file into a Song."""

    def __init__(self, data):
        if not isinstance(data, dict):
            raise SongFileError('a song file must have settings like tempo, scale and scenes')
        self._check_keys(data, 'the file', {
            'tempo', 'scale', 'scales', 'seed', 'default_length', 'granularity', 'default_octave',
            'default_drum_octave', 'patterns', 'arps', 'auto_ratchets', 'tracks', 'chains', 'scenes',
        })
        for key in ['tempo', 'tracks', 'scenes']:
            if key not in data:
                raise SongFileError(f'the file needs a {key} section')
        self.tempo = _number(data['tempo'], 'tempo')
        self.scales = data.get('scales') or {}
        if not isinstance(self.scales, dict):
            raise SongFileError('scales: expected named scales like main: { root: F, type: minor }')
        for name in self.scales:
            self._named_scale(name, LIVE_OCTAVE_OFFSET + DEFAULT_OCTAVE, f'scale {name!r}')
        self.scale_text = data.get('scale')
        self._check_listed_scale(self.scale_text, 'scale')
        self.seed = data.get('seed', DEFAULT_SEED)
        self.default_length = self._positive_length(data.get('default_length', DEFAULT_LENGTH), 'default_length')
        granularity = data.get('granularity', GRANULARITIES[0])
        if granularity not in GRANULARITIES:
            raise SongFileError(f'granularity must be one of {GRANULARITIES}, got {granularity!r}')
        self.default_octave = self._octave(data.get('default_octave', DEFAULT_OCTAVE), 'default_octave')
        self.default_drum_octave = self._octave(data.get('default_drum_octave', DEFAULT_DRUM_OCTAVE), 'default_drum_octave')
        self.patterns = data.get('patterns') or {}
        for name, pattern in self.patterns.items():
            self._check_pattern(name, pattern)
        self.tracks = self._read_tracks(data['tracks'])
        self.named_generators = {step: data.get(section) or {} for step, section in NAMED_GENERATORS.items()}
        self.chains = data.get('chains') or {}
        self._check_chains()
        self.stanzas = self._read_scenes(data['scenes'])
        self.resolved = {}
        self.lengths = {}

    def build(self):
        tempo = float(self.tempo)
        song = Song(tempo=int(tempo) if tempo.is_integer() else tempo)
        tracks = {name: song.add_track(Track(name)) for name in self.tracks}
        for stanza in self.stanzas:
            scene = song.add_scene(self._scene(stanza))
            for name in self.tracks:
                clip = self._cell(stanza, name)
                if clip is not None:
                    song.set_clip(scene, tracks[name], clip)
        return song

    def estimate(self):
        """Return how long each written-out scene and its clips last, in seconds.

        Each item is (number, seconds or None, {track: seconds or None}, problem or None). This
        runs the same code as build, so that it can't disagree with a render, but a problem in
        one scene only affects that scene.
        """
        result = []
        for stanza in self.stanzas:
            tempo = self.tempo if stanza.tempo is None else stanza.tempo
            whole_notes_to_seconds = Fraction(240) / tempo
            clips, problem, seconds = {}, None, None
            try:
                seconds = self._scene_length(stanza) * whole_notes_to_seconds
                for track in stanza.cells:
                    clips[track] = self._cell(stanza, track).total_length() * whole_notes_to_seconds
            except SongFileError as error:
                problem = str(error)
            result.append((stanza.number, seconds, clips, problem))
        return result

    def _scene(self, stanza):
        tempo = None if stanza.tempo is None else float(stanza.tempo)
        return Scene(stanza.name, tempo=tempo)

    # Reading each section.

    def _check_keys(self, data, where, allowed):
        unknown = sorted(set(data) - allowed)
        if unknown:
            raise SongFileError(f'{where}: unknown setting {unknown[0]!r}, expected one of {sorted(allowed)}')

    def _scale(self, root, kind, octave, where):
        if not isinstance(root, str) or not re.fullmatch(r'[A-G][#b]?', root):
            raise SongFileError(f'{where}: expected a root note like F or Bb, got {root!r}')
        kind_name = str(kind).strip().upper().replace(' ', '_')
        if kind_name not in ScaleType.__members__:
            names = ', '.join(sorted(name.lower() for name in ScaleType.__members__))
            raise SongFileError(f'{where}: unknown scale type {kind!r}, expected one of: {names}')
        return Scale(Note(root, octave), ScaleType[kind_name])

    def _named_scale(self, name, octave, where):
        scale = self.scales[name]
        if not isinstance(scale, dict) or set(scale) != {'root', 'type'}:
            raise SongFileError(f'{where}: expected a root and a type, like {{ root: F, type: minor }}, got {scale!r}')
        return self._scale(scale['root'], scale['type'], octave, where)

    def _check_listed_scale(self, name, where):
        if name is not None and name not in self.scales:
            raise SongFileError(f'{where}: no scale called {name!r}')

    def _positive_length(self, value, where):
        length = _number(value, where)
        if length <= 0:
            raise SongFileError(f'{where}: a length must be more than zero, got {value!r}')
        return length

    def _octave(self, value, where):
        if type(value) is not int or not MIN_LIVE_OCTAVE <= value <= MAX_LIVE_OCTAVE:
            raise SongFileError(f'{where}: an octave must be a whole number from {MIN_LIVE_OCTAVE} to {MAX_LIVE_OCTAVE}, got {value!r}')
        return value

    def _check_pattern(self, name, pattern):
        where = f'pattern {name!r}'
        if not isinstance(pattern, dict):
            raise SongFileError(f'{where}: expected settings like steps, degree and duration')
        self._check_keys(pattern, where, {'steps', 'drum', 'direction', 'source_pattern', 'accumulator_limit', *PATTERN_ROWS})
        limit = pattern.get('accumulator_limit', DEFAULT_ACCUMULATOR_LIMIT)
        if type(limit) is not int or limit < 1:
            raise SongFileError(f'{where}: accumulator_limit must be a whole number of 1 or more, got {limit!r}')
        self._check_direction(pattern.get('direction', FORWARD), where)
        if 'source_pattern' in pattern and pattern['source_pattern'] not in self.patterns:
            raise SongFileError(f'{where}: source_pattern: no pattern called {pattern["source_pattern"]!r}')
        steps = pattern.get('steps')
        if type(steps) is not int or steps < 1:
            raise SongFileError(f'{where}: steps must be a whole number of 1 or more, got {steps!r}')
        drum = pattern.get('drum', False)
        if type(drum) is not bool:
            raise SongFileError(f'{where}: drum must be true or false, got {drum!r}')
        for row in PATTERN_ROWS:
            values = pattern.get(row)
            if values is None:
                continue
            if not isinstance(values, list) or len(values) != steps:
                raise SongFileError(f'{where}: {row} must be a list of {steps} values, got {values!r}')
            for value in values:
                if value is not None:
                    self._check_step_value(row, value, drum, where)

    def _check_direction(self, direction, where):
        if direction not in DIRECTIONS:
            raise SongFileError(f'{where}: direction must be one of {DIRECTIONS}, got {direction!r}')

    def _check_step_value(self, row, value, drum, where):
        problem = None
        if row == 'degree':
            if drum and (not isinstance(value, str) or value not in NOTE_LETTERS or len(value) != 1):
                problem = 'in a drum pattern, must be a note letter from A to G'
            if not drum and (type(value) is not int or value < 1):
                problem = 'must be a scale degree of 1 or more'
        elif row == 'duration':
            self._positive_length(value, f'{where}, duration')
        elif row == 'accidental' and value not in ACCIDENTALS:
            problem = 'must be # or b'
        elif row == 'octave':
            self._octave(value, f'{where}, octave')
        elif row == 'chord':
            if drum:
                problem = 'isn\'t used in a drum pattern'
            elif str(value) not in CHORD_SYMBOLS:
                problem = f'must be one of {CHORD_SYMBOLS}'
        elif row == 'velocity' and (type(value) is not int or not 1 <= value <= 127):
            problem = 'must be a whole number from 1 to 127'
        elif row == 'probability' and (type(value) is not int or not 0 <= value <= 100):
            problem = 'must be a whole number from 0 to 100'
        elif row == 'ratchet' and (type(value) is not int or value < 1):
            problem = 'must be a whole number of 1 or more'
        elif row in ('glide', 'grab') and type(value) is not bool:
            problem = 'must be true or false'
        elif row in ('ratchet_offset', 'note_add', 'velocity_add') and type(value) is not int:
            problem = 'must be a whole number'
        if problem:
            raise SongFileError(f'{where}: {row} {problem}, got {value!r}')

    def _read_tracks(self, tracks):
        if not isinstance(tracks, list) or len(set(tracks)) != len(tracks):
            raise SongFileError('tracks: expected a list of different track names')
        return list(tracks)

    def _check_chains(self):
        for name, chain in self.chains.items():
            if not isinstance(chain, list):
                raise SongFileError(f'chain {name!r}: expected a list of generators')
            for step in chain:
                if not isinstance(step, dict) or len(step) != 1:
                    raise SongFileError(f'chain {name!r}: each step must be one generator, got {step!r}')
                generator = next(iter(step))
                if generator not in GENERATORS:
                    raise SongFileError(
                        f'chain {name!r}: unknown generator {generator!r}, expected one of {sorted(GENERATORS)}'
                    )
                # A chain step only names a generator, whose settings are in its own section.
                if not isinstance(step[generator], str) or step[generator] not in self.named_generators[generator]:
                    raise SongFileError(f'chain {name!r}: no {generator} called {step[generator]!r}')

    def _read_scenes(self, scenes):
        if not isinstance(scenes, list):
            raise SongFileError('scenes: expected a list of scenes')
        stanzas = []
        for index, data in enumerate(scenes, start=1):
            where = f'scene entry {index}'
            if not isinstance(data, dict):
                raise SongFileError(f'{where}: expected settings like name and tracks')
            self._check_keys(data, where, {'name', 'repeat', 'scale', 'tempo', 'tempo_start', 'tempo_end', 'tracks'})
            repeat = data.get('repeat', 1)
            if type(repeat) is not int or repeat < 1:
                raise SongFileError(f'{where}: repeat must be a positive whole number, got {repeat!r}')
            cells = data.get('tracks') or {}
            for track, cell in cells.items():
                self._check_cell(track, cell, where)
            scale = data.get('scale') or self.scale_text
            self._check_listed_scale(data.get('scale'), where)
            for place in range(repeat):
                name = str(data.get('name', f'Scene {len(stanzas) + 1}'))
                if repeat > 1:
                    name = f'{name} {place + 1}'
                tempo = self._scene_tempo(data, place, repeat, where)
                stanzas.append(_Stanza(len(stanzas) + 1, name, scale, tempo, cells))
        return stanzas

    def _scene_tempo(self, data, place, repeat, where):
        if 'tempo' in data:
            return _number(data['tempo'], where)
        if 'tempo_start' in data or 'tempo_end' in data:
            if 'tempo_start' not in data or 'tempo_end' not in data:
                raise SongFileError(f'{where}: needs both tempo_start and tempo_end')
            start = _number(data['tempo_start'], where)
            end = _number(data['tempo_end'], where)
            return start + (end - start) * (Fraction(place, repeat - 1) if repeat > 1 else 0)
        return None

    def _check_cell(self, track, cell, where):
        if track not in self.tracks:
            raise SongFileError(f'{where}: no track called {track!r}, expected one of {sorted(self.tracks)}')
        if not isinstance(cell, dict):
            raise SongFileError(f'{where}, track {track!r}: expected settings like {{ pattern: a }}, got {cell!r}')
        where = f'{where}, track {track!r}'
        self._check_keys(cell, where, {'pattern', 'chain', 'loop', 'repeat', 'direction', 'morph_to', 'morph_style', 'rhythm_from', 'notes_from'})
        self._check_direction(cell.get('direction', FORWARD), where)
        for setting in ['rhythm_from', 'notes_from']:
            if setting in cell and cell[setting] not in self.patterns:
                raise SongFileError(f'{where}: {setting}: no pattern called {cell[setting]!r}')
        repeat = cell.get('repeat', 1)
        if type(repeat) is not int or repeat < 1:
            raise SongFileError(f'{where}: repeat must be a positive whole number, got {repeat!r}')
        if not isinstance(cell.get('loop', False), bool):
            raise SongFileError(f'{where}: loop must be true or false, got {cell["loop"]!r}')
        if ('morph_to' in cell) != ('morph_style' in cell):
            raise SongFileError(f'{where}: a morph needs both morph_to and morph_style')
        if 'morph_to' in cell:
            if repeat < 2:
                raise SongFileError(f'{where}: a morph needs a repeat of 2 or more')
            if cell['morph_to'] not in self.patterns:
                raise SongFileError(f'{where}: no pattern called {cell["morph_to"]!r}')
            if cell['morph_style'] not in MORPH_STYLES:
                raise SongFileError(f'{where}: morph_style must be one of {sorted(MORPH_STYLES)}, got {cell["morph_style"]!r}')
        if 'pattern' not in cell:
            raise SongFileError(f'{where}: needs a pattern')
        if cell['pattern'] not in self.patterns:
            raise SongFileError(f'{where}: no pattern called {cell["pattern"]!r}')
        if 'chain' in cell and cell['chain'] not in self.chains:
            raise SongFileError(f'{where}: no chain called {cell["chain"]!r}')

    # Writing each clip.

    def _scene_length(self, stanza):
        """Return how long a scene lasts, which is its longest clip that doesn't loop."""
        if stanza.number in self.lengths:
            return self.lengths[stanza.number]
        where = f'scene {stanza.number} ({stanza.name})'
        if stanza.cells and all(cell.get('loop') for cell in stanza.cells.values()):
            raise SongFileError(f'{where}: every clip is set to loop, so the scene would never end. Turn off loop on at least one clip.')
        length = Fraction(0)
        for track, cell in stanza.cells.items():
            if not cell.get('loop'):
                length = max(length, self._cell(stanza, track).total_length())
        self.lengths[stanza.number] = length
        return length

    def _cell(self, stanza, track):
        key = (stanza.number, track)
        if key in self.resolved:
            return self.resolved[key]
        cell = stanza.cells.get(track)
        if cell is None:
            return None
        where = f'scene {stanza.number}, track {track!r}'
        octave = self._clip_octave(cell)
        scale = None if stanza.scale is None else self._named_scale(stanza.scale, octave, where)
        context = _Context(stanza, cell, scale, track)
        loop = bool(cell.get('loop'))
        fill = self._scene_length(stanza) if loop else None
        try:
            clip = self._source(context, where, fill)
            if clip.total_length() > 0 and 'chain' in cell:
                for index, step in enumerate(self.chains[cell['chain']]):
                    clip = self._generator(step, context, cell['chain'], index).generate(clip)
            end = fill if loop else clip.total_length()
            notes = clip.section(0, end).notes if end > 0 else []
            clip = Clip(name=stanza.name, notes=notes, scale=scale, loop=loop)
        except (ValueError, TypeError) as error:
            raise SongFileError(f'{where}: {error}') from error
        self.resolved[key] = clip
        return clip

    def _clip_octave(self, cell):
        """Return the octave for the root of this clip's scale.

        It's the octave of the first note the clip plays, in this project's numbering.
        """
        pattern = self.patterns[cell.get('notes_from', cell['pattern'])]
        octave = next((value for value in (pattern.get('octave') or []) if value is not None), self.default_octave)
        return octave + LIVE_OCTAVE_OFFSET

    def _source(self, context, where, fill):
        """Return what a clip plays before any chains, filling a length if one is given."""
        cell, stanza = context.cell, context.stanza
        rolls = random.Random(f'{self.seed}/{stanza.number}/{context.track}')
        play = _Play(random.Random(f'{self.seed}/{stanza.number}/{context.track}/direction'))
        repeat = cell.get('repeat', 1)
        notes, total, place = [], Fraction(0), 0
        while (place < repeat) if fill is None else (total < fill):
            played = self._frame(cell, place % repeat, repeat, context, where, rolls, play)
            length = sum((Fraction(position.length) for position in played), Fraction(0))
            if length == 0:
                break
            notes += played
            total += length
            place += 1
        clip = Clip(notes=notes, scale=context.scale)
        return clip.section(0, fill) if fill else clip

    def _frame(self, cell, place, repeat, context, where, rolls, play):
        """Return one pass through a clip's pattern, part way through any morph.

        Only the first pattern takes a rhythm, notes or a direction from the clip, and a morph's
        target plays as it's written.
        """
        notes = self._one_pass(
            cell.get('rhythm_from', cell['pattern']), cell.get('notes_from', cell['pattern']),
            cell.get('direction'), context, where, rolls, play,
        )
        if 'morph_to' not in cell or not notes:
            return notes
        clip = Clip(notes=notes, scale=context.scale)
        target = self._one_pass(cell['morph_to'], cell['morph_to'], None, context, where, rolls, play)
        amount = Fraction(place, repeat - 1) * 100
        target = self._looped(target, context, clip.total_length())
        return Blend(target, amount, mode=MORPH_STYLES[cell['morph_style']]).generate(clip).played_notes()

    def _looped(self, notes, context, length):
        """Return a clip of notes that repeat or are cut to last a length."""
        clip = Clip(notes=notes, scale=context.scale)
        if clip.total_length() > 0:
            clip = clip.repeated(ceil(length / clip.total_length()))
        return Clip(notes=clip.section(0, length).notes, scale=context.scale)

    def _row(self, pattern, row, step):
        return pattern[row][step] if pattern.get(row) else None

    def _pattern_length(self, pattern):
        return sum(
            (self.default_length if self._row(pattern, 'duration', step) is None else _number(self._row(pattern, 'duration', step), 'duration')
             for step in range(pattern['steps'])),
            Fraction(0),
        )

    def _one_pass(self, rhythm_name, notes_name, direction, context, where, rolls, play):
        """Return one pass through a rhythm, as notes, chords and rests.

        Whichever order the steps play in, a pass lasts as long as the rhythm pattern does, so that
        a direction can't change how long a clip or scene is. The last step is cut to fit.
        """
        for name in (rhythm_name, notes_name):
            if name not in self.patterns:
                raise SongFileError(f'{where}: no pattern called {name!r}')
        rhythm, notes = self.patterns[rhythm_name], self.patterns[notes_name]
        combined = rhythm_name != notes_name
        note_steps = [step for step in range(notes['steps']) if self._row(notes, 'degree', step) is not None]
        source_name = notes.get('source_pattern')
        source = self.patterns.get(source_name)

        def order(pattern):
            return direction or pattern.get('direction', FORWARD)

        length = self._pattern_length(rhythm)
        where = f'pattern {notes_name!r}'
        positions, time = [], Fraction(0)
        while time < length:
            step = play.next(('rhythm', rhythm_name), rhythm['steps'], order(rhythm))
            # A source pattern keeps moving on every step, whether or not this one takes from it.
            source_step = play.next(('source', source_name), source['steps'], order(source)) if source else None
            values = {row: self._row(rhythm, row, step) for row in PATTERN_ROWS}
            duration = self.default_length if values['duration'] is None else _number(values['duration'], where)
            time += duration
            if values['degree'] is None or (combined and not note_steps):
                positions.append(Rest(duration))
                continue
            note_step = step
            if combined:
                note_step = note_steps[play.next(('notes', notes_name), len(note_steps), order(notes))]
                values.update({row: self._row(notes, row, note_step) for row in NOTE_ROWS})
            drum = notes.get('drum', False)
            if source and self._row(notes, 'grab', note_step) and self._row(source, 'degree', source_step) is not None:
                values.update({row: self._row(source, row, source_step) for row in GRAB_ROWS})
                drum = source.get('drum', False)
            totals = (
                play.accumulate('note', values['note_add'], notes.get('accumulator_limit', DEFAULT_ACCUMULATOR_LIMIT)),
                play.accumulate('velocity', values['velocity_add'], rhythm.get('accumulator_limit', DEFAULT_ACCUMULATOR_LIMIT)),
            )
            positions += self._step(values, drum, context, where, rolls, *totals)
        if time > length:
            positions = Clip(notes=positions, scale=context.scale).section(0, length).notes
        return positions

    def _step(self, values, drum, context, where, rolls, note_total, velocity_total):
        """Return what one step plays, as more than one position if it ratchets."""
        length = self.default_length if values['duration'] is None else _number(values['duration'], where)
        default = self.default_drum_octave if drum else self.default_octave
        octave = (default if values['octave'] is None else values['octave']) + LIVE_OCTAVE_OFFSET
        velocity = DEFAULT_VELOCITY if values['velocity'] is None else values['velocity']
        velocity = max(min(velocity + velocity_total, 127), 1)
        ratchet = values['ratchet'] or DEFAULT_RATCHET
        offset = values['ratchet_offset'] or 0
        slices = []
        for place in range(ratchet):
            played = self._sound(values, drum, length, octave, note_total + place * offset, context, where)
            slices.append(divide(_with_sound(played, velocity=velocity), ratchet))
        if values['glide']:
            slices[-1] = _with_sound(slices[-1], glide=True)
        probability = DEFAULT_PROBABILITY if values['probability'] is None else values['probability']
        if probability >= 100:
            return slices
        return [
            piece if rolls.random() * 100 < probability else Rest(piece.length)
            for piece in slices
        ]

    def _sound(self, values, drum, length, octave, shift, context, where):
        """Return a step's note or chord, moved by a number of scale degrees or, for drums, half steps.

        A note moved outside the MIDI range goes to the nearest octave that fits.
        """
        def attempt(at_octave):
            if not drum:
                return self._degree_sound(values, length, at_octave, shift, context, where)
            note = Note(values['degree'] + (values['accidental'] or ''), at_octave, length)
            return note.half_step(shift) if shift else note

        changes = [0]
        if shift:
            changes += [change for size in range(1, MAX_OCTAVE_CHANGE + 1) for change in (-size, size)]
        problem = None
        for change in changes:
            try:
                return attempt(octave + change)
            except ValueError as error:
                problem = problem or error
        raise SongFileError(f'{where}: {problem}') from problem

    def _degree_sound(self, values, length, octave, shift, context, where):
        if context.stanza.scale is None:
            raise SongFileError(f'{where}: it uses scale degrees, but scene {context.stanza.number} and the song have no scale')
        scale = self._named_scale(context.stanza.scale, octave, where)
        half_steps = ACCIDENTALS.get(values['accidental'], 0)
        degree = values['degree']
        root = Degree(degree, length, half_steps=half_steps, scale_notes=shift).to_note(scale)
        symbol = None if values['chord'] is None else str(values['chord'])
        if symbol is None:
            return root
        if symbol in FIXED_CHORDS:
            return root.to_chord(FIXED_CHORDS[symbol])
        return Chord([
            Degree(degree + stack * 2, length, half_steps=half_steps, scale_notes=shift).to_note(scale)
            for stack in range(SCALE_CHORDS[symbol])
        ])

    # Building generators.

    def _generator(self, step, context, chain, index):
        name, settings_name = next(iter(step.items()))
        settings = self.named_generators[name][settings_name] or {}
        where = f'chain {chain!r}, {name}'
        generator_class, allowed, required = GENERATORS[name]
        self._check_keys(settings, where, set(allowed))
        values = {key: self._value(settings[key], kind, key, where) for key, kind in allowed.items() if key in settings}
        for setting in required:
            if setting not in values:
                raise SongFileError(f'{where}: needs {setting}')
        if name == 'arp' and 'seed' not in values:
            track = list(self.tracks).index(context.track)
            values['seed'] = self.seed * 1_000_003 + context.stanza.number * 1_009 + track * 31 + index
        return generator_class(**values)

    def _value(self, value, kind, key, where):
        if isinstance(kind, dict):
            if value not in kind:
                raise SongFileError(f'{where}: {key} must be one of {sorted(kind)}, got {value!r}')
            return kind[value]
        if kind == WHOLE:
            if type(value) is not int:
                raise SongFileError(f'{where}: {key} must be a whole number, got {value!r}')
            return value
        if kind == LENGTH:
            return _number(value, where)
        if not isinstance(value, list):
            raise SongFileError(f'{where}: {key} must be a list, got {value!r}')
        return value


def load_song(path):
    """Return a Song from a song file, or raise SongFileError if something's wrong with it."""
    try:
        with open(path, encoding='utf-8') as file:
            data = yaml.safe_load(file)
    except OSError as error:
        raise SongFileError(f'can\'t read {path}: {error.strerror}') from error
    except yaml.YAMLError as error:
        raise SongFileError(f'{path} isn\'t valid YAML: {error}') from error
    return SongBuilder(data).build()
