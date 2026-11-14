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

"""Rendering a composed Song into a ClipGrid of finished clips, for the exporters to write."""

from fractions import Fraction
from typing import NamedTuple

from llamatron.composition.strum import strums_at_all
from llamatron.grid.strum_plan import StrumPlan
from llamatron.exporters.timing import timed_events
from llamatron.grid.handed_note import HandedNote
from llamatron.grid.nudge_plan import MovingRow, NudgePlan, amount_moved
from llamatron.support.rational import Rational
from llamatron.composition.file_format import REGISTER_NAMES, GeneratorKind, Restart, Section
from llamatron.generators.base import Continuation
from llamatron.music.sound import CHORD, HELD, HELD_SOUND, KIND
from llamatron.composition.song_file_error import SongFileError
from llamatron.support.random_source import random_source
from llamatron.playback.clip_slot_player import ClipSlotPlayer
from llamatron.playback.drift import DriftPlay, drifts_named
from llamatron.playback.pattern_player import check_pattern_has_a_scale
from llamatron.playback.grab_source import GrabSource
from llamatron.playback.registers import RegisterChange, RegisterReader, RegisterRecorder, RegisterTimeline, starting_values, with_resets
from llamatron.playback.written_scene import WrittenScene
from llamatron.grid.clip_grid import ClipGrid
from llamatron.grid.clip_row import ClipRow
from llamatron.grid.clip_column import ClipColumn
from llamatron.grid.control import Control
from llamatron.music.midi import MAX_CC_VALUE, MIN_CC_VALUE
from llamatron.strings.errors import ERR_CIRCULAR_GRAB, ERR_RENDERER_EVERY_CLIP_LOOPS, ERR_WHERE_CHAIN

# How a circular grab's tracks are joined in its message, like a → b → a.
GRAB_ARROW = ' → '
# An arp with no seed of its own gets one made from the render's seed, its scene, its track and
# its place in the chain, multiplied by these so that each comes out different.
SEED_SONG_FACTOR = 1_000_003
SEED_SCENE_FACTOR = 1_009
SEED_TRACK_FACTOR = 31
# The registers' random values, for an At limit that picks one, come from a generator of their own, so that they can't change what probability or an arp draws.
REGISTER_SEED_OFFSET = 7
# The generators that move notes early or late in the timing, rather than running on a clip's notes.
MOVING_KINDS = (GeneratorKind.RUSH, GeneratorKind.DRAG)
# What a strum's seed adds, so that its loose timing draws apart from everything else, and how many seeds a render picks from.
STRUM_SEED_OFFSET = 977
STRUM_SEEDS = 1_000_000
# A tempo is held to this denominator, and a whole note lasts this many milliseconds at one beat a minute.
TEMPO_DENOMINATOR = 1000
MILLISECONDS_PER_WHOLE_NOTE_AT_ONE_BEAT_A_MINUTE = 240_000
# Turning a length in whole notes into seconds, at a tempo in quarter notes a minute.
SECONDS_PER_MINUTE = 60
QUARTER_NOTES_PER_WHOLE_NOTE = 4
# A drift's register adds come before every track's at the same moment, from a place before the first track's.
DRIFT_PLACE = -1
# How long a scene with nothing in it lasts, and where a clip starts in its scene.
NO_LENGTH = Rational(0)
START = Rational(0)


class SceneEstimate(NamedTuple):
    """How long one written-out scene lasts: its number, its seconds, each track's clip's seconds, and what stops it, if anything.

    A scene with a problem has no seconds and no clip seconds, and the problem says why.
    """

    number: int
    seconds: object
    clip_seconds: dict
    problem: object


