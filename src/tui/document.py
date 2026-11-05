# noose6: a Python language and framework for producing MIDI clips.
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

"""The song being edited in the text UI: its data, and everything that changes or reads it.

The data is exactly what a song file holds, so that saving only ever writes it out. Nothing here
draws anything, and nothing is saved or rendered unless one of those methods is called.
"""

import contextlib
import io
import os
from fractions import Fraction

import yaml

from src.cli import replace_output
from src.renderers.ableton_project import AbletonProject
from src.renderers.clip_tree import ClipTree
from src.note import Note
from src.scale import ScaleType
from src.song import Song
from src.song_file import (
    DEFAULT_DRUM_OCTAVE, DEFAULT_LENGTH, DEFAULT_OCTAVE, DEFAULT_PROBABILITY, DEFAULT_RATCHET,
    DEFAULT_SEED, DEFAULT_VELOCITY, DIRECTIONS, FORWARD, GENERATORS, GRANULARITIES, PATTERN,
    PATTERN_ROWS, PATTERNS,
    SongBuilder, SongFileError,
)
from src.song_writer import dump_song

ROOTS = ['C', 'C#', 'Db', 'D', 'D#', 'Eb', 'E', 'F', 'F#', 'Gb', 'G', 'G#', 'Ab', 'A', 'A#', 'Bb', 'B']
SCALE_KINDS = [name.lower() for name in ScaleType.__members__]
DEFAULT_SCALE = 'C Major'
# The sections of a file that name generators, and what a chain step calls each of them.
GENERATOR_SECTIONS = {'arps': 'arp', 'auto_ratchets': 'auto_ratchet'}
MORPH_STYLES = ['left', 'right', 'middle']
UNTITLED = 'untitled'
# Each direction, and what it does.
DIRECTION_NAMES = {
    'forward': 'first step to last', 'reverse_a': 'step 1, then backward from the last',
    'reverse_b': 'last step to first', 'alternate': 'forward, then reverse',
    'pendulum': 'forward and back without repeating the ends', 'random': 'any step',
    'brownian': 'on 50%, back 25%, stay 25%', 'eitherway': 'on or back, 50% each',
}
# The settings on a clip that name a pattern.
CLIP_PATTERNS = ('pattern', 'morph_to', 'rhythm_from', 'notes_from')


def new_song():
    """Return the data for a new song, which has a C major scale that can be deleted."""
    return {
        'tempo': 120, 'scale': DEFAULT_SCALE, 'scales': {DEFAULT_SCALE: {'root': 'C', 'type': 'major'}}, 'seed': DEFAULT_SEED,
        'default_length': DEFAULT_LENGTH, 'granularity': GRANULARITIES[0],
        'default_octave': DEFAULT_OCTAVE, 'default_drum_octave': DEFAULT_DRUM_OCTAVE,
        'patterns': {}, 'tracks': [], 'arps': {}, 'auto_ratchets': {}, 'chains': {}, 'scenes': [],
    }


def fraction(value):
    """Return a duration from a file as an exact fraction."""
    return Fraction(str(value))


def fraction_text(value):
    """Return a fraction the way a file holds it, as a whole number or text like 3/16."""
    return int(value) if value.denominator == 1 else f'{value.numerator}/{value.denominator}'


def clock(seconds):
    """Return seconds as minutes and seconds, like 3:05, or dashes if they aren't known."""
    if seconds is None:
        return '--:--'
    total = int(round(seconds))
    return f'{total // 60}:{total % 60:02}'


def unique_name(base, taken):
    """Return a name that's not in use, based on another one."""
    if base not in taken:
        return base
    number = 2
    while f'{base} {number}' in taken:
        number += 1
    return f'{base} {number}'


def _moved(items, place, offset):
    """Return a list with one item moved, or None if that would go past either end."""
    target = place + offset
    if not 0 <= place < len(items) or not 0 <= target < len(items):
        return None
    result = list(items)
    result.insert(target, result.pop(place))
    return result


