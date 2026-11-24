# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The piano roll pages of a packet: the melody drawn as boxes on a lane for each half step, each box in its scale degree's
colour and named with its letter, over the counting, 1 & 2 &, and the chords, each a box on the beat it starts with its name
and Roman numeral.

Each row holds as many bars as fill ROW_BEATS beats, its lanes spanning the melody's notes in it; each section begins with
its name over its first bar, and a section played several times in a row is drawn once, its name saying how many times.
Along the foot of every page runs the strip of the chord changes on it, each chord on a small keyboard, the keys that stay
from the chord before blue and those that move red.
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from typing import NamedTuple

from llamatron.exporters.pdf import canvas, chord_changes, palette
from llamatron.exporters.pdf.canvas import draw_heading
from llamatron.exporters.pdf.chord_changes import nearest_voicing
from llamatron.exporters.pdf.chord_chart import closest_voicing
from llamatron.exporters.pdf.keyboard import draw_keyboard, keyboard_range, PrintedKeyboard
from llamatron.music_theory.fundamentals import intervals
from llamatron.music_theory.harmony.heard_chords import spelled
from llamatron.user_strings import printing

PAGE_SIZE = landscape(letter)
OCTAVE = intervals.HALF_STEPS_PER_OCTAVE
BLACK_KEYS = frozenset({1, 3, 6, 8, 10})
MARGIN = 32
LABEL_WIDTH = 34
ROW_BEATS = 16
LANE_HEIGHT = 8
NARROWEST_LANE = 4
ROWS_PER_PAGE = 2
FEWEST_LANES = 13
TOP_HEIGHT = 26
# Section names stand on a line of their own over the bar numbers.
SECTION_RISE = 12
COUNT_HEIGHT = 11
CHORD_HEIGHT = 26
ROW_GAP = 14
STRIP_HEIGHT = 52
STRIP_LABEL_WIDTH = 70
STRIP_CELL_WIDTH = 60
STRIP_KEYBOARD_HEIGHT = 22
STRIP_ARROW_WIDTH = 14
GRID = colors.HexColor('#E4E4E4')
BAR_LINE = colors.HexColor('#9A9A9A')
BLACK_LANE = colors.HexColor('#F4F4F6')
SMALL_SIZE = 6.5
LABEL_SIZE = 7
SECTION_SIZE = 9
CHORD_SIZE = 9
NOTE_SIZE = 6
GRID_WIDTH = 0.4
BAR_WIDTH = 0.8
CORNER = 2
HALF = 2
NOTE_INSET = 1
TEXT_RISE = 2
HEADING_GAP = 6
# A note's letter is drawn this share of its lane's height, no larger than NOTE_SIZE.
NOTE_LETTER_SHARE = 0.85


class PrintedRollRow(NamedTuple):
    """A row of the roll: when it starts and ends, in whole notes, the bars it holds by their starts, and the lowest and
    highest MIDI numbers its lanes span."""

    start: object
    end: object
    bars: tuple
    low: int
    high: int


def printed_spans(printed):
    """Return the stretches of a song the roll draws, in order: every section once, a section played several times in a row
    only its first time."""
    starts = [section.start for section in printed.sections] or [0 * printed.length]
    ends = starts[1:] + [printed.length]
    spans = []
    times = [section.times for section in printed.sections] or [1]
    for start, end, count in zip(starts, ends, times):
        spans.append((start, start + (end - start) / count))
    if starts[0] > 0:
        spans.insert(0, (0 * printed.length, starts[0]))
    return spans