class SongRenderer:
    """Plays every scene of a song into finished clips, remembering each clip once it's played.

    Clips are played when they're first asked for, so that a clip that grabs from another track
    can simply ask for that track's clip, and a grab that goes round in a circle is caught.

    How long a clip or a scene lasts never depends on what it plays, so get_clip_length and
    get_scene_length work that out from the patterns and clip slots without playing anything, and the
    estimate the tracker shows after every change uses nothing else.

    In a song where a step sets or adds to a register, each clip is played twice: first counted,
    without grabs or register values, to record what it changes in the registers, and then
    finished, reading the registers from the scene's RegisterTimeline. See registers.py. In a song
    where nothing changes a register, the registers keep their values throughout, so the counting
    pass would record nothing, and only the finished pass is played.

    A finished clip on a track whose CC lanes are bound to registers then sends each bound
    register's value on its lane, as a CC value held between 0 and 127: at the clip's start, and
    whenever the value it would send changes while the clip plays. A track with nothing in a
    scene sends nothing there, and a CC value of the clip's own at the same moment on the same
    lane wins (the user's design of 2026-11-11).
    """

    __slots__ = ('_song', '_seed', '_scenes', '_registers', '_clips', '_counted', '_lengths', '_timelines', '_grabbing', '_register_chooser', '_drifts', '_starts', '_strum_seed', '_end_states', '_chord_counts', '_hocket_turns', '_source_turns', '_looping_scenes_go_round')

    def __init__(self, song, *, seed=None, looping_scenes_go_round=False):
        """Render a song, with a seed in place of the song's own if one is given, so that any render can be repeated.

        A scene whose every clip loops can't be exported, since nothing says how long it lasts. With
        looping_scenes_go_round, as real-time playback renders, such a scene lasts as long as its longest
        clip would play once, and goes round, so that a scene made to loop while it plays plays on.
        """
        self._looping_scenes_go_round = looping_scenes_go_round
        self._song = song
        self._seed = song.get_seed() if seed is None else seed
        self._scenes = WrittenScene.write_out(song)
        self._registers = {name: song.get_register(name) for name in REGISTER_NAMES}
        self._clips = {}
        # Clips played only to record their register changes, with those changes.
        self._counted = {}
        self._lengths = {}
        self._timelines = {}
        # The tracks whose clips are waiting on a grab, to catch clips that grab in a circle.
        self._grabbing = []
        self._register_chooser = random_source(None if self._seed is None else self._seed * SEED_SONG_FACTOR + REGISTER_SEED_OFFSET)
        self._drifts = DriftPlay(song=song, seed=self._seed)
        # What every strum's loose timing draws from, fixed for the render so that every export of it and its playing agree.
        # The state each generator left each track's clip in, by pass, written scene, track and the generator's place, for a Restart that carries on.
        self._end_states = {}
        # How many chords each track's finished clip in each written scene holds, for a Strum's down up that carries on.
        self._chord_counts = {}
        self._strum_seed = random_source(None if self._seed is None else self._seed * SEED_SONG_FACTOR + STRUM_SEED_OFFSET).randrange(STRUM_SEEDS)
        # Where each written-out scene starts from the song's top, in whole notes, for the drifts' clocks.
        self._starts = {}
        # Each Hocket's notes dealt out to its pool in each written scene, and each source track's notes there as turns, each worked out once.
        self._hocket_turns = {}
        self._source_turns = {}

    def instrument_of(self, track):
        """Return a track's instrument, or None when it has none."""
        name = track.get_instrument_name()
        setlist = self._song.get_setlist()
        if name is None or setlist is None or not setlist.has_item(section=Section.INSTRUMENTS, name=name):
            return None
        return setlist.get_instrument(name)

    def gm_sound_of(self, track):
        """Return the General MIDI sound of a track's instrument, or None when the track has no instrument or the instrument no sound."""
        instrument = self.instrument_of(track)
        return None if instrument is None else instrument.get_gm_sound()

    def plays_through_fluidsynth(self, track):
        """Return whether a track's instrument plays through FluidSynth."""
        instrument = self.instrument_of(track)
        return instrument is not None and instrument.uses_fluidsynth()

    def render(self):
        """Return a ClipGrid with every scene's finished clips, or raise SongFileError."""
        grid = ClipGrid(tempo=_whole_if_possible(float(self._song.get_tempo())), time_signature=self._song.get_time_signature())
        tracks = self._add_tracks(grid)
        for scene in self._scenes:
            tempo = None if scene.get_tempo() is None else float(scene.get_tempo())
            grid_scene = grid.add_row(ClipRow(name=scene.get_name(), tempo=tempo))
            for name in self._song.get_track_names():
                clip = self.get_clip(scene=scene, track=name)
                if clip is not None:
                    # The groove goes on last, so that generators, grabs and lengths never see it.
                    clip.set_groove(self._song.groove_at(scene=scene, track=name))
                    clip.set_strum(self.strum_plan(scene=scene, track=name, tempo=self._song.get_tempo() if tempo is None else tempo))
                    self._chord_counts[(scene.get_number(), name)] = _chords_in(clip)
                    clip.set_nudge(self.nudge_plan(scene=scene, track=name))
                    clip.set_handed(self.handed_notes(scene=scene, track=name))
                    grid.set_clip(row=grid_scene, column=tracks[name], clip=clip)
        return grid

    def strum_plan(self, *, scene, track, tempo):
        """Return how a clip strums its chords at its scene's tempo, or None: the last Strum generator its chains name, else the clip's own strum, else its track's."""
        strum = None
        restart = Restart.EVERY_CLIP
        for chain in self.chains_of(scene=scene, track=track):
            for step in self._song.get_chain(chain).get_steps():
                if step.kind == GeneratorKind.STRUM:
                    settings = self._song.get_generator_settings(kind=GeneratorKind.STRUM, name=step.name)
                    strum = settings.get_strum()
                    restart = settings.get_restart()
        if strum is None:
            strum = scene.get_scene().get_clip_slot(track).get_strum() or self._song.get_track(track).get_strum()
        if not strums_at_all(strum):
            return None
        # A gap in milliseconds is that share of a whole note, which lasts four beats at the tempo.
        gap = Fraction(strum.milliseconds) * Fraction(tempo).limit_denominator(TEMPO_DENOMINATOR) / MILLISECONDS_PER_WHOLE_NOTE_AT_ONE_BEAT_A_MINUTE
        place = self._song.get_track_names().index(track)
        return StrumPlan(
            direction=strum.direction, gap=Rational(gap.numerator, gap.denominator), fade=strum.fade, loose_timing=strum.loose_timing,
            upstroke_count=strum.upstroke_count, beat=self._song.get_time_signature().beat_length(), seed=self._strum_seed + scene.get_number() * SEED_SCENE_FACTOR + place * SEED_TRACK_FACTOR,
            offset=self.run_offset(scene=scene, restart=restart), chords_before=self._chords_before(scene=scene, track=track, restart=restart),
        )

    def nudge_plan(self, *, scene, track):
        """Return how a clip's notes are rushed and dragged, from every Rush and Drag its chains name, or None when they name neither."""
        pattern_step = self._song.get_pattern_step_size(self._song.get_pattern(scene.get_clip_slot(track).get_pattern_name()))
        bar = self._song.get_time_signature().bar_length()
        rows = []
        for chain in self.chains_of(scene=scene, track=track):
            for step in self._song.get_chain(chain).get_steps():
                if step.kind in MOVING_KINDS:
                    settings = self._song.get_generator_settings(kind=step.kind, name=step.name)
                    rows.append(MovingRow(
                        steps=settings.get_steps(), step=settings.step_length(default_step=pattern_step, bar=bar),
                        amount=amount_moved(percent=settings.get_amount(), later=step.kind == GeneratorKind.DRAG),
                        offset=self.run_offset(scene=scene, restart=settings.get_restart()),
                    ))
        return NudgePlan(rows=rows) if rows else None

    def handed_notes(self, *, scene, track):
        """Return the notes the Hockets a track's clip names hand it in a written-out scene, in time order, or none.

        A Hocket whose source is the track itself is skipped there, since a track can't hand notes to itself.
        """
        handed = []
        for name in self.hockets_of(scene=scene, track=track):
            if self._song.get_generator_settings(kind=GeneratorKind.HOCKET, name=name).get_source() != track:
                handed += self.hocket_turns(scene=scene, name=name).get(track, [])
        return sorted(handed)

    def hockets_of(self, *, scene, track):
        """Return the names of the Hockets a track's clip names in its chains in a written-out scene, each once, in order."""
        names = [step.name for chain in self.chains_of(scene=scene, track=track) for step in self._song.get_chain(chain).get_steps() if step.kind == GeneratorKind.HOCKET]
        return list(dict.fromkeys(names))

    def hocket_pool(self, *, scene, name):
        """Return the tracks that take turns at a Hocket's notes in a written-out scene: every track but the source whose clip names it, in the song's track order."""
        source = self._song.get_generator_settings(kind=GeneratorKind.HOCKET, name=name).get_source()
        return [track for track in self._song.get_track_names() if track != source and name in self.hockets_of(scene=scene, track=track)]

    def hocket_turns(self, *, scene, name):
        """Return the notes a Hocket hands each track of its pool in a written-out scene, by the track, worked out once for the scene.

        Each turn is the source's notes that start together, a chord passing whole, and a rest
        passes no turn. The turns go round the pool from its first track, carrying on from the
        scenes before in the Hocket's run, as its Restart says, counted from the source's clips.
        """
        key = (scene.get_number(), name)
        if key not in self._hocket_turns:
            settings = self._song.get_generator_settings(kind=GeneratorKind.HOCKET, name=name)
            pool = self.hocket_pool(scene=scene, name=name)
            dealt = {}
            if pool and self.plays_source(scene=scene, source=settings.get_source()):
                start = self._scenes.index(self.run_start(scene=scene, restart=settings.get_restart()))
                turn = sum(len(self.source_turns(scene=written, source=settings.get_source())) for written in self._scenes[start:self._scenes.index(scene)]
                           if self.hocket_pool(scene=written, name=name) and self.plays_source(scene=written, source=settings.get_source()))
                for notes in self.source_turns(scene=scene, source=settings.get_source()):
                    dealt.setdefault(pool[turn % len(pool)], []).extend(notes)
                    turn += 1
            self._hocket_turns[key] = dealt
        return self._hocket_turns[key]

    def plays_source(self, *, scene, source):
        """Return whether a Hocket's source track is a track of the song with a clip in a written-out scene."""
        return source in self._song.get_track_names() and scene.get_clip_slot(source) is not None

    def source_turns(self, *, scene, source):
        """Return a source track's notes in a written-out scene as turns: the notes that start together, each a HandedNote, in time order, before any groove."""
        key = (scene.get_number(), source)
        if key not in self._source_turns:
            clip = self.get_clip(scene=scene, track=source)
            notes, _ = timed_events(clip=clip, scale=clip.get_scale(), grooved=False)
            turns = {}
            for note in sorted(notes):
                turns.setdefault(note.start, []).append(HandedNote(note.start, note.end, note.midi_number, note.velocity))
            self._source_turns[key] = list(turns.values())
        return self._source_turns[key]

    def _chords_before(self, *, scene, track, restart):
        """Return how many chords a track's clips strummed earlier in a run, which the render loop has counted, scene by scene."""
        start = self._scenes.index(self.run_start(scene=scene, restart=restart))
        return sum(self._chord_counts.get((written.get_number(), track), 0) for written in self._scenes[start:self._scenes.index(scene)])

    def _add_tracks(self, grid):
        """Add a finished track to the grid for each of the song's tracks, and return them by name."""
        tracks = {}
        for name in self._song.get_track_names():
            track = self._song.get_track(name)
            tracks[name] = grid.add_column(ClipColumn(name=name, mute=track.is_muted(), drum=track.is_drum(), gm_sound=self.gm_sound_of(track), fluidsynth=self.plays_through_fluidsynth(track)))
        return tracks

    def get_scenes(self):
        """Return the song's scenes as they play, written out once for each repeat."""
        return list(self._scenes)

    def estimate(self):
        """Return a SceneEstimate for each written-out scene, in seconds, without playing anything.

        The lengths come from get_scene_length and get_clip_length, which render uses too, so the two
        can't disagree, and a problem in one scene only affects that scene. The problems it
        reports are the ones that show without playing: every clip looping, scale degrees with no
        scale, and grabs that go round in a circle. A note a render can't fit in the MIDI range
        only shows when rendering.
        """
        result = []
        for scene in self._scenes:
            tempo = self._song.get_tempo() if scene.get_tempo() is None else scene.get_tempo()
            whole_notes_to_seconds = Rational(SECONDS_PER_MINUTE * QUARTER_NOTES_PER_WHOLE_NOTE) / tempo
            clips = {}
            problem = None
            seconds = None
            try:
                length = self.get_scene_length(scene)
                self._check_plays(scene)
                for track in scene.get_track_names():
                    clips[track] = self.get_clip_length(scene=scene, track=track) * whole_notes_to_seconds
                # A scene with a problem has no length, so it's set only once the checks pass.
                seconds = length * whole_notes_to_seconds
            except SongFileError as error:
                problem = str(error)
            result.append(SceneEstimate(scene.get_number(), seconds, clips, problem))
        return result

    def _check_plays(self, scene):
        """Raise the SongFileError a render of a scene would, for the problems that show without playing."""
        for track in scene.get_track_names():
            clip_slot = scene.get_clip_slot(track)
            for pattern_name in _patterns_played(clip_slot):
                check_pattern_has_a_scale(song=self._song, scene=scene, pattern_name=pattern_name, clip_scale=clip_slot.get_scale_name())
        circle = _grab_circle(scene)
        if circle is not None:
            raise SongFileError(ERR_CIRCULAR_GRAB.format(scene=scene.describe(), loop=GRAB_ARROW.join(circle)))

    def get_clip(self, *, scene, track):
        """Return the finished clip a track plays in a written-out scene, or None if it plays nothing."""
        clip_slot = scene.get_clip_slot(track)
        if clip_slot is None:
            return None
        key = (scene.get_number(), track)
        if key not in self._clips:
            registers = RegisterReader(timeline=self.get_timeline(scene), place=self._track_place(track))
            clip = ClipSlotPlayer(renderer=self, song=self._song, scene=scene, track_name=track).play(grabbing=clip_slot.get_grab_track() is not None, registers=registers)
            settings = self._song.get_track(track)
            bound = [(number, name) for number, name in zip(settings.get_cc_numbers(), settings.get_cc_registers()) if number is not None and name is not None]
            if bound:
                clip.add_controls(_bound_controls(
                    bound=bound, timeline=self.get_timeline(scene), own=clip.get_controls(), end=self.get_clip_length(scene=scene, track=track),
                ))
            self._clips[key] = clip
        return self._clips[key]

    def _counted_clip(self, *, scene, track):
        """Return a track's clip in a scene played without grabs or register values, and what it adds to the registers.

        Register changes from every track have to be collected, and put in time order, before any
        finished clip can read them, which is why this pass comes first.
        """
        key = (scene.get_number(), track)
        if key not in self._counted:
            recorder = RegisterRecorder(self._track_place(track))
            clip = ClipSlotPlayer(renderer=self, song=self._song, scene=scene, track_name=track).play(grabbing=False, registers=recorder)
            self._counted[key] = (clip, recorder.get_changes())
        return self._counted[key]

    def _track_place(self, track):
        """Return a track's place in the song, counted from 0, which orders register changes made at the same time."""
        return self._song.get_track_names().index(track)

    def get_timeline(self, scene):
        """Return the register values through a written-out scene.

        A scene starts with the values the scene before it ended with, or the registers' defaults
        for the first scene, and then sets the registers it resets back to their defaults, and as
        it first starts, not on its repeats, every register that resets each scene. A scene
        before it that can't be played changes nothing, so that estimates can still show this one.
        """
        values = starting_values(self._registers)
        for written in self._scenes[:self._scenes.index(scene) + 1]:
            number = written.get_number()
            if number not in self._timelines:
                start = with_resets(values=values, registers=self._registers, names=self._resets_of(written))
                try:
                    self._timelines[number] = RegisterTimeline(
                        registers=self._registers, start=start, changes=self._scene_changes(written), chooser=self._register_chooser,
                    )
                except SongFileError:
                    if written is scene:
                        raise
                    continue
            values = self._timelines[number].end_values()
        return self._timelines[scene.get_number()]

    def _resets_of(self, written):
        """Return the registers a written-out scene sets back to their defaults as it starts: its own resets, and on its first play every register that resets each scene."""
        names = written.get_reset_names()
        if written.is_first_play():
            names += [name for name, register in self._registers.items() if register.resets_each_scene() and name not in names]
        return names

    def _scene_changes(self, scene):
        """Return every change a scene's clips make to the registers before the scene ends, and the adds at the triggers of the drifts its clips name.

        A drift is one process for the song, so it adds once a trigger however many clips name
        it, before every track's change at that moment.
        """
        if not self._song.changes_registers():
            return []
        length = self.get_scene_length(scene)
        changes = []
        for track in scene.get_track_names():
            changes += _before(changes=self._counted_clip(scene=scene, track=track)[1], end=length)
        start = self.scene_start(scene)
        for name in dict.fromkeys(name for track in scene.get_track_names() for name in self.drifts_of(scene=scene, track=track)):
            origin = self.drift_origin(scene=scene, name=name)
            for time in self._drifts.trigger_times(name=name, start=start, end=start + length, origin=origin):
                adds = self._drifts.adds_at(name=name, trigger=self._drifts.trigger_at(name=name, time=time - origin))
                if adds:
                    changes.append(RegisterChange(time - start, DRIFT_PLACE, {}, adds))
        return changes

    def chains_of(self, *, scene, track):
        """Return the chains a track's clip in a written-out scene runs, in order: the clip's own, the scene's, then the track's; none when it plays nothing."""
        clip_slot = scene.get_clip_slot(track)
        if clip_slot is None:
            return []
        return [*clip_slot.get_chain_names(), *scene.get_scene().get_chain_names(), *self._song.get_track(track).get_chain_names()]

    def drifts_of(self, *, scene, track):
        """Return the names of the drifts a track's clip in a scene names in its chains, or none when it plays nothing."""
        return drifts_named(song=self._song, chain_names=self.chains_of(scene=scene, track=track))

    def get_drifts(self):
        """Return the song's drifts as they play, which every clip naming one reads."""
        return self._drifts

    def scene_start(self, scene):
        """Return where a written-out scene starts from the song's top, in whole notes: the scenes before it laid end to end."""
        number = scene.get_number()
        if number not in self._starts:
            place = self._scenes.index(scene)
            self._starts[number] = NO_LENGTH if place == 0 else self.scene_start(self._scenes[place - 1]) + self.get_scene_length(self._scenes[place - 1])
        return self._starts[number]

    def get_scene_length(self, scene):
        """Return how long a scene lasts, in whole notes: its longest clip that doesn't loop, worked out without playing."""
        number = scene.get_number()
        if number in self._lengths:
            return self._lengths[number]
        if scene.every_clip_loops():
            if not self._looping_scenes_go_round:
                raise SongFileError(ERR_RENDERER_EVERY_CLIP_LOOPS.format(scene=scene.describe()))
            length = max((self._played_once(scene=scene, track=track) for track in scene.get_track_names()), default=NO_LENGTH)
            self._lengths[number] = length
            return length
        length = NO_LENGTH
        for track in scene.get_track_names():
            if not scene.get_clip_slot(track).loops():
                length = max(length, self.get_clip_length(scene=scene, track=track))
        self._lengths[number] = length
        return length

    def get_clip_length(self, *, scene, track):
        """Return how long a track's clip lasts in a written-out scene, in whole notes, worked out without playing.

        A looping clip lasts as long as its scene. Any other plays its pattern repeat times, and
        every pass lasts the pattern's steps times its step size whatever the steps hold: a gate
        is cut at the end of its pass, ties and glides only lengthen a note's sound, a direction
        only reorders the steps, a morph's target is looped or cut to the pass, grabs and
        registers change only pitches and velocities, and a chain's generators keep a clip's
        length. test_clip_lengths.py checks this against a real play of every example.
        """
        clip_slot = scene.get_clip_slot(track)
        if clip_slot.loops():
            return self.get_scene_length(scene)
        return self._played_once(scene=scene, track=track)

    def _played_once(self, *, scene, track):
        """Return how long a clip lasts played once: its pattern repeat times, whether or not it loops."""
        clip_slot = scene.get_clip_slot(track)
        return clip_slot.get_repeat() * self._song.get_pattern_length(self._song.get_pattern(clip_slot.get_pattern_name()))

    def get_grab_source(self, *, scene, track):
        """Return the notes the track that a track's clip slot grabs from plays in a scene, or None if it plays nothing there."""
        other = scene.get_clip_slot(track).get_grab_track()
        if scene.get_clip_slot(other) is None:
            return None
        waiting = [*self._grabbing, track]
        if other in waiting:
            raise SongFileError(ERR_CIRCULAR_GRAB.format(scene=scene.describe(), loop=_grab_loop(waiting=waiting, track=other)))
        self._grabbing.append(track)
        try:
            source = self.get_clip(scene=scene, track=other)
        finally:
            self._grabbing.pop()
        return GrabSource(source)

    def get_seed(self):
        """Return the seed this render makes every random choice from, or None for a new take."""
        return self._seed

    def run_start(self, *, scene, restart):
        """Return the written-out scene a generator's run starts in, as its Restart says: this one, the first play of this scene, or the song's first."""
        if restart == Restart.WHOLE_SONG:
            return self._scenes[0]
        if restart == Restart.ON_NEW_SCENE:
            place = self._scenes.index(scene)
            while place > 0 and not self._scenes[place].is_first_play():
                place -= 1
            return self._scenes[place]
        return scene

    def run_offset(self, *, scene, restart):
        """Return how far into its run a generator is as a written-out scene starts, in whole notes."""
        return self.scene_start(scene) - self.scene_start(self.run_start(scene=scene, restart=restart))

    def run_span(self, *, scene, restart, clip_length):
        """Return how long a generator's whole run lasts: the clip, every play of the scene in a row, or the whole song."""
        if restart == Restart.EVERY_CLIP:
            return clip_length
        start = self._scenes.index(self.run_start(scene=scene, restart=restart))
        end = start + 1
        while end < len(self._scenes) and (restart == Restart.WHOLE_SONG or not self._scenes[end].is_first_play()):
            end += 1
        return sum((self.get_scene_length(written) for written in self._scenes[start:end]), NO_LENGTH)

    def continuation(self, *, settings, scene, track, key, counting, clip_length=None):
        """Return where a generator carries on from in a track's clip: how far into its run, how long the run lasts, and the state the same track's latest clip before in the run left it in.

        The clips before are worked out first if they aren't yet, without the grabs waiting on
        this one, since a clip before can't be part of a grab circle with it.
        """
        restart = settings.get_restart()
        offset = self.run_offset(scene=scene, restart=restart)
        span = self.run_span(scene=scene, restart=restart, clip_length=clip_length)
        state = None
        start = self._scenes.index(self.run_start(scene=scene, restart=restart))
        waiting = self._grabbing
        self._grabbing = []
        try:
            for written in reversed(self._scenes[start:self._scenes.index(scene)]):
                if written.get_clip_slot(track) is None:
                    continue
                if counting:
                    self._counted_clip(scene=written, track=track)
                else:
                    self.get_clip(scene=written, track=track)
                found = (counting, written.get_number(), track, key)
                if found in self._end_states:
                    state = self._end_states[found]
                    break
        finally:
            self._grabbing = waiting
        return Continuation(offset, span, state)

    def keep_end_state(self, *, scene, track, key, counting, state):
        """Keep the state a generator left a track's clip in, for the same track's next clip in its run."""
        self._end_states[(counting, scene.get_number(), track, key)] = state

    def drift_origin(self, *, scene, name):
        """Return where a drift's clock starts for a written-out scene, from the song's top, as its Restart says."""
        settings = self._song.get_generator_settings(kind=GeneratorKind.DRIFT, name=name)
        return self.scene_start(self.run_start(scene=scene, restart=settings.get_restart()))

    def make_generator(self, *, step, scene, track, chain, index, key=None, counting=False):
        """Return the generator for one step of a chain, as a clip slot on a track in a scene uses it.

        An arp with no seed of its own gets one from the render's, which differs for every scene,
        track and place in the chain, so that a seeded render is always the same. With no seed
        at all, the arp draws its own random numbers.
        """
        settings = self._song.get_generator_settings(kind=step.kind, name=step.name)
        place = self._song.get_track_names().index(track)
        seed = None if self._seed is None else self._seed * SEED_SONG_FACTOR + scene.get_number() * SEED_SCENE_FACTOR + place * SEED_TRACK_FACTOR + index
        pattern_step = self._song.get_pattern_step_size(self._song.get_pattern(scene.get_clip_slot(track).get_pattern_name()))
        continuation = None if key is None else self.continuation(settings=settings, scene=scene, track=track, key=key, counting=counting)
        return settings.make_generator(
            where=ERR_WHERE_CHAIN.format(chain=chain, kind=step.kind), default_seed=seed, default_step=pattern_step, bar=self._song.get_time_signature().bar_length(),
            continuation=continuation,
        )


