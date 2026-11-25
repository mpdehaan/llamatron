# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A column of the grid a song renders into: one track's clips."""

from llamatron.engine.clips import track_sound
from llamatron.model.file.checks import check_drum, check_mute, check_name
from llamatron.user_strings import errors, reprs


class ClipColumn:
    """A column of the grid a song renders into, which is one track's clips. Its id is None unless it's in a grid.

    A muted column still has its clips, so a Realizer writes them, but Live starts with the
    track switched off. It's for tracks that other tracks grab notes from. Whether the track is a
    drum track and the General MIDI sound of its instrument are for the General MIDI export, which
    puts drums on channel 10 and gives every other track its sound; whether its instrument plays
    through FluidSynth, or is built in, is for the WAV export, which plays those tracks.
    """

    __slots__ = ('_id', '_name', '_mute', '_drum', '_sound')

    def __init__(self, *, name=None, mute=False, drum=False, sound=None):
        """sound is what the track's instrument sounds through, a TrackSound, or None for none."""
        check_name(name)
        check_mute(mute)
        check_drum(drum)
        self._id = None
        self._name = name
        self._mute = mute
        self._drum = drum
        self._sound = sound or track_sound.NO_SOUND

    def get_id(self):
        return self._id

    def set_id(self, new_id):
        """Give the column its id as it joins a grid. A column joins only one grid, so a second id is refused."""
        if self._id is not None:
            raise ValueError(errors.ERR_COLUMN_IN_A_GRID.format(column=self))
        self._id = new_id

    def get_name(self):
        return self._name

    def set_name(self, name):
        check_name(name)
        self._name = name

    def get_mute(self):
        return self._mute

    def set_mute(self, mute):
        check_mute(mute)
        self._mute = mute

    def is_drum(self):
        return self._drum

    def get_gm_sound(self):
        """Return the General MIDI sound of the track's instrument, 1 to 128, or None for none."""
        return self._sound.get_gm_sound()

    def plays_through_fluidsynth(self):
        """Return whether the track's instrument plays through FluidSynth, which the WAV export plays."""
        return self._sound.plays_through_fluidsynth()

    def built_in_spec(self):
        """Return the spec of the track's built-in instrument as the synth daemon compiles it, made now, or None when the
        track's instrument is not built in."""
        return self._sound.built_in_spec()

    def __repr__(self):
        return reprs.REPR_CLIP_COLUMN.format(name=self._name, mute=self._mute, drum=self._drum, gm_sound=self.get_gm_sound(), id=self._id)
