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

"""The kinds of output a song renders to, which the command line's --to and the tracker's render keys choose between.

Each kind has a writer, and a way to find what an earlier render of it left in a directory, so
that it can be replaced or asked about before being written over.
"""

import glob
import os

from llamatron.renderers.ableton_project import DEFAULT_TEMPLATE, AbletonProject
from llamatron.renderers.clip_tree import ClipTree
from llamatron.renderers.midi_arrangement import MidiSong, MidiStems, stem_files_pattern
from llamatron.clip_grid import ClipGrid


class OutputKind:
    """What --to can write, as it's named on the command line."""

    ABLETON = 'ableton'
    MIDI_FILE = 'midi'
    STEMS = 'stems'
    CLIP_TREE = 'cliptree'


# Every kind, in the order --to's help lists them, with Live first because it's the default.
OUTPUT_KINDS = [OutputKind.ABLETON, OutputKind.MIDI_FILE, OutputKind.STEMS, OutputKind.CLIP_TREE]
# The kinds that write MIDI files, in the order the tracker offers them.
MIDI_KINDS = [OutputKind.MIDI_FILE, OutputKind.STEMS, OutputKind.CLIP_TREE]
# How each kind is described to people.
OUTPUT_NAMES = {
    OutputKind.ABLETON: 'Ableton set',
    OutputKind.MIDI_FILE: 'MIDI file',
    OutputKind.STEMS: 'MIDI stems',
    OutputKind.CLIP_TREE: 'clip tree',
}
# The MIDI files a clip tree writes: <scene>-<track>-<name>.mid.
CLIP_TREE_FILES = '[0-9]*-[0-9]*.mid'


def make_writer(kind, directory, grid, template=None):
    """Return the writer for a kind of output, which writes a rendered grid into a directory when told to render()."""
    if kind == OutputKind.ABLETON:
        return AbletonProject(directory, grid, template=template or DEFAULT_TEMPLATE)
    if kind == OutputKind.MIDI_FILE:
        return MidiSong(directory, grid)
    if kind == OutputKind.STEMS:
        return MidiStems(directory, grid)
    return ClipTree(directory, grid)


def output_path(kind, directory):
    """Return where a kind of output goes: the file, for the kinds that write one, or the directory for the rest."""
    if kind == OutputKind.ABLETON:
        return AbletonProject(directory, ClipGrid()).path
    if kind == OutputKind.MIDI_FILE:
        return MidiSong(directory, ClipGrid()).path()
    return directory


def earlier_output(kind, directory):
    """Return the files an earlier render of a kind left in a directory, and nothing else that's there."""
    if kind == OutputKind.ABLETON or kind == OutputKind.MIDI_FILE:
        path = output_path(kind, directory)
        return [path] if os.path.exists(path) else []
    if kind == OutputKind.STEMS:
        return sorted(glob.glob(stem_files_pattern(directory)))
    return sorted(glob.glob(os.path.join(glob.escape(os.fspath(directory)), CLIP_TREE_FILES)))


def replace_output(kind, directory):
    """Remove what an earlier render of a kind left in a directory, and leave everything else."""
    for path in earlier_output(kind, directory):
        os.remove(path)
