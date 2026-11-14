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

"""The pattern editor: a grid of steps that's already drawn, with one row per kind of value.

The grid's size comes from the pattern's step count, and typing never changes it or moves the
cursor. Every step lasts the pattern's step size. A step with a note sounds for its gate, which
can run on past later steps, up to the end of the pattern, and a step with no note is a rest. A
pattern wider than the screen scrolls sideways as the cursor moves, rather than wrapping onto more
blocks, as the user chose, so that a bar is always one row of columns.

The editor shows one of two views, each a component with its own cursor, keys and drawing:
PatternRows (tui/components/pattern_rows.py), the rows, and PianoRoll. The editor keeps what
they share: the cursor's step, the keys that work in both, and the edits to the whole pattern.
Each row of the grid is an object from tui/components, built once per row name, which says what
its cells show and what its keys do when the cursor is on it. The Degree row is a gauge, and
the pinned rows (the gauge with its number, and the octave under it) stay at the top while the
rows beneath scroll. Those rows come in sections, the user's design of 2026-11-08 in place of sets
of rows that Tab cycled through: each section is headed by a row of the grid (SectionRow) that
Space or Enter opens or closes, PgUp and PgDn jump between the headings, and which sections
are open is kept on the app for the session.

A pattern that isn't drums opens on the piano roll (tui/components/piano_roll.py, drawn by
RollDrawing), and Tab switches between the roll and the rows; drum patterns have no roll and open
on the rows.
"""


from llamatron.composition.checks import is_written_length
from llamatron.composition.file_format import DIRECTIONS, Row, Section
from llamatron.composition.limits import MAX_STEP_SIZE, MAX_STEPS, MIN_STEPS
from llamatron.tui.components.chord_row import step_chord_in_words
from llamatron.tui.components.pattern_rows import PatternRows
from llamatron.tui.components.piano_roll import PianoRoll
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.screens.listening import pattern_listen_keys
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.screens.shows_named_item import ShowsNamedItem
from llamatron.tui.drawing import NOTHING
from llamatron.tui.key_table import STEP_BACK
from llamatron.tui.screens.pattern_drawing import PatternDrawing
from llamatron.tui.screens.roll_drawing import RollDrawing
from llamatron.tui.screens.shared import ask_time_signature, columns
from llamatron.tui.screens.step_editor import StepEditor
from llamatron.composition.checks import fraction_text
from llamatron.composition.naming import words
from llamatron.tui.text import fraction, sorted_names
from llamatron.strings.errors import (
    ERR_LENGTH_OUT_OF_RANGE, ERR_NO_OTHER_PATTERNS, ERR_NOT_A_LENGTH, ERR_TYPED_NOT_AN_INTEGER, ERR_NOTHING_AFTER,
    ERR_NOTHING_BEFORE, ERR_NOTHING_TO_PIVOT, ERR_ONE_STEP, ERR_STEPS_OUT_OF_RANGE,
)
from llamatron.strings.help import HELP_PATTERN_EDITOR
from llamatron.strings.labels import Crumb, MSG_DIRECTION_NAMES, MSG_MUNGE_CHOICES, MSG_PATTERN_CRUMB
from llamatron.strings.legends import (
    MSG_DEGREES_WHAT, MSG_DIRECTION_WHAT, MSG_DRUM_OFF_WHAT, MSG_DRUM_ON_WHAT, MSG_LETTERS_WHAT, MSG_LOAD_OVER_WHAT, MSG_STEP_SIZE_WHAT,
    MSG_TIME_SIGNATURE_WHAT, What,
)
from llamatron.strings.messages import MSG_RESTING_STEP
from llamatron.strings.messages import (
    MSG_CHANGE_TYPE_EMPTY_QUESTION, MSG_CHANGE_TYPE_QUESTION, MSG_CHANGE_TYPE_TITLE, MSG_LOAD_OVER_CHOICE_TITLE, MSG_LOAD_OVER_QUESTION,
    MSG_LOAD_OVER_TITLE, MSG_PLAY_DIRECTION_TITLE, MSG_RENAME_PATTERN_PROMPT, MSG_RECONFIGURE_TITLE, MSG_SHORTEN_QUESTION,
    MSG_SHORTEN_TITLE, MSG_STEP_SIZE_PROMPT, MSG_TIME_SIGNATURE_PROMPT, MSG_STEPS_PROMPT, MSG_MUNGE_TITLE,
)
from llamatron.tui import keybindings


