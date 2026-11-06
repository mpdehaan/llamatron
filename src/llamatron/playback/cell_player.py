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
from llamatron.song import Clip


class CellPlayer:
    """Plays a track's cell in a scene: its pattern, repeated or looped, morphing, then through its chain.

    It asks the SongRenderer it belongs to for the scene's length, which a looping clip fills, and
    for the notes of a track it grabs from.
    """

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
        where = f'scene {scene.get_number()}, track {self._track_name!r}'
        scale = None if scene.get_scale_name() is None else self._song.get_named_scale(scene.get_scale_name()).scale_at(self._clip_octave())
        player = PatternPlayer(self._song, scene, scale, self._track)
        grab = self._renderer.get_grab_source(scene, self._track_name) if grabbing else None
        loop = cell.loops()
        fill = self._renderer.get_scene_length(scene) if loop else None
        try:
            clip = self._play_passes(player, grab, scale, where, fill)
            controls = clip.controls
            chain = cell.get_chain_name()
            if clip.total_length() > 0 and chain is not None:
                for index, step in enumerate(self._song.get_chain(chain).get_steps()):
                    clip = self._renderer.make_generator(step, scene, self._track_name, chain, index).generate(clip)
            end = fill if loop else clip.total_length()
            notes = clip.section(0, end).notes if end > 0 else []
            # Until here a control's number is its lane, which the track turns into a CC number.
            numbers = self._track.get_cc_numbers()
            controls = [
                replace(item, number=numbers[item.number]) for item in controls
                if item.time < end and numbers[item.number] is not None
            ]
            return Clip(name=scene.get_name(), notes=notes, scale=scale, loop=loop, controls=controls)
        except (ValueError, TypeError) as error:
            raise SongFileError(f'{where}: {error}') from error

    def _clip_octave(self):
        """Return the octave for the root of this clip's scale.

        It's the octave of the first note the clip plays, in this project's numbering.
        """
        octave = self._song.get_pattern(self._cell.get_pattern_name()).get_first_octave()
        return (self._song.get_default_octave() if octave is None else octave) + LIVE_OCTAVE_OFFSET

    def _play_passes(self, player, grab, scale, where, fill):
        """Return what the clip plays before any chains: its repeats, or enough passes to fill a length."""
        seed, number = self._song.get_seed(), self._scene.get_number()
        rolls = random.Random(f'{seed}/{number}/{self._track_name}')
        order = StepOrder(random.Random(f'{seed}/{number}/{self._track_name}/direction'))
        totals = Accumulators()
        repeat = self._cell.get_repeat()
        notes, controls, total, place = [], [], Fraction(0), 0
        while (place < repeat) if fill is None else (total < fill):
            played = self._play_pass(player, grab, scale, place % repeat, repeat, where, rolls, order, totals, total)
            length = played.total_length()
            if length == 0:
                break
            notes += played.notes
            controls += [replace(item, time=item.time + total) for item in played.controls]
            total += length
            place += 1
        clip = Clip(notes=notes, scale=scale, controls=controls)
        return clip.section(0, fill) if fill else clip

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
        amount = Fraction(place, repeat - 1) * 100
        target = _looped(target, clip.total_length())
        blend = Blend(target, amount, mode=cell.get_morph_style())
        controls = morph_controls(clip, target, *blend.region(clip))
        return Clip(notes=blend.generate(clip).played_notes(), scale=scale, controls=controls)


def _looped(clip, length):
    """Return a clip repeated or cut to last a length."""
    if clip.total_length() > 0:
        clip = clip.repeated(ceil(length / clip.total_length()))
    return clip.section(0, length)
