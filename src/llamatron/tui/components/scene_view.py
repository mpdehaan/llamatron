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
"""Scene View, the user's design: what one scene of Arrange plays, every track's notes laid over each other in one read-only piano roll, inside an Inset Window.

Its first line is a caption saying which view shows, as written or as played (tui/scene_notes.py),
which Tab switches, and the window's border says it too, purple for written and blue for played; then
what the scene plays with in the end and where each value comes from; a legend of the tracks in their
colours, each with its number, a clip with a scale of its own naming it; the chord heard on each beat
and its Roman numeral in the scene's scale; the roll, a row for every key with a line along each C, the
name of every key a note plays beside its octave's label, a column for every sixteenth, as many cells
wide as the zoom says, with a mark at each bar, and the drums in lanes at the foot; a sidebar of each
track's details, as Arrange's details view shows them, which PgUp and PgDn scroll; and a line naming
the notes under the cursor, which the arrows move. A cell where two tracks sound at once shows the first
track's colour behind a bold X in the second's, or for more the count in black, the user's choice, and
the line under the roll names every note there. A clip that reads the registers is drawn in a hatched
block, apart from the rest, since what the registers do depends on the song before it. Velocity isn't
shown, the user's choice.
"""

from rich.style import Style as RichStyle
from rich.text import Text

from llamatron.composition.checks import fraction_text
from llamatron.music.note import SHARP_NAMES
from llamatron.strings.marks import (
    MSG_SCENE_VIEW_CANT_SHOW, MSG_SCENE_VIEW_CHORD_LABEL, MSG_SCENE_VIEW_CLIP_SCALE, MSG_SCENE_VIEW_EFFECTIVE, MSG_SCENE_VIEW_LEGEND_GAP, MSG_SCENE_VIEW_LEGEND_MARK,
    MSG_SCENE_VIEW_NOTE, MSG_SCENE_VIEW_NOTE_READS, MSG_SCENE_VIEW_NOTE_SEPARATOR, MSG_SCENE_VIEW_NOTHING_HERE, MSG_SCENE_VIEW_NUMERAL_LABEL, MSG_SCENE_VIEW_ONE_TAKE,
    MSG_SCENE_VIEW_PLACE, MSG_SCENE_VIEW_PLAYED, MSG_SCENE_VIEW_REGISTERS, MSG_SCENE_VIEW_SIGNATURE, MSG_SCENE_VIEW_TRACK, MSG_SCENE_VIEW_WRITTEN,
)
from llamatron.strings.visualizers import MSG_PIANO_ROLL_DRUM_LANES, MSG_PIANO_ROLL_OCTAVE_LABEL
from llamatron.tui.components.title_card import TITLE_BLUE
from llamatron.tui.key_table import cursor_moved
from llamatron.tui.keys import Key
from llamatron.tui.scene_notes import beat_chords, effective_values, scene_notes
from llamatron.tui.screens.arrange_details import ADD_CHAIN, clip_details, or_stock, track_details
from llamatron.visualizers.cells import CellPainter
from llamatron.visualizers.piano_roll import DRUM_ROWS, drum_lane