def direction_choices(directions):
    """Return each direction as words beside what it does, lined up for a picker."""
    return columns([(words(name), MSG_DIRECTION_NAMES[name]) for name in directions])


class Munge:
    """The munge dialog's choices, in the order of MSG_MUNGE_CHOICES."""

    REVERSE_AFTER = 0
    REVERSE_BEFORE = 1
    REVERSE = 2
    PIVOT = 3
    RANDOMIZE = 4


class Reconfigure:
    """The Reconfigure dialog's choices, in the order reconfigure_choices lists them: the whole-pattern actions that R gathers, as the user asked on 2026-11-08, so that the legend stays short."""

    MUNGE = 0
    LOAD_OVER = 1
    STEP_SIZE = 2
    TIME_SIGNATURE = 3
    DRUM = 4
    DIRECTION = 5
    RENAME = 6


def reconfigure_choices(*, drum):
    """Return the Reconfigure dialog's options, in the order of the Reconfigure class, with the drum entry saying which way it switches."""
    return [What.MUNGE, MSG_LOAD_OVER_WHAT, MSG_STEP_SIZE_WHAT, MSG_TIME_SIGNATURE_WHAT, MSG_DRUM_OFF_WHAT if drum else MSG_DRUM_ON_WHAT, MSG_DIRECTION_WHAT, What.RENAME]


