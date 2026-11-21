# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The pattern editor: a grid of steps that's already drawn, with one row per kind of value.

The grid's size comes from the pattern's step count, and typing never changes it or moves the
cursor. Every step lasts the pattern's step size. A step with a note sounds for its gate, which
can run on past later steps, up to the end of the pattern, and a step with no note is a rest. A
pattern wider than the screen scrolls sideways as the cursor moves, rather than wrapping onto more
blocks, so that a bar is always one row of columns.

The editor shows one of two views, each a component with its own cursor, keys and drawing:
PatternRows (tui/components/pattern_rows.py), the rows, and PianoRoll. The editor keeps what
they share: the cursor's step, the keys that work in both, and the edits to the whole pattern.
Each row of the grid is an object from tui/components, built once per row name, which says what
its cells show and what its keys do when the cursor is on it. The Degree row is a gauge, and
the pinned rows (the gauge with its number, and the octave under it) stay at the top while the
rows beneath scroll. Those rows come in sections, in place of sets
of rows that Tab cycled through: each section is headed by a row of the grid (SectionRow) that
Space or Enter opens or closes, PgUp and PgDn jump between the headings, and which sections
are open is kept on the app for the session.

A pattern that isn't drums opens on the piano roll (tui/components/piano_roll.py, drawn by
RollDrawing), and Tab switches between the roll and the rows; drum patterns have no roll and open
on the rows.
"""


from llamatron.model.file.checks import fraction_text, is_written_length, listed
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects.naming import words
from llamatron.model.objects.pattern import Pattern
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import Row, Section
from llamatron.model.values import midi
from llamatron.tui import drawing, key_table, keybindings
from llamatron.tui.components.chord_row import step_chord_in_words
from llamatron.tui.components.pattern_rows import PatternRows
from llamatron.tui.components.piano_roll import PianoRoll
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.grouped_choice_dialog import GroupedChoiceDialog
from llamatron.tui.screens.pattern.pattern_drawing import PatternDrawing
from llamatron.tui.screens.pattern.roll_drawing import RollDrawing
from llamatron.tui.screens.shared.listening import pattern_listen_keys
from llamatron.tui.screens.shared.shared import ask_time_signature, columns
from llamatron.tui.screens.shared.shows_named_item import ShowsNamedItem
from llamatron.tui.screens.shared.step_editor import StepEditor
from llamatron.tui.text import fraction, sorted_names
from llamatron.user_strings import errors, help as help_text, labels, legends, marks, messages


def direction_choices(directions):
    """Return each direction as words beside what it does, lined up for a picker."""
    return columns([(words(name), labels.MSG_DIRECTION_NAMES[name]) for name in directions])


class Munge:
    """The munge dialog's choices, each its place in MSG_MUNGE_CHOICES; the dialog lists them sorted by name."""

    REVERSE_AFTER = 0
    REVERSE_BEFORE = 1
    REVERSE = 2
    PIVOT = 3
    RANDOMIZE = 4
    COPY_BEFORE_TO_END = 5
    COPY_AFTER_TO_END = 6
    COPY_BEFORE_TO_START = 7
    COPY_AFTER_TO_START = 8
    RANDOMIZE_AFTER = 9
    RANDOMIZE_BEFORE = 10
    CLEAR_ALL_BUT_PITCH = 11
    CLEAR_REGISTER_CHANGES = 12
    CLEAR_STATEMENTS = 13
    ROLL_LEFT = 14
    ROLL_RIGHT = 15
    CLEAR_CHORDS = 16
    MIRROR = 17
    INTERLEAVE = 18
    SMOOTH_CCS = 19
    SMOOTH_VELOCITY = 20
    SMOOTH_AX = 21
    SMOOTH_BX = 22
    SMOOTH_CX = 23
    SMOOTH_DX = 24
    SPLICE = 25
    SPLICE_BEFORE = 26
    SPLIT = 27
    SPLICE_AT_CURSOR = 28
    ROLL_LEFT_AT_CURSOR = 29
    ROLL_RIGHT_AT_CURSOR = 30
    JOIN_NOTES = 31
    DIVIDE_NOTES = 32
    RANDOMIZE_RHYTHM = 33
    RANDOMIZE_PITCHES = 34
    REVERSE_PITCHES = 35
    CLEAR_EVERY = 36
    CROP = 37
    HUMANIZE_VELOCITY = 38
    INVERT_MELODY = 39
    VOICE_LEADING = 40
    VOICE_LEADING_OCTAVES = 41


