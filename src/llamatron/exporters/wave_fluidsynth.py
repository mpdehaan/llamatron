# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Writes a song as a WAV file, the sound of its tracks that play through FluidSynth and on built-in instruments, for anyone
with no DAW.

The song is written as the General MIDI export writes it, but with only the tracks whose
instrument's Device is *FluidSynth, into a MIDI file in a folder of its own that is always removed, and
FluidSynth plays that file into <directory>/<name>.wav with the SoundFont, faster than real time. The file is
then normalized, its loudest moment 1 dB below full scale, as the demos' WAV files are (exporters/wave_level.py),
so that it is as loud as it can be without distorting.
"""

import os
import subprocess
import tempfile

from llamatron.exporters.built_in_wave import BuiltInHalf, mixed_into
from llamatron.exporters.exporter import ExportKind
from llamatron.exporters.midi_arrangement import MidiGeneralMidi
from llamatron.exporters.wave_level import normalize_wave
from llamatron.user_strings import errors, names

WAV_FILE = '{name}.wav'
# The MIDI file FluidSynth plays, in the temporary folder.
MIDI_FILE = 'song.mid'
FLUID_FILE = 'fluidsynth.wav'
SAMPLE_RATE = '44100'
# FluidSynth with no MIDI input and no shell, quietly writing the file it plays to a WAV file at the sample rate.
RENDER_OPTIONS = ['-n', '-i', '-q', '-r', SAMPLE_RATE, '-F']


class WaveFluidSynth(MidiGeneralMidi):
    """Exports a ClipGrid as <directory>/<name>.wav: its tracks that play through FluidSynth, played by FluidSynth, and its
    tracks on built-in instruments, rendered by the synth daemon (exporters/built_in_wave.py), mixed."""

    __slots__ = ('_synth', '_built_in')

    def __init__(self, *, directory, grid, name, synth=None, built_in=None):
        """synth says where FluidSynth and its SoundFont are, as its program and soundfont, or is None where it isn't installed;
        built_in renders built-in instruments, or is None where the synth daemon isn't built."""
        super().__init__(directory=directory, grid=grid, name=name)
        self._synth = synth
        self._built_in = built_in

    @classmethod
    def for_song(cls, *, directory, grid, name, resources=None):
        return cls(directory=directory, grid=grid, name=name, synth=resources and resources.synth, built_in=resources and resources.built_in)

    KIND = ExportKind.WAV
    LABEL = names.MSG_WAV_EXPORT_LABEL
    FILE = WAV_FILE

    def sounding_tracks(self):
        """Return the tracks FluidSynth plays, in order: those that aren't muted and play through FluidSynth."""
        return [track for track in super().sounding_tracks() if track.plays_through_fluidsynth()]

    def built_in_half(self):
        """Return the export's tracks on built-in instruments, read from the whole arrangement."""
        return BuiltInHalf(arrangement=MidiGeneralMidi(directory=self.get_directory(), grid=self.get_grid(), name=self.get_name()))

    def export(self, *, render=subprocess.run):
        """Write the WAV file, unless it already exists, in which case this prints a warning and writes nothing. render runs
        FluidSynth, which the tests replace."""
        fluid = self.sounding_tracks()
        built_in = self.built_in_half()
        has_built_in = bool(built_in.tracks())
        self._check(fluid=fluid, has_built_in=has_built_in)
        path = self.path()
        if not self.can_write([os.path.basename(path)]):
            return
        with tempfile.TemporaryDirectory() as scratch:
            fluid_path = None
            if fluid:
                fluid_path = self._render_fluidsynth(scratch=scratch, render=render)
            built_in_path = None
            if has_built_in:
                built_in_path = built_in.render(renderer=self._built_in, directory=scratch)
            mixed_into(path=path, fluidsynth=fluid_path, built_in=built_in_path)
        normalize_wave(path)

    def _check(self, *, fluid, has_built_in):
        """Refuse an export that would be silent, or that needs FluidSynth or the synth daemon where it is missing."""
        if not fluid and not has_built_in:
            raise ValueError(errors.ERR_NO_FLUIDSYNTH_TRACKS)
        if fluid and self._synth is None:
            raise ValueError(errors.ERR_WAV_NEEDS_FLUIDSYNTH)
        if has_built_in and self._built_in is None:
            raise ValueError(errors.ERR_WAV_NEEDS_SYNTH_DAEMON)

    def _render_fluidsynth(self, *, scratch, render):
        """Play the FluidSynth tracks into a WAV file in the scratch folder, and return its path."""
        midi = os.path.join(scratch, MIDI_FILE)
        played = os.path.join(scratch, FLUID_FILE)
        self.midi_file().save(midi)
        finished = render([self._synth.program, *RENDER_OPTIONS, played, self._synth.soundfont, midi], capture_output=True, text=True, check=False)
        if finished.returncode != 0 or not os.path.exists(played):
            raise ValueError(errors.ERR_FLUIDSYNTH_RENDER_FAILED.format(problem=(finished.stderr or finished.stdout).strip()))
        return played
