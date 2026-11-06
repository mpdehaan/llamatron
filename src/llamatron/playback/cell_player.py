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

"""Playing what one track plays in one scene into a finished clip."""

import random
from dataclasses import replace
from fractions import Fraction
from math import ceil

from llamatron.composition.file_format import LIVE_OCTAVE_OFFSET
from llamatron.composition.song_file_error import SongFileError
from llamatron.generators.blend import Blend
from llamatron.playback.accumulators import Accumulators
from llamatron.playback.morph_controls import morph_controls
from llamatron.playback.pattern_player import PatternPlayer
from llamatron.playback.step_order import StepOrder
from llamatron.clip_grid import Clip

# How messages name a cell: by its scene's number and its track.
WHERE_CELL = 'scene {scene}, track {track!r}'
MSG_CANT_PLAY = '{where}: {problem}'
# The seeds for a cell's random choices: which steps play, by probability, and the order of steps
# in directions that choose as they go. They come from the song's seed, the scene and the track,
# so each cell differs but a render is always the same.
PROBABILITY_SEED = '{seed}/{scene}/{track}'
DIRECTION_SEED = '{seed}/{scene}/{track}/direction'
# A morph moves from 0 percent of the way to its target on the first repeat to 100 on the last.
FULL_MORPH = 100
# A clip with nothing in it ends straight away.
NO_LENGTH = 0


class CellPlayer:
    """Plays a track's cell in a scene: its pattern, repeated or looped, morphing, then through its chain.

    It asks the SongRenderer it belongs to for the scene's length, which a looping clip fills, and
    for the notes of a track it grabs from.
    """

    __slots__ = ('_renderer', '_song', '_scene', '_track_name', '_cell', '_track')

    def __init__(self, renderer, song, scene, track_name):
        self._renderer = renderer
        self._song = song
        self._scene = scene
        self._track_name = track_name
        self._cell = scene.get_cell(track_name)
        self._track = song.get_track(track_name)

    def play(self, grabbing):
        """Return the finished clip, with its grab steps grabbing only if grabbing is true."""
        cell, scene = self._cell, self._scene
        where = WHERE_CELL.format(scene=scene.get_number(), track=self._track_name)
        scale = self._clip_scale()
        player = PatternPlayer(self._song, scene, scale, self._track)
        grab = self._renderer.get_grab_source(scene, self._track_name) if grabbing else None
        loop = cell.loops()
        fill = self._renderer.get_scene_length(scene) if loop else None
        try:
            clip = self._play_passes(player, grab, scale, where, fill)
            controls = clip.controls
            clip = self._through_chain(clip)
            end = fill if loop else clip.total_length()
            notes = clip.section(NO_LENGTH, end).notes if end > NO_LENGTH else []
            controls = self._sent_controls(controls, end)
            return Clip(name=scene.get_name(), notes=notes, scale=scale, loop=loop, controls=controls)
        except (ValueError, TypeError) as error:
            raise SongFileError(MSG_CANT_PLAY.format(where=where, problem=error)) from error

    def _clip_scale(self):
        """Return the scale the clip plays in, rooted at its octave, or None if its scene has no scale."""
        scale_name = self._scene.get_scale_name()
        if scale_name is None:
            return None
        return self._song.get_named_scale(scale_name).scale_at(self._clip_octave())

    def _through_chain(self, clip):
        """Return the clip after each generator of the cell's chain, in order, if it has a chain."""
        chain = self._cell.get_chain_name()
        if clip.total_length() == NO_LENGTH or chain is None:
            return clip
        for index, step in enumerate(self._song.get_chain(chain).get_steps()):
            clip = self._renderer.make_generator(step, self._scene, self._track_name, chain, index).generate(clip)
        return clip

    def _sent_controls(self, controls, end):
        """Return the CC values the track sends before the clip ends, with each lane turned into its CC number.

        Until here a control's number is its lane. A lane the track has no CC number for sends nothing.
        """
        numbers = self._track.get_cc_numbers()
        return [
            replace(item, number=numbers[item.number]) for item in controls
            if item.time < end and numbers[item.number] is not None
        ]

    def _clip_octave(self):
        """Return the octave for the root of this clip's scale.

        It's the octave of the first note the clip plays, in this project's numbering.
        """
        octave = self._song.get_pattern(self._cell.get_pattern_name()).get_first_octave()
        return (self._song.get_default_octave() if octave is None else octave) + LIVE_OCTAVE_OFFSET

    def _play_passes(self, player, grab, scale, where, fill):
        """Return what the clip plays before any chains: its repeats, or enough passes to fill a length."""
        seed, number = self._song.get_seed(), self._scene.get_number()
        rolls = random.Random(PROBABILITY_SEED.format(seed=seed, scene=number, track=self._track_name))
        order = StepOrder(random.Random(DIRECTION_SEED.format(seed=seed, scene=number, track=self._track_name)))
        totals = Accumulators()
        repeat = self._cell.get_repeat()
        notes, controls, total, place = [], [], Fraction(0), 0
        while (place < repeat) if fill is None else (total < fill):
            played = self._play_pass(player, grab, scale, place % repeat, repeat, where, rolls, order, totals, total)
            length = played.total_length()
            if length == NO_LENGTH:
                break
            notes += played.notes
            controls += _moved_later(played.controls, total)
            total += length
            place += 1
        clip = Clip(notes=notes, scale=scale, controls=controls)
        return clip.section(NO_LENGTH, fill) if fill else clip

    def _play_pass(self, player, grab, scale, place, repeat, where, rolls, order, totals, start):
        """Return one pass through the cell's pattern, part way through any morph.

        Only the first pattern takes a rhythm, grabs or a direction from the cell, and a morph's
        target plays as it's written.
        """
        cell = self._cell
        clip = player.play_pass(
            cell.get_rhythm_pattern_name(), cell.get_pattern_name(), grab,
            cell.get_direction(), where, rolls, order, totals, start,
        )
        morph_to = cell.get_morph_target()
        if morph_to is None or not clip.notes:
            return clip
        target = player.play_pass(morph_to, morph_to, None, None, where, rolls, order, totals, start)
        amount = Fraction(place, repeat - 1) * FULL_MORPH
        target = _looped(target, clip.total_length())
        blend = Blend(target, amount, mode=cell.get_morph_style())
        controls = morph_controls(clip, target, *blend.region(clip))
        return Clip(notes=blend.generate(clip).played_notes(), scale=scale, controls=controls)


def _looped(clip, length):
    """Return a clip repeated or cut to last a length."""
    if clip.total_length() > NO_LENGTH:
        clip = clip.repeated(ceil(length / clip.total_length()))
    return clip.section(NO_LENGTH, length)


def _moved_later(controls, time):
    """Return CC values moved later by a time, for a pass that starts there."""
    return [replace(item, time=item.time + time) for item in controls]
