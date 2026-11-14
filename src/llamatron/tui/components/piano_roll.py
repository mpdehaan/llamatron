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
"""The piano roll, the pattern editor's first page: one row per note of the scale across the octaves, with notes as bars.

The user's design of 2026-11-08: the roll is the interface music people expect, and everything it
does maps onto the pattern's rows, so the rows under P show exactly what was painted. A pitch
is a row, counted from the bottom as octave times the scale's size plus the degree's place, so a
sharpened or flattened note stays on its degree's row with the symbol drawn inside its bar. A note
of the entry size is written as a degree on its step and a tie on each step it covers after it,
never a gate, except an entry size shorter than a step, the one case that writes a gate. There is
one mode, the user's decision of 2026-11-08 after a join method was tried: Space is the pencil,
which draws on an empty cell, takes out a note already at the cursor's pitch as Bksp does (the
user's choice of 2026-11-09, so that Space on a note turns the note off) and cuts a note at another
pitch, whose rest carries on after; Shift+Left and Shift+Right drag a note's end; K is the knife and Bksp the
eraser. The roll holds the cursor's pitch and the keys; RollDrawing draws it. It knows nothing of
Textual.
"""

import functools

from llamatron.composition.file_format import ACCIDENTALS, STEP_SIZE_CHOICES, Accidental, Row
from llamatron.composition.limits import MAX_OCTAVE, MIN_DEGREE, MIN_OCTAVE
from llamatron.tui.components.chord_row import pick_chord
from llamatron.tui.components.degree_row import GAUGE_ROWS_WITHOUT_SCALE
from llamatron.music.midi import HALF_STEPS_PER_OCTAVE
from llamatron.music.note import ROOT_NAMES
from llamatron.tui.drawing import NOTHING
from llamatron.tui.key_table import STEP_BACK, STEP_FORWARD, cursor_moved, BindsKeys
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.keys import Key
from llamatron.strings.errors import (
    ERR_NO_NOTE_HERE, ERR_NO_ROOM_AFTER, ERR_NOTE_IS_ONE_STEP, ERR_NOTHING_TO_SPLIT,
)
from llamatron.strings.labels import MSG_ENTRY_SIZE_LABEL, MSG_ROLL_ROW_LABEL, MSG_SONG_ENTRY_SIZE_CHOICE
from llamatron.strings.marks import MSG_ROLL_OCTAVE_ONLY
from llamatron.tui import keybindings

# A natural note has no symbol in its bar.
NO_ACCIDENTAL = None


def on_a_note(method):
    """Mark a key of the roll as one that works on the note under the cursor, from any of the cells the note covers.

    The method is written to take start, the step the note starts on, and is called without it:
    the note under the cursor is found first. With no note there, the status line says so and
    the method isn't called. The knife isn't marked, since it has its own sentence for an empty
    cell.
    """
    @functools.wraps(method)
    def on_the_note(self):
        start = self.note_here()
        if start is None:
            self.editor.refuse(ERR_NO_NOTE_HERE)
            return
        method(self, start)
    return on_the_note


