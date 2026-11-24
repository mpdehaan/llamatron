# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The PDF export page, which PDF in the Export dialog opens: what goes in the current song's PDFs, and Export.

The packet's pages are ticked in two columns; the Chords field says how simply the chords are printed; each track is a row
with its role and a dot in one of three columns, MELODY, CHORDS and LEFT OUT, its part, starting from what its notes' role
gives it; the export directory and the file's name follow, saying what an export would replace; then Export and CANCEL. The
cursor moves through them with the arrows, Space or ENTER ticks a page, chooses a column or presses a button, [ and ] step
the Chords field and ENTER opens its picker, and Tab goes to the next part. Export is dim and refuses, the line above it saying why in amber,
while nothing is ticked, or a page ticked needs a melody or chords that no track plays; a drums track among the chords is
warned of. The choices are remembered for the session, by the set and the song.
"""

from rich.text import Text

from llamatron.exporters.exports import PacketPage, pdf_options, PdfChoices, PrintedPart
from llamatron.interface.tracker import drawing, keybindings, themes
from llamatron.interface.tracker.components.button_row import button_row
from llamatron.interface.tracker.drawing import cursor_mark, Style
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.shared.everywhere import write_pdfs
from llamatron.interface.tracker.screens.shared.page import Page
from llamatron.user_strings import errors, help as help_text, labels, marks, messages

# What the page offers: the packet's pages, the chord levels, the parts a track plays and the roles its notes may play.
OPTIONS = pdf_options()
# The places the cursor stands on, in order: the packet's pages, the Chords field, the tracks, and the buttons.
PAGE_PLACES = len(OPTIONS.packet_pages)
# The packet's pages stand in two columns, the first half in the first.
PAGE_COLUMNS = 2
EXPORT_BUTTON = 0
CANCEL_BUTTON = 1
NAME_WIDTH = 14
ROLE_WIDTH = 10
COLUMN_WIDTH = 8
PAGE_NAME_WIDTH = 22
# The lines the page takes besides the tracks' rows: the gap, the packet's heading and its two lines, the Chords field, a
# gap, the tracks' heading, a gap, the export directory, a gap and the three lines of the buttons.
LINES_BESIDES_TRACKS = 12
FEWEST_TRACK_ROWS = 1
# The pages that draw the melody, and those that draw the chords.
NEEDS_MELODY = frozenset({PacketPage.PIANO_ROLL})
NEEDS_CHORDS = frozenset({PacketPage.PIANO_ROLL, PacketPage.CHORD_CHANGES, PacketPage.CHORD_CHART, PacketPage.CHORD_SEQUENCE})


class PdfExportPage(Page):
    """What goes in the current song's PDFs: the packet's pages, the chord level and each track's part; and Export."""

    THEME = themes.SET_FILE
    KEYS = keybindings.PdfExportPage
    HELP = help_text.HELP_PDF_EXPORT_PAGE
    crumbs = (labels.Crumb.EXPORT, labels.Crumb.PDF)

    def __init__(self, *, holder):
        super().__init__(holder)
        self.tracks = holder.get_document().pdf_tracks()
        remembered = holder.get_pdf_choices().get(self.choices_key())
        if remembered is None:
            remembered = PdfChoices(parts={track.name: track.part for track in self.tracks}, level=OPTIONS.default_level)
        self.ticked = set(remembered.packet_pages)
        self.parts = dict(remembered.parts)
        self.level = remembered.level
        self.place = 0
        self.column = 0
        self.top_track = 0

    def choices_key(self):
        """Return what the choices are remembered by: the set's file and the song."""
        document = self.document()
        return (document.get_path(), document.get_current_song_name())

    def choices(self):
        """Return the choices as the page holds them now."""
        return PdfChoices(packet_pages=tuple(page for page in OPTIONS.packet_pages if page in self.ticked), parts=dict(self.parts), level=self.level)

    def keys(self):
        result = [self.bind(self.KEYS.BACK, action=self.go_back), self.bind(self.KEYS.MOVE, action=self.move_cursor, wants_key=True)]
        if self.on_level():
            result += [self.bind(self.KEYS.LESS, action=self.step_level_back), self.bind(self.KEYS.MORE, action=self.step_level_forward)]
            result.append(self.bind(self.KEYS.PICK, action=self.pick_level))
        else:
            result.append(self.bind(self.KEYS.CHOOSE, action=self.choose))
        result.append(self.bind(self.KEYS.NEXT_PART, action=self.next_part))
        return result

    def place_count(self):
        return PAGE_PLACES + 1 + len(self.tracks) + 2

    def level_place(self):
        return PAGE_PLACES

    def first_track_place(self):
        return PAGE_PLACES + 1

    def first_button_place(self):
        return self.first_track_place() + len(self.tracks)

    def on_level(self):
        return self.place == self.level_place()

    def on_track(self):
        return self.first_track_place() <= self.place < self.first_button_place()

    def go_back(self):
        self.remember()
        super().go_back()

    def remember(self):
        """Keep the choices for the session, so that the page opens on them again for this set and song."""
        self.holder.get_pdf_choices()[self.choices_key()] = self.choices()

    def move_cursor(self, name):
        """Move between the places: Up and Down one place, Left and Right between the pages' columns, a track's three columns
        and the buttons, stopping at every edge."""
        if name in (Key.UP, Key.DOWN):
            self.place = self._place_above_or_below(name)
        elif self.place < PAGE_PLACES:
            self.place = self._page_beside(name)
        elif self.on_track():
            self.column = min(max(self.column + (1 if name == Key.RIGHT else -1), 0), len(OPTIONS.printed_parts) - 1)
        elif self.place >= self.first_button_place():
            self.place = min(max(self.place + (1 if name == Key.RIGHT else -1), self.first_button_place()), self.place_count() - 1)
        self._keep_track_in_view()
        self.draw()

    def next_part(self):
        """Go to the first place of the next part, from the buttons back to the packet's pages."""
        starts = [0, self.level_place(), self.first_track_place(), self.first_button_place()]
        later = [start for start in starts if start > self.place and (start < self.first_button_place() or start == self.first_button_place())]
        self.place = later[0] if later else 0
        self._keep_track_in_view()
        self.draw()

    def choose(self):
        """Tick or untick a page, give the track the column under the cursor, or press the button."""
        if self.place < PAGE_PLACES:
            self.ticked ^= {OPTIONS.packet_pages[self.place]}
        elif self.on_track():
            track = self.tracks[self.place - self.first_track_place()]
            self.parts[track.name] = OPTIONS.printed_parts[self.column]
            self._warn_of_drums(track)
        elif self.place == self.first_button_place() + EXPORT_BUTTON:
            self.export()
            return
        else:
            self.go_back()
            return
        self.draw()

    def step_level_back(self):
        self._step_level(-1)

    def step_level_forward(self):
        self._step_level(1)

    def pick_level(self):
        names = list(labels.MSG_CHORD_LEVEL_NAMES)
        self.ask_choice(title=labels.MSG_PDF_CHORDS_LABEL, options=names, current=OPTIONS.chord_levels.index(self.level), then=self._take_level)

    def refusal(self):
        """Return why Export can't go on, or None: nothing ticked, or a page that needs a melody or chords no track plays."""
        choices = self.choices()
        if not choices.packet_pages:
            return errors.ERR_PDF_NOTHING_TICKED
        parts = set(self.parts.values())
        if NEEDS_MELODY & set(choices.packet_pages) and PrintedPart.MELODY not in parts:
            return errors.ERR_PDF_NEEDS_MELODY
        if NEEDS_CHORDS & set(choices.packet_pages) and PrintedPart.CHORDS not in parts:
            return errors.ERR_PDF_NEEDS_CHORDS
        return None

    def export(self):
        """Write the PDFs, or say why not, and go back, saying where they went."""
        refusal = self.refusal()
        if refusal is not None:
            self.refuse(refusal)
            self.draw()
            return
        self.remember()
        written = write_pdfs(self, choices=self.choices())
        if written is None:
            return
        super().go_back()
        self.say(messages.MSG_EXPORTED_PDFS.format(count=len(written), paths=messages.MSG_PATHS_JOIN.join(written)))

    def body(self, *, width, height):
        rows = max(height - LINES_BESIDES_TRACKS, FEWEST_TRACK_ROWS)
        lines = [Text(drawing.NOTHING), Text(drawing.INDENT + labels.MSG_PACKET_HEADING, style=Style.BOLD), *self._page_lines()]
        lines += [self._level_line(), Text(drawing.NOTHING), self._tracks_heading(rows), *self._track_lines(rows), Text(drawing.NOTHING)]
        lines += [self._directory_line(), self._refusal_line(), *self._button_lines()]
        return lines

    def _place_above_or_below(self, name):
        """Return the place Up or Down goes to: along a column of the packet's pages, from either column's foot to the Chords
        field and from it to the first column's foot, and otherwise the place before or after, stopping at the ends."""
        half = PAGE_PLACES // PAGE_COLUMNS
        if self.place < PAGE_PLACES:
            row = self.place % half
            if name == Key.DOWN:
                return self.place + 1 if row < half - 1 else self.level_place()
            return self.place - 1 if row > 0 else self.place
        if self.on_level() and name == Key.UP:
            return half - 1
        step = 1 if name == Key.DOWN else -1
        return min(max(self.place + step, 0), self.place_count() - 1)

    def _page_beside(self, name):
        """Return the place of the packet's page beside the cursor's, in the other column, or the cursor's at an edge."""
        half = PAGE_PLACES // PAGE_COLUMNS
        if name == Key.RIGHT and self.place < half:
            return self.place + half
        if name == Key.LEFT and self.place >= half:
            return self.place - half
        return self.place

    def _keep_track_in_view(self):
        """Scroll the tracks so that the cursor's track shows."""
        if not self.on_track():
            return
        track = self.place - self.first_track_place()
        rows = max(self.size.height - LINES_BESIDES_TRACKS - 6, FEWEST_TRACK_ROWS) if self.size.height else len(self.tracks)
        self.top_track = min(max(self.top_track, track - rows + 1), track)

    def _warn_of_drums(self, track):
        if track.role == OPTIONS.track_roles[-1] and self.parts[track.name] == PrintedPart.CHORDS:
            self.refuse(messages.MSG_PDF_DRUMS_AS_CHORDS.format(track=track.name))

    def _step_level(self, step):
        place = min(max(OPTIONS.chord_levels.index(self.level) + step, 0), len(OPTIONS.chord_levels) - 1)
        self.level = OPTIONS.chord_levels[place]
        self.draw()

    def _take_level(self, place):
        self.level = OPTIONS.chord_levels[place]

    def _page_lines(self):
        """Return the packet's pages in two columns, each ticked or not."""
        half = PAGE_PLACES // PAGE_COLUMNS
        lines = []
        for row in range(half):
            line = Text(no_wrap=True)
            for place in (row, row + half):
                mark = marks.MSG_TOGGLE_ON if OPTIONS.packet_pages[place] in self.ticked else marks.MSG_FIELD_TOGGLE_OFF
                here = place == self.place
                line.append(cursor_mark(here))
                line.append(marks.MSG_TICKED_PAGE.format(mark=mark, page=labels.MSG_PACKET_PAGE_NAMES[place]).ljust(PAGE_NAME_WIDTH), style=Style.BOLD if here else Style.PLAIN)
            lines.append(line)
        return lines

    def _level_line(self):
        here = self.on_level()
        line = Text(cursor_mark(here), no_wrap=True)
        line.append(labels.MSG_PDF_CHORDS_LABEL.ljust(NAME_WIDTH), style=Style.BOLD if here else Style.PLAIN)
        line.append(labels.MSG_CHORD_LEVEL_NAMES[OPTIONS.chord_levels.index(self.level)])
        line.append(marks.MSG_PICKER_MARK, style=Style.DIM)
        return line

    def _tracks_heading(self, rows):
        heading = drawing.INDENT + labels.MSG_PDF_TRACK.ljust(NAME_WIDTH) + labels.MSG_PDF_ROLE.ljust(ROLE_WIDTH)
        heading += drawing.NOTHING.join(name.ljust(COLUMN_WIDTH) for name in labels.MSG_PRINTED_PART_NAMES)
        if len(self.tracks) > rows:
            heading += marks.MSG_ROWS_SHOWN.format(first=self.top_track + 1, last=min(self.top_track + rows, len(self.tracks)), total=len(self.tracks))
        return Text(heading, style=Style.BOLD)

    def _track_lines(self, rows):
        lines = []
        for index in range(self.top_track, min(self.top_track + rows, len(self.tracks))):
            track = self.tracks[index]
            here = self.place == self.first_track_place() + index
            line = Text(cursor_mark(here), no_wrap=True)
            line.append(track.name[:NAME_WIDTH - 1].ljust(NAME_WIDTH), style=Style.BOLD if here else Style.PLAIN)
            line.append(role_name(track.role).ljust(ROLE_WIDTH), style=Style.DIM)
            for column, part in enumerate(OPTIONS.printed_parts):
                mark = marks.MSG_TOGGLE_ON if self.parts.get(track.name, PrintedPart.LEFT_OUT) == part else marks.MSG_FIELD_TOGGLE_OFF
                line.append(drawing.INDENT + mark, style=Style.REVERSE if here and column == self.column else Style.PLAIN)
                line.append(drawing.SPACE * (COLUMN_WIDTH - len(drawing.INDENT) - len(mark)))
            lines.append(line)
        return lines

    def _directory_line(self):
        paths, replaced = self.document().pdf_paths(self.choices())
        text = labels.MSG_EXPORT_DIRECTORY.format(directory=self.document().export_directory(), files=messages.MSG_PATHS_JOIN.join(paths) or labels.MSG_NO_FILES)
        if replaced:
            text += labels.MSG_REPLACES_FILES.format(count=len(replaced))
        return Text(drawing.INDENT + text, no_wrap=True)

    def _refusal_line(self):
        """Return the line above the buttons: why Export can't go on, in amber, while it can't, else nothing."""
        refusal = self.refusal()
        if refusal is None:
            return Text(drawing.NOTHING)
        return Text(drawing.INDENT + refusal, style=Style.REFUSAL)

    def _button_lines(self):
        selected = None
        if self.place >= self.first_button_place():
            selected = self.place - self.first_button_place()
        buttons = button_row(buttons=[(drawing.NOTHING, name) for name in labels.MSG_PDF_EXPORT_BUTTONS], selected=selected)
        dim = self.refusal() is not None
        return [Text(drawing.INDENT, style=Style.DIM if dim else Style.PLAIN) + line for line in buttons]


def role_name(role):
    """Return a track's role as the page shows it, or that its track plays no notes."""
    if role not in OPTIONS.track_roles:
        return labels.MSG_NO_ROLE
    return labels.MSG_TRACK_ROLE_NAMES[OPTIONS.track_roles.index(role)]