# The heading each munge is listed under.
MUNGE_GROUPS = {
    labels.MungeGroup.CLEAR: [Munge.CLEAR_ALL_BUT_PITCH, Munge.CLEAR_CHORDS, Munge.CLEAR_EVERY, Munge.CROP],
    labels.MungeGroup.COPY: [Munge.COPY_BEFORE_TO_END, Munge.COPY_AFTER_TO_END, Munge.COPY_BEFORE_TO_START, Munge.COPY_AFTER_TO_START, Munge.MIRROR],
    labels.MungeGroup.OTHER_PATTERNS: [Munge.INTERLEAVE, Munge.SPLICE, Munge.SPLICE_BEFORE, Munge.SPLICE_AT_CURSOR, Munge.SPLIT],
    labels.MungeGroup.PITCH: [Munge.REVERSE_PITCHES, Munge.RANDOMIZE_PITCHES, Munge.INVERT_MELODY, Munge.VOICE_LEADING, Munge.VOICE_LEADING_OCTAVES],
    labels.MungeGroup.REGISTERS: [Munge.CLEAR_REGISTER_CHANGES, Munge.CLEAR_STATEMENTS, Munge.SMOOTH_AX, Munge.SMOOTH_BX, Munge.SMOOTH_CX, Munge.SMOOTH_DX],
    labels.MungeGroup.REORDER: [Munge.REVERSE_AFTER, Munge.REVERSE_BEFORE, Munge.REVERSE, Munge.PIVOT, Munge.RANDOMIZE, Munge.RANDOMIZE_AFTER, Munge.RANDOMIZE_BEFORE],
    labels.MungeGroup.RHYTHM: [Munge.JOIN_NOTES, Munge.DIVIDE_NOTES, Munge.RANDOMIZE_RHYTHM],
    labels.MungeGroup.ROLL: [Munge.ROLL_LEFT, Munge.ROLL_RIGHT, Munge.ROLL_LEFT_AT_CURSOR, Munge.ROLL_RIGHT_AT_CURSOR],
    labels.MungeGroup.VELOCITY_AND_CCS: [Munge.HUMANIZE_VELOCITY, Munge.SMOOTH_VELOCITY, Munge.SMOOTH_CCS],
}


def munge_name(choice):
    """Return what the munge dialog calls a choice."""
    return labels.MSG_MUNGE_CHOICES[choice]


def munge_groups():
    """Return the munge dialog's headings, sorted by name, each with its choices sorted by name, whatever is added."""
    return [(heading, sorted(MUNGE_GROUPS[heading], key=lambda choice: munge_name(choice).lower())) for heading in sorted(MUNGE_GROUPS)]


def munges_in_order():
    """Return every munge in the order the dialog holds them: heading by heading, which is the place the dialog answers with."""
    return [choice for _, choices in munge_groups() for choice in choices]


# The scale lengths a pattern can be written for, in the order the picker lists them after any.
SCALE_LENGTHS = tuple(range(limits.MIN_SCALE_LENGTH, limits.MAX_SCALE_LENGTH + 1))


