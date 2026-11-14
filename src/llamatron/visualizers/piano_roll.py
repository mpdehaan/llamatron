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
"""The piano roll, a visualizer mode, the user's design: the notes as bars rolling in from the right, to give a feel for what the song is doing.

Every key of the piano has a row, one half step each, not only the scale's, with a line along each C,
labelled at the left. A note comes in at the right edge as it starts and rolls off to the left; while
it sounds its bar keeps growing at the right, so a held note looks long, and each bar's first cell is
brighter, with a gap after it on its row, so that notes one after another stay apart. Each track has a
bold colour of its own, given in the order the tracks are first heard, so that the colours go round only
when more tracks play than there are colours, and the legend across the top names the tracks with a note on the roll now, in the order of the song's tracks. The rows stay still, the user's rule: they sit on the
middle of every pitch heard so far while those pitches fit the rows, and only when they don't fit does the middle ease, slowly, toward the notes that sound now. Drum tracks have lanes of their own at the bottom,
kick, snare, hats, toms, cymbal and the rest, where each hit is a short mark. The background is black.
The amounts are named constants here, for the user to tune by eye.
"""

from llamatron.composition.file_format import LIVE_OCTAVE_OFFSET
from llamatron.strings.visualizers import (
    MSG_PIANO_ROLL, MSG_PIANO_ROLL_DRUM_LANES, MSG_PIANO_ROLL_LEGEND_GAP, MSG_PIANO_ROLL_LEGEND_MARK, MSG_PIANO_ROLL_OCTAVE_LABEL,
)
from llamatron.visualizers.cells import CellPainter
from llamatron.visualizers.heard import SILENCE
from llamatron.visualizers.visualizer import Visualizer

# How fast the notes roll, in columns a beat, so a sixteenth is one column.
COLUMNS_PER_BEAT = 4
# The columns at the left for the octaves' and the lanes' labels, and the rows the legend and the drum lanes take.
LABEL_COLUMNS = 7
LEGEND_ROWS = 1
DRUM_ROWS = len(MSG_PIANO_ROLL_DRUM_LANES)
# Where the rows centre: how fast the middle eases toward where it is wanted, as a share of the way a second, slowly, and where it starts.
CENTRE_EASE_PER_SECOND = 0.2
START_CENTRE = 60
LOWEST_PITCH = 0
HIGHEST_PITCH = 127
HALF_STEPS_PER_OCTAVE = 12
# The colours: black behind everything, each track's bold colour on it in turn, the attack of a note this much nearer white, the octave lines and labels dim.
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
TRACK_COLOURS = (
    (255, 64, 64), (255, 160, 0), (255, 224, 0), (64, 224, 96), (0, 208, 224), (64, 128, 255), (192, 96, 255), (255, 80, 176), (160, 255, 64), (255, 255, 255),
)
ATTACK_WHITENING = 0.4
LINE_COLOUR = (70, 70, 90)
LABEL_COLOUR = (140, 140, 160)
# What the cells are drawn with: a note's bar, an octave's line, and a blank.
NOTE_CHARACTER = '█'
LINE_CHARACTER = '─'
SPACE = ' '
# Which drum lane each General MIDI drum note goes in, by its place in MSG_PIANO_ROLL_DRUM_LANES; any other goes in the last.
KICK_LANE = 0
SNARE_LANE = 1
HATS_LANE = 2
TOMS_LANE = 3
CYMBAL_LANE = 4
OTHER_LANE = 5
DRUM_LANES = {
    35: KICK_LANE, 36: KICK_LANE, 37: SNARE_LANE, 38: SNARE_LANE, 39: SNARE_LANE, 40: SNARE_LANE, 42: HATS_LANE, 44: HATS_LANE, 46: HATS_LANE,
    41: TOMS_LANE, 43: TOMS_LANE, 45: TOMS_LANE, 47: TOMS_LANE, 48: TOMS_LANE, 50: TOMS_LANE,
    49: CYMBAL_LANE, 51: CYMBAL_LANE, 52: CYMBAL_LANE, 53: CYMBAL_LANE, 55: CYMBAL_LANE, 57: CYMBAL_LANE, 59: CYMBAL_LANE,
}
# The longest a frame may count as, so that a stall doesn't jump the middle.
LONGEST_FRAME_SECONDS = 0.2


