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

"""Playing what one track plays in one scene into a finished clip."""

from math import ceil

from llamatron.support.length import Length
from llamatron.support.rational import Rational
from llamatron.composition.song_file_error import SongFileError
from llamatron.generators.blend import Blend
from llamatron.music.sound import CHORD, HELD, HELD_SOUND, KIND, LENGTH, NOTE, Sound
from llamatron.playback.morph_controls import morph_controls
from llamatron.playback.pattern_player import PatternPlayer
from llamatron.playback.step_order import StepOrder
from llamatron.support.random_source import random_source
from llamatron.composition.conditions import any_true
from llamatron.composition.file_format import ClipSlotSetting, GeneratorKind, Shape, TrackSetting
from llamatron.composition.generator_settings import GENERATOR_SETTINGS
from llamatron.playback.shapes import reshaped
from llamatron.generators.euclid import EuclidMask
from llamatron.composition.checks import in_whole_notes
from llamatron.grid.clip import Clip
from llamatron.grid.keyswitch import SwitchNote
from llamatron.strings import errors

# The seeds for a clip slot's random choices: which steps play, by probability, and the order of steps
# in directions that choose as they go. They come from the render's seed, the scene and the track,
# so each clip slot differs but a seeded render is always the same.
PROBABILITY_SEED = '{seed}/{scene}/{track}'
DIRECTION_SEED = '{seed}/{scene}/{track}/direction'
# A morph's target chooses its steps from a stream of its own, so that a random direction on the
# clip can't change what the clip's own pattern draws.
MORPH_DIRECTION_SEED = '{seed}/{scene}/{track}/morph direction'
# A morph moves from 0 percent of the way to its target on the first repeat to 100 on the last.
FULL_MORPH = 100
# A clip with nothing in it ends straight away.
NO_LENGTH = 0
# The kinds of generator that move a clip's notes to a chord, which a drum pattern is spared.
KINDS_MOVING_PITCHES = (GeneratorKind.PROGRESSION, GeneratorKind.FOLLOW_CHORDS)


# What a chain's generator sets in the registers: nothing, since only the pattern's = rows set.
# The generator kind of each shape, which the render reads for each clip rather than running on its notes.
# Where a clip's or a scene's own shape starts: with the clip.
NO_OFFSET = 0
SHAPE_KINDS = {GeneratorKind.DENSITY: Shape.DENSITY, GeneratorKind.SWELL: Shape.SWELL, GeneratorKind.ARTICULATE: Shape.ARTICULATE}
NO_SETS = {}
# The pass a clip launches on, when it sets registers, and the pass whose statements speak for a shape, which works on the whole clip.
FIRST_PASS = 0


def _time_of(change):
    """Return when a generator's register change happens, which orders them."""
    return change[0]


