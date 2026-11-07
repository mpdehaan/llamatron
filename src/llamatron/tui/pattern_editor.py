# llamatron: a Python language and framework for producing MIDI clips.
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
can run on past later steps, up to the end of the pattern, and a step with no note is a rest.
"""

from rich.text import Text

from llamatron.composition.checks import is_written_length
from llamatron.composition.file_format import (
    CC_ROWS, CHORD_SYMBOLS, DIRECTIONS, FORWARD, GATE_LENGTH_CHOICES, NOTE_LETTERS, REGISTER_ADD_ROWS,
    REGISTER_NOTE_ROWS, REGISTER_VELOCITY_ROWS, TOGGLE_ROWS, ChordSymbol, GateModifier,
)
from llamatron.composition.limits import MAX_GATE, MAX_REGISTER_VALUE, MAX_STEP_SIZE, MIN_REGISTER_VALUE
from llamatron.tui.base import ChoiceDialog, ConfirmDialog, GridChoiceDialog, Page, PromptDialog, columns, fit, grouped_grid, key, pressed_key
from llamatron.composition.defaults import DEFAULT_PROBABILITY, DEFAULT_RATCHET, DEFAULT_VELOCITY
from llamatron.tui.document import DIRECTION_NAMES, fraction, fraction_text

# How each register's rows are labelled: AX+Note moves the note by AX, AX+Vel adds AX to the
# velocity, and AX+= adds to AX.
REGISTER_NOTE_LABEL = '{name}+Note'
REGISTER_VELOCITY_LABEL = '{name}+Vel'
REGISTER_ADD_LABEL = '{name}+='


def register_labels(rows, label):
    """Return each register's row in a group of register rows with its label, like ax_note with AX+Note."""
    return {row: label.format(name=name) for name, row in rows.items()}