def _whole_if_possible(number):
    """Return a number as a whole number if it is one, like 120 rather than 120.0."""
    return int(number) if number.is_integer() else number


def _patterns_played(clip_slot):
    """Return the names of the patterns a clip slot plays: its own, and the one it morphs to if it morphs."""
    names = [clip_slot.get_pattern_name()]
    if clip_slot.get_morph_target() is not None:
        names.append(clip_slot.get_morph_target())
    return names


def _grab_circle(scene):
    """Return the tracks whose grabs go round in a circle in a scene, like [lead, kick, lead], or None.

    A clip grabbing from a track follows that track's grab, and so on. A grab from a track with
    nothing in the scene grabs nothing, so it can't be part of a circle.
    """
    for start in scene.get_track_names():
        path = [start]
        while True:
            following = scene.get_clip_slot(path[-1]).get_grab_track()
            if following is None or scene.get_clip_slot(following) is None or following in path[1:]:
                break
            if following == start:
                return [*path, start]
            path.append(following)
    return None


def _bound_controls(*, bound, timeline, own, end):
    """Return the CC values a clip's bound lanes send: each lane's register, as it is at the clip's start and after each change before end, held to a CC value.

    bound holds (CC number, register name) for each lane that has a CC number on the track and a
    register bound to it; a lane with no CC number sends nothing, bound or not. A value is sent
    only when it differs from the last value the lane sent, the clip's own included, and never at
    a moment where the clip sends a value of its own on the lane, which wins.
    """
    moments = [(START, timeline.values_after(START))] + [moment for moment in timeline.changes_within(start=START, end=end) if moment[0] != START]
    controls = []
    for number, name in bound:
        own_values = {control.get_time(): control.get_value() for control in own if control.get_number() == number}
        sent = sorted([(time, value, True) for time, value in own_values.items()] + [(time, _cc_value(values[name]), False) for time, values in moments],
                      key=_sent_order)
        last = None
        for time, value, is_own in sent:
            if is_own:
                last = value
            elif time not in own_values and value != last:
                controls.append(Control(time=time, number=number, value=value))
                last = value
    return controls


def _sent_order(item):
    """Return when a lane's value is sent, as (time, whether it's the clip's own), so that the clip's own comes after a bound one at the same time and is what holds."""
    return item[0], item[2]


def _cc_value(value):
    """Return a register's value held to what a CC value can be."""
    return max(min(value, MAX_CC_VALUE), MIN_CC_VALUE)


def _before(*, changes, end):
    """Return the register changes made before a time, the end of their scene."""
    return [change for change in changes if change.time < end]


def _grab_loop(*, waiting, track):
    """Return the tracks that grab from each other in a circle, from where the circle starts, like a → b → a."""
    return GRAB_ARROW.join([*waiting[waiting.index(track):], track])


def _chords_in(clip):
    """Return how many chords a finished clip plays, a held one too, which a strum's down up counts."""
    return sum(1 for sound in clip.get_sounds() if sound[KIND] == CHORD or (sound[KIND] == HELD and sound[HELD_SOUND][KIND] == CHORD))