def nth_colour(place):
    """Return the colour of the track heard place-th, going round the colours."""
    return TRACK_COLOURS[place % len(TRACK_COLOURS)]


def whitened(*, colour, share):
    """Return a colour that share of the way to white."""
    return tuple(int(channel + (255 - channel) * share) for channel in colour)


def drum_lane(pitch):
    """Return the lane of the drum lanes a drum note goes in, counted from the bottom."""
    return DRUM_LANES.get(pitch, OTHER_LANE)


def is_octave_line(pitch):
    return pitch % HALF_STEPS_PER_OCTAVE == 0


class RolledNote:
    """A note on the roll: its track's place, its pitch, whether it's a drum's, and when it started and ended, its end None while it sounds."""

    __slots__ = ('track', 'pitch', 'drum', 'start', 'end')

    def __init__(self, *, track, pitch, drum, start):
        self.track = track
        self.pitch = pitch
        self.drum = drum
        self.start = start
        self.end = None


class PianoRoll(Visualizer):
    """The notes as bars rolling in from the right, every key a row, each track in its colour, the drums in lanes at the bottom."""

    __slots__ = ('_cells', '_notes', '_centre', '_last', '_seconds_per_beat', '_names', '_heard_tracks', '_lowest', '_highest', '_placed')

    NAME = MSG_PIANO_ROLL
    OPTION = 'piano_roll'

    def __init__(self):
        super().__init__()
        self._cells = CellPainter()
        self._notes = []
        self._centre = float(START_CENTRE)
        self._last = None
        self._seconds_per_beat = SILENCE.seconds_per_beat
        self._names = ()
        # The tracks heard so far, by their places in the song, in the order they were first heard, which gives each its colour.
        self._heard_tracks = []
        # The lowest and highest pitch heard so far, drums apart, None until a note is heard, and whether the rows have been put on the first notes yet.
        self._lowest = None
        self._highest = None
        self._placed = False

    def track_colour(self, track):
        """Return a track's colour, by the order it was first heard in."""
        return nth_colour(self._heard_tracks.index(track))

    def centre(self):
        """Return the pitch the rows centre on now."""
        return self._centre

    def notes(self):
        """Return the notes on the roll."""
        return list(self._notes)

    def frame(self, *, width, height, now, heard=SILENCE):
        if width <= LABEL_COLUMNS or height <= LEGEND_ROWS:
            return []
        elapsed = 0.0 if self._last is None else min(max(now - self._last, 0.0), LONGEST_FRAME_SECONDS)
        self._last = now
        self._seconds_per_beat = heard.seconds_per_beat
        if heard.names:
            self._names = heard.names
        self.hear(heard=heard, now=now)
        columns_per_second = COLUMNS_PER_BEAT / self._seconds_per_beat
        oldest = now - (width - LABEL_COLUMNS) / columns_per_second
        self._notes = [note for note in self._notes if note.end is None or note.end >= oldest]
        drums = any(note.drum for note in self._notes)
        pitch_rows = height - LEGEND_ROWS - (DRUM_ROWS if drums else 0)
        self.follow(elapsed=elapsed, pitch_rows=pitch_rows)
        top = min(max(int(round(self._centre + pitch_rows / 2)), LOWEST_PITCH + pitch_rows - 1), HIGHEST_PITCH)
        characters = [[SPACE] * width for _ in range(height)]
        colours = [[None] * width for _ in range(height)]
        self.draw_grid(characters=characters, colours=colours, top=top, pitch_rows=pitch_rows, drums=drums)
        right = width - 1
        for note in self._notes:
            row = self.row_of(note=note, top=top, pitch_rows=pitch_rows, drums=drums)
            if row is None:
                continue
            start = right - int((now - note.start) * columns_per_second)
            end = right if note.end is None else right - int((now - note.end) * columns_per_second) - 1
            end = max(end, start)
            colour = self.track_colour(note.track)
            for column in range(max(start, LABEL_COLUMNS), min(end, right) + 1):
                characters[row][column] = NOTE_CHARACTER
                colours[row][column] = whitened(colour=colour, share=ATTACK_WHITENING) if column == start else colour
        self.draw_legend(characters=characters, colours=colours, width=width)
        return [self.line(characters=row, colours=colour_row) for row, colour_row in zip(characters, colours)]

    def hear(self, *, heard, now):
        """Start a note for each one heard starting, and end each that is no longer heard."""
        sounding = {(note.track, note.pitch) for note in heard.notes}
        for note in self._notes:
            if note.end is None and (note.track, note.pitch) not in sounding:
                note.end = now
        for note in heard.notes:
            if note.started:
                for older in self._notes:
                    if older.end is None and older.track == note.track and older.pitch == note.pitch:
                        older.end = now
                self._notes.append(RolledNote(track=note.track, pitch=note.pitch, drum=note.drum, start=now))
                if note.track not in self._heard_tracks:
                    self._heard_tracks.append(note.track)
                if not note.drum:
                    self._lowest = note.pitch if self._lowest is None else min(self._lowest, note.pitch)
                    self._highest = note.pitch if self._highest is None else max(self._highest, note.pitch)

    def follow(self, *, elapsed, pitch_rows):
        """Keep the rows still where they can be, the user's rule: on the middle of every pitch heard so far while those fit the rows, and otherwise
        easing slowly toward the middle of the notes that sound now, staying put while none sounds. The first notes heard place the rows at once."""
        if self._lowest is None:
            return
        if self._highest - self._lowest < pitch_rows:
            wanted = (self._lowest + self._highest) / 2
        else:
            sounding = [note.pitch for note in self._notes if note.end is None and not note.drum]
            if not sounding:
                return
            wanted = sum(sounding) / len(sounding)
        if not self._placed:
            self._placed = True
            self._centre = wanted
            return
        self._centre += (wanted - self._centre) * min(CENTRE_EASE_PER_SECOND * elapsed, 1.0)

    @staticmethod
    def row_of(*, note, top, pitch_rows, drums):
        """Return the row a note is drawn on: its pitch's below the legend, or its lane's among the drum rows at the bottom, or None off the rows shown."""
        if note.drum:
            return LEGEND_ROWS + pitch_rows + DRUM_ROWS - 1 - drum_lane(note.pitch) if drums else None
        row = LEGEND_ROWS + top - note.pitch
        return row if LEGEND_ROWS <= row < LEGEND_ROWS + pitch_rows else None

    @staticmethod
    def draw_grid(*, characters, colours, top, pitch_rows, drums):
        """Draw a line along each C with its label at the left, and the drum lanes' labels."""
        width = len(characters[0])
        for offset in range(pitch_rows):
            pitch = top - offset
            row = LEGEND_ROWS + offset
            if is_octave_line(pitch):
                label = MSG_PIANO_ROLL_OCTAVE_LABEL.format(octave=pitch // HALF_STEPS_PER_OCTAVE - LIVE_OCTAVE_OFFSET)
                for column in range(width):
                    characters[row][column] = label[column] if column < len(label) else LINE_CHARACTER
                    colours[row][column] = LABEL_COLOUR if column < len(label) else LINE_COLOUR
        if drums:
            for lane, label in enumerate(MSG_PIANO_ROLL_DRUM_LANES):
                row = LEGEND_ROWS + pitch_rows + DRUM_ROWS - 1 - lane
                for column, character in enumerate(label[:LABEL_COLUMNS - 1]):
                    characters[row][column] = character
                    colours[row][column] = LABEL_COLOUR

    def draw_legend(self, *, characters, colours, width):
        """Draw the name of each track with a note on the roll now, in its colour, across the top, in the order of the song's tracks, as far as they fit (the user's rule)."""
        column = LABEL_COLUMNS
        for track in sorted({note.track for note in self._notes}):
            if track >= len(self._names):
                continue
            text = MSG_PIANO_ROLL_LEGEND_MARK + self._names[track]
            if column + len(text) > width:
                break
            for offset, character in enumerate(text):
                characters[0][column + offset] = character
                colours[0][column + offset] = self.track_colour(track)
            column += len(text) + len(MSG_PIANO_ROLL_LEGEND_GAP)

    def line(self, *, characters, colours):
        """Return a row of cells as text, each in its colour on black, a blank cell black."""
        styles = [self._cells.style_of(colour=colour or BLACK, background=BLACK) for colour in colours]
        return self._cells.line(characters=characters, styles=styles)
