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

"""Reads a song written in the YAML song format, and builds a ClipGrid from it.

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

A clip can take its rhythm from another pattern with rhythm_from, and then its pattern gives the
notes. They match step by step, and the notes carry on across repeats and skip any rests, so lists
of different lengths drift apart. A clip's grab_track names another track in the same scene, like
the Cirklon's note grab: each of the pattern's grab steps plays the note that track most recently
started (the lowest, for a chord), after its chain, so a silent track gives the last note it
played. Clips that grab in a circle are refused. A pattern's direction sets the order its steps
play in, and a clip's direction overrides it. A step's ratchet_offset moves each ratchet slice further along the scale. A step's note_add and velocity_add
add to running totals that apply from that step on, across the clip's repeats, and clear at the
pattern's accumulator_limit.
"""

import random
from dataclasses import replace
from fractions import Fraction
from math import ceil

import yaml

from llamatron.chord import Chord
from llamatron.composition.checks import number
# The file format's lists and defaults are imported from here by the rest of the program until
# song_file.py is gone, so they stay importable under these names.
from llamatron.composition.file_format import (  # noqa: F401
    ACCIDENTALS, CC_ROWS, CHORD_SYMBOLS, DEFAULT_ACCUMULATOR_LIMIT, DEFAULT_DRUM_OCTAVE, DEFAULT_LENGTH,
    DEFAULT_OCTAVE, DEFAULT_PROBABILITY, DEFAULT_RATCHET, DEFAULT_SEED, DEFAULT_TEMPO, DEFAULT_VELOCITY,
    DIRECTIONS, FIXED_CHORDS, FORWARD, GRANULARITIES, LIVE_OCTAVE_OFFSET, MAX_LIVE_OCTAVE, MAX_TRANSPOSE,
    MIN_LIVE_OCTAVE, NAMED_GENERATORS, NOTE_LETTERS, NOTE_ROWS, PATTERN_ROWS, SCALE_CHORDS, TOGGLE_ROWS,
)
from llamatron.composition.song_file_error import SongFileError
from llamatron.composition.cell import MORPH_STYLES  # noqa: F401
from llamatron.composition.generator_settings import GENERATOR_SETTINGS
from llamatron.composition.song import Song
from llamatron.generators.arp import along_scale
from llamatron.generators.auto_ratchet import divide
from llamatron.generators.blend import Blend
from llamatron.note import SHARP_NAMES, Degree, Note, Rest
from llamatron.renderers.timing import timed_events
from llamatron.song import Clip, ClipGrid, Control, Scene, Track

# The generators a chain step can name.
GENERATORS = GENERATOR_SETTINGS


def _with_sound(played, **changes):
    """Return a note or chord with changes to how every note in it plays."""
    if isinstance(played, Chord):
        return Chord([replace(note, **changes) for note in played.notes])
    return replace(played, **changes)


def _blended_controls(source, target, start, end):
    """Return the CC values of a morph: the target's from start to end, and the source's elsewhere.

    Each side's values carry across the edges, so a lane holds what it would hold there.
    """
    def in_effect(clip, time):
        latest = {}
        for item in clip.controls:
            if item.time <= time:
                latest[item.number] = item
        return latest

    if end <= start:
        return list(source.controls)
    result = [item for item in source.controls if item.time < start]
    result += [replace(item, time=start) for item in in_effect(target, start).values() if item.time < start]
    result += [item for item in target.controls if start <= item.time < end]
    if end < source.total_length():
        result += [replace(item, time=end) for item in in_effect(source, end).values() if item.time < end]
        result += [item for item in source.controls if item.time >= end]
    return result


# How many octaves away a moved note can go to find one that fits the MIDI range.
MAX_OCTAVE_CHANGE = 10
_number = number


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
    """One scene in the song, after repeats have been written out, with its cells by track."""

    def __init__(self, number, name, scale, tempo, scene):
        self.number, self.name, self.scale = number, name, scale
        self.tempo, self.scene = tempo, scene
        self.cells = {track: scene.get_cell(track) for track in scene.get_track_names()}


