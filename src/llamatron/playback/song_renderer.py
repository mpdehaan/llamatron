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

"""Rendering a composed Song into a ClipGrid of finished clips, for the renderers to write."""

from typing import NamedTuple

from llamatron.rational import Rational
from llamatron.composition.file_format import REGISTER_NAMES
from llamatron.composition.song_file_error import SongFileError
from llamatron.playback.cell_player import CellPlayer
from llamatron.playback.pattern_player import check_pattern_has_a_scale
from llamatron.playback.grab_source import GrabSource
from llamatron.playback.registers import RegisterReader, RegisterRecorder, RegisterTimeline, starting_values, with_resets
from llamatron.playback.written_scene import WrittenScene
from llamatron.clip_grid import ClipGrid, Scene, Track

MSG_EVERY_CLIP_LOOPS = '{scene}: every clip is set to loop, so the scene would never end. Turn off loop on at least one clip.'
MSG_CIRCULAR_GRAB = '{scene}: circular grab: {loop}. Remove the grab track from one of these clips.'
# How a circular grab's tracks are joined in its message, like a → b → a.
GRAB_ARROW = ' → '
# How messages name the chain a generator is used in.
WHERE_CHAIN = 'chain {chain!r}, {kind}'
# An arp with no seed of its own gets one made from the song's seed, its scene, its track and its
# place in the chain, multiplied by these so that each comes out different.
SEED_SONG_FACTOR = 1_000_003
SEED_SCENE_FACTOR = 1_009
SEED_TRACK_FACTOR = 31
# Turning a length in whole notes into seconds, at a tempo in quarter notes a minute.
SECONDS_PER_MINUTE = 60
QUARTER_NOTES_PER_WHOLE_NOTE = 4
# How long a scene with nothing in it lasts.
NO_LENGTH = Rational(0)


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
    get_scene_length work that out from the patterns and cells without playing anything, and the
    estimate the tracker shows after every change uses nothing else.

    In a song where a step adds to a register, each clip is played twice: first counted, without
    grabs or register values, to record what it adds to the registers, and then finished, reading
    the registers from the scene's RegisterTimeline. See registers.py. In a song where nothing
    adds to a register, the registers keep their defaults throughout, so the counting pass would
    record nothing, and only the finished pass is played.
    """

    __slots__ = ('_song', '_scenes', '_registers', '_clips', '_counted', '_lengths', '_timelines', '_grabbing')

    def __init__(self, song):
        self._song = song
        self._scenes = WrittenScene.write_out(song)
        self._registers = {name: song.get_register(name) for name in REGISTER_NAMES}
        self._clips = {}
        # Clips played only to record their register changes, with those changes.
        self._counted = {}
        self._lengths = {}
        self._timelines = {}
        # The tracks whose clips are waiting on a grab, to catch clips that grab in a circle.
        self._grabbing = []

    def render(self):
        """Return a ClipGrid with every scene's finished clips, or raise SongFileError."""
        grid = ClipGrid(tempo=_whole_if_possible(float(self._song.get_tempo())))
        tracks = self._add_tracks(grid)
        for scene in self._scenes:
            tempo = None if scene.get_tempo() is None else float(scene.get_tempo())
            grid_scene = grid.add_scene(Scene(scene.get_name(), tempo=tempo))
            for name in self._song.get_track_names():
                clip = self.get_clip(scene, name)
                if clip is not None:
                    grid.set_clip(grid_scene, tracks[name], clip)
        return grid

    def _add_tracks(self, grid):
        """Add a finished track to the grid for each of the song's tracks, and return them by name."""
        tracks = {}
        for name in self._song.get_track_names():
            tracks[name] = grid.add_track(Track(name, mute=self._song.get_track(name).is_muted()))
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
            clips, problem, seconds = {}, None, None
            try:
                length = self.get_scene_length(scene)
                self._check_plays(scene)
                for track in scene.get_track_names():
                    clips[track] = self.get_clip_length(scene, track) * whole_notes_to_seconds
                # A scene with a problem has no length, so it's set only once the checks pass.
                seconds = length * whole_notes_to_seconds
            except SongFileError as error:
                problem = str(error)
            result.append(SceneEstimate(scene.get_number(), seconds, clips, problem))
        return result

    def _check_plays(self, scene):
        """Raise the SongFileError a render of a scene would, for the problems that show without playing."""
        for track in scene.get_track_names():
            for pattern_name in _patterns_played(scene.get_cell(track)):
                check_pattern_has_a_scale(self._song, scene, pattern_name)
        circle = _grab_circle(scene)
        if circle is not None:
            raise SongFileError(MSG_CIRCULAR_GRAB.format(scene=scene.describe(), loop=GRAB_ARROW.join(circle)))

    def get_clip(self, scene, track):
        """Return the finished clip a track plays in a written-out scene, or None if it plays nothing."""
        cell = scene.get_cell(track)
        if cell is None:
            return None
        key = (scene.get_number(), track)
        if key not in self._clips:
            registers = RegisterReader(self.get_timeline(scene), self._track_place(track))
            self._clips[key] = CellPlayer(self, self._song, scene, track).play(cell.get_grab_track() is not None, registers)
        return self._clips[key]

    def _counted_clip(self, scene, track):
        """Return a track's clip in a scene played without grabs or register values, and what it adds to the registers.

        Register changes from every track have to be collected, and put in time order, before any
        finished clip can read them, which is why this pass comes first.
        """
        key = (scene.get_number(), track)
        if key not in self._counted:
            recorder = RegisterRecorder(self._track_place(track))
            clip = CellPlayer(self, self._song, scene, track).play(False, recorder)
            self._counted[key] = (clip, recorder.get_changes())
        return self._counted[key]

    def _track_place(self, track):
        """Return a track's place in the song, counted from 0, which orders register changes made at the same time."""
        return self._song.get_track_names().index(track)

    def get_timeline(self, scene):
        """Return the register values through a written-out scene.

        A scene starts with the values the scene before it ended with, or the registers' defaults
        for the first scene, and then sets the registers it resets back to their defaults. A scene
        before it that can't be played changes nothing, so that estimates can still show this one.
        """
        values = starting_values(self._registers)
        for written in self._scenes[:self._scenes.index(scene) + 1]:
            number = written.get_number()
            if number not in self._timelines:
                start = with_resets(values, self._registers, written.get_reset_names())
                try:
                    self._timelines[number] = RegisterTimeline(self._registers, start, self._scene_changes(written))
                except SongFileError:
                    if written is scene:
                        raise
                    continue
            values = self._timelines[number].end_values()
        return self._timelines[scene.get_number()]

    def _scene_changes(self, scene):
        """Return every change a scene's clips make to the registers before the scene ends."""
        if not self._song.adds_to_registers():
            return []
        length = self.get_scene_length(scene)
        changes = []
        for track in scene.get_track_names():
            changes += _before(self._counted_clip(scene, track)[1], length)
        return changes

    def get_scene_length(self, scene):
        """Return how long a scene lasts, in whole notes: its longest clip that doesn't loop, worked out without playing."""
        number = scene.get_number()
        if number in self._lengths:
            return self._lengths[number]
        if _every_clip_loops(scene):
            raise SongFileError(MSG_EVERY_CLIP_LOOPS.format(scene=scene.describe()))
        length = NO_LENGTH
        for track in scene.get_track_names():
            if not scene.get_cell(track).loops():
                length = max(length, self.get_clip_length(scene, track))
        self._lengths[number] = length
        return length

    def get_clip_length(self, scene, track):
        """Return how long a track's clip lasts in a written-out scene, in whole notes, worked out without playing.

        A looping clip lasts as long as its scene. Any other plays its pattern repeat times, and
        every pass lasts the pattern's steps times its step size whatever the steps hold: a gate
        is cut at the end of its pass, ties and glides only lengthen a note's sound, a direction
        only reorders the steps, a morph's target is looped or cut to the pass, grabs and
        registers change only pitches and velocities, and a chain's generators keep a clip's
        length. test_clip_lengths.py checks this against a real play of every example.
        """
        cell = scene.get_cell(track)
        if cell.loops():
            return self.get_scene_length(scene)
        return cell.get_repeat() * self._song.get_pattern_length(self._song.get_pattern(cell.get_pattern_name()))

    def get_grab_source(self, scene, track):
        """Return the notes the track that a track's cell grabs from plays in a scene, or None if it plays nothing there."""
        other = scene.get_cell(track).get_grab_track()
        if scene.get_cell(other) is None:
            return None
        waiting = [*self._grabbing, track]
        if other in waiting:
            raise SongFileError(MSG_CIRCULAR_GRAB.format(scene=scene.describe(), loop=_grab_loop(waiting, other)))
        self._grabbing.append(track)
        try:
            source = self.get_clip(scene, other)
        finally:
            self._grabbing.pop()
        return GrabSource(source)

    def make_generator(self, step, scene, track, chain, index):
        """Return the generator for one step of a chain, as a cell on a track in a scene uses it.

        An arp with no seed of its own gets one from the song's, which differs for every scene,
        track and place in the chain, so that a render is always the same.
        """
        settings = self._song.get_generator_settings(step.kind, step.name)
        place = self._song.get_track_names().index(track)
        seed = self._song.get_seed() * SEED_SONG_FACTOR + scene.get_number() * SEED_SCENE_FACTOR + place * SEED_TRACK_FACTOR + index
        return settings.make_generator(WHERE_CHAIN.format(chain=chain, kind=step.kind), seed)


