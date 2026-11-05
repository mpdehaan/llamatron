# noose6: a Python language and framework for producing MIDI clips.
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
cursor. Each step has its own duration, so steps aren't fixed slices of time. A step with nothing
to play is a rest, and is shown as a blank, and every step takes time.
"""

from rich.text import Text

from src.song_file import CHORD_SYMBOLS, DEFAULT_ACCUMULATOR_LIMIT, DIRECTIONS, FORWARD, NOTE_LETTERS
from src.tui.base import ChoiceDialog, ConfirmDialog, Page, PromptDialog, columns, fit, key, pressed_key
from src.tui.document import (
    DEFAULT_PROBABILITY, DEFAULT_RATCHET, DEFAULT_VELOCITY, DIRECTION_NAMES, fraction, fraction_text,
)

# The rows on screen. Degree always shows, and the rest depend on the mode.
ROW_LABELS = {
    'degree': 'Degree', 'duration': 'Duration', 'accidental': '#/b', 'octave': 'Octave', 'chord': 'Chord',
    'velocity': 'Velocity', 'probability': 'Prob', 'glide': 'Glide', 'ratchet': 'Ratchet',
    'ratchet_offset': 'Ratchet Offset', 'note_add': 'Note Add', 'velocity_add': 'Velocity Add', 'grab': 'Grab',
}
NORMAL_ROWS = ['degree', 'duration', 'accidental', 'octave', 'chord', 'velocity', 'probability', 'glide']
ADVANCED_ROWS = ['degree', 'ratchet', 'ratchet_offset', 'note_add', 'velocity_add', 'grab']
DRUM_LETTER_ROW = 'Note'
ACCIDENTAL_CYCLE = [None, '#', 'b']
CELL_WIDTH = 5
MIN_OCTAVE, MAX_OCTAVE = -2, 8
NUMBER_RANGE = {
    'velocity': (1, 127), 'probability': (0, 100), 'ratchet': (1, 16), 'ratchet_offset': (-24, 24),
    'note_add': (-24, 24), 'velocity_add': (-127, 127),
}
NUMBER_DEFAULT = {
    'velocity': DEFAULT_VELOCITY, 'probability': DEFAULT_PROBABILITY, 'ratchet': DEFAULT_RATCHET,
    'ratchet_offset': 0, 'note_add': 0, 'velocity_add': 0,
}
# Rows whose default means nothing happens, so that they show a dot until they're set.
QUIET_ROWS = ('ratchet', 'ratchet_offset', 'note_add', 'velocity_add')
DIGITS = tuple('0123456789')
CHORD_NAMES = {
    'M': 'major', 'm': 'minor', 'M7': 'major seventh', 'm7': 'minor seventh', 'dim': 'diminished',
    'sus4': 'suspended fourth', '3': 'triad from the scale', '7': 'seventh from the scale',
}


def _chord_text(value):
    return None if value is None else str(value)


def _chord_value(text):
    """Return a chord symbol the way a file holds it, where the scale's chords are numbers."""
    return int(text) if text and text.isdigit() else text