class PianoRoll(BindsKeys):
    """The roll's cursor, its mapping between rows and notes, and its keys, which read and write the pattern through the editor's document."""

    KEYS = keybindings.PianoRoll

    __slots__ = ('editor', 'drawing', 'pitch', 'top_pitch')

    def __init__(self, *, editor, drawing):
        self.editor = editor
        # What draws the roll, which the editor asks for when the roll is showing.
        self.drawing = drawing
        # The cursor's row, as a pitch counted from the bottom, placed when the roll is first shown; the drawing keeps top_pitch, its first row.
        self.pitch = None
        self.top_pitch = None

    def remembered(self, *, key, compute):
        """Return an answer about the pattern on the roll, worked out by compute the first time it's asked since the set last changed.

        The answers are kept in the document's one memory, under the pattern's name, since drawing
        asks for the same things for every row and cell. They come from the pattern, its scale and
        the tracks that play it, so they're kept on the whole document.
        """
        document = self.document()
        return document.remembered(key=(PianoRoll.__name__, self.name(), key), on=(document,), compute=compute)

    def document(self):
        return self.editor.document()

    def name(self):
        return self.editor.item

    # Rows and pitches.

    def scale_name(self):
        """Return the one scale the pattern plays under, or None when its uses disagree or nothing says."""
        return self.remembered(key=PianoRoll.scale_name.__name__, compute=lambda: self.document().pattern_scale(self.name()))

    def size(self):
        """Return how many rows an octave has: the scale's notes, or room for the largest scale the pattern can play in."""
        return self.remembered(key=PianoRoll.size.__name__, compute=self._size)

    def _size(self):
        scale = self.scale_name()
        if scale is not None:
            return self.document().scale_size(scale)
        return max(self.document().degree_limit(self.name()), GAUGE_ROWS_WITHOUT_SCALE)

    def per_octave(self):
        """Return how many pitches an octave has: twelve half steps when the scale is known, so that a sharp or flat has a row between two degrees, and otherwise one per row."""
        return HALF_STEPS_PER_OCTAVE if self.scale_name() is not None else self.size()

    def scale_steps(self):
        """Return the pitches within an octave that are the scale's degrees, in degree order: its half steps, or every pitch when the scale isn't known."""
        return self.remembered(key=PianoRoll.scale_steps.__name__, compute=self._scale_steps)

    def _scale_steps(self):
        scale = self.scale_name()
        if scale is None:
            return tuple(range(self.size()))
        return self.document().scale_half_steps(scale)

    def highest_pitch(self):
        return (MAX_OCTAVE + 1) * self.per_octave() - 1

    def pitch_of(self, step):
        """Return the row of a step's note, a degree past the scale's size carried into the next octave and a sharp or flat a pitch up or down, or None on a rest."""
        return self.remembered(key=(PianoRoll.pitch_of.__name__, step), compute=lambda: self._pitch_of(step))

    def note_span(self, step):
        """Return how many steps the note on a step covers, which the document works out from its ties and gate."""
        return self.remembered(key=(PianoRoll.note_span.__name__, step), compute=lambda: self.document().note_span(name=self.name(), step=step))

    def partial_cell(self, step):
        """Return what part of a note's last cell its gate fills, or None for a full cell, as the document works it out."""
        return self.remembered(key=(PianoRoll.partial_cell.__name__, step), compute=lambda: self.document().partial_cell(name=self.name(), step=step))

    def _pitch_of(self, step):
        degree = self.document().step_value(name=self.name(), row=Row.DEGREE, step=step)
        if degree is None:
            if not self.document().step_value(name=self.name(), row=Row.GRAB, step=step):
                return None
            # A file can mark a grab on a step with no note of its own, which the roll shows on the root, where marking it from the rows would put it.
            degree = MIN_DEGREE
        octaves_up, place = divmod(degree - MIN_DEGREE, self.size())
        pitch = (self.step_octave(step) + octaves_up) * self.per_octave() + self.scale_steps()[place]
        if self.scale_name() is not None:
            pitch += ACCIDENTALS.get(self.accidental_symbol(step), 0)
        return self.clamped(pitch)

    def is_degree(self, pitch):
        """Return whether a row is one of the scale's degrees, rather than a row between two of them for a sharp or flat."""
        return pitch % self.per_octave() in self.scale_steps()

    def note_at(self, pitch):
        """Return the degree, octave and accidental a row writes.

        A row between two degrees is the degree below sharpened, or the degree above flattened
        when the scale's root is spelled with flats or when the row is a whole step above the
        degree below, as in a pentatonic scale's wider gaps.
        """
        steps = self.scale_steps()
        octave, within = divmod(pitch, self.per_octave())
        if within in steps:
            return steps.index(within) + MIN_DEGREE, octave, NO_ACCIDENTAL
        below = max(index for index, step in enumerate(steps) if step < within)
        above = steps[below + 1] if below + 1 < len(steps) else self.per_octave()
        flats = self.document().scale_spells_flats(self.scale_name())
        if within - steps[below] == 1 and not (flats and above - within == 1):
            return below + MIN_DEGREE, octave, Accidental.SHARP
        octaves_more, place = divmod(below + 1, len(steps))
        return place + MIN_DEGREE, octave + octaves_more, Accidental.FLAT

    def clamped(self, pitch):
        return max(min(pitch, self.highest_pitch()), 0)

    def rows(self):
        """Return every row the roll has, highest first: a row per degree of every octave, and a row between two degrees wherever a note or a chord's note of this pattern is sharp or flat.

        Rows for sharps and flats exist only while something is on them, the user's choice of
        2026-11-08, so that a pattern that stays in its scale looks like a scale and the cursor can
        only reach a pitch outside the scale that a note already has.
        """
        return self.remembered(key=PianoRoll.rows.__name__, compute=self._rows)

    def _rows(self):
        per = self.per_octave()
        pitches = {octave * per + step for octave in range(MAX_OCTAVE + 1) for step in self.scale_steps()}
        for start in self.editor.pattern().get_note_steps():
            pitches.add(self.pitch_of(start))
            pitches |= self.ghost_pitches(start)
        return sorted(pitches, reverse=True)

    def snapped(self, pitch):
        """Return the row at a pitch, or the nearest row below it when its row for a sharp or flat has gone, or the lowest row."""
        rows = self.rows()
        below = [row for row in rows if row <= pitch]
        return below[0] if below else rows[-1]

    def row_label(self, pitch):
        """Return a row's label: the note's name and octave with its degree, the name alone on a row between two degrees, or the octave alone when the scale isn't known."""
        return self.remembered(key=(PianoRoll.row_label.__name__, pitch), compute=lambda: self._row_label(pitch))

    def _row_label(self, pitch):
        degree, octave, accidental = self.note_at(pitch)
        song = self.document().song()
        scale = self.scale_name()
        if scale is None:
            return MSG_ROLL_ROW_LABEL.format(note=MSG_ROLL_OCTAVE_ONLY.format(octave=song.shown_octave(octave)), degree=degree)
        if accidental is not NO_ACCIDENTAL:
            name, sounding = self.document().scale_note_at(name=scale, octave=octave, half_steps=pitch % self.per_octave())
            return MSG_ROLL_ROW_LABEL.format(note=name + str(song.shown_octave(sounding)), degree=NOTHING).rstrip()
        place = degree - MIN_DEGREE
        sounding = self.document().scale_degree_octave(name=scale, octave=octave, place=place)
        return MSG_ROLL_ROW_LABEL.format(note=self.document().scale_note_names(scale)[place] + str(song.shown_octave(sounding)), degree=degree)

    def widest_row_label(self):
        """Return how wide a row's label can be, from the label's parts at their widest: the widest note name with the widest octave label, or the octave alone, and the largest degree.

        The width is worked out from the parts rather than from a row because a row's label needs a note that exists, and the top row's may not while a degree past the scale's top is being typed.
        """
        song = self.document().song()
        octave = max((str(song.shown_octave(number)) for number in (MIN_OCTAVE, MAX_OCTAVE)), key=len)
        notes = [MSG_ROLL_OCTAVE_ONLY.format(octave=octave), *[name + octave for name in ROOT_NAMES]]
        return max(len(MSG_ROLL_ROW_LABEL.format(note=note, degree=self.size())) for note in notes)

    def starts_an_octave(self, pitch):
        """Return whether a row is the first degree of its octave, under which a rule is drawn."""
        return pitch % self.per_octave() == 0

    def in_range(self, pitch):
        """Return whether a row is within the octaves of the one track that plays the pattern, which is always so when no one track does."""
        octaves = self.document().pattern_octave_range(self.name())
        if octaves is None:
            return True
        lowest, highest = octaves
        return lowest <= pitch // self.per_octave() <= highest

    def accidental_symbol(self, step):
        """Return the symbol drawn inside a note's bar, a sharp or a flat, or None for a natural."""
        symbol = self.document().step_value(name=self.name(), row=Row.ACCIDENTAL, step=step)
        return symbol if symbol in (Accidental.SHARP, Accidental.FLAT) else NO_ACCIDENTAL

    def step_octave(self, step):
        """Return the octave a step's note is in: its own, or the pattern's default."""
        octave = self.document().step_value(name=self.name(), row=Row.OCTAVE, step=step)
        return self.editor.default_octave() if octave is None else octave

    def ghost_pitches(self, step):
        """Return the rows of the notes a step's chord adds above its own note, for the thin lines the roll draws them as.

        A step that grabs has none: its chord is built on whatever note the grab takes, which
        the roll can't know, so the note's G is all the roll shows, as the user chose.
        """
        ghosts = set()
        if self.grabs(step):
            return ghosts
        for degree, octave, accidental in self.document().chord_tones(name=self.name(), step=step, octave=self.step_octave(step)):
            octaves_up, place = divmod(degree - MIN_DEGREE, self.size())
            pitch = (octave + octaves_up) * self.per_octave() + self.scale_steps()[place]
            if self.scale_name() is not None:
                pitch += ACCIDENTALS.get(accidental, 0)
            if 0 <= pitch <= self.highest_pitch():
                ghosts.add(pitch)
        return ghosts

    def grabs(self, step):
        """Return whether a step takes its note from the clip's grab track, which the roll marks with G in place of the accidental."""
        return bool(self.document().step_value(name=self.name(), row=Row.GRAB, step=step))

    # The cursor.

    def place_cursor(self):
        """Put the cursor on the pattern's first note, or on the root in the default octave, the first time the roll is shown, and keep it on the rows."""
        if self.pitch is None:
            steps = self.editor.pattern().get_note_steps()
            self.pitch = self.pitch_of(steps[0]) if steps else self.editor.default_octave() * self.per_octave()
        self.pitch = self.snapped(self.clamped(self.pitch))

    def covering(self):
        """Return the step of the note sounding through each step, by step, which the document keeps until the set changes."""
        return self.document().covering_notes(self.name())

    def note_here(self):
        """Return the step of the note under the cursor, at its pitch, or None."""
        start = self.covering().get(self.editor.step)
        if start is not None and self.pitch_of(start) == self.pitch:
            return start
        return None

    # What the editor asks of whichever view is showing.

    def other_view_binding(self):
        """Return the editor's binding for Tab from here, which goes to the rows."""
        return keybindings.PatternEditor.TO_EDITOR

    def other_view_what(self):
        """Return what Tab does from here, for the legend."""
        _, _, what = self.other_view_binding()
        return what

    def step_keys(self, *, can_remove):
        """Return no keys: the roll neither inserts nor removes a step, the user's rule, as Live's piano roll never did; the rows view does both."""
        return []

    def lists_step_keys(self):
        """Return False, since the roll has no keys that insert or remove a step."""
        return False

    def takes_note_letters(self):
        """Return whether letters type notes where the cursor is, which they never do on the roll."""
        return False

    def move_keys(self):
        """Return the keys that move the cursor, which the editor lists after Esc: the arrows, and the ends, which only the F1 dialog names."""
        self.place_cursor()
        return [
            self.bind(self.KEYS.MOVE, action=self.move, wants_key=True),
            self.bind(self.KEYS.ENDS, action=self.editor.jump_end),
        ]

    def keys(self):
        """Return the roll's own keys, which the editor lists last."""
        self.place_cursor()
        return [
            self.bind(self.KEYS.PLACE, action=self.place_or_erase),
            self.bind(self.KEYS.CHORD, action=self.pick_chord),
            self.bind(self.KEYS.SHORTER, action=lambda: self.drag(STEP_BACK)),
            self.bind(self.KEYS.LONGER, action=lambda: self.drag(STEP_FORWARD)),
            self.bind(self.KEYS.KNIFE, action=self.split),
            self.bind(self.KEYS.ACCIDENTAL, action=self.cycle_accidental),
            self.bind(self.KEYS.ERASE, action=self.erase),
            self.bind(self.KEYS.GRAB, action=self.toggle_grab),
            self.bind(self.KEYS.ENTRY_SIZE, action=self.pick_entry_size),
        ]

    def drag(self, direction):
        """Drag the end of the note under the cursor a step later, which ] does, or a step earlier, which [ does."""
        if direction == STEP_FORWARD:
            self.lengthen()
        else:
            self.shorten()

    def move(self, name):
        """Move a step along or a row up or down, stopping at every edge like every cursor."""
        editor = self.editor
        if name in (Key.UP, Key.DOWN):
            rows = self.rows()
            self.pitch = rows[cursor_moved(place=rows.index(self.pitch), name=name, count=len(rows))]
        else:
            editor.step = cursor_moved(place=editor.step, name=name, count=editor.steps())

    def place_or_erase(self):
        """Draw a note of the entry size at the cursor, or take out the note already under the cursor, from any of the cells the note covers, exactly as Bksp does."""
        if self.note_here() is not None:
            self.erase()
            return
        degree, octave, accidental = self.note_at(self.pitch)
        self.document().place_note(name=self.name(), step=self.editor.step, degree=degree, octave=octave, accidental=accidental)

    @on_a_note
    def pick_chord(self, start):
        """Open the Chord dialog on the note under the cursor, a single note among the qualities, so that a note becomes a chord or a chord a note again."""
        pick_chord(editor=self.editor, step=start)

    def split(self):
        """Split the note under the cursor at the cursor's step, which has to be one of the steps it holds, not its first."""
        start = self.note_here()
        if start is None or start == self.editor.step:
            self.editor.refuse(ERR_NOTHING_TO_SPLIT)
            return
        self.document().split_note(name=self.name(), step=self.editor.step)

    @on_a_note
    def lengthen(self, start):
        if not self.document().lengthen_note(name=self.name(), step=start):
            self.editor.refuse(ERR_NO_ROOM_AFTER)

    @on_a_note
    def shorten(self, start):
        if not self.document().shorten_note(name=self.name(), step=start):
            self.editor.refuse(ERR_NOTE_IS_ONE_STEP)

    @on_a_note
    def cycle_accidental(self, start):
        """Move the note under the cursor on to the next of natural, sharp and flat, and follow it to its new row, which may be a row of its own between two degrees."""
        self.document().cycle_accidental(name=self.name(), step=start)
        self.pitch = self.pitch_of(start)

    @on_a_note
    def toggle_grab(self, start):
        """Mark the note under the cursor to take its note from the clip's grab track, or unmark it."""
        self.document().set_step_value(name=self.name(), row=Row.GRAB, step=start, value=not self.grabs(start))

    @on_a_note
    def erase(self, start):
        """Take out the note under the cursor with the ties that held it."""
        self.document().clear_sound(name=self.name(), step=start)

    def pick_entry_size(self):
        """Open a picker of the pattern's entry size: the song's first, then the step sizes, on what the pattern has now."""
        choices = [None, *STEP_SIZE_CHOICES]
        written = self.document().written_entry_size(self.name())
        place = choices.index(written) if written in choices else 0
        self.editor.ask(
            dialog=ChoiceDialog(title=MSG_ENTRY_SIZE_LABEL, options=[MSG_SONG_ENTRY_SIZE_CHOICE, *STEP_SIZE_CHOICES], current=place),
            then=lambda chosen: self.document().set_pattern_entry_size(name=self.name(), entry_size=choices[chosen]),
        )