def _whole_if_possible(number):
    """Return a number as a whole number if it is one, like 120 rather than 120.0."""
    return int(number) if number.is_integer() else number


def _patterns_played(cell):
    """Return the names of the patterns a cell plays: its own, and the one it morphs to if it morphs."""
    names = [cell.get_pattern_name()]
    if cell.get_morph_target() is not None:
        names.append(cell.get_morph_target())
    return names


def _grab_circle(scene):
    """Return the tracks whose grabs go round in a circle in a scene, like [lead, kick, lead], or None.

    A clip grabbing from a track follows that track's grab, and so on. A grab from a track with
    nothing in the scene grabs nothing, so it can't be part of a circle.
    """
    for start in scene.get_track_names():
        path = [start]
        while True:
            following = scene.get_cell(path[-1]).get_grab_track()
            if following is None or scene.get_cell(following) is None or following in path[1:]:
                break
            if following == start:
                return [*path, start]
            path.append(following)
    return None


def _every_clip_loops(scene):
    """Return whether every clip in a scene loops, which would leave the scene with no end."""
    cells = [scene.get_cell(track) for track in scene.get_track_names()]
    return bool(cells) and all(cell.loops() for cell in cells)


def _before(changes, end):
    """Return the register changes made before a time, the end of their scene."""
    return [change for change in changes if change.time < end]


def _grab_loop(waiting, track):
    """Return the tracks that grab from each other in a circle, from where the circle starts, like a → b → a."""
    return GRAB_ARROW.join([*waiting[waiting.index(track):], track])