# The rows on screen. Degree always shows, and the rest depend on the set of rows showing.
ROW_LABELS = {
    'degree': 'Degree', 'gate': 'Gate', 'dot': 'Dot', 'accidental': '#/b', 'octave': 'Octave', 'chord': 'Chord',
    'velocity': 'Velocity', 'probability': 'Prob', 'glide': 'Glide', 'ratchet': 'Ratchet',
    'ratchet_offset': 'Ratchet Offset', 'grab': 'Grab',
    'cc1': 'CC 1', 'cc2': 'CC 2', 'cc3': 'CC 3', 'cc4': 'CC 4', 'slide': 'Slide',
    **register_labels(REGISTER_NOTE_ROWS, REGISTER_NOTE_LABEL),
    **register_labels(REGISTER_VELOCITY_ROWS, REGISTER_VELOCITY_LABEL),
    **register_labels(REGISTER_ADD_ROWS, REGISTER_ADD_LABEL),
}
NORMAL_ROWS = ['degree', 'gate', 'dot', 'accidental', 'octave', 'chord', 'velocity', 'probability', 'glide']
ADVANCED_ROWS = ['degree', 'ratchet', 'ratchet_offset', 'grab']
CC_SET = ['degree', 'cc1', 'cc2', 'cc3', 'cc4', 'slide']
# The rows that use the registers' values, and then the rows that change them.
REGISTER_SET = ['degree', *REGISTER_NOTE_ROWS.values(), *REGISTER_VELOCITY_ROWS.values()]
REGISTER_CHANGE_SET = ['degree', *REGISTER_ADD_ROWS.values()]
# The sets of rows under Degree that PgUp and PgDn step through, in order, and what each is called on screen.
NORMAL = 'normal'
ADVANCED = 'advanced'
CC = 'cc'
REGISTERS = 'registers'
REGISTER_CHANGES = 'register_changes'
ROW_SETS = {NORMAL: NORMAL_ROWS, ADVANCED: ADVANCED_ROWS, CC: CC_SET, REGISTERS: REGISTER_SET, REGISTER_CHANGES: REGISTER_CHANGE_SET}
ROW_SET_NAMES = {
    NORMAL: 'normal rows', ADVANCED: 'advanced rows', CC: 'CC rows', REGISTERS: 'registers', REGISTER_CHANGES: 'register changes',
}
# Rows that don't belong in a drum pattern, which has no chords and no scale to move notes along.
NOT_FOR_DRUMS = ('chord', *REGISTER_NOTE_ROWS.values())
# Rows that a rest can hold, because CC values and register changes don't need a note.
REST_EDITABLE = (*CC_ROWS, 'slide', *REGISTER_ADD_ROWS.values())
# What the second line of the header says for each set of rows, besides the normal ones.
ROW_SET_HEADERS = {
    ADVANCED: "Advanced rows: Grab plays what each clip's Grab track last played",
    CC: 'CC rows: each track sets which CC number each row sends',
    REGISTERS: "Registers: +Note moves the note along the scale by the register's value, +Vel adds it to the velocity",
    REGISTER_CHANGES: 'Register changes: each step adds to the registers as it plays, even an empty one',
}
TOGGLE_ON, TOGGLE_OFF = '*', ' '
DRUM_LETTER_ROW = 'Note'
ACCIDENTAL_CYCLE = [None, '#', 'b']
# The Dot row's values in the order + steps through them: none, dotted, then triplet.
DOT_CYCLE = [None, GateModifier.DOTTED, GateModifier.TRIPLET]
# A gate that's doubled or halved stays between the shortest and longest gate lengths offered.
SHORTEST_GATE = GATE_LENGTH_CHOICES[0]
MSG_NOT_A_LENGTH = '{text!r} is not a whole number or a fraction like 1/8.'
MSG_LENGTH_OUT_OF_RANGE = 'A length must be more than 0 and at most {most}.'
GATE_PROMPT, STEP_SIZE_PROMPT = 'Gate', "Step size (blank for the song's)"
DESCRIBE_EMPTY = 'Step {step}: empty'
DESCRIBE_NOTE = 'Step {step}: {sound}, gate {gate}{chord}'
DESCRIBE_CHORD = ', chord {chord}'
DOT_NAMES = {GateModifier.DOTTED: ' dotted', GateModifier.TRIPLET: ' triplet'}
STEP_SIZE_SHOWN = 'Step size {size}{whose}'
SONG_STEP_SIZE_SHOWN = " (the song's)"
CELL_WIDTH = 5
MIN_OCTAVE, MAX_OCTAVE = -2, 8
NUMBER_RANGE = {
    'velocity': (1, 127), 'probability': (0, 100), 'ratchet': (1, 16),
    'ratchet_offset': (-24, 24),
    'cc1': (0, 127), 'cc2': (0, 127), 'cc3': (0, 127), 'cc4': (0, 127),
    **dict.fromkeys(REGISTER_ADD_ROWS.values(), (MIN_REGISTER_VALUE, MAX_REGISTER_VALUE)),
}
NUMBER_DEFAULT = {
    'velocity': DEFAULT_VELOCITY, 'probability': DEFAULT_PROBABILITY, 'ratchet': DEFAULT_RATCHET,
    'ratchet_offset': 0,
    'cc1': 64, 'cc2': 64, 'cc3': 64, 'cc4': 64,
    **dict.fromkeys(REGISTER_ADD_ROWS.values(), 0),
}
# Rows whose default means nothing happens, so that they show a dot until they're set.
QUIET_ROWS = ('ratchet', 'ratchet_offset', *CC_ROWS, *REGISTER_ADD_ROWS.values())
DIGITS = tuple('0123456789')
# The chord picker's columns, which hold every chord symbol in the order + steps through them.
# The chord picker's groups, each a heading and its symbols, in the order the picker shows them.
CHORD_GROUPS = [
    ('TRIADS', [
        ChordSymbol.MAJOR, ChordSymbol.MINOR, ChordSymbol.DIMINISHED, ChordSymbol.AUGMENTED, ChordSymbol.SUS2,
        ChordSymbol.SUS4, ChordSymbol.POWER, ChordSymbol.MAJOR6, ChordSymbol.MINOR6,
    ]),
    ('SEVENTHS', [
        ChordSymbol.DOMINANT7, ChordSymbol.MAJOR7, ChordSymbol.MINOR7, ChordSymbol.MINOR_MAJOR7, ChordSymbol.DIMINISHED7,
        ChordSymbol.HALF_DIMINISHED7, ChordSymbol.AUGMENTED7, ChordSymbol.AUGMENTED_MAJOR7, ChordSymbol.DOMINANT7_SUS4,
    ]),
    ('NINTHS', [ChordSymbol.DOMINANT9, ChordSymbol.MAJOR9, ChordSymbol.MINOR9, ChordSymbol.ADD9, ChordSymbol.MINOR_ADD9]),
    ('11THS, 13THS', [
        ChordSymbol.DOMINANT11, ChordSymbol.MAJOR11, ChordSymbol.MINOR11,
        ChordSymbol.DOMINANT13, ChordSymbol.MAJOR13, ChordSymbol.MINOR13,
    ]),
    ('SCALE', [
        ChordSymbol.SCALE_FIFTH, ChordSymbol.SCALE_TRIAD, ChordSymbol.SCALE_SEVENTH,
        ChordSymbol.SCALE_NINTH, ChordSymbol.SCALE_ELEVENTH, ChordSymbol.SCALE_THIRTEENTH,
    ]),
]
# What each chord symbol means, as the editor describes it.
CHORD_NAMES = {
    ChordSymbol.MAJOR: 'major', ChordSymbol.MINOR: 'minor', ChordSymbol.DIMINISHED: 'diminished',
    ChordSymbol.AUGMENTED: 'augmented', ChordSymbol.SUS2: 'suspended second', ChordSymbol.SUS4: 'suspended fourth',
    ChordSymbol.POWER: 'power, root and fifth', ChordSymbol.MAJOR6: 'major sixth', ChordSymbol.MINOR6: 'minor sixth',
    ChordSymbol.DOMINANT7: 'dominant seventh', ChordSymbol.MAJOR7: 'major seventh', ChordSymbol.MINOR7: 'minor seventh',
    ChordSymbol.MINOR_MAJOR7: 'minor-major seventh', ChordSymbol.DIMINISHED7: 'diminished seventh',
    ChordSymbol.HALF_DIMINISHED7: 'half-diminished', ChordSymbol.AUGMENTED7: 'augmented seventh',
    ChordSymbol.AUGMENTED_MAJOR7: 'augmented major seventh', ChordSymbol.DOMINANT7_SUS4: 'seventh, suspended fourth',
    ChordSymbol.ADD9: 'added ninth', ChordSymbol.MINOR_ADD9: 'minor added ninth',
    ChordSymbol.DOMINANT9: 'dominant ninth', ChordSymbol.MAJOR9: 'major ninth', ChordSymbol.MINOR9: 'minor ninth',
    ChordSymbol.DOMINANT11: 'dominant eleventh', ChordSymbol.MAJOR11: 'major eleventh', ChordSymbol.MINOR11: 'minor eleventh',
    ChordSymbol.DOMINANT13: 'dominant thirteenth', ChordSymbol.MAJOR13: 'major thirteenth', ChordSymbol.MINOR13: 'minor thirteenth',
    ChordSymbol.SCALE_FIFTH: 'root and fifth from the scale', ChordSymbol.SCALE_TRIAD: 'triad from the scale',
    ChordSymbol.SCALE_SEVENTH: 'seventh from the scale', ChordSymbol.SCALE_NINTH: 'ninth from the scale',
    ChordSymbol.SCALE_ELEVENTH: 'eleventh from the scale', ChordSymbol.SCALE_THIRTEENTH: 'thirteenth from the scale',
}