class PatternEditor(Page):
    HELP = (
        'Each column is a step with its own Duration. The grid does not grow as you type. Arrows move, and typing never moves the cursor.',
        '',
        'Degree: 1 is the root of the scale. Bksp makes a rest, shown as a blank.',
        'Duration: + and - use the Granularity. * doubles and / halves.',
        'Octave: exactly the octave you type, as Live numbers them.',
        'Chord: Enter shows the chords. 3 and 7 build from the scale.',
        'Velocity, Prob: type numbers. Glide: slides into the next note.',
        '',
        'A switches to advanced rows. Ratchet splits a step into quick notes, and Ratchet Offset moves each along the scale. Note Add and Velocity Add build up a running total. O sets a source pattern for the Grab row.',
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
        """Return the rows on screen. Chords aren't used in a drum pattern."""
        names = ADVANCED_ROWS if self.holder.advanced_rows else NORMAL_ROWS
        names = [
            name for name in names
            if not (self.is_drum() and name == 'chord') and not (name == 'grab' and not self.pattern().get('source_pattern'))
        ]
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
        # On a drum pattern's Note row, the letters A and F are notes.
        on_letters = self.is_drum() and self.row_name() == 'degree'
        if not on_letters:
            result.append(key('a', 'normal rows' if self.holder.advanced_rows else 'advanced rows', self.toggle_advanced))
            result.append(key('f', 'flip after', self.flip))
        result += [key('s', 'swap sides', self.swap), key('l', 'load over', self.load_over)]
        if self.holder.advanced_rows:
            result += [key('o', 'source', self.pick_source), key('m', 'add limit', self.ask_limit)]
        result += [
            key('r', 'resize', self.ask_steps),
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
        if name == 'duration':
            return [
                key(('+', '='), 'longer', lambda: self.nudge_duration(1), label='+'),
                key('-', 'shorter', lambda: self.nudge_duration(-1)),
                key('*', 'double', lambda: self.scale_duration(2)),
                key('/', 'halve', lambda: self.scale_duration(0.5)),
                key('backspace', 'default', self.reset_duration),
            ]
        if not self.is_note():
            return []
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
        if name in ('glide', 'grab'):
            return [
                key('space', 'toggle', self.toggle_glide),
                key('backspace', 'clear', lambda: self.set_value(None)),
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
        """Give a new note what every note has: the default duration and octave."""
        if self.value('duration') is None:
            self.set_value(self.document.data['default_length'], 'duration')
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

    def granularity(self):
        return fraction(self.document.data['granularity'])

    def duration_now(self, step=None):
        """Return a step's duration, which is the song's default if the step doesn't have one."""
        current = self.value('duration', step)
        return fraction(self.document.data['default_length'] if current is None else current)

    def nudge_duration(self, offset):
        new = self.duration_now() + offset * self.granularity()
        self.set_value(fraction_text(max(new, self.granularity())), 'duration')

    def scale_duration(self, factor):
        new = self.duration_now() * 2 if factor == 2 else self.duration_now() / 2
        self.set_value(fraction_text(max(new, self.granularity())), 'duration')

    def reset_duration(self):
        self.set_value(self.document.data['default_length'], 'duration')

    def cycle_accidental(self, offset):
        place = ACCIDENTAL_CYCLE.index(self.value())
        self.set_value(ACCIDENTAL_CYCLE[(place + offset) % len(ACCIDENTAL_CYCLE)])

    def pick_chord(self):
        options = [None, *CHORD_SYMBOLS]
        labels = columns([('(none)', ''), *[(symbol, CHORD_NAMES[symbol]) for symbol in CHORD_SYMBOLS]])
        self.ask(
            ChoiceDialog('Chord', labels, options.index(_chord_text(self.value()))),
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
                self.status = f'{name.capitalize()} must be from {low} to {high}.'
        self.ask(PromptDialog(f'{name.capitalize()} ({low} to {high})', self.number_now()), answered)

    def pick_direction(self):
        current = self.pattern().get('direction', FORWARD)
        labels = columns([(name.replace('_', ' '), DIRECTION_NAMES[name]) for name in DIRECTIONS])
        self.ask(
            ChoiceDialog('Play direction', labels, DIRECTIONS.index(current)),
            lambda chosen: self.document.set_direction(self.item, DIRECTIONS[chosen]),
        )

    def pick_source(self):
        patterns = list(self.document.data['patterns'])
        options = ['(none)', *patterns]
        current = self.pattern().get('source_pattern')
        place = options.index(current) if current in options else 0

        def chosen(item):
            self.document.set_source_pattern(self.item, None if item == 0 else patterns[item - 1])
            self.clamp()
        self.ask(ChoiceDialog('Source pattern for the Grab row', options, place), chosen)

    def toggle_advanced(self):
        """Switch the rows under Degree, staying on the same row if the other mode has it."""
        name = self.row_name()
        self.holder.advanced_rows = not self.holder.advanced_rows
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

    def ask_limit(self):
        current = self.pattern().get('accumulator_limit', DEFAULT_ACCUMULATOR_LIMIT)

        def answered(text):
            try:
                limit = int(text.strip())
            except ValueError:
                self.status = f'{text!r} is not a whole number.'
                return
            if limit < 1:
                self.status = 'The limit must be 1 or more.'
                return
            self.pattern()['accumulator_limit'] = limit
            self.document.changed()
        self.ask(PromptDialog('Note Add and Velocity Add clear past', current), answered)

    def toggle_glide(self):
        self.set_value(None if self.value() else True)

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
        if name == 'duration':
            return fraction_text(self.duration_now(step))
        if not note:
            return ''
        if name in ('glide', 'grab'):
            return 'G' if value else '.'
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
        source = pattern.get('source_pattern', '(none)')
        extra = f'Scale {scale}'
        if self.holder.advanced_rows:
            limit = pattern.get('accumulator_limit', DEFAULT_ACCUMULATOR_LIMIT)
            extra = f'Advanced rows    Source {source}    Add limit {limit}'
        return [
            Text(f'  Steps {pattern["steps"]}    Drum {drum}    Direction {direction}', no_wrap=True),
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
        duration = fraction_text(self.duration_now())
        if not self.is_note():
            return f'Step {step}: rest, {duration}'
        where = '' if self.is_drum() else f' in {self.document.data.get("scale") or "no scale"}'
        played = self.document.note_name(self.item, self.step)
        sound = f'{played}{where}' if played else f'degree {self.value("degree")}, no scale'
        chord = self.value('chord')
        chord_text = f', chord {chord}' if chord is not None else ''
        return f'Step {step}: {sound}, {duration}{chord_text}'

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