def roll_rows(printed):
    """Return the rows of the roll: the bars of every stretch it draws, ROW_BEATS beats a row, a stretch starting a row of
    its own, each row's lanes spanning its melody's notes, an octave at least."""
    bar = printed.bar_length()
    per_row = max(1, ROW_BEATS // printed.signature.get_beats())
    rows = []
    for start, end in printed_spans(printed):
        bars = []
        place = start
        while place < end:
            bars.append(place)
            place += bar
        for first in range(0, len(bars), per_row):
            chunk = tuple(bars[first:first + per_row])
            rows.append(_row(printed=printed, bars=chunk, end=min(chunk[-1] + bar, end)))
    return rows


def draw_piano_roll(*, page, printed):
    """Draw a printed song's piano roll pages from the page's start, each with its heading and its strip of chord changes."""
    PrintedRollDrawing(page=page, printed=printed).draw()


class PrintedRollDrawing:
    """The piano roll of one song being drawn: the page, the song, the rows, how wide a whole note is and how tall a lane."""

    __slots__ = ('_page', '_printed', '_rows', '_whole_width', '_lane')

    def __init__(self, *, page, printed):
        self._page = page
        self._printed = printed
        self._rows = roll_rows(printed)
        width, _ = PAGE_SIZE
        longest = max((row.end - row.start for row in self._rows), default=printed.bar_length())
        self._whole_width = (width - 2 * MARGIN - LABEL_WIDTH) / float(longest)
        self._lane = lane_height(self._rows)

    def draw(self):
        """Draw every row, as many to a page as fit above the strip, numbering the pages."""
        pages = self._pages()
        for index, rows in enumerate(pages, start=1):
            self._page.setPageSize(PAGE_SIZE)
            top = draw_heading(page=self._page, title=self._printed.title, detail=printing.MSG_PAGE_OF.format(page=printing.MSG_PIANO_ROLL, index=index, total=len(pages))) - HEADING_GAP
            for row in rows:
                self._draw_row(row=row, top=top)
                top -= row_height(row=row, lane=self._lane)
            self._draw_strip(start=rows[0].start, end=rows[-1].end)
            self._page.showPage()

    def _pages(self):
        """Return the rows in pages, as many to a page as fit between the heading and the strip."""
        _, height = PAGE_SIZE
        room = height - 2 * MARGIN - STRIP_HEIGHT - TOP_HEIGHT * 2
        pages = [[]]
        used = 0
        for row in self._rows:
            if pages[-1] and used + row_height(row=row, lane=self._lane) > room:
                pages.append([])
                used = 0
            pages[-1].append(row)
            used += row_height(row=row, lane=self._lane)
        return [rows for rows in pages if rows]

    def _x(self, *, row, time):
        """Return where a time falls across a row, in points."""
        return MARGIN + LABEL_WIDTH + float(time - row.start) * self._whole_width

    def _draw_row(self, *, row, top):
        """Draw a row: its lanes, its beats and bars, its section names, its notes, its counting and its chords."""
        roll_top = top - TOP_HEIGHT
        bottom = roll_top - (row.high - row.low + 1) * self._lane
        self._draw_lanes(row=row, bottom=bottom)
        self._draw_beats(row=row, bottom=bottom, top=roll_top)
        self._draw_sections(row=row, top=roll_top)
        self._draw_notes(row=row, bottom=bottom)
        self._draw_counting(row=row, y=bottom - COUNT_HEIGHT + TEXT_RISE)
        self._draw_chords(row=row, top=bottom - COUNT_HEIGHT)

    def _draw_lanes(self, *, row, bottom):
        """Shade the black keys' lanes, and name each C at the left with its octave."""
        right = self._x(row=row, time=row.end)
        for pitch in range(row.low, row.high + 1):
            y = bottom + (pitch - row.low) * self._lane
            if pitch % OCTAVE in BLACK_KEYS:
                self._page.setFillColor(BLACK_LANE)
                self._page.rect(MARGIN + LABEL_WIDTH, y, right - MARGIN - LABEL_WIDTH, self._lane, stroke=0, fill=1)
            if pitch % OCTAVE == 0:
                self._page.setFont(canvas.FONT, SMALL_SIZE)
                self._page.setFillColor(palette.INK)
                self._page.drawRightString(MARGIN + LABEL_WIDTH - 4, y + TEXT_RISE, printing.MSG_OCTAVE_C.format(octave=pitch // OCTAVE - 1))

    def _draw_beats(self, *, row, bottom, top):
        """Draw a line at every beat, darker at every bar, and each bar's number over it."""
        beat = self._printed.signature.beat_length()
        time = row.start
        while time <= row.end:
            is_bar = time in row.bars or time == row.end
            self._page.setStrokeColor(BAR_LINE if is_bar else GRID)
            self._page.setLineWidth(BAR_WIDTH if is_bar else GRID_WIDTH)
            self._page.line(self._x(row=row, time=time), bottom, self._x(row=row, time=time), top)
            time += beat
        self._page.setFont(canvas.FONT, LABEL_SIZE)
        self._page.setFillColor(palette.MUTED)
        for start in row.bars:
            self._page.drawString(self._x(row=row, time=start) + TEXT_RISE, top + TEXT_RISE, str(int(start / self._printed.bar_length()) + 1))

    def _draw_sections(self, *, row, top):
        """Name each section that begins in a row over its first bar, with how many times it plays where more than once."""
        for section in self._printed.sections:
            if row.start <= section.start < row.end:
                text = section.name
                if section.times > 1:
                    text = printing.MSG_SECTION_TIMES.format(section=section.name, times=section.times)
                self._page.setFont(canvas.BOLD_FONT, SECTION_SIZE)
                self._page.setFillColor(palette.INK)
                self._page.drawString(self._x(row=row, time=section.start), top + SECTION_RISE, text)

    def _draw_notes(self, *, row, bottom):
        """Draw each melody note in a row as a box in its degree's colour, named with its letter."""
        for note in self._printed.melody:
            if note.end <= row.start or note.start >= row.end:
                continue
            scale = self._printed.key_at(note.start)
            left = self._x(row=row, time=max(note.start, row.start))
            right = self._x(row=row, time=min(note.end, row.end))
            y = bottom + (note.pitch - row.low) * self._lane
            self._page.setFillColor(palette.color_of(pitch_class=note.pitch % OCTAVE, scale=scale))
            self._page.roundRect(left + NOTE_INSET, y + NOTE_INSET, max(right - left - HALF * NOTE_INSET, NOTE_INSET), self._lane - HALF * NOTE_INSET, CORNER, stroke=0, fill=1)
            self._page.setFillColor(palette.WHITE)
            self._page.setFont(canvas.BOLD_FONT, min(NOTE_SIZE, self._lane * NOTE_LETTER_SHARE))
            self._page.drawString(left + HALF * NOTE_INSET, y + self._lane * (1 - NOTE_LETTER_SHARE), spelled(pitch_class=note.pitch % OCTAVE, scale=scale))

    def _draw_counting(self, *, row, y):
        """Write the counting under a row: each beat's number and an & on each half beat."""
        beat = self._printed.signature.beat_length()
        self._page.setFont(canvas.FONT, SMALL_SIZE)
        self._page.setFillColor(palette.MUTED)
        for start in row.bars:
            for count in range(self._printed.signature.get_beats()):
                time = start + count * beat
                if time >= row.end:
                    break
                self._page.drawString(self._x(row=row, time=time) + TEXT_RISE, y, str(count + 1))
                self._page.drawString(self._x(row=row, time=time + beat / 2) + TEXT_RISE, y, printing.MSG_AND)

    def _draw_chords(self, *, row, top):
        """Draw each chord sounding in a row as a box from where it starts, with its name and numeral."""
        for chord in self._printed.chords:
            if chord.end <= row.start or chord.start >= row.end:
                continue
            left = self._x(row=row, time=max(chord.start, row.start))
            right = self._x(row=row, time=min(chord.end, row.end))
            color = palette.color_of(pitch_class=chord.root, scale=self._printed.key_at(chord.start))
            self._page.setFillColor(palette.tint(color=color, amount=palette.LIGHT_TINT))
            self._page.roundRect(left + NOTE_INSET, top - CHORD_HEIGHT, max(right - left - HALF * NOTE_INSET, NOTE_INSET), CHORD_HEIGHT - HALF, CORNER, stroke=0, fill=1)
            if chord.start >= row.start:
                self._page.setFillColor(palette.INK)
                self._page.setFont(canvas.BOLD_FONT, CHORD_SIZE)
                self._page.drawString(left + HALF * HALF, top - CHORD_SIZE - HALF, chord.name)
                self._page.setFont(canvas.FONT, SMALL_SIZE)
                self._page.drawString(left + HALF * HALF, top - CHORD_HEIGHT + HALF * HALF, chord.numeral)

    def _draw_strip(self, *, start, end):
        """Draw the strip of the chord changes on a page along its foot: each chord in the order played, a change shown once."""
        played = page_chords(printed=self._printed, start=start, end=end)
        self._page.setFont(canvas.BOLD_FONT, LABEL_SIZE)
        self._page.setFillColor(palette.MUTED)
        top = MARGIN + STRIP_HEIGHT - HEADING_GAP
        self._page.drawString(MARGIN, top - LABEL_SIZE - HALF, printing.MSG_STRIP_HEADING)
        self._page.setFont(canvas.FONT, SMALL_SIZE)
        self._page.drawString(MARGIN, top - 2 * LABEL_SIZE - HALF * HALF, printing.MSG_STRIP_KEY)
        width, _ = PAGE_SIZE
        fit = int((width - 2 * MARGIN - STRIP_LABEL_WIDTH) // (STRIP_CELL_WIDTH + STRIP_ARROW_WIDTH))
        before = None
        for place, item in enumerate(played[:fit]):
            if not item.follows:
                before = None
            notes = strip_voicing(chord=item.chord, before=before)
            self._draw_strip_chord(chord=item.chord, notes=notes, before=before, left=MARGIN + STRIP_LABEL_WIDTH + place * (STRIP_CELL_WIDTH + STRIP_ARROW_WIDTH), top=top)
            before = notes

    def _draw_strip_chord(self, *, chord, notes, before, left, top):
        """Draw one chord of the strip: its keyboard, the keys that stay from the chord before blue and those that move red,
        and its name under it."""
        low, high = keyboard_range(notes)
        keyboard = PrintedKeyboard(x=left, y=top - STRIP_KEYBOARD_HEIGHT, width=STRIP_CELL_WIDTH, height=STRIP_KEYBOARD_HEIGHT, low=low, high=high)
        pressed = {pitch: chord_changes.STAY if before is not None and pitch in before else chord_changes.MOVE for pitch in notes}
        draw_keyboard(page=self._page, keyboard=keyboard, pressed=pressed, labels={}, octaves=False)
        self._page.setFillColor(palette.INK)
        self._page.setFont(canvas.BOLD_FONT, CHORD_SIZE)
        self._page.drawCentredString(left + STRIP_CELL_WIDTH / 2, top - STRIP_KEYBOARD_HEIGHT - CHORD_SIZE - HALF * HALF, chord.name)
        if before is not None:
            self._page.setFillColor(palette.MUTED)
            self._page.drawCentredString(left - STRIP_ARROW_WIDTH / 2, top - STRIP_KEYBOARD_HEIGHT / 2 - HALF, printing.MSG_ARROW)


def row_height(*, row, lane):
    """Return how much of a page a row takes, its lanes, counting, chords and the gap after it."""
    return TOP_HEIGHT + (row.high - row.low + 1) * lane + COUNT_HEIGHT + CHORD_HEIGHT + ROW_GAP


def lane_height(rows):
    """Return how tall a lane is drawn: LANE_HEIGHT, or less, down to NARROWEST_LANE, so that ROWS_PER_PAGE rows of the
    widest range fit on a page."""
    _, height = PAGE_SIZE
    room = (height - 2 * MARGIN - STRIP_HEIGHT - TOP_HEIGHT * 2) / ROWS_PER_PAGE - TOP_HEIGHT - COUNT_HEIGHT - CHORD_HEIGHT - ROW_GAP
    lanes = max((row.high - row.low + 1 for row in rows), default=FEWEST_LANES)
    return max(NARROWEST_LANE, min(LANE_HEIGHT, room / lanes))


class StripChord(NamedTuple):
    """A chord of a page's strip, and whether it follows the chord drawn before it, which draws an arrow between them."""

    chord: object
    follows: bool


def page_chords(*, printed, start, end):
    """Return the chords of a page's strip (StripChord): those sounding between two times, in order, one of a name back to
    back as one, each move between two chords only the first time it is made, and a chord after a move left out starting
    afresh, with the chord before it where that isn't drawn already."""
    strip = []
    shown = set()
    before = None
    for chord in printed.chords:
        if chord.end <= start or chord.start >= end or (before is not None and before.name == chord.name):
            continue
        move = (before.name, chord.name) if before is not None else None
        if move not in shown:
            shown.add(move)
            follows = bool(strip) and strip[-1].chord is before
            if before is not None and not follows:
                strip.append(StripChord(chord=before, follows=False))
                follows = True
            strip.append(StripChord(chord=chord, follows=follows))
        before = chord
    return strip


def strip_voicing(*, chord, before):
    """Return how a strip voices a chord: nearest the chord before it, or its closest voicing where it comes first."""
    if before is None:
        voicing, _ = closest_voicing(root=chord.root, symbol=chord.symbol)
        return voicing
    return nearest_voicing(chord=chord, before=before)


def _row(*, printed, bars, end):
    """Return a row of bars, its lanes spanning its melody's notes, FEWEST_LANES at least, centred on them."""
    pitches = [note.pitch for note in printed.melody if note.start < end and note.end > bars[0]]
    low = min(pitches, default=60)
    high = max(pitches, default=60 + FEWEST_LANES - 1)
    missing = FEWEST_LANES - (high - low + 1)
    if missing > 0:
        low -= missing // HALF
        high = low + FEWEST_LANES - 1
    return PrintedRollRow(start=bars[0], end=end, bars=bars, low=low, high=high)