def _chord_text(value):
    return None if value is None else str(value)


def _chord_value(text):
    """Return a chord symbol the way a file holds it, where the scale's chords are numbers."""
    return int(text) if text and text.isdigit() else text


class PatternEditor(Page):
    HELP = (
        'Each column is one step, as long as the step size, which E sets. Typing never moves the cursor.',
        '',
        'Degree: 1 is the scale\'s root. Bksp empties the step.',
        'Gate: how long the note sounds, one step if blank. + and - step through lengths, * and / double and halve, Enter types one.',
        'Dot: d is dotted, t a triplet. Octave: as Live numbers them.',
        'Chord: Enter shows them, and 3 or 7 use the scale.',
        'Velocity, Prob: type numbers. Glide (*): runs into the next note.',
        '',
        'PgUp/PgDn change rows. Advanced: Ratchet splits a step, Ratchet Offset moves each slice, Grab takes another track\'s note.',
        'CC 1 to 4 send values even on rests. Slide ramps them on.',
        'AX+= adds to AX. AX+Note, AX+Vel add it to the note or velocity.',
        'F reverses every step after the cursor, and S swaps both sides of it. L loads another pattern over this one.',
    )

    def __init__(self, holder, name):
        super().__init__(holder)
        self.item = name
        self.step = 0
        self.row = 0
        self.crumbs = ('PATTERNS', name)
        self.top_block = 0
        # The digits typed so far into the current cell, so that 1 and then 2 makes 12.
        self.typed = ''

    def on_key(self, event):
        name = pressed_key(event)
        if not (name and name.isdigit()):
            self.typed = ''
        super().on_key(event)

    def duration(self):
        return self.document.pattern_seconds(self.item)

    # What's under the cursor.

    def pattern(self):
        return self.document.data['patterns'][self.item]

    def is_drum(self):
        return bool(self.pattern().get('drum'))

    def rows(self):
        """Return the rows on screen. Chords and moving notes by registers aren't used in a drum pattern."""
        names = ROW_SETS[self.holder.row_set]
        if self.is_drum():
            names = [name for name in names if name not in NOT_FOR_DRUMS]
        return [(name, DRUM_LETTER_ROW if self.is_drum() and name == 'degree' else ROW_LABELS[name]) for name in names]

    def row_name(self):
        return self.rows()[self.row][0]

    def value(self, row=None, step=None):
        return self.document.step_value(self.item, row or self.row_name(), self.step if step is None else step)

    def is_note(self, step=None):
        return self.value('degree', step) is not None

    def steps(self):
        return self.pattern()['steps']

    def clamp(self):
        self.step = max(min(self.step, self.steps() - 1), 0)
        self.row = max(min(self.row, len(self.rows()) - 1), 0)

    def set_value(self, value, row=None, step=None):
        self.document.set_step_value(self.item, row or self.row_name(), self.step if step is None else step, value)

    # The keys, which depend on the row.

    def keys(self):
        self.clamp()
        result = [key(('left', 'right', 'up', 'down'), 'move', self.move, label='←↑↓→', wants_key=True)]
        result += self.row_keys()
        result.append(key(('pageup', 'pagedown'), ROW_SET_NAMES[self.next_row_set(1)], self.change_row_set, label='PgUp/PgDn', wants_key=True))
        # On a drum pattern's Note row, the letter F is a note.
        on_letters = self.is_drum() and self.row_name() == 'degree'
        if not on_letters:
            result.append(key('f', 'flip after', self.flip))
        result += [key('s', 'swap sides', self.swap), key('l', 'load over', self.load_over)]
        result += [
            key('r', 'resize', self.ask_steps),
            key('e', 'step size', self.ask_step_size),
            key('t', 'drum on' if not self.is_drum() else 'drum off', self.toggle_drum),
            key('p', 'direction', self.pick_direction),
            key('i', 'insert step', self.insert_step),
        ]
        if self.steps() > 1:
            result.append(key('x', 'remove step', self.remove_step))
        result += [key('n', 'rename', self.rename), key('tab', 'back', self.go_back)]
        return result

    def row_keys(self):
        name = self.row_name()
        if name == 'degree':
            return self.degree_keys()
        if not self.is_note() and name not in REST_EDITABLE:
            return []
        if name == 'gate':
            return [
                key(('+', '='), 'longer', lambda: self.nudge_gate(1), label='+'),
                key('-', 'shorter', lambda: self.nudge_gate(-1)),
                key('*', 'double', lambda: self.scale_gate(2)),
                key('/', 'halve', lambda: self.scale_gate(0.5)),
                key('enter', 'type', self.ask_gate),
                key('backspace', 'one step', lambda: self.set_value(None)),
            ]
        if name == 'dot':
            return [
                key(('space', '+', '='), 'next', lambda: self.cycle_dot(1), label='Space/+'),
                key('-', 'back', lambda: self.cycle_dot(-1)),
                key('backspace', 'clear', lambda: self.set_value(None)),
            ]
        if name == 'accidental':
            return [
                key(('space', '+', '='), 'next', lambda: self.cycle_accidental(1), label='Space/+'),
                key('-', 'back', lambda: self.cycle_accidental(-1)),
                key('backspace', 'clear', lambda: self.set_value(None)),
            ]
        if name == 'octave':
            return [
                key(DIGITS, 'type octave', lambda digit: self.type_number(digit, MIN_OCTAVE, MAX_OCTAVE), label='0-8', wants_key=True),
                key(('+', '='), 'up', lambda: self.nudge_octave(1), label='+'),
                key('-', 'down', lambda: self.nudge_octave(-1)),
                key('backspace', 'default', lambda: self.set_value(None)),
            ]
        if name == 'chord':
            return [
                key('enter', 'choose', self.pick_chord),
                key(('space', '+', '='), 'next', lambda: self.cycle_chord(1), label='Space/+'),
                key('-', 'back', lambda: self.cycle_chord(-1)),
                key('backspace', 'clear', lambda: self.set_value(None)),
            ]
        if name in TOGGLE_ROWS:
            return [
                key('space', 'toggle', self.toggle_glide),
                key('backspace', 'clear', lambda: self.set_value(False)),
            ]
        low, high = NUMBER_RANGE[name]
        return [
            key(DIGITS, 'type', lambda digit: self.type_number(digit, low, high), label='0-9', wants_key=True),
            key(('+', '='), 'more', lambda: self.nudge_number(1), label='+'),
            key('-', 'less', lambda: self.nudge_number(-1)),
            key('enter', 'type', self.ask_number),
            key('backspace', 'default', lambda: self.set_value(None)),
        ]

    def degree_keys(self):
        if self.is_drum():
            result = [key(tuple(NOTE_LETTERS.lower()), 'note', self.type_letter, label='A-G', wants_key=True)]
        else:
            limit = self.document.degree_limit(self.item)
            digits = DIGITS if limit > 9 else tuple(str(number) for number in range(1, limit + 1))
            result = [
                key(digits, 'degree', self.type_degree, label=f'1-{limit}', wants_key=True),
                key(('+', '='), 'up', lambda: self.nudge_degree(1), label='+'),
                key('-', 'down', lambda: self.nudge_degree(-1)),
            ]
        if self.is_note():
            result.append(key('backspace', 'to rest', self.clear_degree))
        return result

    # Moving, which is the only thing that moves the cursor.

    def move(self, name):
        rows = len(self.rows())
        if name == 'left':
            self.step = (self.step - 1) % max(self.steps(), 1)
        elif name == 'right':
            self.step = (self.step + 1) % max(self.steps(), 1)
        elif name == 'up':
            self.row = (self.row - 1) % rows
        else:
            self.row = (self.row + 1) % rows

    # Editing each row.

    def fill_in(self):
        """Give a new note what every note has: an octave. Its gate starts blank, which is one step."""
        if self.value('octave') is None:
            setting = 'default_drum_octave' if self.is_drum() else 'default_octave'
            self.set_value(self.document.data[setting], 'octave')

    def typed_number(self, digit, low, high):
        """Return the number made by another digit, or just that digit if it would be too big."""
        for text in (self.typed + digit, digit):
            if low <= int(text) <= high:
                self.typed = text
                return int(text)
        self.typed = ''
        return None

    def type_number(self, digit, low, high):
        number = self.typed_number(digit, low, high)
        if number is not None:
            self.set_value(number)

    def type_degree(self, digit):
        number = self.typed_number(digit, 1, self.document.degree_limit(self.item))
        if number is not None:
            self.set_value(number, 'degree')
            self.fill_in()

    def type_letter(self, letter):
        self.set_value(letter.upper(), 'degree')
        self.fill_in()

    def nudge_degree(self, offset):
        limit = self.document.degree_limit(self.item)
        current = self.value('degree') or 0
        self.set_value(max(min(current + offset, limit), 1), 'degree')
        self.fill_in()

    def clear_degree(self):
        self.document.clear_sound(self.item, self.step)

    def gate_now(self, step=None):
        """Return a step's gate before its Dot row, which is one step if it has none."""
        current = self.value('gate', step)
        return self.document.step_size(self.item) if current is None else fraction(current)

    def nudge_gate(self, offset):
        """Set the gate to the next plain length longer or shorter than it is now."""
        now = self.gate_now()
        lengths = [fraction(length) for length in GATE_LENGTH_CHOICES]
        if offset > 0:
            choices = [length for length in lengths if length > now] or [lengths[-1]]
            self.set_value(fraction_text(choices[0]), 'gate')
        else:
            choices = [length for length in lengths if length < now] or [lengths[0]]
            self.set_value(fraction_text(choices[-1]), 'gate')

    def scale_gate(self, factor):
        new = self.gate_now() * 2 if factor == 2 else self.gate_now() / 2
        new = max(min(new, MAX_GATE), fraction(SHORTEST_GATE))
        self.set_value(fraction_text(new), 'gate')

    def ask_gate(self):
        self.ask_length(GATE_PROMPT, self.value('gate') or '', MAX_GATE, lambda text: self.set_value(text, 'gate'), blank_allowed=False)

    def ask_step_size(self):
        current = self.pattern().get('step_size') or ''
        self.ask_length(STEP_SIZE_PROMPT, current, MAX_STEP_SIZE, lambda text: self.document.set_step_size(self.item, text), blank_allowed=True)

    def ask_length(self, title, current, most, then, blank_allowed):
        """Ask for a length, a whole number or a fraction like 5/16, and pass it on if it's in range."""
        def answered(text):
            text = text.strip()
            if not text and blank_allowed:
                then(None)
                return
            if not is_written_length(text) or not 0 < fraction(text) <= most:
                self.status = (MSG_LENGTH_OUT_OF_RANGE.format(most=most) if is_written_length(text) else MSG_NOT_A_LENGTH.format(text=text))
                return
            then(fraction_text(fraction(text)))
        self.ask(PromptDialog(title, current), answered)

    def cycle_dot(self, offset):
        place = DOT_CYCLE.index(self.value())
        self.set_value(DOT_CYCLE[(place + offset) % len(DOT_CYCLE)])

    def cycle_accidental(self, offset):
        place = ACCIDENTAL_CYCLE.index(self.value())
        self.set_value(ACCIDENTAL_CYCLE[(place + offset) % len(ACCIDENTAL_CYCLE)])

    def pick_chord(self):
        options = [None, *CHORD_SYMBOLS]
        labels = ['(none)', *CHORD_SYMBOLS]
        details = ['No chord, just the note', *[CHORD_NAMES[symbol] for symbol in CHORD_SYMBOLS]]
        details = [text[0].upper() + text[1:] for text in details]
        grid = grouped_grid([[(heading, [labels.index(symbol) for symbol in symbols])] for heading, symbols in CHORD_GROUPS])
        self.ask(
            GridChoiceDialog('Chord', labels, grid, options.index(_chord_text(self.value())), lambda place: details[place], top=[0]),
            lambda chosen: self.set_value(_chord_value(options[chosen])),
        )

    def cycle_chord(self, offset):
        options = [None, *CHORD_SYMBOLS]
        place = options.index(_chord_text(self.value()))
        self.set_value(_chord_value(options[(place + offset) % len(options)]))

    def octave_now(self):
        current = self.value()
        if current is not None:
            return current
        return self.document.data['default_drum_octave' if self.is_drum() else 'default_octave']

    def nudge_octave(self, offset):
        self.set_value(max(min(self.octave_now() + offset, MAX_OCTAVE), MIN_OCTAVE))

    def number_now(self):
        name = self.row_name()
        current = self.value()
        return NUMBER_DEFAULT[name] if current is None else current

    def nudge_number(self, offset):
        name = self.row_name()
        low, high = NUMBER_RANGE[name]
        self.set_value(max(min(self.number_now() + offset, high), low))

    def ask_number(self):
        name = self.row_name()
        low, high = NUMBER_RANGE[name]

        def answered(text):
            try:
                number = int(text.strip())
            except ValueError:
                self.status = f'{text!r} is not a whole number.'
                return
            if low <= number <= high:
                self.set_value(number)
            else:
                self.status = f'{ROW_LABELS[name]} must be from {low} to {high}.'
        self.ask(PromptDialog(f'{ROW_LABELS[name]} ({low} to {high})', self.number_now()), answered)

    def pick_direction(self):
        current = self.pattern().get('direction', FORWARD)
        labels = columns([(name.replace('_', ' '), DIRECTION_NAMES[name]) for name in DIRECTIONS])
        self.ask(
            ChoiceDialog('Play direction', labels, DIRECTIONS.index(current)),
            lambda chosen: self.document.set_direction(self.item, DIRECTIONS[chosen]),
        )

    def next_row_set(self, offset):
        """Return the set of rows after the one showing, or before it if offset is -1, going round."""
        names = list(ROW_SETS)
        return names[(names.index(self.holder.row_set) + offset) % len(names)]

    def change_row_set(self, pressed):
        """Switch to the next rows under Degree with PgDn, or the ones before with PgUp, staying on the same row if they have it."""
        name = self.row_name()
        self.holder.row_set = self.next_row_set(-1 if pressed == 'pageup' else 1)
        names = [row for row, _ in self.rows()]
        self.row = names.index(name) if name in names else 0

    def flip(self):
        if self.step >= self.steps() - 1:
            self.status = 'There are no steps after this one to flip.'
            return
        self.document.flip_after(self.item, self.step)

    def swap(self):
        if self.steps() < 2:
            self.status = 'There are no other steps to swap.'
            return
        self.step = self.document.swap_around(self.item, self.step)

    def load_over(self):
        others = [name for name in self.document.data['patterns'] if name != self.item]
        if not others:
            self.status = 'There are no other patterns to load.'
            return

        def load(name):
            self.document.load_over(self.item, name)
            self.row = 0
            self.clamp()

        def chosen(place):
            name = others[place]
            if self.document.has_notes(self.item):
                self.ask(ConfirmDialog('Load over', [f'Replace everything in {self.item} with a copy of {name}?']), lambda _: load(name))
            else:
                load(name)
        self.ask(ChoiceDialog(f'Load over {self.item}', others), chosen)

    def toggle_glide(self):
        self.set_value(not self.value())

    # The whole pattern.

    def ask_steps(self):
        def answered(text):
            try:
                steps = int(text.strip())
            except ValueError:
                self.status = f'{text!r} is not a whole number.'
                return
            if not 1 <= steps <= 4096:
                self.status = 'Steps must be from 1 to 4096.'
                return
            lost = self.document.steps_with_anything_past(self.item, steps)
            if lost:
                self.ask(ConfirmDialog('Shorten pattern', [f'This removes {lost} step(s) that hold something. Continue?']), lambda _: self.document.set_steps(self.item, steps))
            else:
                self.document.set_steps(self.item, steps)
        self.ask(PromptDialog('Number of steps', self.steps()), answered)

    def toggle_drum(self):
        drum = not self.is_drum()

        def change(_=None):
            self.document.set_drum(self.item, drum)
            self.row = 0
        if self.document.has_notes(self.item):
            what = 'letters' if drum else 'scale degrees'
            self.ask(ConfirmDialog('Change pattern type', [f'This pattern will use {what}, which clears the notes it has now. Continue?']), change)
        else:
            change()

    def insert_step(self):
        self.document.insert_step(self.item, self.step)

    def remove_step(self):
        self.document.remove_step(self.item, self.step)
        self.clamp()

    def rename(self):
        def named(text):
            text = text.strip()
            patterns = self.document.data['patterns']
            if not text or (text != self.item and text in patterns):
                self.status = 'That name is empty or already in use.'
            elif text != self.item:
                self.document.rename_pattern(self.item, text)
                self.item = text
                self.crumbs = ('PATTERNS', text)
        self.ask(PromptDialog('Rename pattern', self.item), named)

    # Drawing.

    def cell_text(self, name, step):
        """Return what one cell shows. Rests are blank, and values that aren't set show a dot."""
        value = self.value(name, step)
        note = self.is_note(step)
        if name == 'degree':
            return '' if value is None else str(value)
        if name in ('gate', 'dot'):
            return '' if not note or value is None else str(value)
        if name in TOGGLE_ROWS and (note or name in REST_EDITABLE):
            return TOGGLE_ON if value else TOGGLE_OFF
        if not note and name not in REST_EDITABLE:
            return ''
        if name == 'octave':
            return str(self.document.data['default_drum_octave' if self.is_drum() else 'default_octave'] if value is None else value)
        if name in NUMBER_DEFAULT:
            if value is None:
                return '.' if name in QUIET_ROWS else str(NUMBER_DEFAULT[name])
            return str(value)
        return '.' if value is None else str(value)

    def label_width(self):
        return max(len(label) for _, label in self.rows()) + 2

    def steps_per_block(self, width):
        return max((width - self.label_width() - 2) // (CELL_WIDTH + 1), 1)

    def header_lines(self):
        pattern = self.pattern()
        drum = '[x]' if pattern.get('drum') else '[ ]'
        scale = 'no scale needed' if pattern.get('drum') else f"song: {self.document.data.get('scale') or 'none'}, or the scene's"
        direction = pattern.get('direction', FORWARD).replace('_', ' ')
        extra = ROW_SET_HEADERS.get(self.holder.row_set, f'Scale {scale}')
        whose = '' if pattern.get('step_size') else SONG_STEP_SIZE_SHOWN
        step_size = STEP_SIZE_SHOWN.format(size=fraction_text(self.document.step_size(self.item)), whose=whose)
        return [
            Text(f'  Steps {pattern["steps"]}    {step_size}    Drum {drum}    Direction {direction}', no_wrap=True),
            Text(f'  {extra}', no_wrap=True),
        ]

    def block_lines(self, first, last):
        LABEL_WIDTH = self.label_width()
        rule_top = Text('┌' + '─' * LABEL_WIDTH + ('┬' + '─' * CELL_WIDTH) * (last - first) + '┐', style='dim', no_wrap=True)
        rule_bottom = Text('└' + '─' * LABEL_WIDTH + ('┴' + '─' * CELL_WIDTH) * (last - first) + '┘', style='dim', no_wrap=True)
        head = Text(no_wrap=True)
        head.append('│', style='dim')
        head.append(fit(' Step', LABEL_WIDTH), style='bold')
        for step in range(first, last):
            head.append('│', style='dim')
            head.append(fit(str(step + 1), CELL_WIDTH, 'center'), style='bold')
        head.append('│', style='dim')
        lines = [rule_top, head]
        for place, (name, label) in enumerate(self.rows()):
            line = Text(no_wrap=True)
            line.append('│', style='dim')
            line.append(fit(f' {label}', LABEL_WIDTH), style='bold' if place == self.row else '')
            for step in range(first, last):
                line.append('│', style='dim')
                text = fit(self.cell_text(name, step), CELL_WIDTH, 'center')
                selected = step == self.step and place == self.row
                line.append(text, style='reverse' if selected else '')
            line.append('│', style='dim')
            lines.append(line)
        lines.append(rule_bottom)
        return lines

    def describe(self):
        step = self.step + 1
        if not self.is_note():
            return DESCRIBE_EMPTY.format(step=step)
        where = '' if self.is_drum() else f' in {self.document.data.get("scale") or "no scale"}'
        played = self.document.note_name(self.item, self.step)
        sound = f'{played}{where}' if played else f'degree {self.value("degree")}, no scale'
        chord = self.value('chord')
        chord_text = DESCRIBE_CHORD.format(chord=chord) if chord is not None else ''
        gate = str(fraction_text(self.gate_now())) + DOT_NAMES.get(self.value('dot'), '')
        return DESCRIBE_NOTE.format(step=step, sound=sound, gate=gate, chord=chord_text)

    def body(self, width, height):
        self.clamp()
        per_block = self.steps_per_block(width)
        lines = self.header_lines()
        block_height = len(self.rows()) + 3
        blocks = max((height - len(lines) - 2) // block_height, 1)
        block = self.step // per_block
        if block < self.top_block:
            self.top_block = block
        elif block >= self.top_block + blocks:
            self.top_block = block - blocks + 1
        for number in range(self.top_block, self.top_block + blocks):
            first = number * per_block
            if first >= self.steps():
                break
            lines += self.block_lines(first, min(first + per_block, self.steps()))
        lines += [Text(''), Text(' ' + fit(self.describe(), width - 1), style='bold')]
        return lines

