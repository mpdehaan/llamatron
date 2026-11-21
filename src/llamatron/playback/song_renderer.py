# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Rendering a composed Song into a ClipGrid of finished clips, for the exporters to write."""

from fractions import Fraction
from typing import NamedTuple

from llamatron.exporters.timing import timed_events
from llamatron.generators.base import Continuation
from llamatron.generators.follow_chords import FollowChords
from llamatron.generators.musician import Surroundings
from llamatron.grid.clip_column import ClipColumn
from llamatron.grid.clip_grid import ClipGrid
from llamatron.grid.clip_row import ClipRow
from llamatron.grid.control import Control
from llamatron.grid.handed_note import HandedNote
from llamatron.grid.nudge_plan import amount_moved, MovingRow, NudgePlan
from llamatron.grid.row_clock import RowClock
from llamatron.grid.strum_plan import StrumPlan
from llamatron.math.random_source import random_source
from llamatron.math.rational import Rational
from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.objects.strum import strums_at_all
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import GeneratorKind, RampWay, Restart, Section, StepStatement
from llamatron.model.values import midi, sound as sound_values
from llamatron.playback import registers as registers_values
from llamatron.playback.chord_source import ChordSource
from llamatron.playback.clip_slot_player import ClipSlotPlayer
from llamatron.playback.draws import DrawPlay
from llamatron.playback.drift import DriftPlay, drifts_named
from llamatron.playback.grab_source import GrabSource
from llamatron.playback.pass_memory import PassMemory
from llamatron.playback.pattern_player import check_pattern_has_a_scale
from llamatron.playback.registers import RegisterChange, RegisterReader, RegisterRecorder, RegisterSolo, RegisterTimeline, RegisterTrial, scene_change, starting_values, with_resets
from llamatron.playback.scene_reuse import changed_clips, first_changed_scene, SceneCheckpoint
from llamatron.playback.tempo_ramps import ramped_tempos, tempos_within
from llamatron.playback.tune_source import TuneSource
from llamatron.playback.written_scene import WrittenScene
from llamatron.user_strings import errors