class ClipSlotPlayer:
    """Plays a track's clip slot in a scene: its pattern, repeated or looped, morphing, then through its chain.

    It asks the SongRenderer it belongs to for the scene's length, which a looping clip fills, and
    for the notes of a track it grabs from.
    """

    __slots__ = ('_renderer', '_song', '_scene', '_track_name', '_clip_slot', '_track')

    def __init__(self, *, renderer, song, scene, track_name):
        self._renderer = renderer
        self._song = song
        self._scene = scene
        self._track_name = track_name
        self._clip_slot = scene.get_clip_slot(track_name)
        self._track = song.get_track(track_name)

    def play(self, *, grabbing, registers):
        """Return the finished clip, with its grab steps grabbing only if grabbing is true.

        registers is the RegisterRecorder or RegisterReader its steps use.
        """
        clip_slot = self._clip_slot
        scene = self._scene
        where = errors.ERR_CLIP_SLOT_PLAYER_WHERE.format(scene=scene.get_number(), track=self._track_name)
        scale = self._clip_scale()
        drifts = self._renderer.drifts_of(scene=scene, track=self._track_name)
        origins = {name: self._renderer.drift_origin(scene=scene, name=name) for name in drifts}
        hearing = None if not drifts or registers.is_counting() else (self._renderer.get_drifts(), drifts, self._renderer.scene_start(scene), origins)
        player = PatternPlayer(song=self._song, scene=scene, scale=scale, track=self._track, scale_name=self._scale_name(), drifts=hearing)
        grab = self._renderer.get_grab_source(scene=scene, track=self._track_name) if grabbing else None
        loop = clip_slot.loops()
        fill = self._renderer.get_scene_length(scene) if loop else None
        try:
            clip, switched, passes = self._play_passes(player=player, grab=grab, scale=scale, where=where, fill=fill, registers=registers)
            controls = clip.get_controls()
            clip, chain_adds = self._through_chain(clip, counting=registers.is_counting(), passes=passes)
            if not registers.is_counting():
                clip = self._shaped(self._masked(clip), passes=passes)
            # What the chain's generators add to the registers comes after what the pattern's steps add at the same moment.
            for time, adds in chain_adds:
                registers.at_step(time=time, sets=NO_SETS, adds=adds)
            end = fill if loop else clip.total_length()
            # A looping clip is cut where its scene ends. One that doesn't loop plays the whole of what it played, so nothing is cut, and sectioning it to its own length would only rebuild every position.
            if loop:
                sounds = clip.section(start=NO_LENGTH, end=end).get_sounds() if end > NO_LENGTH else []
            else:
                sounds = clip.played_sounds()
            controls = self._sent_controls(controls=controls, end=end)
            # A clip is named after the pattern it plays unless it has a name of its own, while its scene keeps
            # the scene's name, and it carries the pattern's own time signature, if it has one, for the bars a DAW draws.
            signature = self._song.get_pattern(clip_slot.get_pattern_name()).get_time_signature()
            finished = Clip(name=clip_slot.get_display_name(), sounds=sounds, scale=scale, loop=loop, controls=controls, time_signature=signature)
            if switched:
                finished.set_keyswitches(self._switch_notes(switched=switched, end=end))
            return finished
        except (ValueError, TypeError) as error:
            raise SongFileError(errors.ERR_CANT_PLAY.format(where=where, problem=error)) from error

    def _scale_name(self):
        """Return the name of the scale the clip plays in: its own, or else its scene's, which is the song's when the scene has none."""
        return self._clip_slot.get_scale_name() or self._scene.get_scale_name()

    def _clip_scale(self):
        """Return the scale the clip plays in, rooted at its octave, or None if neither it, its scene nor its song has one."""
        scale_name = self._scale_name()
        if scale_name is None:
            return None
        return self._song.get_named_scale(scale_name).scale_at(self._clip_octave())

    def _through_chain(self, clip, *, counting, passes):
        """Return the clip after each generator of its chains, in order, and what the generators add to the registers, as (time, adds) in time order.

        Its chains are the clip slot's own, then its scene's, then its track's,
        each in its own order, so a chain named in two places runs twice. Each
        generator is counted along all of them for its seed, so a clip with one chain draws as
        it always has.

        passes are the clip's passes of its pattern, each with the registers' values as it
        started. A pass on which a generator's statements hold goes by that generator
        untouched, one on which a chain's hold goes by the whole chain, and one on which the
        scene's, the clip's or the track's hold goes by every chain. A generator still runs
        over the whole clip, so that what it carries from note to note and what it adds to the
        registers never depend on the registers, and the passes it is left out of are put back
        as they were.
        """
        chains = self._renderer.chains_of(scene=self._scene, track=self._track_name)
        if not chains or clip.total_length() == NO_LENGTH:
            return clip, []
        adds = []
        index = 0
        # How many times each generator has come up in the clip's chains, so that one named twice keeps two states.
        times = {}
        untouched = clip
        for chain in chains:
            entering = clip
            written = self._song.get_chain(chain)
            for step in written.get_steps():
                # A drift works on the steps as the pattern plays, and a shape on the finished clip after the chains (playback/drift.py, playback/shapes.py).
                # A progression and a Follow Chords leave a drum pattern alone, since moving a drum note changes the drum, not the pitch.
                if GENERATOR_SETTINGS[step.kind].GENERATOR is not None and not (step.kind in KINDS_MOVING_PITCHES and self._plays_drums()):
                    key = (step.kind, step.name, times.get((step.kind, step.name), 0))
                    times[(step.kind, step.name)] = key[-1] + 1
                    generator = self._renderer.make_generator(step=step, scene=self._scene, track=self._track_name, chain=chain, index=index, key=key, counting=counting)
                    generated = generator.generate(clip)
                    self._renderer.keep_end_state(scene=self._scene, track=self._track_name, key=key, counting=counting, state=generator.end_state())
                    adds += generator.register_adds()
                    own = self._song.get_generator_settings(kind=step.kind, name=step.name).get_bypass_when()
                    clip = _kept_where(tripped=_tripped(passes=passes, tables=[own]), before=clip, after=generated, passes=passes)
                index += 1
            clip = _kept_where(tripped=_tripped(passes=passes, tables=[written.get_bypass_when()]), before=entering, after=clip, passes=passes)
        clip = _kept_where(tripped=_tripped(passes=passes, tables=self._bypass_tables()), before=untouched, after=clip, passes=passes)
        return clip, sorted(adds, key=_time_of)

    def _bypass_tables(self):
        """Return the tables of statements that bypass every generator of the clip: its scene's, its own and its track's."""
        return [
            self._scene.get_scene().get_bypass_when(), self._clip_slot.get_statements(ClipSlotSetting.BYPASS_WHEN),
            self._track.get_statements(TrackSetting.BYPASS_WHEN),
        ]

    def _skip_tables(self):
        """Return the tables of statements that make the clip sit a pass out: its own and its track's."""
        return [self._clip_slot.get_statements(ClipSlotSetting.SKIP_WHEN), self._track.get_statements(TrackSetting.SKIP_WHEN)]

    def _shape_is_bypassed(self, *, chain, name, kind, passes):
        """Return whether a shape a chain names is left out of the clip. A shape works on the whole clip at once, so the registers as the clip's first pass starts speak for all of it."""
        tables = [*self._bypass_tables(), self._song.get_chain(chain).get_bypass_when(), self._song.get_generator_settings(kind=kind, name=name).get_bypass_when()]
        return any(_tripped(passes=passes[:FIRST_PASS + 1], tables=tables))

    def _masked(self, clip):
        """Return the clip with its track's Euclidean mask applied after its chains, or as it is when the track has none."""
        track = self._song.get_track(self._track_name)
        mask = track.get_euclid()
        if mask is None:
            return clip
        bar = self._song.get_time_signature().bar_length()
        step = self._song.get_pattern_step_size(self._song.get_pattern(self._clip_slot.get_pattern_name())) if mask.step is None else in_whole_notes(time=mask.step, bar=bar)
        return EuclidMask(hits=mask.hits, steps=mask.steps, rotate=mask.rotate, step=step).generate(clip)

    def _plays_drums(self):
        """Return whether the clip slot's own pattern is a drum pattern."""
        return self._song.get_pattern(self._clip_slot.get_pattern_name()).is_drum()

    def _shaped(self, clip, *, passes):
        """Return the clip with its Density, Swell and Articulate applied: the last generator of each kind its chains name, else the clip's own, else its scene's. A generator its statements bypass is not named."""
        named = {}
        for chain in self._renderer.chains_of(scene=self._scene, track=self._track_name):
            for step in self._song.get_chain(chain).get_steps():
                if step.kind in SHAPE_KINDS and not self._shape_is_bypassed(chain=chain, name=step.name, kind=step.kind, passes=passes):
                    named[SHAPE_KINDS[step.kind]] = step.name
        clip_length = clip.total_length()
        scene_length = self._renderer.get_scene_length(self._scene)
        shapes = {}
        for kind, shape in SHAPE_KINDS.items():
            if shape in named:
                # A generator's ramp runs over its whole run, which its Restart says: the clip, every play of the scene in a row, or the song.
                settings = self._song.get_generator_settings(kind=kind, name=named[shape])
                restart = settings.get_restart()
                span = self._renderer.run_span(scene=self._scene, restart=restart, clip_length=clip_length)
                shapes[shape] = (settings.get_shape(), span, self._renderer.run_offset(scene=self._scene, restart=restart))
            elif self._clip_slot.get_shape(shape) is not None:
                shapes[shape] = (self._clip_slot.get_shape(shape), clip_length, NO_OFFSET)
            elif self._scene.get_scene().get_shape(shape) is not None:
                shapes[shape] = (self._scene.get_scene().get_shape(shape), scene_length, NO_OFFSET)
        if not shapes:
            return clip
        signature = self._song.get_time_signature()
        shapes = {shape: (_in_whole_notes(values=values, bar=signature.bar_length()), span, offset) for shape, (values, span, offset) in shapes.items()}
        sounds = reshaped(
            sounds=clip.resolved_sounds(), density=shapes.get(Shape.DENSITY), swell=shapes.get(Shape.SWELL), articulate=shapes.get(Shape.ARTICULATE),
            span=clip_length, bar=signature.bar_length(), beat=signature.beat_length(),
        )
        return Clip(name=clip.get_name(), sounds=sounds, scale=clip.get_scale(), length=clip.get_length(), note_length=clip.get_note_length(), controls=clip.get_controls())

    def _switch_notes(self, *, switched, end):
        """Return the keyswitch notes the clip sends before it ends, SwitchNotes in time order: each slot's note in the track's instrument, cut at the clip's end.

        A slot the instrument gives no note sends nothing until it has one, and a track with no
        instrument, or one that plays through FluidSynth, which would sound each as a note, sends
        none. The notes are the instrument's as written: no
        scale, transposing or generator reaches them.
        """
        instrument = self._renderer.instrument_of(self._track)
        if instrument is None or instrument.uses_fluidsynth():
            return []
        notes = instrument.get_keyswitch_notes()
        return [
            SwitchNote(slots.start, min(slots.end, end), notes[slot])
            for slots in switched if slots.start < end for slot in slots.slots if slot in notes
        ]

    def _sent_controls(self, *, controls, end):
        """Return the CC values the track sends before the clip ends, with each lane turned into its CC number.

        Until here a control's number is its lane. A lane the track has no CC number for sends nothing.
        """
        numbers = self._track.get_cc_numbers()
        return [
            item.with_number(numbers[item.get_number()]) for item in controls
            if item.get_time() < end and numbers[item.get_number()] is not None
        ]

    def _clip_octave(self):
        """Return the octave for the root of this clip's scale: the octave of the first note the clip plays."""
        octave = self._song.get_pattern(self._clip_slot.get_pattern_name()).get_first_octave()
        return self._song.get_default_octave() if octave is None else octave

    def _play_passes(self, *, player, grab, scale, where, fill, registers):
        """Return what the clip plays before any chains, its repeats or enough passes to fill a length, the keyswitch slots played, and its passes.

        Each pass is (start, end, values): when it starts and ends in the clip, and the
        registers' values as it started, or None while the clip is only played to count its
        changes. As a pass starts the clip adds to the registers, and on its first pass sets
        them. A pass on which a statement that makes the clip sit out holds is silence of the
        pass's length: it is still played, so that every random choice and every register
        change is what it would have been, and what it played is dropped.
        """
        sets = self._clip_slot.get_register_sets()
        adds = self._clip_slot.get_register_adds()
        skips = [table for table in self._skip_tables() if table]
        passes = []
        rolls = random_source(self._seed_for(PROBABILITY_SEED))
        order = StepOrder(random_source(self._seed_for(DIRECTION_SEED)))
        target_order = StepOrder(random_source(self._seed_for(MORPH_DIRECTION_SEED)))
        repeat = self._clip_slot.get_repeat()
        sounds = []
        controls = []
        switched = []
        total = Rational(0)
        place = 0
        while (place < repeat) if fill is None else (total < fill):
            values = registers.at_pass(time=total, sets=sets if place == FIRST_PASS else NO_SETS, adds=adds)
            played = self._play_pass(player=player, grab=grab, scale=scale, place=place % repeat, repeat=repeat, where=where, rolls=rolls, order=order, target_order=target_order, registers=registers, start=total)
            length = played.length
            if length == NO_LENGTH:
                break
            if values is not None and any(any_true(statements=table, values=values) for table in skips):
                played.clip = Clip(sounds=[Sound.rest(Length.of(length))], scale=scale)
                played.tied_from_before = NO_LENGTH
                played.keyswitches = []
            passes.append((total, total + length, values))
            # Ties at the start of this pass hold the note the passes so far ended with.
            if played.tied_from_before > NO_LENGTH:
                sounds = _tied_on(sounds=sounds, extra=Length.of(played.tied_from_before))
                # A keyswitch still held where the pass before ended is held on with its note.
                if switched and switched[-1].end == total:
                    switched[-1] = switched[-1].ending(total + played.tied_from_before)
            sounds += played.clip.get_sounds()
            controls += _moved_later(controls=played.clip.get_controls(), time=total)
            switched += [slots.moved_by(total) for slots in played.keyswitches]
            total += length
            place += 1
        clip = Clip(sounds=sounds, scale=scale, controls=controls)
        return (clip.section(start=NO_LENGTH, end=fill) if fill else clip), switched, passes

    def _seed_for(self, template):
        """Return the seed for one of this clip's random choices, or None when the render has no seed."""
        seed = self._renderer.get_seed()
        if seed is None:
            return None
        return template.format(seed=seed, scene=self._scene.get_number(), track=self._track_name)

    def _play_pass(self, *, player, grab, scale, place, repeat, where, rolls, order, target_order, registers, start):
        """Return one pass through the clip slot's pattern as a Pass, part way through any morph.

        The clip slot's direction applies to everything the clip slot plays, its own pattern and a morph's
        target, which otherwise follows its own pattern's direction and keeps its place from pass
        to pass in target_order. Only the first pattern takes
        grabs. A morph's target uses the registers but doesn't add to them, so that a step isn't
        counted twice, and ties at the start of a pass follow the clip slot's own pattern, whatever the
        morph puts there. A pass with no positions at all, which only ties can make, has nothing
        to morph.
        """
        clip_slot = self._clip_slot
        played = player.play_pass(pattern_name=clip_slot.get_pattern_name(), grab=grab, direction=clip_slot.get_direction(), where=where, rolls=rolls, order=order, registers=registers, start=start)
        clip = played.clip
        morph_to = clip_slot.get_morph_target()
        if morph_to is None or not clip.has_positions():
            return played
        target = player.play_pass(pattern_name=morph_to, grab=None, direction=clip_slot.get_direction(), where=where, rolls=rolls, order=target_order, registers=registers, start=start, changes_registers=False).clip
        amount = Rational(place, repeat - 1) * FULL_MORPH
        target = _looped(clip=target, length=played.length)
        blend = Blend(target=target, amount=amount, mode=clip_slot.get_morph_style())
        start, end = blend.region(clip)
        controls = morph_controls(source=clip, target=target, start=start, end=end)
        played.clip = Clip(sounds=blend.generate(clip).played_sounds(), scale=scale, controls=controls)
        return played


