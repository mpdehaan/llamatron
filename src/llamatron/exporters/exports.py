# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The kinds of export a song has, which the command line's --to and the tracker's X key choose between.

Every export is a file or files beside the set's file, named <set>_<song> plus what the file is:
foo_bar.als for the Live set, foo_bar.mid for the single MIDI file, foo_bar_stem_001-lead.mid
for each stem and foo_bar_clip_s_001-verse-t_001-lead.mid for each clip, so that a set's exports
sit beside it with predictable names and no folders. Each kind is a class built on Exporter
(exporters/exporter.py), which writes the files and finds what an earlier export of its kind left
in a directory, so that it can be replaced or asked about before being written over. The classes
are listed here, and the functions below ask the class of the kind they're given.
"""

from typing import NamedTuple

from llamatron.exporters.ableton_project import AbletonProject
from llamatron.exporters.clip_tree import ClipTree
from llamatron.exporters.exporter import ExportKind
from llamatron.exporters.midi_arrangement import MidiGeneralMidi, MidiSong, MidiStems
# The PDF export, which the UI reaches through this front door like every other export.
from llamatron.exporters.pdf.pdf_export import export_pdfs, PacketPage, pdf_options, pdf_path, PdfChoices, PdfKind, pdf_tracks
from llamatron.exporters.wave_fluidsynth import WaveFluidSynth

# Everything the UI and the command line may take from here, the PDF export's names among them.
__all__ = [
    'EXPORT_NAME', 'EXPORTERS', 'EXPORT_KINDS_IN_HELP', 'EXPORT_LABELS', 'ExportKind', 'ExportResources', 'export_name', 'make_exporter',
    'shown_export_path', 'earlier_export', 'remove_earlier_export',
    'export_pdfs', 'PacketPage', 'pdf_options', 'pdf_path', 'PdfChoices', 'PdfKind', 'pdf_tracks',
]

# What a song's exports are named: the set's name, then the song's.
EXPORT_NAME = '{setlist}_{song}'

# Every exporter, by the kind --to names, in the order --to's help lists them, with Live first because it's the default. A new kind of export is added here.
EXPORTERS = {exporter.KIND: exporter for exporter in (AbletonProject, MidiSong, MidiStems, ClipTree, MidiGeneralMidi, WaveFluidSynth)}
EXPORT_KINDS_IN_HELP = list(EXPORTERS)
# How each kind is described to people.
EXPORT_LABELS = {kind: exporter.LABEL for kind, exporter in EXPORTERS.items()}


def export_name(*, setlist, song):
    """Return what a song's exports are named after: <set>_<song>, like foo_bar."""
    return EXPORT_NAME.format(setlist=setlist, song=song)



class ExportResources(NamedTuple):
    """What some kinds of export are made with: the Live set a Live export is built from, None for the one that comes with the
    program, and where FluidSynth and its SoundFont are, as its program and soundfont, for a WAV export, None where it isn't installed."""

    template: object = None
    synth: object = None




def make_exporter(*, kind, directory, name, grid, resources=None):
    """Return the exporter for a kind of export, which writes a played grid into a directory, as files named after name, when told to
    export(), made with the ExportResources a kind needs: a Live set's template, and where FluidSynth is for a WAV."""
    return EXPORTERS[kind].for_song(directory=directory, grid=grid, name=name, resources=resources)


def shown_export_path(*, kind, directory, name):
    """Return where a kind of export goes, as shown to people: the file, for the kinds that write one, or the files' pattern for the rest."""
    return EXPORTERS[kind].shown_path(directory=directory, name=name)


def earlier_export(*, kind, directory, name):
    """Return the files an earlier export of a kind left in a directory, and nothing else that's there."""
    return EXPORTERS[kind].earlier_files(directory=directory, name=name)


def remove_earlier_export(*, kind, directory, name):
    """Remove what an earlier export of a kind left in a directory, and leave everything else."""
    EXPORTERS[kind].remove_earlier_files(directory=directory, name=name)
