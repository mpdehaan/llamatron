# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The PDF export from the command line (user_scripts/export_pdf.sh): a song of a set made into its learning packet.

    sh user_scripts/export_pdf.sh SET [--song NAME] [--output-dir FOLDER] [--pages piano_roll,chord_chart]
        [--tracks lead,piano] [--chords-level sevenths]

The song is the set's first unless --song names one; the PDF goes beside the set unless --output-dir names a folder. The
tracks named are merged and read as a lead sheet; without --tracks, every track that plays pitched notes, as the export page
starts with.
"""

import argparse
import os
import sys

from llamatron.exporters.exports import export_name
from llamatron.exporters.pdf import pdf_export
from llamatron.exporters.pdf.pdf_export import PdfChoices
from llamatron.model.objects.setlist import Setlist
from llamatron.music_theory.harmony import chord_estimate
from llamatron.user_strings import printing

PROGRAM = 'export_pdf.sh'
OPTION_SONG = '--song'
OPTION_OUTPUT = '--output-dir'
OPTION_PAGES = '--pages'
OPTION_TRACKS = '--tracks'
OPTION_LEVEL = '--chords-level'
LIST_JOIN = ','
SET_SUFFIX = '.yml'


def main(*, arguments=None):
    """Write the learning packet of a set's song, and say where it went."""
    options = parser().parse_args(arguments)
    setlist = Setlist.read_file(options.set)
    name = options.song or setlist.first_song_name()
    if name not in setlist.get_song_names():
        sys.exit(printing.MSG_SCRIPT_NO_SONG.format(song=name))
    song = setlist.get_song(name)
    directory = options.output_dir or os.path.dirname(os.path.abspath(options.set))
    os.makedirs(directory, exist_ok=True)
    choices = PdfChoices(packet_pages=options.pages, tracks=frozenset(options.tracks or pdf_export.default_tracks(song)), level=options.chords_level)
    file_name = export_name(setlist=os.path.basename(options.set).removesuffix(SET_SUFFIX), song=name)
    for path in pdf_export.export_pdfs(song=song, title=name, directory=directory, name=file_name, choices=choices):
        print(printing.MSG_SCRIPT_WROTE.format(path=path))


def parser():
    """Return the script's options, which --help lists."""
    made = argparse.ArgumentParser(prog=PROGRAM, description=printing.MSG_SCRIPT_DESCRIPTION)
    made.add_argument('set', help=printing.MSG_SCRIPT_HELP_SET)
    made.add_argument(OPTION_SONG, help=printing.MSG_SCRIPT_HELP_SONG)
    made.add_argument(OPTION_OUTPUT, help=printing.MSG_SCRIPT_HELP_OUTPUT)
    made.add_argument(OPTION_PAGES, type=packet_pages, default=pdf_export.DEFAULT_PACKET_PAGES, help=printing.MSG_SCRIPT_HELP_PAGES.format(
        pages=LIST_JOIN.join(pdf_export.PACKET_PAGES)))
    made.add_argument(OPTION_TRACKS, type=track_names, help=printing.MSG_SCRIPT_HELP_TRACKS)
    made.add_argument(OPTION_LEVEL, choices=chord_estimate.CHORD_LEVELS, default=chord_estimate.DEFAULT_CHORD_LEVEL, help=printing.MSG_SCRIPT_HELP_LEVEL)
    return made


def packet_pages(text):
    """Return the packet's pages --pages names, refusing a page the packet hasn't."""
    pages = tuple(page for page in text.split(LIST_JOIN) if page)
    for page in pages:
        if page not in pdf_export.PACKET_PAGES:
            raise argparse.ArgumentTypeError(printing.MSG_SCRIPT_BAD_PAGE.format(page=page, pages=LIST_JOIN.join(pdf_export.PACKET_PAGES)))
    return pages


def track_names(text):
    """Return the track names a comma-separated list gives."""
    return [name for name in text.split(LIST_JOIN) if name]


if __name__ == '__main__':
    main()