def _tripped(*, passes, tables):
    """Return, for each pass of a clip, whether any statement of any of the tables holds for the registers as the pass started. A pass with no values known trips nothing."""
    tables = [table for table in tables if table]
    if not tables:
        return []
    return [values is not None and any(any_true(statements=table, values=values) for table in tables) for _, _, values in passes]


def _kept_where(*, tripped, before, after, passes):
    """Return a clip that is the clip before a generator on the passes that tripped and the clip after it on the rest.

    A generator that changes how long the clip lasts leaves no pass to put back, so its
    clip is taken whole unless every pass tripped.
    """
    if not any(tripped):
        return after
    if all(tripped):
        return before
    total = after.total_length()
    if before.total_length() != total:
        return after
    sounds = []
    for (start, end, _), left_out in zip(passes, tripped):
        end = min(end, total)
        if start < end:
            sounds += (before if left_out else after).section(start=start, end=end).get_sounds()
    return Clip(name=after.get_name(), sounds=sounds, scale=after.get_scale(), length=after.get_length(), note_length=after.get_note_length(), controls=after.get_controls())


def _tied_on(*, sounds, extra):
    """Return a clip's sounds with the note still sounding at their end held for extra longer, for ties that follow.

    The last sound is that note if it's a note or chord, or a held one whose sound reaches the end.
    Anything else, like a rest, means nothing is sounding, so the ties are silence and nothing
    changes. The note becomes a held one, so that the next positions still start on time.
    """
    if not sounds:
        return sounds
    last = sounds[-1]
    kind = last[KIND]
    place = last[LENGTH]
    if kind == NOTE or kind == CHORD:
        held = Sound.held(Sound.lasting(last, Length.add(place, extra)), place)
    elif kind == HELD and Length.at_most(place, last[HELD_SOUND][LENGTH]):
        sound = last[HELD_SOUND]
        held = Sound.held(Sound.lasting(sound, Length.add(sound[LENGTH], extra)), place)
    else:
        return sounds
    return [*sounds[:-1], held]


def _looped(*, clip, length):
    """Return a clip repeated or cut to last a length."""
    own_length = clip.total_length()
    if own_length > NO_LENGTH:
        clip = clip.repeated(ceil(length / own_length))
    return clip.section(start=NO_LENGTH, end=length)


def _moved_later(*, controls, time):
    """Return CC values moved later by a time, for a pass that starts there."""
    return [item.moved_by(time) for item in controls]


def _in_whole_notes(*, values, bar):
    """Return a shape's values with its over, which may be written in bars, as a length in whole notes."""
    return values if values.over is None else values._replace(over=in_whole_notes(time=values.over, bar=bar))
