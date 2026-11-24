# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""What every page of a PDF shares: its number in the lower right corner, out of how many pages the file has, and its heading
in the upper right, the song's title over what the page is."""

from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from llamatron.exporters.pdf import palette
from llamatron.user_strings import printing

FONT = 'Helvetica'
BOLD_FONT = 'Helvetica-Bold'
NUMBER_SIZE = 8
TITLE_SIZE = 14
DETAIL_SIZE = 10
NUMBER_RIGHT = 0.45 * inch
NUMBER_BOTTOM = 0.35 * inch
HEADING_MARGIN = 0.6 * inch
# Where the heading's lines sit below the top margin, and the room it takes there.
TITLE_DROP = 12
DETAIL_DROP = 26
HEADING_HEIGHT = 34


class NumberedCanvas(canvas.Canvas):
    """A reportlab canvas that numbers every page, page 3/7: it holds each page back until the file is saved, when the total
    is known."""

    def __init__(self, path, *, pagesize):
        super().__init__(path, pagesize=pagesize)
        self._held_pages = []

    def showPage(self):
        """Hold the finished page back, to be numbered when the file is saved, and start the next."""
        self._held_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """Number every page held back, with the last if anything is drawn on it, and write the file."""
        if not self._held_pages or self._code:
            self._held_pages.append(dict(self.__dict__))
        total = len(self._held_pages)
        for number, state in enumerate(self._held_pages, start=1):
            self.__dict__.update(state)
            self._draw_number(number=number, total=total)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def get_page_size(self):
        """Return the page's width and height, in points."""
        return self._pagesize

    def page_count(self):
        """Return how many pages are finished so far."""
        return len(self._held_pages)

    def _draw_number(self, *, number, total):
        width, _ = self._pagesize
        self.setFont(FONT, NUMBER_SIZE)
        self.setFillColor(palette.MUTED)
        self.drawRightString(width - NUMBER_RIGHT, NUMBER_BOTTOM, printing.MSG_PAGE_NUMBER.format(number=number, total=total))


def draw_heading(*, page, title, detail):
    """Draw a page's heading in its upper right corner, the title over the detail, and return the height below it where the
    page's own drawing starts."""
    width, height = page.get_page_size()
    top = height - HEADING_MARGIN
    page.setFillColor(palette.INK)
    page.setFont(BOLD_FONT, TITLE_SIZE)
    page.drawRightString(width - HEADING_MARGIN, top - TITLE_DROP, title)
    page.setFillColor(palette.MUTED)
    page.setFont(FONT, DETAIL_SIZE)
    page.drawRightString(width - HEADING_MARGIN, top - DETAIL_DROP, detail)
    return top - HEADING_HEIGHT