# Each column of the roll is a sixteenth note, in whole notes, drawn as many cells wide as the zoom, from FEWEST_CELLS to MOST_CELLS.
COLUMNS_PER_WHOLE = 16
START_CELLS = 3
FEWEST_CELLS = 1
MOST_CELLS = 5
# The labels at the left: an octave's name along its C from the first column, and a played key's name from NOTE_LABEL_COLUMN.
LABEL_COLUMNS = 8
NOTE_LABEL_COLUMN = 4
# The lines above the roll's body (the caption, the effective values and the legend), the chord lines at the top of the body, and the line under it.
LINES_ABOVE = 3
CHORD_LINES = 2
LINES_BELOW = 1
# The sidebar of each track's details, at the right, with a divider before it, and how far PgUp and PgDn scroll it.
SIDEBAR_COLUMNS = 28
SIDEBAR_SCROLL = 6
# The keys the roll shows beyond its highest and lowest notes, and the fewest it shows.
MARGIN_KEYS = 2
FEWEST_KEYS = 24
HALF_STEPS_PER_OCTAVE = 12
LOWEST_PITCH = 0
HIGHEST_PITCH = 127
FIRST_NUMBER = 1
# What the cells are drawn with: a note, two tracks' notes at once, a note of a clip that reads the registers, the octave lines, a bar's mark, the sidebar's divider and a blank.
NOTE_CHARACTER = '█'
OVERLAP_CHARACTER = 'X'
READING_CHARACTER = '░'
LINE_CHARACTER = '─'
BAR_CHARACTER = '┊'
DIVIDER_CHARACTER = '│'
SPACE = ' '
# The colours: the count of three tracks or more at once in black, the lines and labels dim, each note in one colour, and the border purple while the view is as written and the splash's blue while it is as played.
COUNT_COLOUR = (0, 0, 0)
LINE_COLOUR = (80, 80, 100)
LABEL_COLOUR = (150, 150, 170)
NOTE_LABEL_COLOUR = (210, 210, 225)
WRITTEN_COLOUR = (150, 80, 230)
PLAYED_COLOUR = TITLE_BLUE
# The tracks' colours, pure where they can be, the user's design: the drum tracks take the warm ones, reds, oranges, yellows and
# white, and the others the cool ones, green first and the colours most unlike it next; a group that needs more borrows the other's that are left.
WARM_COLOURS = [
    (255, 0, 0), (255, 128, 0), (255, 255, 0), (255, 255, 255), (255, 64, 64), (255, 192, 0), (255, 0, 128), (140, 0, 0), (140, 70, 0), (140, 140, 0),
]
COOL_COLOURS = [
    (0, 255, 0), (170, 0, 255), (0, 128, 255), (0, 255, 255), (255, 0, 255), (90, 90, 255), (0, 140, 140), (95, 0, 140), (0, 255, 128), (128, 255, 0),
    (0, 140, 0),
]
SCENE_COLOURS = COOL_COLOURS + WARM_COLOURS
CAPTION_STYLE = RichStyle(bold=True, reverse=True)
PLAIN_STYLE = RichStyle()
DIM_STYLE = RichStyle(dim=True)
BOLD = RichStyle(bold=True)
CURSOR_STYLE = RichStyle(reverse=True, bold=True)
# A drum lane's row stands for no pitch, and a seeded song's played view is no one take.
LANE = None
NO_TAKE = ''
NOTHING = ''


def coloured(*, drums, others):
    """Return each track's colour, by its place, the drum tracks in drums taking the warm colours and the tracks in others the cool ones, in order; a group that needs more takes the other group's that are left, and past every colour they go round."""
    colours = {}
    warm = list(WARM_COLOURS)
    cool = list(COOL_COLOURS)
    for places, own, other in ((others, cool, warm), (drums, warm, cool)):
        for count, place in enumerate(places):
            pool = own if own else other
            colours[place] = pool.pop(0) if pool else SCENE_COLOURS[count % len(SCENE_COLOURS)]
    return colours


def track_label(*, name, place):
    """Return a track's name with its number, counted from 1, as the legend shows it."""
    return MSG_SCENE_VIEW_TRACK.format(name=name, number=place + FIRST_NUMBER)