# The steps a part has when a pattern is split into new patterns, until another number is typed, and the most names the dialog lists.
SPLIT_STEPS = 16
SPLIT_NAMES_SHOWN = 8
# What the munges that take a number call it.
EVERY = 'every'
MOST = 'most'
# Voice leading moves a chord toward the chord before it, so a pattern needs this many chords.
FEWEST_CHORDS_TO_LEAD = 2
# The fewest steps a pattern is rolled.
FIRST_ROLL = 1
# The munges that blank or fill rows of every step and need nothing else, each with the method of Pattern that does it.
CLEARING = {
    Munge.CLEAR_ALL_BUT_PITCH: Pattern.clear_all_but_pitch,
    Munge.CLEAR_REGISTER_CHANGES: Pattern.clear_register_changes,
    Munge.CLEAR_STATEMENTS: Pattern.clear_statements,
    Munge.CLEAR_CHORDS: Pattern.clear_chords,
    Munge.SMOOTH_CCS: Pattern.smooth_ccs,
    Munge.SMOOTH_VELOCITY: Pattern.smooth_velocity,
    Munge.JOIN_NOTES: Pattern.join_repeated_notes,
    Munge.RANDOMIZE_RHYTHM: Pattern.randomize_rhythm,
    Munge.RANDOMIZE_PITCHES: Pattern.randomize_pitches,
    Munge.REVERSE_PITCHES: Pattern.reverse_pitches,
}
# The munges that take steps from another pattern, each with the title of the picker that asks which.
OTHER_PATTERN_TITLES = {
    Munge.INTERLEAVE: messages.MSG_INTERLEAVE_CHOICE_TITLE,
    Munge.SPLICE: messages.MSG_SPLICE_CHOICE_TITLE,
    Munge.SPLICE_BEFORE: messages.MSG_SPLICE_BEFORE_CHOICE_TITLE,
    Munge.SPLICE_AT_CURSOR: messages.MSG_SPLICE_AT_CURSOR_CHOICE_TITLE,
}
# The munges that smooth the row setting one register.
SMOOTHED_REGISTERS = dict(zip((Munge.SMOOTH_AX, Munge.SMOOTH_BX, Munge.SMOOTH_CX, Munge.SMOOTH_DX), file_format.REGISTER_NAMES))


class Reconfigure:
    """The Reconfigure dialog's choices, in the order reconfigure_choices lists them: the whole-pattern actions that R gathers, so that the legend stays short."""

    LOAD_OVER = 0
    STEP_SIZE = 1
    TIME_SIGNATURE = 2
    DRUM = 3
    DIRECTION = 4
    RENAME = 5
    SCALE_LENGTH = 6


def reconfigure_choices(*, drum):
    """Return the Reconfigure dialog's options, in the order of the Reconfigure class, with the drum entry saying which way it switches. The scale length is last and offered only for a pattern that is not a drum pattern, which has none."""
    choices = [legends.MSG_LOAD_OVER_WHAT, legends.MSG_STEP_SIZE_WHAT, legends.MSG_TIME_SIGNATURE_WHAT, legends.MSG_DRUM_OFF_WHAT if drum else legends.MSG_DRUM_ON_WHAT, legends.MSG_DIRECTION_WHAT, legends.What.RENAME]
    return choices if drum else [*choices, legends.MSG_SCALE_LENGTH_WHAT]


