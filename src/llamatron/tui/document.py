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

"""The song being edited in the text UI: its data, and everything that changes or reads it.

The data is exactly what a song file holds, so that saving only ever writes it out. Nothing here
draws anything, and nothing is saved or rendered unless one of those methods is called.
"""

import contextlib
import copy
import io
import os
from fractions import Fraction

import yaml

from llamatron.cli import replace_output
from llamatron.renderers.ableton_project import AbletonProject
from llamatron.renderers.clip_tree import ClipTree
from llamatron.note import ROOT_NAMES, Note
from llamatron.scale import ScaleType
from llamatron.clip_grid import ClipGrid
from llamatron.composition.defaults import (
    DEFAULT_DRUM_OCTAVE, DEFAULT_OCTAVE, DEFAULT_SEED, DEFAULT_STEP_SIZE, DEFAULT_TEMPO,
)
from llamatron.composition.file_format import (
    CC_ROWS, FORWARD, PATTERN_ROWS, REGISTER_ADD_ROWS, REGISTER_NAMES, REGISTER_NOTE_ROWS, PatternSetting,
    Row, SceneSetting, Section, SongSetting, TOGGLE_ROWS,
)
from llamatron.composition.register import Register
from llamatron.composition.song_file_error import SongFileError
from llamatron.composition.song import Song
from llamatron.playback.song_renderer import SongRenderer
from llamatron.song_writer import dump_song
from llamatron.version import VERSION

ROOTS = ROOT_NAMES
SCALE_KINDS = [name.lower() for name in ScaleType.__members__]
DEFAULT_SCALE = 'C Major'
# The sections of a file that name generators, and what a chain step calls each of them.
GENERATOR_SECTIONS = {'arps': 'arp', 'auto_ratchets': 'auto_ratchet'}
UNTITLED = 'untitled'
# Each direction, and what it does.
DIRECTION_NAMES = {
    'forward': 'first step to last', 'reverse_a': 'step 1, then backward from the last',
    'reverse_b': 'last step to first', 'alternate': 'forward, then reverse',
    'pendulum': 'forward and back without repeating the ends', 'random': 'any step',
    'brownian': 'on 50%, back 25%, stay 25%', 'eitherway': 'on or back, 50% each',
}
# The settings on a clip that name a pattern.
CLIP_PATTERNS = ('pattern', 'morph_to')


