# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Sound dialog: a sound chosen from groups, each a row that opens a flyout of its sounds.

Its first rows, where it has any, are choices of their own, such as taking no sound. Then come
the groups, General MIDI's families, each drawn as a button since it opens a flyout: Space or
Enter opens the flyout of the group under the cursor, where Up and Down move, Enter takes the
sound and Esc or Left closes the flyout with nothing chosen. / searches every group's sounds at
once: the rows give way to the sounds that contain what was typed, and Enter opens the flyout of
the sound under the cursor, on that sound. L tries the sound under the cursor, where the asker
gave a way to, and L again or moving the cursor stops it. It answers with the value of the sound
taken, or None when cancelled.

An asker whose sound plays on one note gives the note, and the dialog has a Note row under the
groups: [ and ] step the note, typing a note's name and Enter sets it, and Enter on the row takes
the sound the dialog opened on with the note shown. The dialog then answers (value, note).
"""

from rich.text import Text

from llamatron.interface.forms import moves
from llamatron.interface.forms.cursor import Cursor
from llamatron.interface.tracker import drawing, keybindings, keys as keys_values, note_names
from llamatron.interface.tracker.cursor import completed, places_matching
from llamatron.interface.tracker.dialogs.dialog import Dialog
from llamatron.interface.tracker.drawing import cursor_mark, fit, legend, Style
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.note_names import note_shown, note_typed
from llamatron.user_strings import errors, marks

# How many rows show at once, the list scrolling to keep the cursor's in view, so that the dialog fits an 80 by 24 console.
SHOWN = 12
# The lines the Note row takes at the foot of the rows: a blank line and the row.
NOTE_ROW_LINES = 2


class SoundDialog(Dialog):
    """Offers sounds in groups and answers with the value of the one taken."""

    KEYS = keybindings.SoundDialog

    def __init__(self, *, title, groups, top=(), current=None, trial=None, note=None):
        """top is the rows before the groups, each (label, value); groups is each group's name with its sounds, each (label, value); current is the
        value the dialog opens on; trial, where sounds can be tried, answers can_try(value), start(value), playing() and stop()."""
        super().__init__()
        self.title = title
        self.top = list(top)
        self.groups = [(name, list(sounds)) for name, sounds in groups]
        self.current = current
        self.trial = trial
        # The note the sound plays on, where the asker gave one, and what is being typed as another, or None while nothing is.
        self.note = note
        self.note_typed = None
        self.cursor = Cursor(place=self.row_of(current))
        # The group whose flyout is open, or None, and the cursor's place in it.
        self.flyout = None
        self.flyout_place = 0
        # What was typed into the search, or None while nothing is searched for, and the cursor's place among what it found.
        self.typed = None
        self.found_place = 0
        # Why the sound last tried did not play, shown until the next key.
        self.said = drawing.NOTHING

    # Where things are.

    def group_of(self, value):
        """Return the place of the group that holds a value, or None."""
        return next((place for place, (_, sounds) in enumerate(self.groups) if holds_sound(sounds=sounds, value=value)), None)

    def row_of(self, value):
        """Return the row a value is found on: its own row at the top, its group's row, or the first row."""
        if any(value == held for _, held in self.top):
            return [held for _, held in self.top].index(value)
        group = self.group_of(value)
        return 0 if group is None else len(self.top) + group

    def every_sound(self):
        """Return every group's sounds in order, each as (group, place in the group, label)."""
        return [(group, place, label) for group, (_, sounds) in enumerate(self.groups) for place, (label, _) in enumerate(sounds)]

    def found(self):
        """Return the sounds that contain what was typed, ignoring case, each as (group, place in the group, label)."""
        every = self.every_sound()
        shown = [label for _, _, label in every]
        return [every[place] for place in places_matching(options=shown, text=self.typed)]

    def under_cursor(self):
        """Return the value of the sound under the cursor, or None on a group's row and while searching."""
        if self.typed is not None:
            return None
        if self.flyout is not None:
            return self.groups[self.flyout][1][self.flyout_place][1]
        return self.top[self.cursor.get_place()][1] if self.cursor.get_place() < len(self.top) else None

    # The keys, by what is open.

    def keys(self):
        if self.typed is not None:
            result = [
                self.bind(self.KEYS.CLOSE, action=self.end_search),
                self.bind(self.KEYS.MOVE, action=self.move_in_found, wants_key=True),
                self.bind(self.KEYS.FIND, action=self.go_to_found),
                self.bind(self.KEYS.TYPE, action=self.type_character, wants_key=True),
            ]
            if self.typed:
                result += [self.bind(self.KEYS.ERASE, action=self.erase), self.bind(self.KEYS.COMPLETE, action=self.complete)]
            return result
        if self.flyout is not None:
            return [
                self.bind(self.KEYS.CLOSE, action=self.close_flyout),
                self.bind(self.KEYS.MOVE_IN_FLYOUT, action=self.move_in_flyout, wants_key=True),
                self.bind(self.KEYS.CHOOSE, action=self.choose),
                *self.trial_keys(),
            ]
        if self.on_note_row():
            return self.note_keys()
        on_group = self.cursor.get_place() >= len(self.top)
        return [
            self.bind(self.KEYS.CANCEL, action=self.cancel),
            self.bind(self.KEYS.MOVE, action=self.move_cursor, wants_key=True),
            self.bind(self.KEYS.OPEN, action=self.open_flyout) if on_group else self.bind(self.KEYS.CHOOSE, action=self.choose),
            self.bind(self.KEYS.SEARCH, action=self.start_search),
            *self.trial_keys(),
        ]

    def trial_keys(self):
        """Return the key that tries the sound under the cursor, or stops it while it plays, and none where it cannot be tried."""
        value = self.under_cursor()
        if self.trial is None or value is None or not self.trial.can_try(value):
            return []
        if self.trial.playing() == value:
            return [self.bind(self.KEYS.STOP_LISTENING, action=self.trial.stop)]
        return [self.bind(self.KEYS.LISTEN, action=lambda: self.listen(value))]

    def listen(self, value):
        """Try the sound under the cursor, and keep what the trial says where nothing plays."""
        self.said = self.trial.start(value) or drawing.NOTHING

    def hush(self):
        """Stop a sound being tried, as moving the cursor and closing do."""
        if self.trial is not None and self.trial.playing() is not None:
            self.trial.stop()

    def cancel(self):
        self.hush()
        self.dismiss(None)

    def answer(self, value):
        """Return what the dialog answers with for a value: the value, or the value and the note where the asker gave a note."""
        return value if self.note is None else (value, self.note)

    def choose(self):
        self.hush()
        self.dismiss(self.answer(self.under_cursor()))

    def rows(self):
        """Return how many rows there are: the top rows, the groups, and the Note row where there is a note."""
        return len(self.top) + len(self.groups) + (0 if self.note is None else 1)

    def move_cursor(self, name):
        self.hush()
        self.note_typed = None
        self.cursor.move(name=name, count=self.rows())

    # The Note row.

    def on_note_row(self):
        return self.note is not None and self.typed is None and self.flyout is None and self.cursor.get_place() == len(self.top) + len(self.groups)

    def note_keys(self):
        result = [
            self.bind(self.KEYS.CANCEL, action=self.cancel),
            self.bind(self.KEYS.MOVE, action=self.move_cursor, wants_key=True),
            self.bind(self.KEYS.NOTE_LESS, action=lambda: self.step_note(-1)),
            self.bind(self.KEYS.NOTE_MORE, action=lambda: self.step_note(1)),
            self.bind(self.KEYS.TYPE_NOTE, action=self.type_note, wants_key=True),
            self.bind(self.KEYS.TAKE_NOTE, action=self.take_note),
        ]
        if self.note_typed:
            result.append(self.bind(self.KEYS.ERASE, action=self.erase_note))
        return result

    def step_note(self, offset):
        self.note_typed = None
        self.note = max(min(self.note + offset, note_names.HIGHEST_NOTE), note_names.LOWEST_NOTE)

    def type_note(self, name):
        self.note_typed = (self.note_typed or drawing.NOTHING) + name

    def erase_note(self):
        self.note_typed = self.note_typed[:-1] or None

    def take_note(self):
        """Set the note typed, where it is a note, and stay; with nothing typed, take the sound the dialog opened on with the note shown."""
        if self.note_typed is None:
            self.hush()
            self.dismiss((self.current, self.note))
            return
        typed = note_typed(self.note_typed)
        if typed is None:
            self.said = errors.ERR_NOT_A_NOTE_NAME.format(text=self.note_typed)
        else:
            self.note = typed
        self.note_typed = None

    # A group's flyout.

    def open_flyout(self):
        """Open the flyout of the group under the cursor, on the current sound where the group holds it."""
        group = self.cursor.get_place() - len(self.top)
        values = [held for _, held in self.groups[group][1]]
        self.flyout = group
        self.flyout_place = values.index(self.current) if self.current in values else 0

    def close_flyout(self):
        self.hush()
        self.flyout = None

    def move_in_flyout(self, name):
        """Move in the flyout with Up and Down, stopping at its edges; Left closes it, and Right does nothing."""
        self.hush()
        if name == Key.LEFT:
            self.flyout = None
        elif name != Key.RIGHT:
            self.flyout_place = moves.moved(place=self.flyout_place, name=name, count=len(self.groups[self.flyout][1]))

    # Searching every group's sounds at once.

    def takes_text(self):
        return self.typed is not None or self.on_note_row()

    def start_search(self):
        self.hush()
        self.typed = drawing.NOTHING
        self.found_place = 0

    def end_search(self):
        self.typed = None

    def type_character(self, name):
        self.typed += keys_values.SPACE_CHARACTER if name == Key.SPACE else name
        self.found_place = 0

    def erase(self):
        self.typed = self.typed[:-1]
        self.found_place = 0

    def complete(self):
        found = self.found()
        self.typed = completed(options=[label for _, _, label in found], matches=range(len(found)), typed=self.typed)
        self.found_place = 0

    def move_in_found(self, name):
        found = self.found()
        if found:
            self.found_place = moves.moved(place=min(self.found_place, len(found) - 1), name=name, count=len(found))

    def go_to_found(self):
        """Open the flyout of the sound the search's cursor is on, on that sound, where it can be tried and taken."""
        found = self.found()
        if not found:
            return
        group, place, _ = found[min(self.found_place, len(found) - 1)]
        self.typed = None
        self.cursor.set_place(len(self.top) + group)
        self.flyout = group
        self.flyout_place = place

    # Drawing.

    def row_text(self, row):
        """Return a row's text: a top row's label, or a group drawn as a button, with the current sound after a mark where the group holds it."""
        if row < len(self.top):
            return self.top[row][0]
        name, sounds = self.groups[row - len(self.top)]
        chosen = next((label for label, held in sounds if held == self.current), None)
        return marks.MSG_FLYOUT_CLOSED.format(name=name) if chosen is None else marks.MSG_FLYOUT_CHOSEN.format(name=name, chosen=chosen)

    def windowed(self, *, rows, at, shown=SHOWN):
        """Return the rows that show, as (place, row), so many of them, scrolled to keep the cursor's in view."""
        start = max(min(at - shown // 2, len(rows) - shown), 0)
        return list(enumerate(rows))[start:start + shown]

    def padded(self, lines, *, rows=SHOWN):
        """Return lines made up to so many rows with blank ones, and under them the line that says why a sound did not play, blank while there is nothing to say."""
        return [*lines, *[Text(drawing.NOTHING)] * (rows - len(lines)), Text(self.said, style=Style.REFUSAL)]

    def on_key(self, event):
        """Clear what was said at the next key, as the status line is cleared."""
        self.said = drawing.NOTHING
        super().on_key(event)

    def lines(self, width):
        if self.typed is not None:
            found = self.found()
            at = min(self.found_place, max(len(found) - 1, 0))
            rows = [marks.MSG_SOUND_FOUND.format(sound=label, group=self.groups[group][0]) for group, _, label in found]
            shown = [Text(fit(text=cursor_mark(place == at) + row, width=width), style=Style.BOLD if place == at else drawing.NOTHING) for place, row in self.windowed(rows=rows, at=at)]
            return [Text(fit(text=drawing.SPACE + marks.MSG_SEARCH_SHOWN.format(text=self.typed), width=width), style=Style.DIM), *self.padded(shown[:SHOWN - 1], rows=SHOWN - 1)]
        rows = [self.row_text(row) for row in range(len(self.top) + len(self.groups))]
        if self.note is None:
            return self.padded([self.row_line(row=row, selected=place == self.cursor.get_place(), width=width) for place, row in self.windowed(rows=rows, at=self.cursor.get_place())])
        # The Note row stays in view under the list, after a blank line, however far the list is scrolled.
        listed = SHOWN - NOTE_ROW_LINES
        on_note = self.cursor.get_place() == len(rows)
        note = marks.MSG_SOUND_NOTE_ROW.format(note=note_shown(self.note)) if self.note_typed is None else marks.MSG_SOUND_NOTE_TYPED.format(text=self.note_typed)
        lines = [self.row_line(row=row, selected=place == self.cursor.get_place(), width=width) for place, row in self.windowed(rows=rows, at=min(self.cursor.get_place(), len(rows) - 1), shown=listed)]
        return self.padded([*lines, *[Text(drawing.NOTHING)] * (listed - len(lines)), Text(drawing.NOTHING), self.row_line(row=note, selected=on_note, width=width)])

    def row_line(self, *, row, selected, width):
        """Return a row as drawn: the cursor's with the triangle, in bold."""
        return Text(fit(text=cursor_mark(selected) + row, width=width), style=Style.BOLD if selected else drawing.NOTHING)

    def flyout_lines(self, width):
        """Return the open flyout's lines, or None: its group as the heading, a sound a row with the cursor's marked, and its own keys."""
        if self.flyout is None or self.typed is not None:
            return None
        name, sounds = self.groups[self.flyout]
        rows = [label for label, _ in sounds]
        shown = [Text(fit(text=cursor_mark(place == self.flyout_place) + row, width=width), style=Style.BOLD if place == self.flyout_place else drawing.NOTHING)
                 for place, row in self.windowed(rows=rows, at=self.flyout_place)]
        return [Text(name, style=Style.BOLD), Text(drawing.NOTHING), *self.padded(shown), Text(drawing.NOTHING), *legend(keys=self.keys(), width=width)]


def holds_sound(*, sounds, value):
    """Return whether a group's sounds, each (label, value), hold a value."""
    return any(value == held for _, held in sounds)