# How a circular grab's tracks are joined in its message, like a → b → a.
GRAB_ARROW = ' → '
# An arp with no seed of its own gets one made from the render's seed, its scene, its track and
# its place in the chain, multiplied by these so that each comes out different.
SEED_SONG_FACTOR = 1_000_003
SEED_SCENE_FACTOR = 1_009
SEED_TRACK_FACTOR = 31
# How far a clip's seeds move for each take after the first, a prime far past what a song's places reach.
SEED_TAKE_FACTOR = 1_000_000_007
FIRST_TAKE = 0
# The seed the song's random draws start afresh from as a retaken scene first starts.
DRAWS_TAKE_SEED = '{seed}/{scene}/draws take {take}'
# The registers' random values, for a Reset behavior that picks one, come from a generator of their own, so that they can't change what probability or an arp draws.
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
# The generators that follow another track's chords or tune, so that an edit reaching that track reaches theirs.
FOLLOWING_KINDS = (GeneratorKind.FOLLOW_CHORDS, GeneratorKind.MUSICIAN)
# A drift's register adds come before every track's at the same moment, from a place before the first track's.
DRIFT_PLACE = -1
# The seed of the random values a register draws while a scene's first guess is played, which the plays after it replace.
GUESS_SEED = 0
# Where a pattern's two answers about cutting stand: whether a step can cut a pass short, and whether one can stop the clip.
CUTS = 0
STOPS = 1
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
    lane wins.
    """

    __slots__ = ('_song', '_seed', '_scenes', '_registers', '_draws', '_clips', '_counted', '_lengths', '_timelines', '_grabbing', '_register_chooser', '_drifts', '_starts', '_strum_seed', '_end_states', '_chord_counts', '_hocket_turns', '_source_turns', '_looping_scenes_go_round', '_following', '_chord_sources', '_tune_sources', '_decided', '_guesses', '_cutting', '_settled_by_playing', '_ramped', '_data', '_checkpoints', '_reused', '_kept_clips', '_changes_registers', '_earlier', '_passes', '_takes', '_song_places')

    def __init__(self, song, *, seed=None, looping_scenes_go_round=False, data=None, takes=None):
        """Render a song, its random parts drawn afresh, or from a seed where one is given, so that a test or a tool can repeat a render.

        A scene whose every clip loops can't be exported, since nothing says how long it lasts. With
        looping_scenes_go_round, as real-time playback renders, such a scene lasts as long as its longest
        clip would play once, and goes round, so that a scene made to loop while it plays plays on.

        data, the set's data as its objects kept it (Setlist.kept_data) when the song was copied from it, makes a render that a
        later render of the same song, after an edit, can take its first scenes from (render(after=), scene_reuse.py).

        takes gives a clip new random choices, its take, by (the scene's place in the song, the track): every random choice of the
        clip, its probabilities, its order of steps and patterns, its generators and its strum, is drawn from its seed and its
        take, while the song's draws and drifts stay the song's. Take 0, every clip's unless given, draws as a render always has.
        """
        self._looping_scenes_go_round = looping_scenes_go_round
        self._song = song
        self._seed = seed
        self._takes = {} if takes is None else dict(takes)
        self._song_places = {id(scene): place for place, scene in enumerate(song.get_scenes())}
        self._scenes = WrittenScene.write_out(song)
        self._registers = {name: song.get_register(name) for name in file_format.REGISTER_NAMES}
        # Whether playing changes the registers, which every scene asks and which looks through every pattern of the set, asked
        # once, since nothing changes the song while it renders.
        self._changes_registers = song.changes_registers()
        self._draws = {name: song.get_draw(name) for name in file_format.DRAW_NAMES}
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
        # Each ramping scene's tempos, repeat by repeat, worked out once.
        self._ramped = {}
        self._strum_seed = random_source(None if self._seed is None else self._seed * SEED_SONG_FACTOR + STRUM_SEED_OFFSET).randrange(STRUM_SEEDS)
        # Where each written-out scene starts from the song's top, in whole notes, for the drifts' clocks.
        self._starts = {}
        # Each Hocket's notes dealt out to its pool in each written scene, and each source track's notes there as turns, each worked out once.
        self._hocket_turns = {}
        self._source_turns = {}
        # The clips waiting on the chords of a track they follow, as (scene, track), which finds tracks following each other in a circle, and the chords each followed track plays in each written scene, worked out once.
        self._following = []
        self._chord_sources = {}
        self._tune_sources = {}
        # How long each clip that the registers can cut short lasts, by written scene and track, found by playing, and the registers each such scene's clips read while it is still being found.
        self._decided = {}
        self._guesses = {}
        # What is asked once for the render: of each pattern, whether a step can cut a pass short, and of each written scene, whether any of its clips plays such a pattern.
        self._cutting = {}
        self._settled_by_playing = {}
        # The set's data the song was copied from, where its threads were kept at each written scene's start, and how many
        # written scenes the render took from an earlier one.
        self._data = data
        self._checkpoints = None if data is None else []
        self._reused = 0
        self._kept_clips = set()
        # The render clips are kept from while this one plays, in a song whose registers a kept clip reads, and None after.
        self._earlier = None
        # The passes the render has played that a key decides (playback/pass_memory.py), handed on from the render before.
        self._passes = PassMemory()

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

    def render(self, *, after=None):
        """Return a ClipGrid with every scene's finished clips, or raise SongFileError.

        after, an earlier render of the same song from the same seed, made with data, gives this render every written scene
        before the first an edit since can change, its clips finished already, so that only the scenes from there are played.
        """
        grid = ClipGrid(tempo=_whole_if_possible(float(self._song.get_tempo())), time_signature=self._song.get_time_signature())
        tracks = self._add_tracks(grid)
        if after is not None:
            self._passes = PassMemory(earlier=after.get_passes())
        self._take_over(after)
        try:
            for place, scene in enumerate(self._scenes):
                self._render_scene(grid=grid, tracks=tracks, scene=scene, place=place)
        finally:
            # A render keeps no earlier render alive, so that a run of edits holds only the last.
            self._earlier = None
        return grid

    def get_passes(self):
        """Return the PassMemory of the passes the render has played that a key decides."""
        return self._passes

    def _render_scene(self, *, grid, tracks, scene, place):
        """Add a written-out scene's row to the grid with its finished clips, played or kept."""
        if place >= self._reused:
            if self._checkpoints is not None:
                self._checkpoints.append(SceneCheckpoint(self._register_chooser.getstate(), self._drifts.snapshot()))
            if self._earlier is not None:
                self._hold_kept_clips_to_registers(scene)
        tempo = None if scene.get_tempo() is None else float(scene.get_tempo())
        grid_scene = grid.add_row(ClipRow(name=scene.get_name(), tempo=tempo))
        for name in self._song.get_track_names():
            clip = self._finished_clip(scene=scene, track=name, tempo=tempo)
            if clip is not None:
                grid.set_clip(row=grid_scene, column=tracks[name], clip=clip)
        tempos = self.tempos_of(scene)
        if tempos is not None:
            grid_scene.set_tempo(tempos[0].tempo)
            grid_scene.set_tempo_changes(tempos[1:])

    def _hold_kept_clips_to_registers(self, scene):
        """Let go of the clips kept for a written scene, and of their tracks' kept clips after it, where the scene's registers
        come out other than they did in the earlier render, since a finished clip reads them and its generators carry on down
        its track; the clips counted for the registers stay, since counting reads no register."""
        number = scene.get_number()
        kept = {track for track in scene.get_track_names() if (number, track) in self._kept_clips}
        earlier = self._earlier._timelines.get(number)
        if not kept or (earlier is not None and self.get_timeline(scene).reads_as(earlier)):
            return
        for key in [key for key in self._kept_clips if key[0] >= number and key[1] in kept]:
            self._kept_clips.discard(key)
            del self._clips[key]
            self._chord_counts.pop(key, None)
        self._end_states = {key: state for key, state in self._end_states.items() if not _finished_from(key=key, number=number, tracks=kept)}

    def _finished_clip(self, *, scene, track, tempo):
        """Return a track's clip in a written-out scene with its groove, strums, nudges, handed notes and keyswitch lead, or None
        when it plays nothing there; a clip taken from an earlier render has them already."""
        clip = self.get_clip(scene=scene, track=track)
        if clip is None or self.is_clip_kept(scene=scene, track=track):
            return clip
        tempo = self._song.get_tempo() if tempo is None else tempo
        # The groove goes on last, so that generators, grabs and lengths never see it.
        clip.set_groove(self._song.groove_at(scene=scene, track=track))
        clip.set_strum(self.strum_plan(scene=scene, track=track, tempo=tempo))
        self._chord_counts[(scene.get_number(), track)] = _chords_in(clip)
        clip.set_nudge(self.nudge_plan(scene=scene, track=track))
        clip.set_handed(self.handed_notes(scene=scene, track=track))
        if clip.get_keyswitches():
            clip.set_keyswitch_lead(self.keyswitch_lead(track=track, tempo=tempo))
        return clip

    def take_of(self, *, scene, track):
        """Return which take a written-out scene's clip on a track plays, 0 unless the render was given another."""
        return self._takes.get((self._song_places[id(scene.get_scene())], track), FIRST_TAKE)

    def taken_seed(self, *, seed, scene, track):
        """Return a whole-number seed made from a clip's place moved on by the clip's take, the same seed for take 0."""
        return seed + self.take_of(scene=scene, track=track) * SEED_TAKE_FACTOR

    def get_reused_scene_count(self):
        """Return how many written scenes, from the first, the render took from an earlier render rather than playing them."""
        return self._reused

    def _take_over(self, after):
        """Take from an earlier render what an edit since cannot change: every written scene before the first that can change,
        with the random streams as they stood there, so that the render goes on as if it had played every scene before; and,
        where each track's clips play apart from the others', every later clip of a track the edit does not reach."""
        if not self._can_take_from(after):
            return
        name = _song_name_of(self._song)
        first = min(first_changed_scene(before=after._data, after=self._data, song_name=name, scenes=self._song.get_scenes()), self._first_retaken(after))
        count = min(sum(scene.get_repeat() for scene in self._song.get_scenes()[:first]), len(after._checkpoints))
        self._take_scenes(after=after, count=count)
        if self._clips_stand_apart():
            changed = changed_clips(before=after._data, after=self._data, song_name=name, scenes=self._song.get_scenes())
            if changed is not None:
                changed = self._with_retaken(changed=changed, after=after)
                self._take_clips(after=after, changed=changed)

    def _retaken(self, after):
        """Return the (scene's place in the song, track) of every clip whose take differs from an earlier render's."""
        return {key for key in set(self._takes) | set(after._takes) if self._takes.get(key, FIRST_TAKE) != after._takes.get(key, FIRST_TAKE)}

    def _first_retaken(self, after):
        """Return the place in the song of the first scene a clip of which has another take than in an earlier render, or the
        number of scenes when none has."""
        return min((place for place, _track in self._retaken(after)), default=len(self._song.get_scenes()))

    def _with_retaken(self, *, changed, after):
        """Return each scene's changed tracks with the tracks whose take differs from an earlier render's added."""
        retaken = self._retaken(after)
        return [here if here is None else here | _tracks_retaken_in(place=index, retaken=retaken) for index, here in enumerate(changed)]

    def _can_take_from(self, after):
        """Return whether this render can take anything from an earlier one: both made with data from the same seed, the song's
        flags alike, every scene lasting as long in both, since a generator's run and a drift's clock reach across scenes by
        their lengths, and no scene played to find how long it lasts, as one is where a register can cut a clip short."""
        if after is None or after._checkpoints is None or self._checkpoints is None or self._seed is None or after._seed != self._seed:
            return False
        if after._looping_scenes_go_round != self._looping_scenes_go_round or after._song_flags() != self._song_flags():
            return False
        try:
            return not (after._settles_any() or self._settles_any()) and after._every_length() == self._every_length()
        except SongFileError:
            return False

    def _take_scenes(self, *, after, count):
        """Take everything an earlier render worked out about its first count written scenes, and its random streams as they
        stood as the next one started."""
        self._reused = count
        self._checkpoints = after._checkpoints[:count]
        self._clips = _through_scene(entries=after._clips, count=count, number_of=_first_part)
        self._counted = _through_scene(entries=after._counted, count=count, number_of=_first_part)
        self._decided = _through_scene(entries=after._decided, count=count, number_of=_first_part)
        self._hocket_turns = _through_scene(entries=after._hocket_turns, count=count, number_of=_first_part)
        self._source_turns = _through_scene(entries=after._source_turns, count=count, number_of=_first_part)
        self._chord_sources = _through_scene(entries=after._chord_sources, count=count, number_of=_first_part)
        self._tune_sources = _through_scene(entries=after._tune_sources, count=count, number_of=_first_part)
        self._chord_counts = _through_scene(entries=after._chord_counts, count=count, number_of=_first_part)
        self._end_states = _through_scene(entries=after._end_states, count=count, number_of=_second_part)
        self._lengths = _through_scene(entries=after._lengths, count=count, number_of=_whole_key)
        self._timelines = _through_scene(entries=after._timelines, count=count, number_of=_whole_key)
        self._starts = _through_scene(entries=after._starts, count=count, number_of=_whole_key)
        if count < len(after._checkpoints):
            checkpoint = after._checkpoints[count]
            self._register_chooser.setstate(checkpoint.register_state)
            self._drifts.restore(checkpoint.drifts)

    def _take_clips(self, *, after, changed):
        """Take from an earlier render every clip after the scenes taken whole that plays as it did, with the states its
        generators left it in and its count of chords, which the same track's later clips carry on from."""
        for key in self._unchanged_clips(changed):
            if key in after._clips:
                self._kept_clips.add(key)
                self._clips[key] = after._clips[key]
                if key in after._chord_counts:
                    self._chord_counts[key] = after._chord_counts[key]
                if key in after._counted:
                    self._counted[key] = after._counted[key]
        if self._changes_registers or self._song.uses_draws():
            # A kept clip read the scene's registers, which the render holds it to scene by scene (_hold_kept_clips_to_registers).
            self._earlier = after
        for key, state in after._end_states.items():
            if (key[1], key[2]) in self._kept_clips:
                self._end_states[key] = state

    def _unchanged_clips(self, changed):
        """Return (written scene number, track) for every clip after the scenes taken whole that plays as before: each track's
        clips before its first that the edit reaches, since what a generator carries on from goes down a track from clip to clip,
        and a track that plays from a reached track's notes is reached too (_reach_through)."""
        song_places = {id(scene): place for place, scene in enumerate(self._song.get_scenes())}
        every_track = self._song.get_track_names()
        reached = set()
        unchanged = []
        for written in self._scenes[self._reused:]:
            here = changed[song_places[id(written.get_scene())]]
            reached.update(every_track if here is None else here)
            self._reach_through(scene=written, reached=reached)
            unchanged += [(written.get_number(), track) for track in written.get_track_names() if track not in reached]
        return unchanged

    def _reach_through(self, *, scene, reached):
        """Add to the reached tracks every track of a written scene whose clip plays from a reached track's notes, by a grab or
        by chords or a tune it follows, and through those, the tracks that play from theirs; where a hocket deals notes out
        among tracks, every track of the scene once any is reached."""
        names = scene.get_track_names()
        if not reached.intersection(names):
            return
        if self._deals_out(scene):
            reached.update(names)
            return
        grown = True
        while grown:
            followed = {track: self._tracks_followed(scene=scene, track=track) for track in names if track not in reached}
            grown = [track for track, others in followed.items() if reached.intersection(others)]
            reached.update(grown)

    def _deals_out(self, scene):
        """Return whether a clip of a written scene runs a hocket, which deals a track's notes out among the clips naming it."""
        return any(step.kind == GeneratorKind.HOCKET for track in scene.get_track_names() for step in self._chain_steps(scene=scene, track=track))

    def _tracks_followed(self, *, scene, track):
        """Return the tracks whose notes a track's clip in a written scene plays from: the one it grabs from, and those whose chords or tune its generators follow."""
        followed = {scene.get_clip_slot(track).get_grab_track()}
        for step in self._chain_steps(scene=scene, track=track):
            if step.kind in FOLLOWING_KINDS:
                settings = self._song.get_generator_settings(kind=step.kind, name=step.name)
                followed.update(name for section, name in settings.named_items() if section == Section.TRACKS)
        return followed

    def _chain_steps(self, *, scene, track):
        """Return every step of every chain a track's clip in a written scene runs."""
        return [step for chain in self.chains_of(scene=scene, track=track) for step in self._song.chain_run(chain).get_steps()]

    def _clips_stand_apart(self):
        """Return whether each track's clips play apart from the other tracks' but where a scene joins them, or where the
        registers they read come out otherwise (_hold_kept_clips_to_registers): no drift draws random numbers in the order the
        clips first ask for its triggers."""
        drifts = self._song.get_setlist().get_generator_names(GeneratorKind.DRIFT)
        return not any(self._drifts.draws_in_order(name) for name in drifts)

    def kept_tracks(self, scenes):
        """Return the tracks whose clips were taken from an earlier render in every written-out scene given."""
        return {track for track in self._song.get_track_names() if self._kept_in_all(scenes=scenes, track=track)}

    def _kept_in_all(self, *, scenes, track):
        return all(self.is_clip_kept(scene=scene, track=track) for scene in scenes)

    def get_kept_clip_count(self):
        """Return how many clips after the scenes taken whole the render took from an earlier one, track by track."""
        return len(self._kept_clips)

    def has_taken_anything(self):
        """Return whether the render took any clip from an earlier one."""
        return bool(self._reused or self._kept_clips)

    def is_clip_kept(self, *, scene, track):
        """Return whether a track's clip in a written-out scene was taken from an earlier render, in a scene taken whole or alone."""
        return scene.get_number() <= self._reused or (scene.get_number(), track) in self._kept_clips

    def _song_flags(self):
        """Return what the song as a whole says about how every scene renders: whether anything changes a register, whether a draw holds a value, and whether a scene changes registers."""
        return (self._changes_registers, self._song.uses_draws(), self._song.scenes_change_registers())

    def _settles_any(self):
        """Return whether any written scene is played to find how long it lasts."""
        return any(self._is_settled_by_playing(scene) for scene in self._scenes)

    def _every_length(self):
        """Return how long every written scene lasts, in order."""
        return [self.get_scene_length(scene) for scene in self._scenes]

    def tempos_of(self, scene):
        """Return a written-out scene's tempos where its scene ramps its tempo, (time in whole notes from its start, tempo) with the first at its start, or None for a scene with no ramp, which keeps one tempo.

        A scene's ramps count bars across its whole play, every repeat together, so each repeat
        takes the part of the ramps that falls inside it.
        """
        played = scene.get_scene()
        if not played.has_tempo_ramp():
            return None
        if id(played) not in self._ramped:
            rows = [written for written in self._scenes if written.get_scene() is played]
            lengths = [self.get_scene_length(written) for written in rows]
            signature = self._song.get_time_signature()
            base = self._song.get_tempo() if played.get_tempo() is None else played.get_tempo()
            tempos = ramped_tempos(
                base=base, ramp_in=played.get_tempo_ramp(RampWay.IN), ramp_out=played.get_tempo_ramp(RampWay.OUT),
                length=sum(lengths, START), bar=signature.bar_length(), step=self._song.get_step_size(),
            )
            start = START
            for written, length in zip(rows, lengths):
                self._ramped[(id(played), written.get_number())] = tempos_within(tempos=tempos, start=start, end=start + length)
                start += length
            self._ramped[id(played)] = True
        return self._ramped[(id(played), scene.get_number())]

    def keyswitch_lead(self, *, track, tempo):
        """Return how much earlier than its note a track's instrument wants each keyswitch, in whole notes at a tempo, or None for at the same moment."""
        instrument = self.instrument_of(self._song.get_track(track))
        if instrument is None or not instrument.get_keyswitch_lead():
            return None
        milliseconds = instrument.get_keyswitch_lead()
        lead = Fraction(milliseconds) * Fraction(tempo).limit_denominator(TEMPO_DENOMINATOR) / MILLISECONDS_PER_WHOLE_NOTE_AT_ONE_BEAT_A_MINUTE
        return Rational(lead.numerator, lead.denominator)

    def strum_plan(self, *, scene, track, tempo):
        """Return how a clip strums its chords at its scene's tempo, or None: the last Strum generator its chains name, else the clip's own strum, else its track's."""
        strum = None
        restart = Restart.EVERY_CLIP
        for chain in self.chains_of(scene=scene, track=track):
            for step in self._song.chain_run(chain).get_steps():
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
            upstroke_count=strum.upstroke_count, beat=self._song.get_time_signature().beat_length(), seed=self.taken_seed(seed=self._strum_seed + scene.get_number() * SEED_SCENE_FACTOR + place * SEED_TRACK_FACTOR, scene=scene, track=track),
            offset=self.run_offset(scene=scene, restart=restart), chords_before=self._chords_before(scene=scene, track=track, restart=restart),
        )

    def nudge_plan(self, *, scene, track):
        """Return how a clip's notes are rushed and dragged, from every Rush and Drag its chains name, or None when they name neither."""
        pattern_step = self._song.get_pattern_step_size(self._song.get_pattern(scene.get_clip_slot(track).get_pattern_name()))
        bar = self._song.get_time_signature().bar_length()
        rows = []
        for chain in self.chains_of(scene=scene, track=track):
            for step in self._song.chain_run(chain).get_steps():
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
        names = [step.name for chain in self.chains_of(scene=scene, track=track) for step in self._song.chain_run(chain).get_steps() if step.kind == GeneratorKind.HOCKET]
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
                tempos = self.tempos_of(scene)
                # A scene that ramps its tempo is timed beat by beat, as its exports are.
                clock = None if tempos is None else RowClock(tempos)
                for track in scene.get_track_names():
                    clips[track] = _seconds_of(length=self.get_clip_length(scene=scene, track=track), clock=clock, whole=whole_notes_to_seconds)
                # A scene with a problem has no length, so it's set only once the checks pass.
                seconds = _seconds_of(length=length, clock=clock, whole=whole_notes_to_seconds)
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
            raise SongFileError(errors.ERR_CIRCULAR_GRAB.format(scene=scene.describe(), loop=GRAB_ARROW.join(circle)))

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
        if key not in self._counted and self._cuts_passes(scene=scene, track=track):
            return self._decided_clip(scene=scene, track=track)
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
        # The registers that reverse and are counting the other way, which a reset puts back to counting forward.
        turned = registers_values.NOT_TURNED
        # Where the song's draws stand, carried from scene to scene, or None in a song whose draws hold no value.
        draws = DrawPlay(self._draws) if self._song.uses_draws() else None
        for written in self._scenes[:self._scenes.index(scene) + 1]:
            number = written.get_number()
            if number not in self._timelines:
                self._draw_afresh_for_a_take(written)
                resets = self._resets_of(written)
                start = with_resets(values=values, registers=self._registers, names=resets)
                if turned:
                    turned = turned.difference(resets)
                if draws is not None:
                    draws = self._with_draw_resets(draws=draws, written=written)
                    start = {**start, **draws.values()}
                try:
                    self._timelines[number] = self._timeline_of(scene=written, start=start, turned=turned, draws=draws)
                except SongFileError:
                    if written is scene:
                        raise
                    continue
            values = self._timelines[number].end_values()
            turned = self._timelines[number].get_end_turned()
            draws = self._timelines[number].get_end_draws()
        return self._timelines[scene.get_number()]

    def _timeline_of(self, *, scene, start, turned, draws):
        """Return a written-out scene's register values from where they start: found by playing the scene where a register can cut
        a clip of it short, and from the changes its clips make otherwise."""
        if self._is_settled_by_playing(scene):
            return self._decide(scene=scene, start=start, turned=turned, draws=draws)
        return RegisterTimeline(registers=self._registers, start=start, changes=self._scene_changes(scene), chooser=self._register_chooser, turned=turned, draws=draws)

    def _draw_afresh_for_a_take(self, written):
        """As a retaken scene first starts, before its repeats, start the song's random draws afresh from the seed, the scene and its
        take, so that a draw that takes any value, or each value once, draws anew on every take, as a looping scene's laps and a
        scene launched again do, rather than as the take before drew; its repeats then draw on from one another as ever."""
        place = self._song_places[id(written.get_scene())]
        take = max((self._takes.get((place, track), FIRST_TAKE) for track in written.get_track_names()), default=FIRST_TAKE)
        if take == FIRST_TAKE or self._seed is None:
            return
        before = self._scenes.index(written) - 1
        if before >= 0 and self._scenes[before].get_scene() is written.get_scene():
            return
        self._register_chooser.seed(DRAWS_TAKE_SEED.format(seed=self._seed, scene=place, take=take))

    def _cutting_of(self, name):
        """Return whether a step of a pattern can cut a pass short, and whether one can stop its clip, asked of the pattern once for the render."""
        if name not in self._cutting:
            pattern = self._song.get_pattern(name)
            self._cutting[name] = (pattern.cuts_passes_short(), pattern.has_statements(StepStatement.STOP))
        return self._cutting[name]

    def _cuts_passes(self, *, scene, track):
        """Return whether a step of the pattern a track's clip plays in a scene can stop the clip or start the pattern over, so that the clip is played with the registers to find what it does."""
        return any(self._cutting_of(name)[CUTS] for name in scene.get_clip_slot(track).get_pattern_names())

    def fills_its_scene(self, *, scene, track):
        """Return whether a track's clip in a scene loops for as long as the scene lasts: a looping clip that no step of its pattern can stop."""
        clip_slot = scene.get_clip_slot(track)
        return clip_slot.loops() and not any(self._cutting_of(name)[STOPS] for name in clip_slot.get_pattern_names())

    def _is_settled_by_playing(self, scene):
        """Return whether any clip of a scene can be cut short by the registers, so that the scene's length and its registers are found together, by playing. Asked once for each play of a scene."""
        number = scene.get_number()
        if number not in self._settled_by_playing:
            self._settled_by_playing[number] = any(self._cuts_passes(scene=scene, track=track) for track in scene.get_track_names())
        return self._settled_by_playing[number]

    def _decide(self, *, scene, start, turned, draws=None):
        """Return the register values through a scene in which a step's statement can stop a clip or start a pattern over, finding how long its clips and the scene last.

        What such a clip changes in the registers depends on the registers, since a step it
        never reaches changes nothing, so its changes cannot be counted before anything reads
        them. Each such clip is first played as if no other track changed a register
        (RegisterSolo), which is right already when one track does the counting. The scene's
        timeline is made from what every clip then changes, the clips are played again reading
        it (RegisterTrial), and so on until a play changes what the timeline was made from in
        no way. It always comes to that: the values at any moment depend only on the changes
        before it, so each play is right for longer than the one before.
        """
        number = scene.get_number()
        every = scene.get_track_names()
        cut = [track for track in every if self._cuts_passes(scene=scene, track=track)]
        # The clips whose own length the registers decide, and the looping ones that fill the scene whatever length it comes to.
        ending = [track for track in cut if not self.fills_its_scene(scene=scene, track=track)]
        filling = [track for track in cut if track not in ending]
        fixed = [self._played_once(scene=scene, track=track) for track in every if track not in cut and not scene.get_clip_slot(track).loops()]
        if not ending and not fixed:
            # Nothing in the scene ends: it is refused, or goes round once, as any scene whose every clip loops.
            if not self._looping_scenes_go_round:
                raise SongFileError(errors.ERR_RENDERER_EVERY_CLIP_LOOPS.format(scene=scene.describe()))
            fixed = [self._played_once(scene=scene, track=track) for track in every]
        own = scene_change(sets=scene.get_scene().get_register_sets() if scene.is_first_play() else {}, adds=scene.get_scene().get_register_adds())
        guess = random_source(GUESS_SEED)
        alone = RegisterTimeline(registers=self._registers, start=start, changes=[own] if own else [], chooser=guess, turned=turned)
        self._guesses[number] = lambda track: RegisterSolo(
            place=self._track_place(track), registers=self._registers, start=alone.end_values(), chooser=guess, turned=alone.get_end_turned(),
        )
        # Until the first play is in, the scene is taken to last as long as the clips nothing can cut.
        self._lengths[number] = max(fixed, default=NO_LENGTH)
        drawn = self._register_chooser.getstate()
        settled = None
        try:
            while True:
                plays = {track: self._tried(scene=scene, track=track) for track in ending}
                self._forget_plays_of(scene)
                for track, play in plays.items():
                    self._counted[(number, track)] = play
                    self._decided[(number, track)] = play[0].total_length()
                self._lengths[number] = max([*fixed, *[self._decided[(number, track)] for track in ending]], default=NO_LENGTH)
                for track in filling:
                    self._counted[(number, track)] = self._tried(scene=scene, track=track)
                changes = self._scene_changes(scene)
                found = (changes, [self._decided[(number, track)] for track in ending])
                # Every round draws a register's random values from the same place, so that the same changes always make the same timeline.
                self._register_chooser.setstate(drawn)
                timeline = RegisterTimeline(registers=self._registers, start=start, changes=changes, chooser=self._register_chooser, turned=turned, draws=draws)
                if found == settled:
                    return timeline
                settled = found
                self._guesses[number] = lambda track, timeline=timeline: RegisterTrial(place=self._track_place(track), timeline=timeline)
        finally:
            del self._guesses[number]

    def _tried(self, *, scene, track):
        """Return a clip the registers can cut short, played to count its changes against the scene's registers as they are guessed so far, and those changes."""
        registers = self._guesses[scene.get_number()](track)
        clip = ClipSlotPlayer(renderer=self, song=self._song, scene=scene, track_name=track).play(grabbing=False, registers=registers)
        return clip, registers.get_changes()

    def _decided_clip(self, *, scene, track):
        """Return a clip the registers can cut short, played to count its changes, and those changes: as its scene settled them, or as guessed so far when another clip asks while the scene is still being settled."""
        number = scene.get_number()
        if number in self._guesses:
            return self._tried(scene=scene, track=track)
        self.get_timeline(scene)
        return self._counted[(number, track)]

    def _forget_plays_of(self, scene):
        """Forget what was worked out from a scene's clips while how long they last was still a guess: the counted clips, and the chords and tunes other clips followed in them."""
        number = scene.get_number()
        for kept in (self._counted, self._chord_sources, self._tune_sources):
            for key in [key for key in kept if key[0] == number]:
                del kept[key]

    def _with_draw_resets(self, *, draws, written):
        """Return the draws as a written-out scene starts them: the draws it resets sent back to their start, on its first play alone."""
        names = written.get_scene().get_reset_draw_names() if written.is_first_play() else []
        if not names:
            return draws
        draws = draws.copy()
        for name in names:
            draws.reset(name)
        return draws

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
        if not self._changes_registers:
            return []
        length = self.get_scene_length(scene)
        changes = []
        # A scene sets registers only as it first starts, and adds to them on every play, its repeats too.
        own = scene_change(sets=scene.get_scene().get_register_sets() if scene.is_first_play() else {}, adds=scene.get_scene().get_register_adds())
        if own is not None:
            changes.append(own)
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
        if self._is_settled_by_playing(scene):
            # The registers can cut one of its clips short, so its length is found by playing it, with its registers.
            self.get_timeline(scene)
            return self._lengths[number]
        if scene.every_clip_loops():
            if not self._looping_scenes_go_round:
                raise SongFileError(errors.ERR_RENDERER_EVERY_CLIP_LOOPS.format(scene=scene.describe()))
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
        if self._cuts_passes(scene=scene, track=track) and not self.fills_its_scene(scene=scene, track=track):
            # A clip the registers can cut short lasts as long as it played, which its scene found.
            self.get_scene_length(scene)
            return self._decided[(scene.get_number(), track)]
        if clip_slot.loops():
            return self.get_scene_length(scene)
        return self._played_once(scene=scene, track=track)

    def _played_once(self, *, scene, track):
        """Return how long a clip lasts played once: its pattern repeat times, whether or not it loops."""
        clip_slot = scene.get_clip_slot(track)
        return clip_slot.get_repeat() * sum(self._song.get_pattern_length(self._song.get_pattern(name)) for name in clip_slot.get_pattern_names())

    def get_grab_source(self, *, scene, track):
        """Return the notes the track that a track's clip slot grabs from plays in a scene, or None if it plays nothing there."""
        other = scene.get_clip_slot(track).get_grab_track()
        if scene.get_clip_slot(other) is None:
            return None
        waiting = [*self._grabbing, track]
        if other in waiting:
            raise SongFileError(errors.ERR_CIRCULAR_GRAB.format(scene=scene.describe(), loop=_grab_loop(waiting=waiting, track=other)))
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

    def chords_followed(self, *, scene, track, source, counting):
        """Return the chords a track followed plays in a written-out scene, after its own chains, or None when it plays nothing there, is no track of the song or is the track that follows.

        In the pass that counts register changes the chords are read from that pass's clip, played
        without grabs or register values, since no finished clip can be had yet.
        """
        if source is None or source == track or source not in self._song.get_track_names() or scene.get_clip_slot(source) is None:
            return None
        key = (scene.get_number(), source, counting)
        if key not in self._chord_sources:
            waiting = [*self._following, (scene.get_number(), track)]
            if (scene.get_number(), source) in waiting:
                tracks = [name for _, name in waiting[waiting.index((scene.get_number(), source)):]]
                raise SongFileError(errors.ERR_CIRCULAR_FOLLOW.format(scene=scene.describe(), loop=GRAB_ARROW.join([*tracks, source])))
            self._following.append((scene.get_number(), track))
            try:
                clip = self._counted_clip(scene=scene, track=source)[0] if counting else self.get_clip(scene=scene, track=source)
            finally:
                self._following.pop()
            self._chord_sources[key] = ChordSource(clip)
        return self._chord_sources[key]

    def _plays_drums(self, *, scene, track):
        """Return whether a track's clip in a written-out scene plays a drum pattern."""
        return self._song.get_pattern(scene.get_clip_slot(track).get_pattern_name()).is_drum()

    def tune_heard(self, *, scene, track, source, counting):
        """Return when the tune sounds on the track a musician reads it from, in a written-out scene, after that track's own chains, or None when the track plays nothing there, is no track of the song or is the musician's own.

        The track's finished clip is found as a followed track's chords are, so tracks that read each other in a circle are refused the same way.
        """
        if source is None or source == track or source not in self._song.get_track_names() or scene.get_clip_slot(source) is None:
            return None
        key = (scene.get_number(), source, counting)
        if key not in self._tune_sources:
            waiting = [*self._following, (scene.get_number(), track)]
            if (scene.get_number(), source) in waiting:
                tracks = [name for _, name in waiting[waiting.index((scene.get_number(), source)):]]
                raise SongFileError(errors.ERR_CIRCULAR_FOLLOW.format(scene=scene.describe(), loop=GRAB_ARROW.join([*tracks, source])))
            self._following.append((scene.get_number(), track))
            try:
                clip = self._counted_clip(scene=scene, track=source)[0] if counting else self.get_clip(scene=scene, track=source)
            finally:
                self._following.pop()
            self._tune_sources[key] = TuneSource(clip)
        return self._tune_sources[key]

    def make_generator(self, *, step, scene, track, chain, index, key=None, counting=False):
        """Return the generator for one step of a chain, as a clip slot on a track in a scene uses it.

        An arp with no seed of its own gets one from the render's, which differs for every scene,
        track and place in the chain, so that a seeded render is always the same. With no seed
        at all, the arp draws its own random numbers.
        """
        settings = self._song.get_generator_settings(kind=step.kind, name=step.name)
        if step.kind == GeneratorKind.FOLLOW_CHORDS:
            return FollowChords(chords=self.chords_followed(scene=scene, track=track, source=settings.get_chords_from(), counting=counting))
        if step.kind == GeneratorKind.PHRASING:
            return settings.generator_for(where=errors.ERR_WHERE_CHAIN.format(chain=chain, kind=step.kind), bar=self._song.get_time_signature().bar_length())
        place = self._song.get_track_names().index(track)
        seed = None if self._seed is None else self.taken_seed(seed=self._seed * SEED_SONG_FACTOR + scene.get_number() * SEED_SCENE_FACTOR + place * SEED_TRACK_FACTOR + index, scene=scene, track=track)
        if step.kind == GeneratorKind.MUSICIAN:
            signature = self._song.get_time_signature()
            surroundings = Surroundings(
                section=scene.get_scene().get_section(),
                # A drum pattern's notes are drums, which no chord moves, whoever is said to play them.
                chords=None if self._plays_drums(scene=scene, track=track) else self.chords_followed(scene=scene, track=track, source=settings.get_chords_from(), counting=counting),
                tune=self.tune_heard(scene=scene, track=track, source=settings.get_tune_from(), counting=counting),
            )
            return settings.generator_for(where=errors.ERR_WHERE_CHAIN.format(chain=chain, kind=step.kind), bar=signature.bar_length(), beat=signature.beat_length(), surroundings=surroundings, seed=seed)
        pattern_step = self._song.get_pattern_step_size(self._song.get_pattern(scene.get_clip_slot(track).get_pattern_name()))
        continuation = None if key is None else self.continuation(settings=settings, scene=scene, track=track, key=key, counting=counting)
        return settings.make_generator(
            where=errors.ERR_WHERE_CHAIN.format(chain=chain, kind=step.kind), default_seed=seed, default_step=pattern_step, bar=self._song.get_time_signature().bar_length(),
            continuation=continuation, tempo=self._song.get_tempo() if scene.get_tempo() is None else scene.get_tempo(),
        )