class PatternEditor(ShowsNamedItem, StepEditor):

    """The pattern editor: one pattern's steps, in the rows view and on the piano roll."""

    KEYS = keybindings.PatternEditor
    HELP = help_text.HELP_PATTERN_EDITOR
    SECTION = Section.PATTERNS
    CRUMBS_BEFORE = (labels.Crumb.PATTERNS,)
    RENAME_PROMPT = messages.MSG_RENAME_PATTERN_PROMPT

    def __init__(self, *, holder, name, opened_from=None, track=None):
        super().__init__(holder=holder, name=name)
        # The track of the clip the editor was opened from, whose instrument names the keyswitches, or None when the Patterns page opened it.
        self.opened_track = track
        # The page a clip opened the editor from, Arrange or the clip page, whose crumbs come first in the editor's, so that the crumbs
        # say where Esc goes back to. None when the Patterns page opened it, whose crumbs are the editor's own.
        self.opened_from = opened_from
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
        return (*self.opened_from.crumb_trail(), labels.MSG_PATTERN_CRUMB.format(name=self.item))

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

    def step_count(self):
        return self.pattern().get_steps()

    def clamp(self):
        self.keep_step()
        self.rows_view.clamp()

    def set_value(self, *, value, row=None, step=None):
        self.document().change(self.document().get_setlist().get_pattern(self.item).set_value, row=row or self.row_name(), step=self.step if step is None else step, value=value)

    def keyswitch_instrument(self):
        """Return the instrument whose keyswitches the pattern's steps are named by, and what the keyswitch dialog says over its slots: the instrument's name, or why none is named.

        The instrument is known when a clip opened the editor, whose track plays it, or when
        every track that plays the pattern has the one instrument; otherwise the slots go by
        their numbers alone.
        """
        document = self.document()
        song = document.song()
        if self.opened_track is not None and song.has_track(self.opened_track):
            names = [song.get_track(self.opened_track).get_instrument_name()]
        else:
            names = document.instruments_of_pattern(self.item)
        known = [name for name in names if name is not None]
        if len(names) == 1 and known:
            return document.get_setlist().get_instrument(known[0]), known[0]
        return None, messages.MSG_KEYSWITCH_SEVERAL_INSTRUMENTS if len(names) > 1 else messages.MSG_KEYSWITCH_NO_INSTRUMENT

    def known_scale(self):
        """Return the scale the pattern is known to play under, as a NamedScale: the first of its uses' scales, or the current song's when nothing uses it, or None when there is none or it is a drum pattern."""
        if self.is_drum():
            return None
        names = self.document().scales_of_pattern(self.item)
        return self.document().song().get_named_scale(names[0]) if names else None

    def resting_status(self):
        """Say the chord under the cursor, in the scale the pattern is known to play under, while the cursor rests on a step that holds one."""
        self.clamp()
        if self.is_drum() or not self.is_note() or not isinstance(self.value(row=Row.DEGREE), int):
            return drawing.NOTHING
        return step_chord_in_words(editor=self, step=self.step).resting(where=messages.MSG_RESTING_STEP.format(step=self.step + 1))

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
        result += view.step_keys(can_remove=self.step_count() > 1 and not view.takes_note_letters())
        result += [
            self.bind(self.KEYS.RESIZE, action=self.ask_steps),
            self.bind(self.KEYS.MUNGE, action=self.munge),
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
        self.ask(dialog=ChoiceDialog(title=messages.MSG_RECONFIGURE_TITLE, options=reconfigure_choices(drum=self.is_drum())), then=self.reconfigure_as)

    def reconfigure_as(self, choice):
        actions = {
            Reconfigure.LOAD_OVER: self.load_over,
            Reconfigure.STEP_SIZE: self.ask_step_size,
            Reconfigure.TIME_SIGNATURE: self.ask_time_signature,
            Reconfigure.DRUM: self.toggle_drum,
            Reconfigure.DIRECTION: self.pick_direction,
            Reconfigure.SCALE_LENGTH: self.pick_scale_length,
            Reconfigure.RENAME: self.rename,
        }
        actions[choice]()

    # Moving along the steps, which both views do.

    def jump_end(self, direction):
        """Go to the first step, which Home does, or the last, which End does."""
        self.step = 0 if direction == key_table.STEP_BACK else self.step_count() - 1

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
                self.refuse(errors.ERR_LENGTH_OUT_OF_RANGE.format(most=most) if is_written_length(text) else errors.ERR_NOT_A_LENGTH.format(text=text))
                return
            then(fraction_text(fraction(text)))
        self.ask_text(title=title, value=current, then=answered)

    # The pattern's own settings.

    def ask_step_size(self):
        current = self.pattern().get_written_step_size() or drawing.NOTHING
        self.ask_length(title=messages.MSG_STEP_SIZE_PROMPT, current=current, most=limits.MAX_STEP_SIZE, then=lambda text: self.document().change(self.document().get_setlist().get_pattern(self.item).set_step_size, text), blank_allowed=True)

    def ask_time_signature(self):
        current = self.pattern().get_written_time_signature() or drawing.NOTHING
        ask_time_signature(
            page=self, title=messages.MSG_TIME_SIGNATURE_PROMPT, current=current, blank_allowed=True,
            then=lambda text: self.document().change(self.document().get_setlist().get_pattern(self.item).set_time_signature, text),
        )

    def pick_direction(self):
        current = self.pattern().get_direction()
        self.ask(
            dialog=ChoiceDialog(title=messages.MSG_PLAY_DIRECTION_TITLE, options=direction_choices(file_format.DIRECTIONS), current=file_format.DIRECTIONS.index(current)),
            then=lambda chosen: self.document().change(self.document().get_setlist().get_pattern(self.item).set_direction, file_format.DIRECTIONS[chosen]),
        )

    def pick_scale_length(self):
        """Ask how many notes the scale has that the pattern was written for, any first."""
        current = self.pattern().get_scale_length()
        options = [marks.MSG_ANY_SCALE_LENGTH, *[str(length) for length in SCALE_LENGTHS]]
        self.ask(
            dialog=ChoiceDialog(title=messages.MSG_SCALE_LENGTH_TITLE, options=options, current=0 if current is None else SCALE_LENGTHS.index(current) + 1),
            then=lambda chosen: self.document().change(self.document().get_setlist().get_pattern(self.item).set_scale_length, SCALE_LENGTHS[chosen - 1] if chosen else None),
        )

    def munge(self):
        """Offer the ways of rearranging, copying and clearing the steps, under headings that open and close, and do the chosen one."""
        groups = [(heading, munge_names(choices)) for heading, choices in munge_groups()]
        order = munges_in_order()
        self.ask(dialog=GroupedChoiceDialog(title=messages.MSG_MUNGE_TITLE, groups=groups, opened=self.holder.open_munge_groups), then=lambda place: self.munge_as(order[place]))

    def munge_as(self, choice):
        """Do one of the munge dialog's choices. A rearranging leaves the cursor on its step, so that choosing the same way again undoes it."""
        name = self.item
        document = self.document()
        last = self.step_count() - 1
        if choice == Munge.REVERSE_AFTER:
            if self.step >= last:
                self.refuse(errors.ERR_NOTHING_AFTER)
                return
            document.change(document.get_setlist().get_pattern(name).reverse_after, self.step)
        elif choice == Munge.REVERSE_BEFORE:
            if self.step == 0:
                self.refuse(errors.ERR_NOTHING_BEFORE)
                return
            document.change(document.get_setlist().get_pattern(name).reverse_before, self.step)
        elif choice == Munge.REVERSE:
            if self.step_count() < 2:
                self.refuse(errors.ERR_ONE_STEP)
                return
            document.change(document.get_setlist().get_pattern(name).reverse)
        elif choice == Munge.PIVOT:
            if self.step_count() < 2:
                self.refuse(errors.ERR_NOTHING_TO_PIVOT)
                return
            self.step = document.change(document.get_setlist().get_pattern(name).pivot_around, self.step)
        elif choice in (Munge.RANDOMIZE, Munge.RANDOMIZE_AFTER, Munge.RANDOMIZE_BEFORE):
            if self.step_count() < 2:
                self.refuse(errors.ERR_ONE_STEP)
                return
            if choice == Munge.RANDOMIZE:
                document.change(document.get_setlist().get_pattern(name).shuffle)
            else:
                document.munge_pattern(name=name, way=Pattern.shuffle_from if choice == Munge.RANDOMIZE_AFTER else Pattern.shuffle_through, step=self.step)
        elif choice in (Munge.COPY_BEFORE_TO_END, Munge.COPY_AFTER_TO_END, Munge.COPY_BEFORE_TO_START, Munge.COPY_AFTER_TO_START):
            self.copy_steps(choice)
        elif choice == Munge.INVERT_MELODY:
            self.invert_melody()
        elif choice in (Munge.VOICE_LEADING, Munge.VOICE_LEADING_OCTAVES):
            self.lead_voices(octaves=choice == Munge.VOICE_LEADING_OCTAVES)
        elif choice == Munge.DIVIDE_NOTES:
            document.divide_long_notes(name)
        elif choice == Munge.CROP:
            if self.step >= last:
                self.refuse(errors.ERR_NOTHING_TO_CROP)
                return
            document.change(document.get_setlist().get_pattern(name).set_steps, self.step + 1)
        elif choice == Munge.CLEAR_EVERY:
            self.ask_number(title=messages.MSG_CLEAR_EVERY_PROMPT, low=limits.MIN_STEPS, high=self.step_count(), way=Pattern.clear_every, named=EVERY)
        elif choice == Munge.HUMANIZE_VELOCITY:
            self.ask_number(title=messages.MSG_HUMANIZE_PROMPT, low=midi.MIN_VELOCITY, high=midi.MAX_VELOCITY, way=Pattern.humanize_velocity, named=MOST)
        elif choice == Munge.ROLL_LEFT_AT_CURSOR:
            if self.step == 0:
                self.refuse(errors.ERR_NOTHING_BEFORE)
                return
            document.munge_pattern(name=name, way=Pattern.roll_through, step=self.step)
        elif choice == Munge.ROLL_RIGHT_AT_CURSOR:
            if self.step >= last:
                self.refuse(errors.ERR_NOTHING_AFTER)
                return
            document.munge_pattern(name=name, way=Pattern.roll_from, step=self.step)
        elif choice in (Munge.ROLL_LEFT, Munge.ROLL_RIGHT):
            self.ask_roll(left=choice == Munge.ROLL_LEFT)
        elif choice == Munge.MIRROR:
            if self.grown_too_long(self.step_count() * 2):
                return
            document.munge_pattern(name=name, way=Pattern.mirror)
        elif choice == Munge.SPLIT:
            self.ask_split()
        elif choice in OTHER_PATTERN_TITLES:
            self.pick_other_pattern(choice)
        elif choice in SMOOTHED_REGISTERS:
            document.munge_pattern(name=name, way=Pattern.smooth_register_sets, register=SMOOTHED_REGISTERS[choice])
        else:
            document.munge_pattern(name=name, way=CLEARING[choice])

    def copy_steps(self, choice):
        """Copy the cursor's step with the steps before it, or with the steps after it, to the end of the pattern or before its start, unless the pattern would hold too many steps.

        After a copy before the start the cursor stays on the note it was on, which the copy moved along.
        """
        before = choice in (Munge.COPY_BEFORE_TO_END, Munge.COPY_BEFORE_TO_START)
        first = 0 if before else self.step
        last = self.step if before else self.step_count() - 1
        copied = last - first + 1
        if self.grown_too_long(self.step_count() + copied):
            return
        to_start = choice in (Munge.COPY_BEFORE_TO_START, Munge.COPY_AFTER_TO_START)
        self.document().munge_pattern(name=self.item, way=Pattern.repeat_at_start if to_start else Pattern.repeat_at_end, first=first, last=last)
        if to_start:
            self.step += copied

    def grown_too_long(self, steps):
        """Return whether a pattern of so many steps would hold more than a pattern may, saying so on the status line when it would."""
        if steps > limits.MAX_STEPS:
            self.refuse(errors.ERR_MUNGE_TOO_MANY_STEPS.format(steps=steps, most=limits.MAX_STEPS))
        return steps > limits.MAX_STEPS

    def pick_other_pattern(self, choice):
        """Choose another pattern and take its steps into this one, leaving the other as it is: spliced after the last step, before the first or before the cursor's step, or interleaved, one after each step, which makes this one twice as long. The cursor stays on its note."""
        others = sorted_names(name for name in self.document().song().get_pattern_names() if name != self.item)
        if not others:
            self.refuse(errors.ERR_NO_OTHER_PATTERNS)
            return

        def chosen(place):
            other = self.document().song().get_pattern(others[place])
            added = self.step_count() if choice == Munge.INTERLEAVE else other.get_steps()
            if other.is_drum() != self.is_drum():
                self.refuse(errors.ERR_INTERLEAVE_DRUM_MISMATCH)
                return
            if self.grown_too_long(self.step_count() + added):
                return
            if choice == Munge.INTERLEAVE:
                self.document().munge_pattern(name=self.item, way=Pattern.interleave, other=other)
                self.step *= 2
                return
            # Steps put before the cursor's step move it along, and the cursor stays on its note.
            places = {Munge.SPLICE: None, Munge.SPLICE_BEFORE: 0, Munge.SPLICE_AT_CURSOR: self.step}
            self.document().munge_pattern(name=self.item, way=Pattern.splice, other=other, at=places[choice])
            if places[choice] is not None:
                self.step += added
        self.ask(dialog=ChoiceDialog(title=OTHER_PATTERN_TITLES[choice], options=others), then=chosen)

    def ask_split(self):
        """Ask how many steps each new pattern has, make new patterns of the pattern's steps, so many each, and say which were made; the pattern itself is left as it is."""
        most = self.step_count() - 1
        if most < FIRST_ROLL:
            self.refuse(errors.ERR_ONE_STEP)
            return

        def answered(text):
            try:
                steps = int(text.strip())
            except ValueError:
                self.refuse(errors.ERR_TYPED_NOT_AN_INTEGER.format(text=text))
                return
            if not FIRST_ROLL <= steps <= most:
                self.refuse(errors.ERR_SPLIT_OUT_OF_RANGE.format(low=FIRST_ROLL, high=most))
                return
            try:
                made = self.document().change(self.document().get_setlist().split_pattern, name=self.item, steps=steps)
            except ValueError as problem:
                self.refuse(str(problem))
                return
            shown = listed(made[:SPLIT_NAMES_SHOWN])
            more = len(made) - SPLIT_NAMES_SHOWN
            said = messages.MSG_SPLIT_CREATED_MANY.format(count=len(made), names=shown, more=more) if more > 0 else messages.MSG_SPLIT_CREATED.format(count=len(made), names=shown)
            self.tell(messages.MSG_SPLIT_TITLE, said)
        self.ask_text(title=messages.MSG_SPLIT_PROMPT, value=str(min(SPLIT_STEPS, most)), then=answered)

    def invert_melody(self):
        """Mirror the pattern's notes around the note on the cursor's step, by the degrees of the scale the pattern plays under, or of the scale length it was written for."""
        scale = self.known_scale()
        size = len(scale.get_half_steps()) if scale is not None else self.pattern().get_scale_length()
        if size is None:
            self.refuse(errors.ERR_MUNGE_NO_SCALE)
            return
        try:
            self.document().munge_pattern(name=self.item, way=Pattern.invert_melody, step=self.step, scale_size=size, default_octave=self.default_octave())
        except InvalidValue as problem:
            self.refuse(str(problem))

    def lead_voices(self, *, octaves):
        """Write the inversions that move each chord the least from the chord before, measured in the scale the pattern plays under."""
        scale = self.known_scale()
        if scale is None:
            self.refuse(errors.ERR_MUNGE_NO_SCALE)
            return
        if len([step for step in range(self.step_count()) if self.pattern().starts_chord(step)]) < FEWEST_CHORDS_TO_LEAD:
            self.refuse(errors.ERR_VOICE_LEADING_NEEDS_CHORDS)
            return
        self.document().munge_pattern(name=self.item, way=Pattern.apply_voice_leading, scale=scale, default_octave=self.default_octave(), octaves=octaves)

    def ask_number(self, *, title, low, high, way, named):
        """Ask for a whole number within limits and munge the pattern with it, handed to the munge under a name, saying on the status line why a number or the munge was refused."""
        def answered(text):
            try:
                number = int(text.strip())
            except ValueError:
                self.refuse(errors.ERR_TYPED_NOT_AN_INTEGER.format(text=text))
                return
            if not low <= number <= high:
                self.refuse(errors.ERR_MUNGE_NUMBER_OUT_OF_RANGE.format(low=low, high=high))
                return
            try:
                self.document().munge_pattern(name=self.item, way=way, **{named: number})
            except InvalidValue as problem:
                self.refuse(str(problem))
        self.ask_text(title=title, value=drawing.NOTHING, then=answered)

    def ask_roll(self, *, left):
        """Ask how many steps to turn the pattern, and turn it: a step pushed off one end comes in at the other. The cursor stays on its step."""
        def answered(text):
            try:
                steps = int(text.strip())
            except ValueError:
                self.refuse(errors.ERR_TYPED_NOT_AN_INTEGER.format(text=text))
                return
            if not FIRST_ROLL <= steps <= self.step_count():
                self.refuse(errors.ERR_ROLL_OUT_OF_RANGE.format(low=FIRST_ROLL, high=self.step_count()))
                return
            self.document().munge_pattern(name=self.item, way=Pattern.roll, steps=steps if left else -steps)
        self.ask_text(title=messages.MSG_ROLL_LEFT_PROMPT if left else messages.MSG_ROLL_RIGHT_PROMPT, value=drawing.NOTHING, then=answered)

    def load_over(self):
        others = sorted_names(name for name in self.document().song().get_pattern_names() if name != self.item)
        if not others:
            self.refuse(errors.ERR_NO_OTHER_PATTERNS)
            return

        def load(name):
            self.document().load_over(name=self.item, other=name)
            self.rows_view.go_to_top()
            self.clamp()

        def chosen(place):
            name = others[place]
            if self.document().has_notes(self.item):
                question = messages.MSG_LOAD_OVER_QUESTION.format(name=self.item, other=name)
                self.confirm(title=messages.MSG_LOAD_OVER_TITLE, lines=[question], then=lambda: load(name))
            else:
                load(name)
        self.ask(dialog=ChoiceDialog(title=messages.MSG_LOAD_OVER_CHOICE_TITLE.format(name=self.item), options=others), then=chosen)

    # The whole pattern.

    def ask_steps(self):
        def answered(text):
            try:
                steps = int(text.strip())
            except ValueError:
                self.refuse(errors.ERR_TYPED_NOT_AN_INTEGER.format(text=text))
                return
            if not limits.MIN_STEPS <= steps <= limits.MAX_STEPS:
                self.refuse(errors.ERR_STEPS_OUT_OF_RANGE.format(low=limits.MIN_STEPS, high=limits.MAX_STEPS))
                return
            lost = self.document().steps_with_anything_past(name=self.item, steps=steps)
            if lost:
                question = messages.MSG_SHORTEN_QUESTION.format(count=lost)
                self.confirm(title=messages.MSG_SHORTEN_TITLE, lines=[question], then=lambda: self.document().change(self.document().get_setlist().get_pattern(self.item).set_steps, steps))
            else:
                self.document().change(self.document().get_setlist().get_pattern(self.item).set_steps, steps)
        self.ask_text(title=messages.MSG_STEPS_PROMPT, value=self.step_count(), then=answered)

    def toggle_drum(self):
        """Switch between drum and note patterns, always asking first, since the rows change and any notes go."""
        drum = not self.is_drum()

        def change(_):
            self.document().change(self.document().get_setlist().get_pattern(self.item).set_drum, drum)
            self.rows_view.go_to_top()
        what = legends.MSG_LETTERS_WHAT if drum else legends.MSG_DEGREES_WHAT
        question = messages.MSG_CHANGE_TYPE_QUESTION if self.document().has_notes(self.item) else messages.MSG_CHANGE_TYPE_EMPTY_QUESTION
        self.ask(dialog=ConfirmDialog(title=messages.MSG_CHANGE_TYPE_TITLE, messages=[question.format(what=what)]), then=change)

    def insert_step(self):
        self.document().change(self.document().get_setlist().get_pattern(self.item).insert_step, self.step)

    def remove_step(self):
        self.document().change(self.document().get_setlist().get_pattern(self.item).remove_step, self.step)
        self.clamp()

    # Drawing, which the showing view's drawing does: RollDrawing on the roll and PatternDrawing from the rows.

    def body(self, *, width, height):
        return self.view().drawing.body(width=width, height=height)


def munge_names(choices):
    """Return what each munge of a group is called."""
    return [munge_name(choice) for choice in choices]