class SceneView:
    """One scene's notes in a read-only roll inside an Inset Window, as written or as played, with a cursor the arrows move, a zoom and a sidebar of each track's details."""

    __slots__ = ('_document', '_index', '_written', '_notes', '_problem', '_column', '_row', '_left', '_top', '_cells', '_zoom', '_side_top')

    def __init__(self, *, document, index):
        self._document = document
        self._index = index
        self._written = True
        self._notes = {}
        self._problem = None
        self._column = 0
        self._row = 0
        self._left = 0
        self._top = 0
        self._zoom = START_CELLS
        self._side_top = 0
        self._cells = CellPainter()
        self.place_cursor()

    def index(self):
        """Return the place of the scene it shows."""
        return self._index

    def track_colour(self, place):
        """Return a track's colour, the drum tracks warm and the others cool (coloured), each track keeping its colour from scene to scene, unless the song has more tracks than there are colours, the user's rule, when only the tracks that play in the scene take them."""
        song = self._document.song()
        names = song.get_track_names()
        places = range(len(names))
        if len(names) > len(SCENE_COLOURS):
            scene = song.get_scenes()[self._index]
            places = [each for each in places if scene.get_clip_slot(names[each]) is not None]
        drums = [each for each in places if song.get_track(names[each]).is_drum()]
        others = [each for each in places if each not in drums]
        return coloured(drums=drums, others=others).get(place, SCENE_COLOURS[place % len(SCENE_COLOURS)])

    def is_written(self):
        return self._written

    def border_colour(self):
        """Return the window's border colour, which says which view shows: purple as written, blue as played."""
        return WRITTEN_COLOUR if self._written else PLAYED_COLOUR

    def cursor_column(self):
        """Return the sixteenth the cursor is on, counted from the scene's start."""
        return self._column

    def zoom(self):
        """Return how many cells wide each sixteenth is drawn."""
        return self._zoom

    def switch(self):
        """Show the other view, as played or as written, keeping the cursor where it is in time, which V does."""
        self._written = not self._written
        self._row = min(self._row, len(self.rows()) - 1)

    def jump_bar(self, direction):
        """Move the cursor to the start of the next bar, or back to the start of its bar or the one before, as PgDn and PgUp do."""
        notes = self.notes()
        bar = max(int(notes.bar * COLUMNS_PER_WHOLE), 1) if notes else COLUMNS_PER_WHOLE
        if direction > 0:
            self._column = min((self._column // bar + 1) * bar, self.columns() - 1)
        else:
            within = self._column % bar
            self._column = max(self._column - (within if within else bar), 0)

    def zoom_by(self, direction):
        """Draw each sixteenth a cell narrower or wider, from FEWEST_CELLS to MOST_CELLS, as [ and ] step a value."""
        self._zoom = min(max(self._zoom + direction, FEWEST_CELLS), MOST_CELLS)

    def scroll_sidebar(self, direction):
        """Scroll the sidebar of the tracks' details up or down, as PgUp and PgDn do."""
        self._side_top = max(self._side_top + direction * SIDEBAR_SCROLL, 0)

    def notes(self):
        """Return the scene's notes in the view showing, worked out the first time each view is shown, since nothing changes while the window is open."""
        if self._written not in self._notes:
            try:
                self._notes[self._written] = scene_notes(song=self._document.song(), index=self._index, written=self._written)
            except ValueError as problem:
                self._problem = str(problem)
                return None
        return self._notes[self._written]

    def problem(self):
        """Return why the scene can't be shown, or None."""
        return self._problem

    def rows(self):
        """Return what each row of the roll stands for, top first: every key from above the highest note to below the lowest, then a lane for each kind of drum when a drum plays."""
        notes = self.notes()
        pitches = [note.pitch for note in notes.notes if not note.drum] if notes else []
        high = min(max(pitches, default=60) + MARGIN_KEYS, HIGHEST_PITCH)
        low = max(min(pitches, default=60) - MARGIN_KEYS, LOWEST_PITCH)
        while high - low + 1 < FEWEST_KEYS:
            high = min(high + 1, HIGHEST_PITCH)
            low = max(low - 1, LOWEST_PITCH)
        return list(range(high, low - 1, -1)) + self.lanes()

    def lanes(self):
        """Return the drum lanes, top first, when a drum plays in the scene, which stay at the foot of the roll while the keys above them scroll."""
        notes = self.notes()
        if notes and any(note.drum for note in notes.notes):
            return [(LANE, lane) for lane in range(DRUM_ROWS - 1, -1, -1)]
        return []

    def columns(self):
        """Return how many columns of sixteenths the scene lasts."""
        notes = self.notes()
        return max(int(notes.length * COLUMNS_PER_WHOLE), 1) if notes else 1

    def place_cursor(self):
        """Put the cursor on the scene's first note, its row on that note's key."""
        notes = self.notes()
        if not notes or not notes.notes:
            return
        first = min((note for note in notes.notes if not note.drum), key=lambda note: note.start, default=None)
        if first is None:
            return
        self._column = int(first.start * COLUMNS_PER_WHOLE)
        self._row = self.rows().index(first.pitch)

    def move(self, name):
        """Move the cursor a sixteenth left or right, or a row up or down, stopping at the edges."""
        if name in (Key.LEFT, Key.RIGHT):
            self._column = cursor_moved(place=self._column, name=name, count=self.columns())
        else:
            self._row = cursor_moved(place=self._row, name=name, count=len(self.rows()))

    def caption(self):
        """Return the line that says which view shows."""
        if self._written:
            return MSG_SCENE_VIEW_WRITTEN
        return MSG_SCENE_VIEW_PLAYED.format(take=MSG_SCENE_VIEW_ONE_TAKE if self._document.song().get_seed() is None else NO_TAKE)

    def lines(self, *, width, height):
        """Return the window's lines, width columns by height rows: the caption, the effective values and the legend across, then the chords and the roll beside the sidebar, then the line under the cursor."""
        lines = [Text(self.caption().ljust(width)[:width], style=CAPTION_STYLE)]
        notes = self.notes()
        if notes is None:
            return lines + [Text(MSG_SCENE_VIEW_CANT_SHOW.format(problem=self._problem)[:width])]
        song = self._document.song()
        effective = effective_values(song=song, index=self._index)
        signature = song.get_time_signature()
        lines.append(Text(MSG_SCENE_VIEW_EFFECTIVE.format(
            tempo=effective.tempo, tempo_source=effective.tempo_source, signature=MSG_SCENE_VIEW_SIGNATURE.format(beats=signature.get_beats(), unit=signature.get_unit()),
            scale=effective.scale or NOTHING, scale_source=effective.scale_source, groove=effective.groove, groove_source=effective.groove_source,
        )[:width], style=DIM_STYLE))
        lines.append(self.legend(notes=notes, effective=effective, width=width))
        body_height = max(height - LINES_ABOVE - LINES_BELOW, CHORD_LINES + 1)
        body_width = max(width - SIDEBAR_COLUMNS - 1, LABEL_COLUMNS + 1)
        sixteenths = max((body_width - LABEL_COLUMNS) // self._zoom, 1)
        roll_height = max(body_height - CHORD_LINES, 1)
        self.scroll(sixteenths=sixteenths, roll_height=roll_height)
        scale = song.get_named_scale(effective.scale) if effective.scale else None
        body = self.chord_lines(notes=notes, scale=scale, sixteenths=sixteenths) + self.roll_lines(notes=notes, sixteenths=sixteenths, roll_height=roll_height)
        sidebar = self.sidebar(height=len(body))
        for line, side in zip(body, sidebar):
            line.truncate(body_width, pad=True)
            line.append(DIVIDER_CHARACTER, style=DIM_STYLE)
            line.append_text(side)
        lines += body
        lines.append(Text(self.under_cursor(notes=notes)[:width]))
        return lines

    def scroll(self, *, sixteenths, roll_height):
        """Keep the cursor's column and row in the window of the roll that shows, the drum lanes always shown at its foot."""
        self._left = min(max(self._left, self._column - sixteenths + 1), self._column)
        keys = len(self.rows()) - len(self.lanes())
        key_rows = max(roll_height - len(self.lanes()), 1)
        if self._row < keys:
            self._top = min(max(self._top, self._row - key_rows + 1), self._row)
        self._top = max(min(self._top, keys - key_rows), 0)

    def legend(self, *, notes, effective, width):
        """Return the legend: each track that plays in the scene in its colour with its number, a clip's own scale after it, and the mark of the clips that read the registers."""
        text = Text()
        for track in sorted({note.track for note in notes.notes}):
            name = notes.names[track]
            entry = MSG_SCENE_VIEW_LEGEND_MARK + track_label(name=name, place=track)
            if name in effective.clip_scales:
                entry += MSG_SCENE_VIEW_CLIP_SCALE.format(scale=effective.clip_scales[name])
            text.append(entry, style=self._cells.style_of(colour=self.track_colour(track)))
            text.append(MSG_SCENE_VIEW_LEGEND_GAP)
        if notes.marked_tracks:
            text.append(MSG_SCENE_VIEW_REGISTERS, style=DIM_STYLE)
        text.truncate(width)
        return text

    def x_of(self, column):
        """Return where a sixteenth's column is drawn among the roll's cells, counted from the window's first column of the roll."""
        return (column - self._left) * self._zoom

    def chord_lines(self, *, notes, scale, sixteenths):
        """Return the chord heard on each beat and its numeral, each written at its beat's column when it differs from the beat's before and there is room."""
        cells = sixteenths * self._zoom
        names = [SPACE] * cells
        numerals = [SPACE] * cells
        last = None
        free = 0
        for chord in beat_chords(notes=notes, scale=scale):
            x = self.x_of(int(chord.start * COLUMNS_PER_WHOLE))
            if chord.name == last or not 0 <= x < cells or x < free:
                last = chord.name
                continue
            last = chord.name
            free = x + max(len(chord.name), len(chord.numeral)) + 1
            for place, character in enumerate(chord.name):
                if x + place < cells:
                    names[x + place] = character
            for place, character in enumerate(chord.numeral):
                if x + place < cells:
                    numerals[x + place] = character
        return [
            Text(MSG_SCENE_VIEW_CHORD_LABEL.ljust(LABEL_COLUMNS) + NOTHING.join(names), style=PLAIN_STYLE),
            Text(MSG_SCENE_VIEW_NUMERAL_LABEL.ljust(LABEL_COLUMNS) + NOTHING.join(numerals), style=DIM_STYLE),
        ]

    def roll_lines(self, *, notes, sixteenths, roll_height):
        """Return the roll's rows that show: the labels, then each sixteenth's cells, a note in its track's colour, two tracks' notes at once in white, the cursor's cells reversed."""
        rows = self.rows()
        lanes = self.lanes()
        keys = rows[:len(rows) - len(lanes)]
        shown = keys[self._top:self._top + max(roll_height - len(lanes), 1)] + lanes
        first = self._left
        occupants = {}
        for note in notes.notes:
            key = (LANE, drum_lane(note.pitch)) if note.drum else note.pitch
            if key not in shown:
                continue
            start = int(note.start * COLUMNS_PER_WHOLE)
            end = max(int(note.end * COLUMNS_PER_WHOLE), start + 1)
            for column in range(max(start, first), min(end, first + sixteenths)):
                occupants.setdefault((key, column), []).append((note, column == start, column == end - 1))
        played = {note.pitch for note in notes.notes if not note.drum}
        bar_columns = max(int(notes.bar * COLUMNS_PER_WHOLE), 1)
        lines = []
        for key in shown:
            characters, styles = self.row_label(key=key, played=played)
            for column in range(first, first + sixteenths):
                found = occupants.get((key, column))
                character, style = self.cell(key=key, column=column, found=found, bar_columns=bar_columns)
                if key == rows[self._row] and column == self._column:
                    style = CURSOR_STYLE if style is None else style + CURSOR_STYLE
                ends = found is not None and all(last for _, _, last in found)
                shared = found is not None and len({note.track for note, _, _ in found}) > 1
                for cell in range(self._zoom):
                    shown_character = character
                    if found is None and character == BAR_CHARACTER and cell:
                        shown_character = SPACE
                    if shared and cell != (self._zoom - (2 if ends and self._zoom > 1 else 1)) // 2:
                        shown_character = SPACE
                    if ends and self._zoom > 1 and cell == self._zoom - 1:
                        characters.append(SPACE)
                        styles.append(None if style is None or style is not CURSOR_STYLE else style)
                        continue
                    characters.append(shown_character)
                    styles.append(style)
            lines.append(self._cells.line(characters=characters, styles=styles))
        return lines

    def row_label(self, *, key, played):
        """Return a row's label as its characters and styles: its octave's name along a C and the key's own name when a note plays it, or its lane's name in the drum lanes."""
        if isinstance(key, tuple):
            text = MSG_PIANO_ROLL_DRUM_LANES[key[1]][:LABEL_COLUMNS - 1].ljust(LABEL_COLUMNS)
            return list(text), [self._cells.style_of(colour=LABEL_COLOUR)] * LABEL_COLUMNS
        characters = [SPACE] * LABEL_COLUMNS
        styles = [None] * LABEL_COLUMNS
        if key % HALF_STEPS_PER_OCTAVE == 0:
            octave = self._document.setlist().shown_octave(key // HALF_STEPS_PER_OCTAVE)
            for place, character in enumerate(MSG_PIANO_ROLL_OCTAVE_LABEL.format(octave=octave)[:NOTE_LABEL_COLUMN]):
                characters[place] = character
                styles[place] = self._cells.style_of(colour=LABEL_COLOUR)
        if key in played:
            for place, character in enumerate(self.note_name(key)[:LABEL_COLUMNS - NOTE_LABEL_COLUMN]):
                characters[NOTE_LABEL_COLUMN + place] = character
                styles[NOTE_LABEL_COLUMN + place] = self._cells.style_of(colour=NOTE_LABEL_COLOUR)
        return characters, styles

    def cell(self, *, key, column, found, bar_columns):
        """Return a cell's character and style: its note's; for tracks at once the first's colour behind, the second's bold X on it, or for more the count in black; a line along a C, a mark at a bar, or a blank."""
        if found:
            tracks = sorted({note.track for note, _, _ in found})
            note = found[0][0]
            if len(tracks) > 1:
                return self.overlap(tracks)
            colour = self.track_colour(note.track)
            character = READING_CHARACTER if note.marked else NOTE_CHARACTER
            return character, self._cells.style_of(colour=colour)
        if not isinstance(key, tuple) and key % HALF_STEPS_PER_OCTAVE == 0:
            return LINE_CHARACTER, self._cells.style_of(colour=LINE_COLOUR)
        if column % bar_columns == 0:
            return BAR_CHARACTER, self._cells.style_of(colour=LINE_COLOUR)
        return SPACE, None

    def overlap(self, tracks):
        """Return the character and style of a cell where several tracks sound at once, the user's choice: the first track's colour behind, the second's bold X on it, or the count in black for three or more."""
        background = self.track_colour(tracks[0])
        if len(tracks) == 2:
            return OVERLAP_CHARACTER, self._cells.style_of(colour=self.track_colour(tracks[1]), background=background) + BOLD
        return str(len(tracks)), self._cells.style_of(colour=COUNT_COLOUR, background=background) + BOLD

    def sidebar_lines(self):
        """Return the sidebar's lines in full: each track that plays in the scene, by its name and number in its colour, then its clip's details in the scene and its own, as Arrange's details view shows them, stock in red for none."""
        song = self._document.song()
        setlist = self._document.setlist()
        scene = song.get_scenes()[self._index]
        lines = []
        for place, name in enumerate(song.get_track_names()):
            clip_slot = scene.get_clip_slot(name)
            if clip_slot is None:
                continue
            lines.append(Text(track_label(name=name, place=place), style=self._cells.style_of(colour=self.track_colour(place)) + BOLD))
            details = clip_details(setlist=setlist, song=song, clip_slot=clip_slot) + track_details(song=song, track=song.get_track(name))
            # Scene View only shows, so the + that adds a chain on Arrange is left out, and stock stands for a track with nothing.
            details = [detail for detail in details if detail.target is None or detail.target.kind != ADD_CHAIN]
            for detail in details or or_stock([]):
                lines.append(Text(SPACE + detail.text, style=detail.style))
            lines.append(Text())
        return lines

    def sidebar(self, *, height):
        """Return the sidebar's lines that show, from where PgUp and PgDn have scrolled it, each SIDEBAR_COLUMNS wide."""
        lines = self.sidebar_lines()
        self._side_top = min(self._side_top, max(len(lines) - height, 0))
        shown = lines[self._side_top:self._side_top + height]
        shown += [Text()] * (height - len(shown))
        for line in shown:
            line.truncate(SIDEBAR_COLUMNS, pad=True)
        return shown

    def under_cursor(self, *, notes):
        """Return the line under the roll: every note sounding at the cursor's cell, by its track and number, name and length, or where the cursor is when none."""
        key = self.rows()[self._row]
        time = self._column / COLUMNS_PER_WHOLE
        found = []
        for note in notes.notes:
            here = (LANE, drum_lane(note.pitch)) if note.drum else note.pitch
            if here == key and note.start <= time < note.end:
                text = MSG_SCENE_VIEW_NOTE.format(track=notes.names[note.track], number=note.track + FIRST_NUMBER, note=self.note_name(note.pitch),
                                                  length=fraction_text(note.end - note.start))
                found.append(text + (MSG_SCENE_VIEW_NOTE_READS if note.marked else NOTHING))
        if found:
            return MSG_SCENE_VIEW_NOTE_SEPARATOR.join(found)
        bar, within = divmod(self._column, max(int(notes.bar * COLUMNS_PER_WHOLE), 1))
        beat = within // max(int(notes.beat * COLUMNS_PER_WHOLE), 1)
        return MSG_SCENE_VIEW_NOTHING_HERE.format(place=MSG_SCENE_VIEW_PLACE.format(bar=bar + 1, beat=beat + 1))

    def note_name(self, pitch):
        """Return a pitch's name with its octave in the set's octave labels."""
        return SHARP_NAMES[pitch % HALF_STEPS_PER_OCTAVE] + str(self._document.setlist().shown_octave(pitch // HALF_STEPS_PER_OCTAVE))