def _through_scene(*, entries, count, number_of):
    """Return the entries of what a render worked out whose written scene, which number_of finds in a key, is among the first count."""
    return {key: value for key, value in entries.items() if number_of(key) <= count}


def _finished_from(*, key, number, tracks):
    """Return whether a generator's end state, by its key (counting, written scene number, track, the generator's place), was
    left by a finished clip of one of the tracks from a written scene on."""
    counting, scene, track, _place = key
    return not counting and scene >= number and track in tracks


def _first_part(key):
    return key[0]


def _second_part(key):
    return key[1]


def _whole_key(key):
    return key


def _tracks_retaken_in(*, place, retaken):
    """Return the tracks of a scene, by its place in the song, whose clips have another take."""
    return {track for scene, track in retaken if scene == place}


def _song_name_of(song):
    """Return the name a song goes by in its set."""
    setlist = song.get_setlist()
    return next(name for name in setlist.get_song_names() if setlist.get_song(name) is song)


def _seconds_of(*, length, clock, whole):
    """Return how long a length in whole notes lasts from a scene's start: by the scene's clock where its tempo ramps, else at the one tempo whose whole note lasts whole seconds."""
    if clock is None:
        return length * whole
    return Rational(clock.seconds_at(length))


def _whole_if_possible(number):
    """Return a number as a whole number if it is one, like 120 rather than 120.0."""
    return int(number) if number.is_integer() else number


def _patterns_played(clip_slot):
    """Return the names of the patterns a clip slot plays: its own, and the one it morphs to if it morphs."""
    names = clip_slot.get_pattern_names()
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
    return max(min(value, midi.MAX_CC_VALUE), midi.MIN_CC_VALUE)


def _before(*, changes, end):
    """Return the register changes made before a time, the end of their scene."""
    return [change for change in changes if change.time < end]


def _grab_loop(*, waiting, track):
    """Return the tracks that grab from each other in a circle, from where the circle starts, like a → b → a."""
    return GRAB_ARROW.join([*waiting[waiting.index(track):], track])


def _chords_in(clip):
    """Return how many chords a finished clip plays, a held one too, which a strum's down up counts."""
    return sum(1 for sound in clip.get_sounds() if sound[sound_values.KIND] == sound_values.CHORD or (sound[sound_values.KIND] == sound_values.HELD and sound[sound_values.HELD_SOUND][sound_values.KIND] == sound_values.CHORD))