class _Context:
    """What's needed while writing one cell, including its track's transpose."""

    def __init__(self, stanza, cell, scale, track, settings):
        self.stanza, self.cell, self.scale, self.track = stanza, cell, scale, track
        # A drum track never transposes, and neither does a drum pattern on any track.
        self.transpose = settings.get_transpose()
        self.cc = settings.get_cc_numbers()


class SongBuilder:
    """Turns the contents of a song file into a ClipGrid of finished clips."""

    def __init__(self, data):
        self.song = Song.from_data(data)
        self.tempo = self.song.get_tempo()
        self.seed = self.song.get_seed()
        self.default_length = self.song.get_default_length()
        self.default_octave = self.song.get_default_octave()
        self.default_drum_octave = self.song.get_default_drum_octave()
        self.tracks = self.song.get_track_names()
        self.stanzas = self._write_out_scenes()
        self.resolved = {}
        self.lengths = {}
        # The tracks whose clips are waiting on a grab, to catch clips that grab in a circle.
        self.grabbing = []

    def build(self):
        tempo = float(self.tempo)
        song = ClipGrid(tempo=int(tempo) if tempo.is_integer() else tempo)
        tracks = {name: song.add_track(Track(name, mute=self.song.get_track(name).is_muted())) for name in self.tracks}
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

    def _write_out_scenes(self):
        """Return every scene, with a scene that repeats written out once for each repeat."""
        stanzas = []
        for scene in self.song.get_scenes():
            scale = scene.get_scale_name() or self.song.get_scale_name()
            repeat = scene.get_repeat()
            for place in range(repeat):
                name = scene.get_name()
                name = str(f'Scene {len(stanzas) + 1}' if name is None else name)
                if repeat > 1:
                    name = f'{name} {place + 1}'
                stanzas.append(_Stanza(len(stanzas) + 1, name, scale, scene.get_tempo(place), scene))
        return stanzas

    def _named_scale(self, name, octave, where):
        return self.song.get_named_scale(name).scale_at(octave)

    # Writing each clip.

    def _scene_length(self, stanza):
        """Return how long a scene lasts, which is its longest clip that doesn't loop."""
        if stanza.number in self.lengths:
            return self.lengths[stanza.number]
        where = f'scene {stanza.number} ({stanza.name})'
        if stanza.cells and all(cell.loops() for cell in stanza.cells.values()):
            raise SongFileError(f'{where}: every clip is set to loop, so the scene would never end. Turn off loop on at least one clip.')
        length = Fraction(0)
        for track, cell in stanza.cells.items():
            if not cell.loops():
                # Grabbing only changes pitches, so lengths come from clips built without it, which
                # means a clip can grab from one that loops to fill the scene.
                length = max(length, self._cell(stanza, track, grabbing=False).total_length())
        self.lengths[stanza.number] = length
        return length

    def _grabber(self, stanza, track, cell):
        """Return a function giving the MIDI numbers another track most recently started by a time."""
        other = cell.get_grab_track()
        if other not in stanza.cells:
            return None
        chain = [*self.grabbing, track]
        if other in chain:
            loop = ' → '.join([*chain[chain.index(other):], other])
            raise SongFileError(
                f'scene {stanza.number} ({stanza.name}): circular grab: {loop}. '
                'Remove the grab track from one of these clips.'
            )
        self.grabbing.append(track)
        try:
            source = self._cell(stanza, other)
        finally:
            self.grabbing.pop()
        events, _ = timed_events(source, source.scale)
        onsets = {}
        for start, _, number, _ in events:
            onsets.setdefault(start, set()).add(number)
        times = sorted(onsets)

        def grab(time):
            # A chord gives its lowest note. Chords are built upward from the root, so that's
            # the root for now, but inversions would need to change this.
            started = [moment for moment in times if moment <= time]
            return min(onsets[started[-1]]) if started else None
        return grab

    def _cell(self, stanza, track, grabbing=True):
        cell = stanza.cells.get(track)
        if cell is None:
            return None
        grabbing = grabbing and cell.get_grab_track() is not None
        key = (stanza.number, track, grabbing)
        if key in self.resolved:
            return self.resolved[key]
        where = f'scene {stanza.number}, track {track!r}'
        octave = self._clip_octave(cell)
        scale = None if stanza.scale is None else self._named_scale(stanza.scale, octave, where)
        context = _Context(stanza, cell, scale, track, self.song.get_track(track))
        context.grab = self._grabber(stanza, track, cell) if grabbing else None
        loop = cell.loops()
        fill = self._scene_length(stanza) if loop else None
        try:
            clip = self._source(context, where, fill)
            controls = clip.controls
            chain = cell.get_chain_name()
            if clip.total_length() > 0 and chain is not None:
                for index, step in enumerate(self.song.get_chain(chain).get_steps()):
                    clip = self._generator(step, context, chain, index).generate(clip)
            end = fill if loop else clip.total_length()
            notes = clip.section(0, end).notes if end > 0 else []
            # Until here a control's number is its lane, which the track turns into a CC number.
            controls = [
                replace(item, number=context.cc[item.number]) for item in controls
                if item.time < end and context.cc[item.number] is not None
            ]
            clip = Clip(name=stanza.name, notes=notes, scale=scale, loop=loop, controls=controls)
        except (ValueError, TypeError) as error:
            raise SongFileError(f'{where}: {error}') from error
        self.resolved[key] = clip
        return clip

    def _clip_octave(self, cell):
        """Return the octave for the root of this clip's scale.

        It's the octave of the first note the clip plays, in this project's numbering.
        """
        octave = self.song.get_pattern(cell.get_pattern_name()).get_first_octave()
        return (self.default_octave if octave is None else octave) + LIVE_OCTAVE_OFFSET

    def _source(self, context, where, fill):
        """Return what a clip plays before any chains, filling a length if one is given."""
        cell, stanza = context.cell, context.stanza
        rolls = random.Random(f'{self.seed}/{stanza.number}/{context.track}')
        play = _Play(random.Random(f'{self.seed}/{stanza.number}/{context.track}/direction'))
        repeat = cell.get_repeat()
        notes, controls, total, place = [], [], Fraction(0), 0
        while (place < repeat) if fill is None else (total < fill):
            played = self._frame(cell, place % repeat, repeat, context, where, rolls, play, total)
            length = played.total_length()
            if length == 0:
                break
            notes += played.notes
            controls += [replace(item, time=item.time + total) for item in played.controls]
            total += length
            place += 1
        clip = Clip(notes=notes, scale=context.scale, controls=controls)
        return clip.section(0, fill) if fill else clip

    def _frame(self, cell, place, repeat, context, where, rolls, play, start):
        """Return one pass through a clip's pattern, part way through any morph.

        Only the first pattern takes a rhythm, grabs or a direction from the clip, and a morph's
        target plays as it's written.
        """
        clip = self._one_pass(
            cell.get_rhythm_pattern_name(), cell.get_pattern_name(), context.grab,
            cell.get_direction(), context, where, rolls, play, start,
        )
        morph_to = cell.get_morph_target()
        if morph_to is None or not clip.notes:
            return clip
        target = self._one_pass(morph_to, morph_to, None, None, context, where, rolls, play, start)
        amount = Fraction(place, repeat - 1) * 100
        target = self._looped(target, clip.total_length())
        blend = Blend(target, amount, mode=cell.get_morph_style())
        controls = _blended_controls(clip, target, *blend.region(clip))
        return Clip(notes=blend.generate(clip).played_notes(), scale=context.scale, controls=controls)

    def _looped(self, clip, length):
        """Return a clip repeated or cut to last a length."""
        if clip.total_length() > 0:
            clip = clip.repeated(ceil(length / clip.total_length()))
        return clip.section(0, length)

    def _row(self, pattern, row, step):
        return pattern.get_value(row, step)

    def _pattern_length(self, pattern):
        return sum(
            (self.default_length if self._row(pattern, 'duration', step) is None else _number(self._row(pattern, 'duration', step), 'duration')
             for step in range(pattern.get_steps())),
            Fraction(0),
        )

    def _one_pass(self, rhythm_name, notes_name, grab, direction, context, where, rolls, play, start):
        """Return one pass through a rhythm, as notes, chords and rests, starting at a time in the clip.

        The notes pattern's grab steps play what grab gives for the time they start, if anything.
        Whichever order the steps play in, a pass lasts as long as the rhythm pattern does, so that
        a direction can't change how long a clip or scene is. The last step is cut to fit.
        """
        for name in (rhythm_name, notes_name):
            if not self.song.has_pattern(name):
                raise SongFileError(f'{where}: no pattern called {name!r}')
        rhythm, notes = self.song.get_pattern(rhythm_name), self.song.get_pattern(notes_name)
        combined = rhythm_name != notes_name
        note_steps = notes.get_note_steps()

        def order(pattern):
            return direction or pattern.get_direction()

        length = self._pattern_length(rhythm)
        where = f'pattern {notes_name!r}'
        positions, controls, time = [], [], Fraction(0)
        while time < length:
            step = play.next(('rhythm', rhythm_name), rhythm.get_steps(), order(rhythm))
            values = {row: self._row(rhythm, row, step) for row in PATTERN_ROWS}
            moment = start + time
            duration = self.default_length if values['duration'] is None else _number(values['duration'], where)
            # CC values belong to the rhythm, and a rest can send them too.
            controls += [
                Control(time, lane, values[row], bool(values['slide']))
                for lane, row in enumerate(CC_ROWS) if values[row] is not None
            ]
            time += duration
            if values['degree'] is None or (combined and not note_steps):
                positions.append(Rest(duration))
                continue
            note_step = step
            if combined:
                note_step = note_steps[play.next(('notes', notes_name), len(note_steps), order(notes))]
                values.update({row: self._row(notes, row, note_step) for row in NOTE_ROWS})
            drum = notes.is_drum()
            values['grabbed'] = grab(moment) if grab and self._row(notes, 'grab', note_step) else None
            totals = (
                play.accumulate('note', values['note_add'], notes.get_accumulator_limit()),
                play.accumulate('velocity', values['velocity_add'], rhythm.get_accumulator_limit()),
            )
            positions += self._step(values, drum, context, where, rolls, *totals)
        clip = Clip(notes=positions, scale=context.scale, controls=controls)
        return clip.section(0, length) if time > length else clip

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
        transpose = 0 if drum else context.transpose
        for place in range(ratchet):
            shift = transpose + note_total + place * offset
            if values['grabbed'] is not None:
                played = self._grabbed_sound(values['grabbed'], length, shift, drum, context)
            else:
                played = self._sound(values, drum, length, octave, shift, context, where)
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

    def _grabbed_sound(self, number, length, shift, drum, context):
        """Return a grabbed note, moved along this clip's scale, or by half steps for drums.

        A note moved outside the MIDI range stays where it was grabbed.
        """
        octave, place = divmod(number, 12)
        note = Note(SHARP_NAMES[place], octave, length)
        try:
            return along_scale(note, shift, None if drum else context.scale)
        except ValueError:
            return note

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
            Degree(degree + above, length, half_steps=half_steps, scale_notes=shift).to_note(scale)
            for above in SCALE_CHORDS[symbol]
        ])

    # Building generators.

    def _generator(self, step, context, chain, index):
        kind, name = step
        settings = self.song.get_generator_settings(kind, name)
        # An arp with no seed of its own gets one from the song's, which differs for every
        # scene, track and place in the chain, so that a render is always the same.
        track = self.tracks.index(context.track)
        seed = self.seed * 1_000_003 + context.stanza.number * 1_009 + track * 31 + index
        return settings.make_generator(f'chain {chain!r}, {kind}', seed)


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