def new_song():
    """Return the data for a new song, which has a C major scale that can be deleted."""
    return {
        'tempo': DEFAULT_TEMPO, 'scale': DEFAULT_SCALE, 'scales': {DEFAULT_SCALE: {'root': 'C', 'type': 'major'}}, 'seed': DEFAULT_SEED,
        SongSetting.STEP_SIZE: DEFAULT_STEP_SIZE,
        'default_octave': DEFAULT_OCTAVE, 'default_drum_octave': DEFAULT_DRUM_OCTAVE,
        'patterns': {}, 'tracks': {}, 'arps': {}, 'auto_ratchets': {}, 'chains': {}, 'scenes': [],
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


def blank(row):
    """Return what a step holds when nothing is set: off for an on or off row, and None otherwise."""
    return False if row in TOGGLE_ROWS else None


# What a rest keeps when a note is turned into one: its time, the CC values it sends, and what it
# adds to the registers.
REST_ROWS = (*CC_ROWS, Row.SLIDE, *REGISTER_ADD_ROWS.values())
# A register change of nothing, which is the same as none.
NO_CHANGE = 0
# How a register's settings are named when one is refused.
WHERE_REGISTER = 'register {name}'


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
            if key not in ('scale', 'scales'):
                self.data.setdefault(key, value)
        # A file without a scale has none, rather than the C major that a new song starts with.
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
        # An empty file is an empty song.
        data = {} if data is None else data
        Song.from_data(data)
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
        """Return the data without pattern rows that hold nothing, so that files stay short.

        On or off rows are written as true and false, so a step that's off is false.
        """
        data = dict(self.data)
        patterns = {}
        for name, pattern in data['patterns'].items():
            saved = {}
            for key, value in pattern.items():
                if key in TOGGLE_ROWS:
                    value = [bool(item) for item in value]
                if key not in PATTERN_ROWS or any(item is not None and item is not False for item in value):
                    saved[key] = value
            patterns[name] = saved
        data['patterns'] = patterns
        # Every saved file records the version of llamatron that wrote it.
        data[SongSetting.VERSION] = VERSION
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
            return AbletonProject(self.output_directory(), ClipGrid()).path
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
        song = SongRenderer(Song.from_data(self.data)).render()
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
                self._estimates = SongRenderer(Song.from_data(self.data)).estimate()
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
        return pattern['steps'] * self.step_size(name)

    def step_size(self, name):
        """Return how long each step of a pattern is: its own step size, or else the song's."""
        own = self.data['patterns'][name].get(PatternSetting.STEP_SIZE)
        return fraction(self.data[SongSetting.STEP_SIZE] if own is None else own)

    def song_step_size(self):
        """Return the song's step size, which a pattern without its own uses."""
        return self.data[SongSetting.STEP_SIZE]

    def set_step_size(self, name, step_size):
        """Give a pattern its own step size, or None to use the song's."""
        pattern = self.data['patterns'][name]
        if step_size is None:
            pattern.pop(PatternSetting.STEP_SIZE, None)
        else:
            pattern[PatternSetting.STEP_SIZE] = step_size
        self.changed()

    # Reordering any list, and copying names.

    def move_track(self, place, offset):
        return self.move_named('tracks', place, offset)

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

    def _chain_uses(self, kind, name):
        return [
            f'chain {chain}' for chain in self.data['chains']
            if any(step.get(kind) == name for step in self.data['chains'][chain])
        ]

    def pattern_uses(self, name):
        uses = []
        for number, scene, track, cell in self._cells():
            if name in (cell.get(setting) for setting in CLIP_PATTERNS):
                uses.append(f'{self._scene_label(number, scene)}, track {track}')
        return uses

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
        """Add a pattern of empty steps."""
        self.data['patterns'][name] = {PatternSetting.STEPS: steps}
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
        self.changed()

    def _rename_in_chains(self, kind, old, new):
        for chain in self.data['chains'].values():
            for step in chain:
                if step.get(kind) == old:
                    step[kind] = new

    def step_value(self, name, row, step):
        values = self.data['patterns'][name].get(row)
        return values[step] if values else None

    def set_step_value(self, name, row, step, value):
        pattern = self.data['patterns'][name]
        if pattern.get(row) is None:
            pattern[row] = [blank(row)] * pattern['steps']
        pattern[row][step] = value
        self.changed()

    def clear_sound(self, name, step):
        """Empty a step, which keeps only its CC values, since they don't need a note."""
        for row in PATTERN_ROWS:
            if row not in REST_ROWS and self.data['patterns'][name].get(row):
                self.data['patterns'][name][row][step] = blank(row)
        self.changed()

    def steps_with_anything_past(self, name, steps):
        """Return how many steps from a position onward hold a note or a CC value."""
        pattern = self.data['patterns'][name]
        return sum(1 for step in range(steps, pattern['steps']) if self._step_holds_anything(name, step))

    def _step_holds_anything(self, name, step):
        """Return whether a step plays a note, holds one with a tie, sends a CC value or adds to a register."""
        if self.step_value(name, Row.DEGREE, step) is not None or self.step_value(name, Row.TIE, step):
            return True
        if any(self.step_value(name, row, step) is not None for row in CC_ROWS):
            return True
        return any(self.step_value(name, row, step) not in (None, NO_CHANGE) for row in REGISTER_ADD_ROWS.values())

    def set_steps(self, name, steps):
        """Change how many steps a pattern has, cutting them or adding empty steps at the end."""
        pattern = self.data['patterns'][name]
        for row in PATTERN_ROWS:
            if pattern.get(row) is not None:
                pattern[row] = (pattern[row] + [blank(row)] * steps)[:steps]
        pattern['steps'] = steps
        self.changed()

    def insert_step(self, name, step):
        pattern = self.data['patterns'][name]
        for row in PATTERN_ROWS:
            if pattern.get(row) is not None:
                pattern[row].insert(step, blank(row))
        pattern['steps'] += 1
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
        for row in ('degree', 'accidental', 'chord', *REGISTER_NOTE_ROWS.values()):
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

    def has_grab_steps(self, name):
        """Return whether a pattern has any steps marked to grab."""
        return any(self.data['patterns'][name].get('grab') or [])

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
        self.data['tracks'][name] = {}
        self.changed()

    def track_names(self):
        return list(self.data['tracks'])

    def track(self, name):
        """Return a track's settings, which the page for it changes in place."""
        return self.data['tracks'][name]

    def copy_track(self, name):
        new = unique_name(f'{name} copy', self.data['tracks'])
        items = list(self.data['tracks'].items())
        place = [key for key, _ in items].index(name) + 1
        items.insert(place, (new, copy.deepcopy(self.data['tracks'][name])))
        self.data['tracks'] = dict(items)
        for scene in self.data['scenes']:
            cells = scene.get('tracks') or {}
            if name in cells:
                cells[new] = dict(cells[name])
        self.changed()
        return new

    def grabbers(self, name):
        """Return the clips that grab from a track, as descriptions."""
        return [
            f'{self._scene_label(number, scene)}, track {track}'
            for number, scene, track, cell in self._cells() if cell.get('grab_track') == name
        ]

    def delete_track(self, name):
        """Delete a track and its clips, and stop any clips grabbing from it."""
        del self.data['tracks'][name]
        for scene in self.data['scenes']:
            (scene.get('tracks') or {}).pop(name, None)
        for _, _, _, cell in self._cells():
            if cell.get('grab_track') == name:
                del cell['grab_track']
        self.changed()

    def rename_track(self, old, new):
        self.data['tracks'] = self._replace_key('tracks', old, new)
        for scene in self.data['scenes']:
            cells = scene.get('tracks') or {}
            if old in cells:
                scene['tracks'] = {new if key == old else key: value for key, value in cells.items()}
        for _, _, _, cell in self._cells():
            if cell.get('grab_track') == old:
                cell['grab_track'] = new
        self.changed()

    def grab_circle(self, index, track, other):
        """Return the tracks a grab would go round in a circle, like [lead, bass, lead], or None.

        A clip grabbing from other follows other's grab, and so on, within the scene.
        """
        cells = self.data['scenes'][index].get('tracks') or {}
        path = [track, other]
        while True:
            if path[-1] == track:
                return path
            following = (cells.get(path[-1]) or {}).get('grab_track')
            if following is None or following in path[1:]:
                return None
            path.append(following)

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
            self.data[section][name] = {'step': self.data[SongSetting.STEP_SIZE], 'order': 'up'}
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
        # Each step only names a generator, so copying the step is enough.
        self.data['chains'][new] = [dict(step) for step in self.data['chains'][name]]
        self.changed()
        return new

    def delete_chain(self, name):
        del self.data['chains'][name]
        self.changed()

    def rename_chain(self, old, new):
        self.data['chains'] = self._replace_key('chains', old, new)
        for _, _, _, cell in self._cells():
            if cell.get('chain') == old:
                cell['chain'] = new
        self.changed()

    # Scenes.

    def add_scene(self, index, name):
        self.data['scenes'].insert(index, {'name': name, 'tracks': {}})
        self.changed()

    def copy_scene(self, index):
        source = self.data['scenes'][index]
        names = {scene.get('name') for scene in self.data['scenes']}
        copy = {
            **source, 'name': unique_name(f"{source.get('name', 'scene')} copy", names),
            'tracks': {track: dict(cell) for track, cell in (source.get('tracks') or {}).items()},
        }
        self.data['scenes'].insert(index + 1, copy)
        self.changed()

    def delete_scene(self, index):
        del self.data['scenes'][index]
        self.changed()

    def move_scene(self, index, offset):
        moved = _moved(self.data['scenes'], index, offset)
        if moved is None:
            return False
        self.data['scenes'] = moved
        self.changed()
        return True

    # Registers. There are always four, and the file only holds the settings that differ from the defaults.

    def register(self, name):
        """Return a register, AX to DX, as a Register, with its defaults for anything not set."""
        settings = (self.data.get(Section.REGISTERS) or {}).get(name) or {}
        return Register.from_data(settings, WHERE_REGISTER.format(name=name))

    def set_register_setting(self, name, setting, value):
        """Change one setting of a register, or return why it can't change, like a default above the maximum.

        A value of None goes back to the setting's default.
        """
        registers = dict(self.data.get(Section.REGISTERS) or {})
        settings = dict(registers.get(name) or {})
        if value is None:
            settings.pop(setting, None)
        else:
            settings[setting] = value
        try:
            Register.from_data(settings, WHERE_REGISTER.format(name=name))
        except SongFileError as error:
            return str(error)
        registers[name] = settings
        self.data[Section.REGISTERS] = {register: registers[register] for register in REGISTER_NAMES if registers.get(register)}
        if not self.data[Section.REGISTERS]:
            del self.data[Section.REGISTERS]
        self.changed()
        return None

    def resets(self, index, register):
        """Return whether a scene sets a register back to its default as it starts."""
        return register in (self.data['scenes'][index].get(SceneSetting.RESET) or [])

    def set_reset(self, index, register, on):
        """Make a scene set a register back to its default as it starts, or stop it, keeping the registers in order."""
        scene = self.data['scenes'][index]
        chosen = set(scene.get(SceneSetting.RESET) or [])
        chosen = chosen | {register} if on else chosen - {register}
        reset = [name for name in REGISTER_NAMES if name in chosen]
        if reset:
            scene[SceneSetting.RESET] = reset
        else:
            scene.pop(SceneSetting.RESET, None)
        self.changed()

    def set_scene_repeat(self, index, repeat):
        if repeat > 1:
            self.data['scenes'][index]['repeat'] = repeat
        else:
            self.data['scenes'][index].pop('repeat', None)
        self.changed()

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
