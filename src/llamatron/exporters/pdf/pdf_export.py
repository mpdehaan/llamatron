# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The PDF export: a song made into the PDFs chosen, beside its set as every export is, named <set>_<song>__<kind>.pdf.

The packet is one PDF of the pages ticked, in the order a learner reads them: the piano roll, the chord changes, the chord
chart and the chord sequence. The tracks chosen as the melody and the chords, and the level the chords are printed at,
come in PdfChoices.
"""

from dataclasses import dataclass
import os
from reportlab.lib.pagesizes import letter

from llamatron.exporters.pdf import song_printing
from llamatron.exporters.pdf.canvas import NumberedCanvas
from llamatron.exporters.pdf.chord_changes import draw_chord_changes
from llamatron.exporters.pdf.chord_chart import draw_chord_chart
from llamatron.exporters.pdf.chord_sequence import draw_chord_sequence
from llamatron.exporters.pdf.piano_roll import draw_piano_roll
from llamatron.music_theory.harmony import chord_charts
from llamatron.user_strings import printing

PDF_SUFFIX = '.pdf'
FILE_NAME = '{name}__{kind}' + PDF_SUFFIX


class PacketPage:
    """A page of the packet a person may tick."""

    PIANO_ROLL = 'piano_roll'
    CHORD_CHANGES = 'chord_changes'
    CHORD_CHART = 'chord_chart'
    CHORD_SEQUENCE = 'chord_sequence'


class PdfKind:
    """A PDF the export writes, by the word its file's name ends with."""

    PACKET = 'packet'


# The packet's pages in the order a learner reads them, each with how it is drawn.
PACKET_PAGES = (PacketPage.PIANO_ROLL, PacketPage.CHORD_CHANGES, PacketPage.CHORD_CHART, PacketPage.CHORD_SEQUENCE)
DRAWN_BY = {
    PacketPage.PIANO_ROLL: draw_piano_roll, PacketPage.CHORD_CHANGES: draw_chord_changes, PacketPage.CHORD_CHART: draw_chord_chart,
    PacketPage.CHORD_SEQUENCE: draw_chord_sequence,
}
DEFAULT_PACKET_PAGES = PACKET_PAGES


@dataclass(slots=True, kw_only=True, frozen=True)
class PdfChoices:
    """What a PDF export makes: the packet's pages ticked, the part each track plays by name (song_printing.PrintedPart),
    a track not named left out, and the level the chords are printed at."""

    packet_pages: tuple = DEFAULT_PACKET_PAGES
    parts: dict
    level: str = chord_charts.DEFAULT_CHORD_LEVEL


def default_parts(song):
    """Return the part each of a song's tracks plays by default, by its name: the role its notes play."""
    tracks = song_printing.track_notes(song_printing.rendered(song))
    return song_printing.default_parts(tracks=tracks, signature=song.get_time_signature())


def pdf_path(*, directory, name, kind):
    """Return where a kind of PDF of a song goes: <directory>/<set>_<song>__<kind>.pdf."""
    return os.path.join(directory, FILE_NAME.format(name=name, kind=kind))


def export_pdfs(*, song, title, directory, name, choices):
    """Write the PDFs chosen of a song, titled as given on every page, into a directory, named after name, <set>_<song>, and
    return the paths written."""
    written = []
    if not choices.packet_pages:
        return written
    printed = song_printing.printed_song(song=song, title=title, parts=choices.parts, level=choices.level)
    path = pdf_path(directory=directory, name=name, kind=PdfKind.PACKET)
    write_packet(path=path, printed=printed, pages=choices.packet_pages)
    written.append(path)
    return written


def write_packet(*, path, printed, pages):
    """Write a packet of a printed song's pages ticked, in the packet's order, as one PDF."""
    page = NumberedCanvas(path, pagesize=letter)
    page.setTitle(printing.MSG_PACKET_TITLE.format(song=printed.title))
    for kind in PACKET_PAGES:
        if kind in pages:
            page.setPageSize(letter)
            DRAWN_BY[kind](page=page, printed=printed)
    page.save()