class PatternEditor(ShowsNamedItem, StepEditor):

    KEYS = keybindings.PatternEditor
    HELP = HELP_PATTERN_EDITOR
    SECTION = Section.PATTERNS
    CRUMBS_BEFORE = (Crumb.PATTERNS,)
    RENAME_PROMPT = MSG_RENAME_PATTERN_PROMPT

    def __init__(self, *, holder, name, opened_from=None):
        super().__init__(holder)
        # The page a clip opened the editor from, Arrange or the clip page, whose crumbs come first in the editor's, so that the crumbs
        # say where Esc goes back to (the user's choice of 2026-11-09). None when the Patterns page opened it, whose crumbs are the editor's own.
        self.opened_from = opened_from
        self.show_item(name)
        # The cursor's step and the window of steps, which StepEditor keeps, are shared by the two views.
        # The two views, each with its own cursor and keys, and what draws each: the rows, and the piano roll.
        self.drawing = PatternDrawing(self)
        self.rows_view = PatternRows(editor=self, drawing=self.drawing)
        self.roll_drawing = RollDrawing(self)
        self.roll = PianoRoll(editor=self, drawing=self.roll_drawing)

    def label_width(self):
        """Return the label column's width, one for both views: the wider of the rows' and the roll's, so that the step columns stay put when Tab switches views."""
        widths = [self.drawing.widest_label()]
        if self.has_roll():
            widths.append(self.roll_drawing.widest_label())
        return max(widths)

    def crumb_trail(self):
        """Return the crumbs: the opener's and then this pattern's, when a clip opened the editor, and PATTERNS and the name otherwise."""
        if self.opened_from is None:
            return self.crumbs
        return (*self.opened_from.crumb_trail(), MSG_PATTERN_CRUMB.format(name=self.item))

    def duration(self):
        return self.document().lengths().pattern_seconds(self.item)

    # What's under the cursor.

    def pattern(self):
        return self.document().song().get_pattern(self.item)

    def is_drum(self):
        return self.pattern().is_drum()

    def default_octave(self):
        """Return the octave a step of this pattern starts on when it has none: the song's drum or note default."""
        song = self.document().song()
        return song.get_default_drum_octave() if self.is_drum() else song.get_default_octave()

    def row_for(self, name):
        """Return the row object for a row name, which the rows keep: the rows ask each other through the editor, as the gate asks the dot."""
        return self.rows_view.row_for(name)

    def row_name(self):
        """Return the name of the row the rows' cursor is on, which a row's edit of the cursor's cell is written to."""
        return self.rows_view.row_name()

    # The two views.

    def has_roll(self):
        """Return whether this pattern can show the piano roll: a drum pattern can't, since drums have no pitch rows."""
        return not self.is_drum()

    def on_roll(self):
        """Return whether the roll is showing over the rows: P opens and closes it, and the choice is kept for the session."""
        return self.has_roll() and self.holder.on_roll

    def toggle_roll(self):
        self.holder.on_roll = not self.holder.on_roll

    def view(self):
        """Return the view that's showing, the piano roll or the rows: each has its cursor, its keys and its drawing, so that nothing else asks which is showing."""
        return self.roll if self.on_roll() else self.rows_view

    def value(self, *, row=None, step=None):
        return self.document().step_value(name=self.item, row=row or self.row_name(), step=self.step if step is None else step)

    def is_note(self, *, step=None):
        """Return whether a step plays something: a degree, or a grab, which opens the note rows on the step too."""
        return self.pattern().has_sound(self.step if step is None else step)

    def steps(self):
        return self.pattern().get_steps()

    def clamp(self):
        self.keep_step()
        self.rows_view.clamp()

    def set_value(self, *, value, row=None, step=None):
        self.document().set_step_value(name=self.item, row=row or self.row_name(), step=self.step if step is None else step, value=value)

    def known_scale(self):
        """Return the scale the pattern is known to play under, as a NamedScale: the first of its uses' scales, or the current song's when nothing uses it, or None when there is none or it is a drum pattern."""
        if self.is_drum():
            return None
        names = self.document().scales_of_pattern(self.item)
        return self.document().song().get_named_scale(names[0]) if names else None

    def resting_status(self):
        """Say the chord under the cursor, in the scale the pattern is known to play under, while the cursor rests on a step that holds one (the user's design)."""
        self.clamp()
        if self.is_drum() or not self.is_note() or not isinstance(self.value(row=Row.DEGREE), int):
            return NOTHING
        return step_chord_in_words(editor=self, step=self.step).resting(where=MSG_RESTING_STEP.format(step=self.step + 1))

    def gate_now(self, *, step=None):
        """Return a step's gate before its Dot row, which is one step if it has none."""
        return self.row_for(Row.GATE).gate_now(step=step)

    def gate_is_overridden(self):
        """Return whether the cursor's step has a gate of its own that the ties after it override, since ties win over the gate."""
        return self.value(row=Row.GATE) is not None and self.row_for(Row.TIE).tied(step=self.step + 1)

    def cell_text(self, *, name, step):
        """Return what one cell shows, which the row for it decides."""
        return self.row_for(name).cell_text(step=step)

    # The keys, which depend on the row.

    def keys(self):
        """Return the keys in the legend's order: Esc, the view's arrows, the keys every view has, and last the view's own, which on the rows come and go with the cursor."""
        self.clamp()
        view = self.view()
        result = [self.bind(self.KEYS.BACK, action=self.go_back), *view.move_keys()]
        if self.has_roll():
            result.append(self.bind(view.other_view_binding(), action=self.toggle_roll))
        # The view binds I and D, since the rows' legend lists them and the roll's keeps to drawing. On a drum pattern's Note row, the letter D is a note.
        result += view.step_keys(can_remove=self.steps() > 1 and not view.takes_note_letters())
        result += [
            self.bind(self.KEYS.RESIZE, action=self.ask_steps),
            self.bind(self.KEYS.RECONFIGURE, action=self.reconfigure),
            self.bind(self.KEYS.RENAME, action=self.rename),
            *pattern_listen_keys(page=self, pattern=self.item),
        ]
        return result + view.keys()

    def playing_step(self):
        """Return the step of the pattern that sounds now, in its preview or else in a clip of the song that plays, for the piano roll's read head, or None."""
        step = self.app.pattern_preview().playing_step(self.item)
        return self.app.transport.playing_step(self.item) if step is None else step

    def reconfigure(self):
        """Offer the whole-pattern actions in one dialog, and run the chosen one, which may ask on in a dialog of its own."""
        self.ask(dialog=ChoiceDialog(title=MSG_RECONFIGURE_TITLE, options=reconfigure_choices(drum=self.is_drum())), then=self.reconfigure_as)

    def reconfigure_as(self, choice):
        actions = {
            Reconfigure.MUNGE: self.munge,
            Reconfigure.LOAD_OVER: self.load_over,
            Reconfigure.STEP_SIZE: self.ask_step_size,
            Reconfigure.TIME_SIGNATURE: self.ask_time_signature,
            Reconfigure.DRUM: self.toggle_drum,
            Reconfigure.DIRECTION: self.pick_direction,
            Reconfigure.RENAME: self.rename,
        }
        actions[choice]()

    # Moving along the steps, which both views do.

    def jump_end(self, direction):
        """Go to the first step, which Home does, or the last, which End does."""
        self.step = 0 if direction == STEP_BACK else self.steps() - 1

    # What the rows share when they edit a step.

    def fill_in(self):
        """Give a new note what every note has: an octave, and no tie, since a tie only holds the note before it. Its gate starts blank, which is one step."""
        if self.value(row=Row.TIE):
            self.set_value(value=False, row=Row.TIE)
        if self.value(row=Row.OCTAVE) is None:
            self.set_value(value=self.default_octave(), row=Row.OCTAVE)

    def ask_length(self, *, title, current, most, then, blank_allowed):
        """Ask for a length, a whole number or a fraction like 5/16, and pass it on if it's in range."""
        def answered(text):
            text = text.strip()
            if not text and blank_allowed:
                then(None)
                return
            if not is_written_length(text) or not 0 < fraction(text) <= most:
                self.refuse(ERR_LENGTH_OUT_OF_RANGE.format(most=most) if is_written_length(text) else ERR_NOT_A_LENGTH.format(text=text))
                return
            then(fraction_text(fraction(text)))
        self.ask(dialog=PromptDialog(title=title, value=current), then=answered)

    # The pattern's own settings.

    def ask_step_size(self):
        current = self.pattern().get_written_step_size() or NOTHING
        self.ask_length(title=MSG_STEP_SIZE_PROMPT, current=current, most=MAX_STEP_SIZE, then=lambda text: self.document().set_step_size(name=self.item, step_size=text), blank_allowed=True)

    def ask_time_signature(self):
        current = self.pattern().get_written_time_signature() or NOTHING
        ask_time_signature(
            page=self, title=MSG_TIME_SIGNATURE_PROMPT, current=current, blank_allowed=True,
            then=lambda text: self.document().set_pattern_time_signature(name=self.item, time_signature=text),
        )

    def pick_direction(self):
        current = self.pattern().get_direction()
        self.ask(
            dialog=ChoiceDialog(title=MSG_PLAY_DIRECTION_TITLE, options=direction_choices(DIRECTIONS), current=DIRECTIONS.index(current)),
            then=lambda chosen: self.document().set_direction(name=self.item, direction=DIRECTIONS[chosen]),
        )

    def munge(self):
        """Offer the ways of rearranging the steps around the cursor, and do the chosen one."""
        self.ask(dialog=ChoiceDialog(title=MSG_MUNGE_TITLE, options=MSG_MUNGE_CHOICES), then=self.munge_as)

    def munge_as(self, choice):
        """Rearrange the steps one way, with the cursor staying on its step, so that choosing the same way again undoes it."""
        name = self.item
        if choice == Munge.REVERSE_AFTER:
            if self.step >= self.steps() - 1:
                self.refuse(ERR_NOTHING_AFTER)
                return
            self.document().reverse_after(name=name, step=self.step)
        elif choice == Munge.REVERSE_BEFORE:
            if self.step == 0:
                self.refuse(ERR_NOTHING_BEFORE)
                return
            self.document().reverse_before(name=name, step=self.step)
        elif choice == Munge.REVERSE:
            if self.steps() < 2:
                self.refuse(ERR_ONE_STEP)
                return
            self.document().reverse_steps(name)
        elif choice == Munge.PIVOT:
            if self.steps() < 2:
                self.refuse(ERR_NOTHING_TO_PIVOT)
                return
            self.step = self.document().pivot_around(name=name, step=self.step)
        elif choice == Munge.RANDOMIZE:
            if self.steps() < 2:
                self.refuse(ERR_ONE_STEP)
                return
            self.document().shuffle_steps(name)

    def load_over(self):
        others = sorted_names(name for name in self.document().song().get_pattern_names() if name != self.item)
        if not others:
            self.refuse(ERR_NO_OTHER_PATTERNS)
            return

        def load(name):
            self.document().load_over(name=self.item, other=name)
            self.rows_view.go_to_top()
            self.clamp()

        def chosen(place):
            name = others[place]
            if self.document().has_notes(self.item):
                question = MSG_LOAD_OVER_QUESTION.format(name=self.item, other=name)
                self.ask(dialog=ConfirmDialog(title=MSG_LOAD_OVER_TITLE, messages=[question]), then=lambda _: load(name))
            else:
                load(name)
        self.ask(dialog=ChoiceDialog(title=MSG_LOAD_OVER_CHOICE_TITLE.format(name=self.item), options=others), then=chosen)

    # The whole pattern.

    def ask_steps(self):
        def answered(text):
            try:
                steps = int(text.strip())
            except ValueError:
                self.refuse(ERR_TYPED_NOT_AN_INTEGER.format(text=text))
                return
            if not MIN_STEPS <= steps <= MAX_STEPS:
                self.refuse(ERR_STEPS_OUT_OF_RANGE.format(low=MIN_STEPS, high=MAX_STEPS))
                return
            lost = self.document().steps_with_anything_past(name=self.item, steps=steps)
            if lost:
                question = MSG_SHORTEN_QUESTION.format(count=lost)
                self.ask(dialog=ConfirmDialog(title=MSG_SHORTEN_TITLE, messages=[question]), then=lambda _: self.document().set_steps(name=self.item, steps=steps))
            else:
                self.document().set_steps(name=self.item, steps=steps)
        self.ask(dialog=PromptDialog(title=MSG_STEPS_PROMPT, value=self.steps()), then=answered)

    def toggle_drum(self):
        """Switch between drum and note patterns, always asking first, as the user chose, since the rows change and any notes go."""
        drum = not self.is_drum()

        def change(_):
            self.document().set_drum(name=self.item, drum=drum)
            self.rows_view.go_to_top()
        what = MSG_LETTERS_WHAT if drum else MSG_DEGREES_WHAT
        question = MSG_CHANGE_TYPE_QUESTION if self.document().has_notes(self.item) else MSG_CHANGE_TYPE_EMPTY_QUESTION
        self.ask(dialog=ConfirmDialog(title=MSG_CHANGE_TYPE_TITLE, messages=[question.format(what=what)]), then=change)

    def insert_step(self):
        self.document().insert_step(name=self.item, step=self.step)

    def remove_step(self):
        self.document().remove_step(name=self.item, step=self.step)
        self.clamp()

    # Drawing, which the showing view's drawing does: RollDrawing on the roll and PatternDrawing from the rows.

    def body(self, *, width, height):
        return self.view().drawing.body(width=width, height=height)
