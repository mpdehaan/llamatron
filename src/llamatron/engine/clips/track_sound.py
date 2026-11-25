# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What a finished track's instrument sounds through, for the exports that sound it: its General MIDI sound, whether it plays
through FluidSynth, and, for a built-in instrument, its sound for the synth daemon."""

from llamatron.model.file.checks import check_fluidsynth, check_gm_sound


class TrackSound:
    """A track's instrument's General MIDI sound, 1 to 128 or None; whether it plays through FluidSynth; and what makes the
    spec of its built-in sound when asked, or None, so that a render never makes a spec only a WAV export reads."""

    __slots__ = ('_gm_sound', '_fluidsynth', '_built_in')

    def __init__(self, *, gm_sound=None, fluidsynth=False, built_in=None):
        check_gm_sound(gm_sound)
        check_fluidsynth(fluidsynth)
        self._gm_sound = gm_sound
        self._fluidsynth = fluidsynth
        self._built_in = built_in

    def get_gm_sound(self):
        return self._gm_sound

    def plays_through_fluidsynth(self):
        return self._fluidsynth

    def built_in_spec(self):
        """Return the built-in instrument's spec as the synth daemon compiles it, made now, or None for an instrument that is
        not built in."""
        if self._built_in is None:
            return None
        return self._built_in()


NO_SOUND = TrackSound()