class Document:
    """One song, along with where it's saved and whether it has unsaved changes."""

    def __init__(self, data=None, path=None):
        self.data = new_song() if data is None else data
        for key, value in new_song().items():
            if key not in ('scale', 'scales', 'tempo'):
                self.data.setdefault(key, value)
        self.data.setdefault('scale', None)
        self.data.setdefault('scales', {})
        self.path = path
        self.dirty = False
        self._estimates = None
        self._estimate_problem = None

    # Loading, saving and rendering.

    @classmethod
    def load(cls, path):
        """Return a song from a file, or raise SongFileError if something's wrong with it."""
        try:
            with open(path, encoding='utf-8') as file:
                data = yaml.safe_load(file)
        except OSError as error:
            raise SongFileError(f"can't read {path}: {error.strerror}") from error
        except yaml.YAMLError as error:
            raise SongFileError(f"{path} isn't valid YAML: {error}") from error
        SongBuilder(data)
        return cls(data, path)

    def save(self, path=None):
        """Write the song to a file, making any folders that it needs."""
        path = path or self.path
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as file:
            file.write(dump_song(self._saved_data()))
        self.path = path
        self.dirty = False

    def _saved_data(self):
        """Return the data without pattern rows that hold nothing, so that files stay short."""
        data = dict(self.data)
        patterns = {}
        for name, pattern in data['patterns'].items():
            patterns[name] = {
                key: value for key, value in pattern.items()
                if key not in PATTERN_ROWS or any(item is not None for item in value)
            }
        data['patterns'] = patterns
        return data

    @property
    def name(self):
        if not self.path:
            return UNTITLED
        return os.path.splitext(os.path.basename(self.path))[0]

    def output_directory(self):
        return os.path.join('output', self.name)

    def render_path(self, to):
        """Return where a render will write: a set's file, or the folder of a clip tree."""
        if to == 'ableton':
            return AbletonProject(self.output_directory(), Song()).path
        return self.output_directory()

    def render_exists(self, to):
        """Return whether rendering would replace earlier output."""
        directory = self.output_directory()
        if to == 'ableton':
            return os.path.exists(self.render_path(to))
        return os.path.isdir(directory) and any(
            name.endswith('.mid') and name[:3].isdigit() for name in os.listdir(directory)
        )

    def render(self, to):
        """Render the song, replacing earlier output, or raise SongFileError if it can't be."""
        if not self.data['tracks'] or not self.data['scenes']:
            raise SongFileError('there is nothing to render yet, because the song needs a track and a scene')
        song = SongBuilder(self.data).build()
        directory = self.output_directory()
        replace_output(to, directory)
        # Renderers print warnings, which would write over the screen.
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                if to == 'ableton':
                    AbletonProject(directory, song).render()
                else:
                    ClipTree(directory, song).render()
            except (ValueError, OSError) as error:
                raise SongFileError(str(error)) from error
        return directory

    def changed(self):
        self.dirty = True
        self._estimates = None

    # How long everything lasts.

    def _estimate(self):
        if self._estimates is None:
            try:
                self._estimates = SongBuilder(self.data).estimate()
                self._estimate_problem = None
            except SongFileError as error:
                self._estimates = []
                self._estimate_problem = str(error)
        return self._estimates

    def song_seconds(self):
        """Return how long the song lasts, or None if any scene can't be worked out."""
        estimates = self._estimate()
        if self._estimate_problem or any(item[1] is None for item in estimates):
            return None
        return sum((item[1] for item in estimates), Fraction(0))

    def _stanzas_of(self, index):
        """Return the written-out scene numbers of one scene, counting from 1."""
        start = sum(scene.get('repeat', 1) for scene in self.data['scenes'][:index])
        return list(range(start + 1, start + self.data['scenes'][index].get('repeat', 1) + 1))

    def scene_seconds(self, index):
        """Return how long a scene and all of its repeats last, or None if it can't be worked out."""
        estimates = self._estimate()
        if self._estimate_problem:
            return None
        values = [estimates[number - 1][1] for number in self._stanzas_of(index)]
        return None if any(value is None for value in values) else sum(values, Fraction(0))

    def scene_problem(self, index):
        """Return what stops a scene from rendering, or None."""
        estimates = self._estimate()
        if self._estimate_problem:
            return self._estimate_problem
        for number in self._stanzas_of(index):
            if estimates[number - 1][3]:
                return estimates[number - 1][3]
        return None

    def clip_seconds(self, index, track):
        """Return how long a clip lasts on the first play of its scene, or None."""
        estimates = self._estimate()
        if self._estimate_problem:
            return None
        return estimates[self._stanzas_of(index)[0] - 1][2].get(track)

    def pattern_seconds(self, name):
        """Return how long one play of a pattern lasts at the song's tempo."""
        return self.pattern_length(name) * 240 / Fraction(str(self.data['tempo']))

    def pattern_length(self, name):
        """Return how long one play of a pattern lasts, in fractions of a whole note."""
        pattern = self.data['patterns'][name]
        total = Fraction(0)
        for step in range(pattern['steps']):
            duration = self.step_value(name, 'duration', step)
            total += fraction(self.data['default_length'] if duration is None else duration)
        return total

    # Reordering any list, and copying names.

    def move_track(self, place, offset):
        return self._set_list('tracks', _moved(self.data['tracks'], place, offset))

    def _set_list(self, key, moved):
        if moved is None:
            return False
        self.data[key] = moved
        self.changed()
        return True

    def move_named(self, section, place, offset):
        """Move a pattern, arp or chain up or down its section."""
        items = list(self.data[section].items())
        moved = _moved(items, place, offset)
        if moved is None:
            return False
        self.data[section] = dict(moved)
        self.changed()
        return True

    def sort_named(self, section):
        self.data[section] = dict(sorted(self.data[section].items(), key=lambda item: str(item[0]).lower()))
        self.changed()

    def _replace_key(self, section, old, new, value=None):
        """Return a section with one key renamed, keeping its place in the order."""
        return {
            (new if key == old else key): (item if key != old or value is None else value)
            for key, item in self.data[section].items()
        }

    # What refers to what. A problem is one line of text for each thing that uses an item.

    def _cells(self):
        for number, scene in enumerate(self.data['scenes'], start=1):
            for track, cell in (scene.get('tracks') or {}).items():
                yield number, scene, track, cell

    def _scene_label(self, number, scene):
        return f"scene {number} ({scene.get('name', 'unnamed')})"

    def _chain_settings(self, chain_name):
        """Yield (kind of setting, name it refers to) for the settings in a chain."""
        for step in self.data['chains'][chain_name]:
            generator, settings = next(iter(step.items()))
            if isinstance(settings, str):
                yield generator, settings
                continue
            allowed = GENERATORS[generator][1]
            for key, value in (settings or {}).items():
                if allowed.get(key) == PATTERN:
                    yield 'pattern', value
                elif allowed.get(key) == PATTERNS:
                    for item in value:
                        yield 'pattern', item

    def _chain_uses(self, kind, name):
        return [
            f'chain {chain}' for chain in self.data['chains']
            if (kind, name) in set(self._chain_settings(chain))
        ]

    def pattern_uses(self, name):
        uses = []
        for number, scene, track, cell in self._cells():
            if name in (cell.get(setting) for setting in CLIP_PATTERNS):
                uses.append(f'{self._scene_label(number, scene)}, track {track}')
        for other, pattern in self.data['patterns'].items():
            if pattern.get('source_pattern') == name:
                uses.append(f'pattern {other}')
        return uses + self._chain_uses('pattern', name)

    def track_clips(self, name):
        return sum(1 for _, _, track, _ in self._cells() if track == name)

    def chain_uses(self, name):
        uses = []
        for number, scene, track, cell in self._cells():
            if cell.get('chain') == name:
                uses.append(f'{self._scene_label(number, scene)}, track {track}')
        return uses

    def generator_uses(self, section, name):
        return self._chain_uses(GENERATOR_SECTIONS[section], name)

    def scale_uses(self, name):
        uses = ['the song'] if self.data.get('scale') == name else []
        for number, scene in enumerate(self.data['scenes'], start=1):
            if scene.get('scale') == name:
                uses.append(self._scene_label(number, scene))
        return uses

    # Patterns.

    def add_pattern(self, name, steps=16):
        """Add a pattern of rests, because every step takes time."""
        self.data['patterns'][name] = {'steps': steps, 'duration': [self.data['default_length']] * steps}
        self.changed()

    def copy_pattern(self, name):
        new = unique_name(f'{name} copy', self.data['patterns'])
        source = self.data['patterns'][name]
        self.data['patterns'][new] = {key: list(value) if isinstance(value, list) else value for key, value in source.items()}
        self.changed()
        return new

    def delete_pattern(self, name):
        del self.data['patterns'][name]
        self.changed()

    def rename_pattern(self, old, new):
        self.data['patterns'] = self._replace_key('patterns', old, new)
        for _, _, _, cell in self._cells():
            for key in CLIP_PATTERNS:
                if cell.get(key) == old:
                    cell[key] = new
        for pattern in self.data['patterns'].values():
            if pattern.get('source_pattern') == old:
                pattern['source_pattern'] = new
        self._rename_in_chains('pattern', old, new)
        self.changed()

    def _rename_in_chains(self, kind, old, new):
        for chain in self.data['chains'].values():
            for step in chain:
                generator, settings = next(iter(step.items()))
                if isinstance(settings, str):
                    if kind == generator and settings == old:
                        step[generator] = new
                    continue
                allowed = GENERATORS[generator][1]
                for key, value in (settings or {}).items():
                    if kind == 'pattern' and allowed.get(key) == PATTERN and value == old:
                        settings[key] = new
                    elif kind == 'pattern' and allowed.get(key) == PATTERNS:
                        settings[key] = [new if item == old else item for item in value]

    def step_value(self, name, row, step):
        values = self.data['patterns'][name].get(row)
        return values[step] if values else None

    def set_step_value(self, name, row, step, value):
        pattern = self.data['patterns'][name]
        if pattern.get(row) is None:
            pattern[row] = [None] * pattern['steps']
        pattern[row][step] = value
        self.changed()

    def clear_sound(self, name, step):
        """Turn a note into a rest, which only keeps its duration."""
        for row in PATTERN_ROWS:
            if row != 'duration' and self.data['patterns'][name].get(row):
                self.data['patterns'][name][row][step] = None
        self.changed()

    def steps_with_anything_past(self, name, steps):
        """Return how many steps from a position onward are more than a rest of the default length."""
        pattern = self.data['patterns'][name]
        default = fraction(self.data['default_length'])
        changed = 0
        for step in range(steps, pattern['steps']):
            duration = self.step_value(name, 'duration', step)
            if self.step_value(name, 'degree', step) is not None or (duration is not None and fraction(duration) != default):
                changed += 1
        return changed

    def set_steps(self, name, steps):
        """Change how many steps a pattern has, cutting them or adding rests at the end."""
        pattern = self.data['patterns'][name]
        added = max(steps - pattern['steps'], 0)
        for row in PATTERN_ROWS:
            if pattern.get(row) is not None:
                pattern[row] = (pattern[row] + [None] * steps)[:steps]
        durations = pattern.get('duration') or [None] * steps
        for step in range(steps - added, steps):
            durations[step] = self.data['default_length']
        pattern['duration'] = durations
        pattern['steps'] = steps
        self.changed()

    def insert_step(self, name, step):
        pattern = self.data['patterns'][name]
        for row in PATTERN_ROWS:
            if pattern.get(row) is not None:
                pattern[row].insert(step, None)
        pattern['steps'] += 1
        self.set_step_value(name, 'duration', step, self.data['default_length'])
        self.changed()

    def remove_step(self, name, step):
        pattern = self.data['patterns'][name]
        for row in PATTERN_ROWS:
            if pattern.get(row) is not None:
                pattern[row].pop(step)
        pattern['steps'] -= 1
        self.changed()

    def set_drum(self, name, drum):
        """Change a pattern's type, which clears the notes because they mean something else."""
        pattern = self.data['patterns'][name]
        for row in ('degree', 'accidental', 'chord'):
            pattern.pop(row, None)
        if drum:
            pattern['drum'] = True
        else:
            pattern.pop('drum', None)
        self.changed()

    def set_direction(self, name, direction):
        if direction == FORWARD:
            self.data['patterns'][name].pop('direction', None)
        else:
            self.data['patterns'][name]['direction'] = direction
        self.changed()

    def set_source_pattern(self, name, source):
        """Set where a pattern's grab row takes notes from. With no source, the row is cleared."""
        pattern = self.data['patterns'][name]
        if source is None:
            pattern.pop('source_pattern', None)
            pattern.pop('grab', None)
        else:
            pattern['source_pattern'] = source
        self.changed()

    def _rearranged(self, name, order):
        """Put a pattern's steps in a new order, with all of each step's values moving together."""
        pattern = self.data['patterns'][name]
        for row in PATTERN_ROWS:
            if pattern.get(row) is not None:
                pattern[row] = [pattern[row][step] for step in order]
        self.changed()

    def flip_after(self, name, step):
        """Reverse every step after this one."""
        steps = list(range(self.data['patterns'][name]['steps']))
        self._rearranged(name, steps[:step + 1] + steps[step + 1:][::-1])

    def swap_around(self, name, step):
        """Swap what's before this step with what's after it, and return where the step ends up."""
        steps = list(range(self.data['patterns'][name]['steps']))
        before, after = steps[:step], steps[step + 1:]
        self._rearranged(name, [*after, step, *before])
        return len(after)

    def load_over(self, name, other):
        """Replace a pattern's contents with a copy of another's, keeping its name."""
        source = self.data['patterns'][other]
        self.data['patterns'][name] = {key: list(value) if isinstance(value, list) else value for key, value in source.items()}
        self.changed()

    def has_notes(self, name):
        return any(value is not None for value in (self.data['patterns'][name].get('degree') or []))

    def degree_limit(self, name):
        """Return the highest degree to allow, from every scale that this pattern can play in.

        Scales come from the scene and then the song, so a pattern used in several scenes can
        play in several scales, and the largest of those sets the limit.
        """
        names = [self.data.get('scale')]
        for _, scene, _, cell in self._cells():
            if name in (cell.get(setting) for setting in CLIP_PATTERNS):
                names.append(scene.get('scale') or self.data.get('scale'))
        sizes = [self.scale_size(scale) for scale in names if scale]
        return max(sizes) if sizes else 7

    def note_name(self, name, step):
        """Return the name of a step's note in the song's scale, like F#3, or None."""
        degree = self.step_value(name, 'degree', step)
        if degree is None:
            return None
        drum = self.data['patterns'][name].get('drum')
        accidental = self.step_value(name, 'accidental', step) or ''
        octave = self.step_value(name, 'octave', step)
        if octave is None:
            octave = self.data['default_drum_octave' if drum else 'default_octave']
        if drum:
            return f'{degree}{accidental}{octave}'
        scale_name = self.data.get('scale')
        if not scale_name:
            return None
        root = self.data['scales'][scale_name]['root']
        scale = self._scale_steps(scale_name)
        places, place = divmod(degree - 1, len(scale))
        half_steps = scale[place] + places * 12 + {'#': 1, 'b': -1}.get(accidental, 0)
        note = Note(root, 5).half_step(half_steps)
        return f'{note.name}{note.octave_number - 5 + octave}'

    # Tracks.

    def add_track(self, name):
        self.data['tracks'].append(name)
        self.changed()

    def copy_track(self, name):
        new = unique_name(f'{name} copy', self.data['tracks'])
        self.data['tracks'].insert(self.data['tracks'].index(name) + 1, new)
        for scene in self.data['scenes']:
            cells = scene.get('tracks') or {}
            if name in cells:
                cells[new] = dict(cells[name])
        self.changed()
        return new

    def delete_track(self, name):
        self.data['tracks'].remove(name)
        for scene in self.data['scenes']:
            (scene.get('tracks') or {}).pop(name, None)
        # Paint is legacy and isn't shown, so it can't be what stops a track from being deleted.
        for paint in self.data.get('paint') or []:
            paint['tracks'] = [track for track in paint['tracks'] if track != name]
        self.changed()

    def rename_track(self, old, new):
        self.data['tracks'] = [new if name == old else name for name in self.data['tracks']]
        for scene in self.data['scenes']:
            cells = scene.get('tracks') or {}
            if old in cells:
                scene['tracks'] = {new if key == old else key: value for key, value in cells.items()}
        for paint in self.data.get('paint') or []:
            paint['tracks'] = [new if name == old else name for name in paint['tracks']]
        self.changed()

    # Scales.

    def _scale_steps(self, name):
        kind = self.data['scales'][name]['type']
        return ScaleType[kind.strip().upper().replace(' ', '_')].value

    def scale_size(self, name):
        return len(self._scale_steps(name))

    def scale_notes_text(self, name):
        """Return what a named scale is, like F minor."""
        scale = self.data['scales'][name]
        return f"{scale['root']} {scale['type'].replace('_', ' ')}"

    def add_scale(self, name, root, kind):
        self.data['scales'][name] = {'root': root, 'type': kind}
        self.changed()

    def copy_scale(self, name):
        new = unique_name(f'{name} copy', self.data['scales'])
        self.data['scales'][new] = dict(self.data['scales'][name])
        self.changed()
        return new

    def delete_scale(self, name):
        del self.data['scales'][name]
        self.changed()

    def change_scale(self, name, root, kind):
        """Change what a named scale is, which changes everything that uses it."""
        self.data['scales'][name] = {'root': root, 'type': kind}
        self.changed()

    def rename_scale(self, old, new):
        self.data['scales'] = self._replace_key('scales', old, new)
        if self.data.get('scale') == old:
            self.data['scale'] = new
        for scene in self.data['scenes']:
            if scene.get('scale') == old:
                scene['scale'] = new
        self.changed()

    # Arps and chains.

    def add_generator(self, section, name):
        if section == 'arps':
            self.data[section][name] = {'step': self.data['default_length'], 'order': 'up'}
        else:
            self.data[section][name] = {'counts': [2]}
        self.changed()

    def copy_generator(self, section, name):
        new = unique_name(f'{name} copy', self.data[section])
        self.data[section][new] = dict(self.data[section][name])
        self.changed()
        return new

    def delete_generator(self, section, name):
        del self.data[section][name]
        self.changed()

    def rename_generator(self, section, old, new):
        self.data[section] = self._replace_key(section, old, new)
        self._rename_in_chains(GENERATOR_SECTIONS[section], old, new)
        self.changed()

    def add_chain(self, name):
        self.data['chains'][name] = []
        self.changed()

    def copy_chain(self, name):
        new = unique_name(f'{name} copy', self.data['chains'])
        self.data['chains'][new] = [
            {generator: (dict(settings) if isinstance(settings, dict) else settings) for generator, settings in step.items()}
            for step in self.data['chains'][name]
        ]
        self.changed()
        return new

    def delete_chain(self, name):
        del self.data['chains'][name]
        # Paint is legacy and isn't shown, so it can't be what stops a chain from being deleted.
        if self.data.get('paint'):
            self.data['paint'] = [paint for paint in self.data['paint'] if paint['chain'] != name]
        self.changed()

    def rename_chain(self, old, new):
        self.data['chains'] = self._replace_key('chains', old, new)
        for _, _, _, cell in self._cells():
            if cell.get('chain') == old:
                cell['chain'] = new
        for paint in self.data.get('paint') or []:
            if paint['chain'] == old:
                paint['chain'] = new
        self.changed()

    # Scenes. Legacy paint lists written-out scene numbers, so these all keep those numbers correct.

    def _renumber_paint(self, mapping):
        """Change paint's scene numbers, given {old number: list of new numbers}."""
        for paint in self.data.get('paint') or []:
            paint['scenes'] = sorted({new for old in paint['scenes'] for new in mapping.get(old, [])})

    def _after_scene_change(self, old_numbers):
        """Fix paint after scenes change, given each scene object's numbers from before."""
        mapping = {}
        for index, scene in enumerate(self.data['scenes']):
            numbers = self._stanzas_of(index)
            for place, old in enumerate(old_numbers.get(id(scene), [])):
                # A scene that repeats less drops its last numbers, and one that repeats more paints them too.
                if place < len(numbers):
                    mapping.setdefault(old, []).append(numbers[place])
                if place == len(old_numbers[id(scene)]) - 1:
                    mapping.setdefault(old, []).extend(numbers[place + 1:])
        self._renumber_paint(mapping)
        self.changed()

    def _numbers_by_scene(self):
        return {id(scene): self._stanzas_of(index) for index, scene in enumerate(self.data['scenes'])}

    def add_scene(self, index, name):
        before = self._numbers_by_scene()
        self.data['scenes'].insert(index, {'name': name, 'tracks': {}})
        self._after_scene_change(before)

    def copy_scene(self, index):
        before = self._numbers_by_scene()
        source = self.data['scenes'][index]
        names = {scene.get('name') for scene in self.data['scenes']}
        copy = {
            **source, 'name': unique_name(f"{source.get('name', 'scene')} copy", names),
            'tracks': {track: dict(cell) for track, cell in (source.get('tracks') or {}).items()},
        }
        self.data['scenes'].insert(index + 1, copy)
        self._after_scene_change(before)
        # A copy sounds like the original, so whatever paints the original paints it too.
        for paint in self.data.get('paint') or []:
            if set(self._stanzas_of(index)) & set(paint['scenes']):
                paint['scenes'] = sorted({*paint['scenes'], *self._stanzas_of(index + 1)})

    def delete_scene(self, index):
        before = self._numbers_by_scene()
        del self.data['scenes'][index]
        self._after_scene_change(before)

    def move_scene(self, index, offset):
        moved = _moved(self.data['scenes'], index, offset)
        if moved is None:
            return False
        before = self._numbers_by_scene()
        self.data['scenes'] = moved
        self._after_scene_change(before)
        return True

    def set_scene_repeat(self, index, repeat):
        before = self._numbers_by_scene()
        if repeat > 1:
            self.data['scenes'][index]['repeat'] = repeat
        else:
            self.data['scenes'][index].pop('repeat', None)
        self._after_scene_change(before)

    # Clips.

    def cell(self, index, track):
        return (self.data['scenes'][index].get('tracks') or {}).get(track)

    def set_cell(self, index, track, cell):
        scene = self.data['scenes'][index]
        if not scene.get('tracks'):
            scene['tracks'] = {}
        scene['tracks'][track] = cell
        self.changed()

    def delete_cell(self, index, track):
        del self.data['scenes'][index]['tracks'][track]
        self.changed()
