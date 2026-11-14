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

"""Writes a song as a WAV file, the sound of its tracks that play through FluidSynth, for anyone with no DAW.

The user's design: the song is written as the General MIDI export writes it, but with only the tracks whose
instrument's Device is *FluidSynth, into a MIDI file in a folder of its own that is always removed, and
FluidSynth plays that file into <directory>/<name>.wav with the SoundFont, faster than real time. The file is
then normalized, its loudest moment 1 dB below full scale, as the demos' WAV files are (exporters/wave_level.py),
so that it is as loud as it can be without distorting.
"""

import os
import subprocess
import tempfile

from llamatron.exporters.exporter import ExportKind
from llamatron.exporters.midi_arrangement import MidiGeneralMidi
from llamatron.exporters.wave_level import normalize_wave
from llamatron.realtime.fluidsynth import fluidsynth_path, is_installed, soundfont_path
from llamatron.strings.errors import ERR_FLUIDSYNTH_RENDER_FAILED, ERR_NO_FLUIDSYNTH_TRACKS, ERR_WAV_NEEDS_FLUIDSYNTH
from llamatron.strings.names import MSG_WAV_EXPORT_LABEL

WAV_FILE = '{name}.wav'
# The MIDI file FluidSynth plays, in the temporary folder.
MIDI_FILE = 'song.mid'
SAMPLE_RATE = '44100'
# FluidSynth with no MIDI input and no shell, quietly writing the file it plays to a WAV file at the sample rate.
RENDER_OPTIONS = ['-n', '-i', '-q', '-r', SAMPLE_RATE, '-F']


class WaveFluidSynth(MidiGeneralMidi):
    """Exports a ClipGrid as <directory>/<name>.wav: its tracks that play through FluidSynth, played by FluidSynth."""

    __slots__ = ()

    KIND = ExportKind.WAV
    LABEL = MSG_WAV_EXPORT_LABEL
    FILE = WAV_FILE

    def sounding_tracks(self):
        """Return the tracks the WAV holds, in order: those that aren't muted and play through FluidSynth."""
        return [track for track in super().sounding_tracks() if track.plays_through_fluidsynth()]

    def export(self, *, render=subprocess.run):
        """Write the WAV file, unless it already exists, in which case this prints a warning and writes nothing. render runs FluidSynth, which the tests replace."""
        if not is_installed():
            raise ValueError(ERR_WAV_NEEDS_FLUIDSYNTH)
        if not self.sounding_tracks():
            raise ValueError(ERR_NO_FLUIDSYNTH_TRACKS)
        path = self.path()
        if not self.can_write([os.path.basename(path)]):
            return
        with tempfile.TemporaryDirectory() as scratch:
            midi = os.path.join(scratch, MIDI_FILE)
            self.midi_file().save(midi)
            finished = render([fluidsynth_path(), *RENDER_OPTIONS, path, soundfont_path(), midi], capture_output=True, text=True, check=False)
        if finished.returncode != 0 or not os.path.exists(path):
            raise ValueError(ERR_FLUIDSYNTH_RENDER_FAILED.format(problem=(finished.stderr or finished.stdout).strip()))
        normalize_wave(path)
