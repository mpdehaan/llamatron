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

"""The main screen, and the pages for the song, patterns, tracks, chains, arps and scales."""

import os
import textwrap

from rich.text import Text

from llamatron.generators.arp import MAX_OCTAVE_RANGE, MAX_OFFSET, MAX_OFFSETS, MIN_OCTAVE_RANGE, ChordOrder, OctaveJump
from llamatron.note import Note, NoteName
from llamatron.scale import ScaleType
from llamatron.composition.defaults import DEFAULT_TRANSPOSE
from llamatron.composition.file_format import CC_ROWS, NAMED_GENERATORS, STEP_SIZE_CHOICES, GeneratorKind, Section
from llamatron.composition.generator_settings import ArpSetting, AutoRatchetSetting, written_name
from llamatron.composition.limits import MAX_CC_NUMBER, MAX_LIVE_OCTAVE, MAX_TEMPO, MAX_TRANSPOSE, MIN_CC_NUMBER, MIN_LIVE_OCTAVE, MIN_TEMPO
from llamatron.composition.named_scale import scale_type_name
from llamatron.composition.song import NO_TEXT
from llamatron.composition.song_file_error import SongFileError
from llamatron.tui.arrange import ArrangePage
from llamatron.tui.base import ARROWS, ARROWS_UP_DOWN, SITE, ChoiceDialog, ConfirmDialog, GridChoiceDialog, Page, PromptDialog, fit, grouped_grid, key, pressed_key
from llamatron.tui.document import Document, NO_OFFSET, ROOTS, SCALE_KINDS, clock, tempo_text, unique_name
from llamatron.tui.lists import Field, FieldPage, ListPage
from llamatron.tui.pattern_editor import TOGGLE_OFF, TOGGLE_ON, PatternEditor
from llamatron.tui.registers_page import RegistersPage

NOTE_LENGTHS = ['1/256', '1/128', '1/64', '1/32', '1/16', '1/8', '1/4', '1/2', '1']
# The Song page's fields, and how it shows what has no value.
TITLE_LABEL = 'Title'
AUTHOR_LABEL = 'Author'
TEMPO_LABEL = 'Tempo'
SCALE_LABEL = 'Scale'
SEED_LABEL = 'Seed'
STEP_SIZE_LABEL = 'Step size'
DEFAULT_OCTAVE_LABEL = 'Default octave'
DEFAULT_DRUM_OCTAVE_LABEL = 'Default drum octave'
TEMPO_SHOWN = '{tempo} BPM'
NO_SCALE_SHOWN = '(none)'
NO_SCALE = 'no scale'
SONG_SUMMARY = '{tempo} BPM   {scale}   {patterns} patterns   {tracks} tracks   {scenes} scenes'
MSG_ADD_A_SCALE_FIRST = 'Add a scale first, on the Scales page.'
SONG_SCALE_TITLE = 'Song scale'
# What the scale picker starts on when there's no scale to start from.
NEW_SCALE_ROOT = NoteName.C
NEW_SCALE_KIND = scale_type_name(ScaleType.MAJOR)
# How a chain's step is shown: the kind of generator and its name.
CHAIN_STEP_SHOWN = '{kind}: {name}'
# How the arp pages show settings a file leaves out, and what they start from.
NO_STEP_SHOWN = ''
SONG_SEED_SHOWN = '(song)'
NO_SEED = 0
DEFAULT_ARP_STEP = '1/16'
ORDERS = [written_name(order) for order in ChordOrder]
DEFAULT_ORDER = ORDERS[0]
JUMPS = [written_name(jump) for jump in OctaveJump]
# How many offsets a new set has, as on the Monomachine.
DEFAULT_OFFSET_STEPS = 8
# The scale picker's pages, each a name and its columns of (heading, scales) groups. The common
# scales come first. Melodic minor is on both pages, the second time leading its modes.
SCALE_PAGES = [
    ('COMMON', [
        [('MODES', ['major', 'ionian', 'dorian', 'phrygian', 'lydian', 'mixolydian', 'minor', 'aeolian', 'natural_minor', 'locrian'])],
        [('MINOR & MAJOR', ['harmonic_minor', 'melodic_minor', 'harmonic_major']),
         ('SYMMETRIC', ['chromatic', 'whole_tone', 'whole_half_diminished', 'half_whole_diminished', 'augmented'])],
        [('PENTATONIC & BLUES', ['major_pentatonic', 'minor_pentatonic', 'blues', 'major_blues', 'egyptian'])],
    ]),
    ('JAZZ & WORLD', [
        [('MELODIC MINOR', ['melodic_minor', 'dorian_flat2', 'lydian_augmented', 'lydian_dominant', 'mixolydian_flat6', 'locrian_natural2', 'altered']),
         ('JAZZ', ['bebop_dominant', 'bebop_major', 'prometheus'])],
        [('MIDDLE EAST & EUROPE', ['phrygian_dominant', 'double_harmonic', 'hungarian_minor', 'hungarian_major', 'ukrainian_dorian', 'persian',
                                   'neapolitan_minor', 'neapolitan_major', 'enigmatic'])],
        [('EAST ASIA', ['hirajoshi', 'in_sen', 'iwato', 'kumoi', 'yo', 'ryukyu']),
         ('INDIA', ['todi', 'marwa', 'purvi'])],
    ]),
]
# Names to show where the full ones are too long to fit.
SHORT_SCALE_NAMES = {
    'whole_half_diminished': 'whole half dim', 'half_whole_diminished': 'half whole dim',
    'lydian_dominant': 'lydian dom', 'bebop_dominant': 'bebop dom', 'phrygian_dominant': 'phrygian dom',
}
# The root picker, laid out like a keyboard, with each flat under the sharp it shares a key with.
ROOT_KEYBOARD = [
    [NoteName.C, NoteName.C_SHARP, NoteName.D, NoteName.D_SHARP, NoteName.E, NoteName.F,
     NoteName.F_SHARP, NoteName.G, NoteName.G_SHARP, NoteName.A, NoteName.A_SHARP, NoteName.B],
    [None, NoteName.D_FLAT, None, NoteName.E_FLAT, None, None,
     NoteName.G_FLAT, None, NoteName.A_FLAT, None, NoteName.B_FLAT, None],
]


def scale_label(kind):
    return SHORT_SCALE_NAMES.get(kind, kind.replace('_', ' '))


def scale_notes(root, kind):
    """Return a scale's notes, like D E F G A B C, spelled as the rest of the program spells them."""
    start = Note(root, 4)
    return ' '.join(start.half_step(step).name for step in ScaleType[kind.upper()].value)



def _octave_moved(octave, offset):
    """Return an octave moved by an offset, kept within Live's range."""
    return max(min(octave + offset, MAX_LIVE_OCTAVE), MIN_LIVE_OCTAVE)


def _stepped(values, current, offset):
    """Return the next value in a list, starting from the middle if the current one isn't there."""
    text = str(current)
    place = values.index(text) if text in values else len(values) // 2
    return values[max(min(place + offset, len(values) - 1), 0)]


class MainPage(Page):
    shows_legend = False
    HELP = (
        'This is the way into every page. Press a letter to open one.',
        '',
        'Patterns hold the notes. Tracks are the columns of the song. Arrange puts patterns on tracks as clips, in scenes that play from top to bottom.',
        '',
        'Tab goes back from any page, and Q quits from here.',
        'Nothing is saved or rendered until you ask for it on the Song page.',
    )
    ABOUT = {
        'Song': 'Tempo, scale, seed, load, save and render',
        'Patterns': 'The notes, in a grid of steps',
        'Tracks': 'The columns of the song',
        'Chains': 'Lists of generators used by clips',
        'Generators': 'Arpeggiators and AutoRatchets',
        'Scales': 'The scales scenes and the song can use',
        'Registers': 'AX to DX, numbers that steps change and use',
        'Arrange': 'Scenes and clips, in the order they render',
        'Quit': 'Asks first if there are unsaved changes',
        'Help': 'What the page you are on does',
    }

    def keys(self):
        return [
            key('s', 'Song', lambda: self.show_page(SongPage(self.holder))),
            key('p', 'Patterns', lambda: self.show_page(PatternsPage(self.holder))),
            key('t', 'Tracks', lambda: self.show_page(TracksPage(self.holder))),
            key('c', 'Chains', lambda: self.show_page(ChainsPage(self.holder))),
            key('g', 'Generators', lambda: self.show_page(GeneratorsPage(self.holder))),
            key('z', 'Scales', lambda: self.show_page(ScalesPage(self.holder))),
            key('r', 'Registers', lambda: self.show_page(RegistersPage(self.holder))),
            key('a', 'Arrange', lambda: self.show_page(ArrangePage(self.holder))),
            key('q', 'Quit', self.app.request_quit),
        ]

    def duration(self):
        return self.document.song_seconds()

    def body(self, width, height):
        song = self.document.song()
        lines = [Text('')]
        lines.append(Text(f"  {self.document.name}   {clock(self.document.song_seconds())}", style='bold'))
        summary = SONG_SUMMARY.format(
            tempo=tempo_text(song.get_tempo()), scale=song.get_scale_name() or NO_SCALE, patterns=len(song.get_pattern_names()),
            tracks=len(song.get_track_names()), scenes=len(song.get_scenes()),
        )
        lines += [Text('  ' + summary), Text('')]
        for item in self.key_table():
            line = Text(no_wrap=True)
            line.append('  ')
            line.append(f' {item.shown_label()} ', style='reverse')
            line.append(f'  {item.what.ljust(11)}', style='bold')
            line.append(self.ABOUT[item.what], style='dim')
            lines.append(line)
        # Three blank lines below the last page, right-justified, unless the screen is too short.
        lines += [Text(''), Text(''), Text(''), Text(SITE.rjust(width - 1), style='dim', no_wrap=True)]
        return lines


class SongPage(FieldPage):
    crumbs = ('SONG',)
    HELP = (
        'Settings for the whole song. Up and down select one. Left and right, or + and -, change it, and Enter types or chooses.',
        '',
        'Title and Author: only for people reading or sharing the song file. Bksp clears them.',
        'Step size: how long each step of a pattern is, unless the pattern sets its own. Default octaves: what a new note or drum hit gets.',
        'Seed: decides what probability drops, so a song renders the same every time.',
        '',
        'D opens the description, for notes about the song. L loads, N starts a new song, S saves, and W saves under a new name.',
        'R writes an Ableton set and M writes a folder of MIDI clips, both under output/. Both ask before replacing an earlier render.',
    )

    def duration(self):
        return self.document.song_seconds()

    def song(self):
        return self.document.song()

    def text_field(self, label, current, set_text):
        """A field for text like the title: current() reads it, and set_text(text) stores it, blank text clearing it."""
        return Field(label, current, None, lambda: self.ask(PromptDialog(label, current()), set_text), 'edit',
                     lambda: set_text(NO_TEXT), 'clear')

    def fields(self):
        document, song = self.document, self.song()
        return [
            self.text_field(TITLE_LABEL, song.get_title, document.set_title),
            self.text_field(AUTHOR_LABEL, song.get_author, document.set_author),
            Field(TEMPO_LABEL, lambda: TEMPO_SHOWN.format(tempo=tempo_text(song.get_tempo())), self.adjust_tempo,
                  lambda: self.ask_number(TEMPO_LABEL, tempo_text(song.get_tempo()), document.set_tempo, MIN_TEMPO, MAX_TEMPO)),
            Field(SCALE_LABEL, lambda: song.get_scale_name() or NO_SCALE_SHOWN, self.step_scale, self.pick_scale, 'choose',
                  lambda: document.set_scale_name(None), NO_SCALE),
            Field(SEED_LABEL, song.get_seed, lambda offset: document.set_seed(song.get_seed() + offset),
                  lambda: self.ask_number(SEED_LABEL, song.get_seed(), document.set_seed)),
            Field(STEP_SIZE_LABEL, lambda: str(song.get_step_size()),
                  lambda offset: document.set_song_step_size(_stepped(STEP_SIZE_CHOICES, song.get_step_size(), offset)),
                  self.pick_step_size, 'choose'),
            Field(DEFAULT_OCTAVE_LABEL, song.get_default_octave,
                  lambda offset: document.set_default_octave(_octave_moved(song.get_default_octave(), offset))),
            Field(DEFAULT_DRUM_OCTAVE_LABEL, song.get_default_drum_octave,
                  lambda offset: document.set_default_drum_octave(_octave_moved(song.get_default_drum_octave(), offset))),
        ]

    def adjust_tempo(self, offset):
        self.document.set_tempo(max(MIN_TEMPO, int(self.song().get_tempo()) + offset))

    def pick_step_size(self):
        current = str(self.song().get_step_size())
        place = STEP_SIZE_CHOICES.index(current) if current in STEP_SIZE_CHOICES else 0
        self.ask(ChoiceDialog(STEP_SIZE_LABEL, STEP_SIZE_CHOICES, place), lambda chosen: self.document.set_song_step_size(STEP_SIZE_CHOICES[chosen]))

    def step_scale(self, offset):
        """Move to the next or previous of the song's scales, with no scale before the first."""
        names = [None, *self.song().get_scale_names()]
        place = names.index(self.song().get_scale_name())
        self.document.set_scale_name(names[max(min(place + offset, len(names) - 1), 0)])

    def pick_scale(self):
        scales = self.song().get_scale_names()
        if not scales:
            self.status = MSG_ADD_A_SCALE_FIRST
            return
        current = self.song().get_scale_name()
        place = scales.index(current) if current in scales else 0
        self.ask(ChoiceDialog(SONG_SCALE_TITLE, scales, place), lambda chosen: self.document.set_scale_name(scales[chosen]))

    def notes(self, width):
        return [
            Text(f"  File          {self.document.path or '(not saved yet)'}", style='dim'),
            Text(f"  Renders       {self.document.output_directory()}", style='dim'),
            Text(f"  Description   {self.description_size()}", style='dim'),
        ]

    def description_size(self):
        text = self.song().get_description()
        lines = text.count('\n') + (not text.endswith('\n')) if text else 0
        return f'{lines} line(s), D to read' if lines else 'not yet, D to write'

    def page_keys(self):
        return [
            key('d', 'description', lambda: self.show_page(DescriptionPage(self.holder))),
            key('l', 'load', self.load),
            key('n', 'new', self.new),
            key('s', 'save', self.save),
            key('w', 'save as', self.save_as),
            key('r', 'render Ableton', lambda: self.render_song('ableton')),
            key('m', 'render clip tree', lambda: self.render_song('cliptree')),
        ]

    def unless_unsaved(self, then):
        if self.document.dirty:
            self.ask(ConfirmDialog('Unsaved changes', ['This song has unsaved changes, which will be lost. Continue?']), lambda _: then())
        else:
            then()

    def new(self):
        self.unless_unsaved(self.start_new)

    def start_new(self):
        self.holder.document = Document()
        self.status = 'Started a new song.'

    def load(self):
        self.unless_unsaved(lambda: self.show_page(FilePage(self.holder, self.opened)))

    def opened(self, document):
        self.holder.document = document
        self.status = f'Loaded {document.path}.'

    def save(self):
        if self.document.path:
            self.write(self.document.path)
        else:
            self.save_as()

    def save_as(self):
        default = self.document.path or os.path.join('songs', 'untitled.yml')

        def chosen(path):
            path = path.strip()
            if not path:
                return
            if not path.endswith(('.yml', '.yaml')):
                path += '.yml'
            if path != self.document.path and os.path.exists(path):
                self.ask(ConfirmDialog('Replace file', [f'Replace {path}?']), lambda _: self.write(path))
            else:
                self.write(path)
        self.ask(PromptDialog('Save as', default), chosen)

    def write(self, path):
        try:
            self.document.save(path)
        except OSError as error:
            self.tell("Can't save", f'{path}: {error.strerror}')
            return
        self.status = f'Saved {path}.'

    def render_song(self, to):
        document = self.document
        if document.render_exists(to):
            what = document.render_path(to)
            self.ask(ConfirmDialog('Replace render', [
                f'Replace the earlier render in {what}?',
                'Anything saved over it in Live is lost. Save your own work under another name.',
            ]), lambda _: self.do_render(to))
        else:
            self.do_render(to)

    def do_render(self, to):
        try:
            directory = self.document.render(to)
        except SongFileError as error:
            self.tell("Can't render", str(error))
            return
        name = 'Ableton set' if to == 'ableton' else 'clip tree'
        self.status = f'Wrote the {name} to {directory}.'


class DescriptionPage(Page):
    """The song's description: text of any length, for people reading or sharing the file.

    It opens for reading, and E starts editing. While editing, letters are text, as in a name
    prompt, so H types an h, and Tab stops editing.
    """

    crumbs = ('SONG', 'DESCRIPTION')
    HELP = (
        'Notes about the song, for anyone reading or sharing its file. They don\'t change how it plays.',
        '',
        'Up and down scroll. E starts editing, and Bksp clears it all, after asking.',
        'While editing, typing adds text where the cursor is, Enter starts a new line, Bksp erases,',
        'and the arrows move the cursor. Tab stops editing, and Tab again goes back.',
    )

    def __init__(self, holder):
        super().__init__(holder)
        self.editing = False
        self.top = 0
        self.row = self.column = 0

    def text_lines(self):
        text = self.document.song().get_description()
        lines = text.split('\n')
        if text.endswith('\n'):
            lines.pop()
        return lines or ['']

    def store(self, lines):
        # A description ends with a newline, so that it reads as plain text in the file.
        self.document.set_description('\n'.join(lines) + '\n')

    def keys(self):
        if self.editing:
            return [
                key(ARROWS, 'move', self.move, label='←↑↓→', wants_key=True),
                key('enter', 'new line', self.new_line),
                key('backspace', 'erase', self.erase),
                key('tab', 'stop editing', self.stop_editing),
            ]
        return [
            key(ARROWS_UP_DOWN, 'scroll', self.scroll, label='↑↓', wants_key=True),
            key('e', 'edit', self.start_editing),
            key('backspace', 'clear', self.clear),
            key('tab', 'back', self.go_back),
        ]

    def key_table(self):
        # While editing, H is text, so help is only there while reading.
        return self.keys() if self.editing else super().key_table()

    def scroll(self, name):
        self.top = max(self.top + (-1 if name == 'up' else 1), 0)

    def start_editing(self):
        self.editing = True
        lines = self.text_lines()
        self.row = len(lines) - 1
        self.column = len(lines[-1])
        self.status = 'Editing. Tab stops.'

    def stop_editing(self):
        self.editing = False
        self.status = ''

    def clear(self):
        if self.document.song().has_description():
            self.ask(ConfirmDialog('Clear the description', ['Delete all of the description?']), lambda _: self.store(['']))

    def move(self, name):
        lines = self.text_lines()
        if name in ('up', 'down'):
            self.row = max(min(self.row + (-1 if name == 'up' else 1), len(lines) - 1), 0)
            self.column = min(self.column, len(lines[self.row]))
        elif name == 'left':
            if self.column:
                self.column -= 1
            elif self.row:
                self.row -= 1
                self.column = len(lines[self.row])
        elif self.column < len(lines[self.row]):
            self.column += 1
        elif self.row < len(lines) - 1:
            self.row, self.column = self.row + 1, 0

    def new_line(self):
        lines = self.text_lines()
        line = lines[self.row]
        lines[self.row:self.row + 1] = [line[:self.column], line[self.column:]]
        self.store(lines)
        self.row, self.column = self.row + 1, 0

    def erase(self):
        lines = self.text_lines()
        if self.column:
            line = lines[self.row]
            lines[self.row] = line[:self.column - 1] + line[self.column:]
            self.column -= 1
        elif self.row:
            self.column = len(lines[self.row - 1])
            lines[self.row - 1:self.row + 1] = [lines[self.row - 1] + lines[self.row]]
            self.row -= 1
        else:
            return
        self.store(lines)

    def type_text(self, character):
        lines = self.text_lines()
        line = lines[self.row]
        lines[self.row] = line[:self.column] + character + line[self.column:]
        self.store(lines)
        self.column += 1

    def on_key(self, event):
        if self.editing and event.character and event.character.isprintable() and pressed_key(event) not in ('enter', 'tab', 'backspace'):
            event.stop()
            event.prevent_default()
            self.type_text(event.character)
            self.draw()
            return
        super().on_key(event)

    def body(self, width, height):
        room = max(height, 1)
        if self.editing:
            lines = self.text_lines()
            self.top = max(min(self.top, self.row), self.row - room + 1, 0)
            shown = []
            for number in range(self.top, min(self.top + room, len(lines))):
                line = lines[number]
                if number != self.row:
                    shown.append(Text('  ' + line, no_wrap=True))
                    continue
                # The cursor's line scrolls sideways to keep the cursor on screen.
                start = max(self.column - (width - 6), 0)
                text = Text('  ' + line[start:self.column], no_wrap=True)
                text.append(line[self.column:self.column + 1] or ' ', style='reverse')
                text.append(line[self.column + 1:])
                shown.append(text)
            return shown
        if not self.document.song().has_description():
            return [Text('  No description yet. Press E to write one.', style='dim')]
        wrapped = []
        for line in self.text_lines():
            wrapped += [Text('  ' + part) for part in (textwrap.wrap(line, width - 4) or [''])]
        self.top = min(self.top, max(len(wrapped) - room, 0))
        return wrapped[self.top:self.top + room]


class FilePage(ListPage):
    """Picks a song file, starting in the examples folder."""

    crumbs = ('SONG', 'LOAD')
    HELP = (
        'Choose a song file. Enter opens a file, or goes into a folder. ../ goes up a folder.',
    )
    columns = (('NAME', None, 'left'),)

    def __init__(self, holder, then):
        super().__init__(holder)
        self.then = then
        self.folder = 'examples' if os.path.isdir('examples') else '.'

    def duration(self):
        return False

    def rows(self):
        try:
            names = sorted(os.listdir(self.folder), key=str.lower)
        except OSError:
            names = []
        folders = [n for n in names if os.path.isdir(os.path.join(self.folder, n)) and not n.startswith('.')]
        files = [n for n in names if n.endswith(('.yml', '.yaml'))]
        rows = [('..', ['../'])]
        rows += [(n, [f'{n}/']) for n in folders]
        rows += [(n, [n]) for n in files]
        return rows

    def keys(self):
        return [*self.move_keys(), key('enter', 'open', self.open), key('tab', 'back', self.go_back)]

    def body(self, width, height):
        return [Text(f'  {os.path.abspath(self.folder)}', style='dim'), Text(''), *super().body(width, height - 2)]

    def open(self):
        name = self.current()
        path = os.path.normpath(os.path.join(self.folder, name))
        if os.path.isdir(path):
            self.folder, self.place = path, 0
            return
        try:
            document = Document.load(path)
        except SongFileError as error:
            self.tell("Can't load", str(error))
            return
        self.app.pop_screen()
        self.then(document)


class PatternsPage(ListPage):
    crumbs = ('PATTERNS',)
    HELP = (
        'Every pattern in the song. Enter edits the selected one.',
        '',
        '+ adds one, C copies it, N renames it, and renames update every clip.',
        'U and D move it, and S sorts them by name.',
        'Bksp deletes it, but only once nothing uses it.',
        '',
        'TIME is one play at the song tempo. USED counts the clips and chains that use it.',
    )
    columns = (('NAME', None, 'left'), ('TYPE', 5, 'left'), ('STEPS', 5, 'right'), ('TIME', 6, 'right'), ('USED', 4, 'right'))

    def rows(self):
        document, song = self.document, self.document.song()
        return [(name, self.row_of(name, song.get_pattern(name), document)) for name in song.get_pattern_names()]

    def row_of(self, name, pattern, document):
        kind = 'drum' if pattern.is_drum() else 'notes'
        return [name, kind, pattern.get_steps(), clock(document.pattern_seconds(name)), len(document.pattern_uses(name))]

    def keys(self):
        result = [*self.move_keys(), key('+', 'add', self.add)]
        if self.current() is not None:
            result += [
                key('enter', 'edit', lambda: self.show_page(PatternEditor(self.holder, self.current()))),
                key('n', 'rename', self.rename),
                key('c', 'copy', self.copy),
                key('backspace', 'delete', self.delete),
                key('u', 'move up', lambda: self.shift(-1)),
                key('d', 'move down', lambda: self.shift(1)),
                key('s', 'sort', self.sort),
            ]
        result.append(key('tab', 'back', self.go_back))
        return result

    def add(self):
        patterns = self.document.song().get_pattern_names()
        default = unique_name('pattern', patterns)

        def named(text):
            text = text.strip()
            if not text or text in patterns:
                self.status = 'That name is empty or already in use.'
                return
            self.document.add_pattern(text)
            self.place = len(patterns)
            self.show_page(PatternEditor(self.holder, text))
        self.ask(PromptDialog('New pattern name', default), named)

    def rename(self):
        name = self.current()
        self.ask_name('Rename pattern', name, self.document.song().get_pattern_names(), lambda new: self.document.rename_pattern(name, new))

    def copy(self):
        self.document.copy_pattern(self.current())
        names = self.document.song().get_pattern_names()
        self.status = f'Copied to {names[-1]}.'
        self.place = len(names) - 1

    def delete(self):
        name = self.current()
        self.delete_after_checks(f'pattern {name}', self.document.pattern_uses(name), lambda: self.document.delete_pattern(name))

    def shift(self, offset):
        if self.document.move_named('patterns', self.place, offset):
            self.place += offset

    def sort(self):
        current = self.current()
        self.document.sort_named('patterns')
        self.place = self.document.song().get_pattern_names().index(current)


def _cc_text(numbers):
    return ' '.join('-' if number is None else str(number) for number in numbers)


class TracksPage(ListPage):
    crumbs = ('TRACKS',)
    HELP = (
        'The columns of the song, which become tracks in Ableton in this order.',
        '',
        'Enter opens its settings: drum, mute, transpose and the CC numbers its patterns send.',
        '+ adds one, N renames it, and C copies it along with its clips.',
        'U and D move it. Bksp deletes it and its clips, after asking.',
    )
    columns = (('NAME', None, 'left'), ('TYPE', 5, 'left'), ('MUTE', 4, 'left'), ('MOVE', 4, 'right'), ('CC 1-4', 16, 'left'), ('CLIPS', 5, 'right'))

    def rows(self):
        song = self.document.song()
        return [(name, self.row_of(name, song.get_track(name))) for name in song.get_track_names()]

    def row_of(self, name, track):
        kind = 'drum' if track.is_drum() else 'notes'
        mute = TOGGLE_ON if track.is_muted() else TOGGLE_OFF
        move = f'{track.get_transpose():+d}' if track.get_transpose() else ''
        return [name, kind, mute, move, _cc_text(track.get_cc_numbers()), self.document.track_clips(name)]

    def keys(self):
        result = [*self.move_keys(), key('+', 'add', self.add)]
        if self.current() is not None:
            result += [
                key('enter', 'settings', lambda: self.show_page(TrackEditor(self.holder, self.current()))),
                key('n', 'rename', self.rename),
                key('c', 'copy', self.copy),
                key('backspace', 'delete', self.delete),
                key('u', 'move up', lambda: self.shift(-1)),
                key('d', 'move down', lambda: self.shift(1)),
            ]
        result.append(key('tab', 'back', self.go_back))
        return result

    def add(self):
        tracks = self.document.song().get_track_names()

        def named(text):
            self.document.add_track(text)
            self.place = len(tracks)
        self.ask_name('New track name', '', tracks, named)

    def rename(self):
        name = self.current()
        self.ask_name('Rename track', name, self.document.song().get_track_names(), lambda new: self.document.rename_track(name, new))

    def copy(self):
        self.document.copy_track(self.current())
        self.place += 1

    def delete(self):
        name = self.current()
        clips = self.document.track_clips(name)
        notes = [f'This also deletes its {clips} clip(s).'] if clips else []
        grabbers = self.document.grabbers(name)
        if grabbers:
            notes.append(f'{len(grabbers)} clip(s) that grab from it will stop grabbing.')
        self.delete_after_checks(f'track {name}', [], lambda: self.document.delete_track(name), ' '.join(notes) or None)

    def shift(self, offset):
        if self.document.move_track(self.place, offset):
            self.place += offset


class TrackEditor(FieldPage):
    """One track's settings, which apply to every clip on it."""

    HELP = (
        'Drum: a drum track is never transposed. Drum patterns never are either, on any track.',
        'Mute: the track starts switched off in Live. Its clips are still written, and other tracks can still grab from it.',
        'Transpose: moves every note on the track along the scale when rendering, without changing its patterns.',
        'CC 1 to CC 4: the CC number that each of a pattern\'s CC rows sends on this track. A row with no number sends nothing here.',
        '',
        'Up and down select a setting. Left and right, or + and -, change it, and Enter types or toggles. Bksp clears.',
    )

    def __init__(self, holder, name):
        super().__init__(holder)
        self.item = name
        self.crumbs = ('TRACKS', name)

    def track(self):
        return self.document.song().get_track(self.item)

    def numbers(self):
        return self.track().get_cc_numbers()

    def set_cc(self, lane, number):
        self.document.set_track_cc_number(self.item, lane, number)

    def nudge_cc(self, lane, offset):
        current = self.numbers()[lane]
        if current is None:
            moved = MIN_CC_NUMBER + 1 if offset > 0 else MIN_CC_NUMBER
        else:
            moved = current + offset
        self.set_cc(lane, max(min(moved, MAX_CC_NUMBER), MIN_CC_NUMBER))

    def set_transpose(self, transpose):
        self.document.set_track_transpose(self.item, transpose)

    def nudge_transpose(self, offset):
        self.set_transpose(max(min(self.track().get_transpose() + offset, MAX_TRANSPOSE), -MAX_TRANSPOSE))

    def fields(self):
        track = self.track()
        drum = track.is_drum()
        result = [
            Field('Drum', lambda: TOGGLE_ON if drum else TOGGLE_OFF, None, lambda: self.document.set_track_drum(self.item, not drum), 'toggle'),
            Field('Mute', lambda: TOGGLE_ON if track.is_muted() else TOGGLE_OFF, None,
                  lambda: self.document.set_track_mute(self.item, not track.is_muted()), 'toggle'),
        ]
        if drum:
            result.append(Field('Transpose', lambda: '(drum track)'))
        else:
            result.append(Field(
                'Transpose', lambda: f'{track.get_transpose():+d}' if track.get_transpose() else '0',
                self.nudge_transpose,
                lambda: self.ask_number('Transpose', track.get_transpose(), self.set_transpose, -MAX_TRANSPOSE, MAX_TRANSPOSE),
                'edit', lambda: self.set_transpose(DEFAULT_TRANSPOSE), 'no transpose',
            ))
        for lane in range(len(CC_ROWS)):
            result.append(Field(
                f'CC {lane + 1}', lambda lane=lane: '(none)' if self.numbers()[lane] is None else str(self.numbers()[lane]),
                lambda offset, lane=lane: self.nudge_cc(lane, offset),
                lambda lane=lane: self.ask_number(f'CC {lane + 1} number', self.numbers()[lane] or MIN_CC_NUMBER, lambda n, lane=lane: self.set_cc(lane, n), MIN_CC_NUMBER, MAX_CC_NUMBER),
                'edit', lambda lane=lane: self.set_cc(lane, None), 'none',
            ))
        return result

    def notes(self, width):
        return [Text('  Transpose counts notes of the scale, so 7 is an octave in a seven-note scale.', style='dim')]


def offsets_text(offsets):
    if offsets is None:
        return '(none)'
    return ' '.join('-' if offset is None else str(offset) for offset in offsets)


def counts_text(counts):
    """Return an AutoRatchet's counts as typed, like 1 1 4, or nothing when it has none yet."""
    return ' '.join(str(count) for count in counts or [])


class OffsetsEditor(Page):
    """An arpeggiator's offsets: one row of up to 16 steps, like a pattern row."""

    HELP = (
        'The arpeggiator plays one note of the chord each step, moved this many notes along the scale.',
        'A blank step is silent, and the next step plays the note it would have played.',
        'The steps start again with each chord, so a length that doesn\'t match the chord makes a new rhythm.',
        '',
        'Digits type an offset, + and - change it, and Space makes the step silent or plays it again.',
        'I inserts a step, X removes one, and there can be 1 to 16.',
    )

    def __init__(self, holder, name):
        super().__init__(holder)
        self.item = name
        self.step = 0
        self.typed = ''
        self.crumbs = ('GENERATORS', 'ARPEGGIATORS', name, 'OFFSETS')

    def offsets(self):
        return self.document.song().get_generator_settings(GeneratorKind.ARP, self.item).get_offsets()

    def on_key(self, event):
        name = pressed_key(event)
        if not (name and name.isdigit()):
            self.typed = ''
        super().on_key(event)

    def keys(self):
        self.step = max(min(self.step, len(self.offsets()) - 1), 0)
        result = [
            key(('left', 'right'), 'move', self.move, label='←→', wants_key=True),
            key(tuple('0123456789'), 'type', self.type_digit, label='0-9', wants_key=True),
            key(('+', '='), 'more', lambda: self.nudge(1), label='+'),
            key('-', 'less', lambda: self.nudge(-1)),
            key('space', 'silent' if self.offsets()[self.step] is not None else 'play', self.toggle),
        ]
        if len(self.offsets()) < MAX_OFFSETS:
            result.append(key('i', 'insert step', self.insert))
        if len(self.offsets()) > 1:
            result.append(key('x', 'remove step', self.remove_step))
        result.append(key('tab', 'back', self.go_back))
        return result

    def move(self, name):
        self.step = (self.step + (1 if name == 'right' else -1)) % len(self.offsets())

    def set_offset(self, value):
        self.document.set_arp_offset(self.item, self.step, value)

    def type_digit(self, digit):
        for text in (self.typed + digit, digit):
            if int(text) <= MAX_OFFSET:
                self.typed = text
                current = self.offsets()[self.step]
                self.set_offset(-int(text) if current is not None and current < 0 else int(text))
                return

    def nudge(self, offset):
        current = self.offsets()[self.step] or 0
        self.set_offset(max(min(current + offset, MAX_OFFSET), -MAX_OFFSET))

    def toggle(self):
        self.set_offset(0 if self.offsets()[self.step] is None else None)

    def insert(self):
        self.document.insert_arp_offset(self.item, self.step)

    def remove_step(self):
        self.document.remove_arp_offset(self.item, self.step)
        self.step = min(self.step, len(self.offsets()) - 1)

    def body(self, width, height):
        offsets = self.offsets()
        size = 5
        rule = '─' * size
        per_block = max((width - 12) // (size + 1), 1)
        lines = [Text('  Steps start again with each chord. A blank step is silent.', style='dim')]
        for first in range(0, len(offsets), per_block):
            places = range(first, min(first + per_block, len(offsets)))
            lines += [Text(''), Text('┌────────┬' + '┬'.join([rule] * len(places)) + '┐', style='dim', no_wrap=True)]
            head = Text('│ Step   │', no_wrap=True)
            row = Text('│ Offset │', no_wrap=True)
            for place in places:
                offset = offsets[place]
                head.append(fit(str(place + 1), size, 'center'), style='bold')
                head.append('│')
                row.append(fit('' if offset is None else str(offset), size, 'center'), style='reverse' if place == self.step else '')
                row.append('│')
            lines += [head, row, Text('└────────┴' + '┴'.join([rule] * len(places)) + '┘', style='dim', no_wrap=True)]
        return lines


class ScalesPage(ListPage):
    crumbs = ('SCALES',)
    HELP = (
        'Named scales for the song and its scenes to choose from. A clip uses its scene\'s scale, or else the song\'s.',
        '',
        'A name can be anything, like main, so you can change what main is later, and everything using it follows.',
        '',
        '+ adds one by choosing a root and a kind, then a name. Enter changes its root and kind. N renames it, and C copies it.',
        'U and D move it. Bksp deletes it, but only once nothing uses it. To delete the song\'s scale, clear it on the Song page first.',
        '',
        'Patterns that use degrees need a scale to render.',
    )
    columns = (('NAME', None, 'left'), ('SCALE', 24, 'left'), ('NOTES', 5, 'right'), ('USED', 4, 'right'))

    def rows(self):
        document, song = self.document, self.document.song()
        return [
            (name, [
                name + (' (song)' if song.get_scale_name() == name else ''),
                document.scale_notes_text(name), document.scale_size(name), len(document.scale_uses(name)),
            ])
            for name in song.get_scale_names()
        ]

    def keys(self):
        result = [*self.move_keys(), key('+', 'add', self.add)]
        if self.current() is not None:
            result += [
                key('enter', 'change', self.change),
                key('n', 'rename', self.rename),
                key('c', 'copy', self.copy),
                key('backspace', 'delete', self.delete),
                key('u', 'move up', lambda: self.shift(-1)),
                key('d', 'move down', lambda: self.shift(1)),
            ]
        result.append(key('tab', 'back', self.go_back))
        return result

    def pick_scale(self, title, root, kind, then):
        """Ask for a root on a keyboard, and then a kind of scale from its pages."""
        kinds = [scale_label(text) for text in SCALE_KINDS]
        kind_pages = [
            (page, grouped_grid([[(heading, [SCALE_KINDS.index(name) for name in names]) for heading, names in groups] for groups in columns]))
            for page, columns in SCALE_PAGES
        ]
        root_grid = [[None if name is None else ROOTS.index(name) for name in row] for row in ROOT_KEYBOARD]

        def rooted(root_place):
            chosen_root = ROOTS[root_place]

            def kinded(kind_place):
                then(chosen_root, SCALE_KINDS[kind_place])

            def notes(place):
                return f'{chosen_root} {kinds[place]}: {scale_notes(chosen_root, SCALE_KINDS[place])}'
            place = SCALE_KINDS.index(kind) if kind in SCALE_KINDS else 0
            self.ask(GridChoiceDialog(f'{title}: {chosen_root}', kinds, None, place, notes, pages=kind_pages), kinded)
        self.ask(GridChoiceDialog(f'{title}: root note', ROOTS, root_grid, ROOTS.index(root) if root in ROOTS else 0), rooted)

    def add(self):
        song = self.document.song()
        scales = song.get_scale_names()
        root, kind = self.root_and_kind(self.current()) if self.current() in scales else (NEW_SCALE_ROOT, NEW_SCALE_KIND)

        def chosen(root, kind):
            default = unique_name(f"{root} {kind.replace('_', ' ').title()}", scales)

            def named(text):
                text = text.strip()
                if not text or text in scales:
                    self.status = 'That name is empty or already in use.'
                    return
                self.document.add_scale(text, root, kind)
                self.place = len(scales)
            self.ask(PromptDialog('Scale name', default), named)
        self.pick_scale('New scale', root, kind, chosen)

    def root_and_kind(self, name):
        scale = self.document.song().get_named_scale(name)
        return scale.get_root(), scale.get_kind()

    def change(self):
        name = self.current()
        root, kind = self.root_and_kind(name)
        self.pick_scale(f'Change {name}', root, kind, lambda root, kind: self.document.change_scale(name, root, kind))

    def rename(self):
        name = self.current()
        self.ask_name('Rename scale', name, self.document.song().get_scale_names(), lambda new: self.document.rename_scale(name, new))

    def copy(self):
        self.document.copy_scale(self.current())
        self.place = len(self.document.song().get_scale_names()) - 1

    def delete(self):
        name = self.current()
        self.delete_after_checks(f'scale {name}', self.document.scale_uses(name), lambda: self.document.delete_scale(name))

    def shift(self, offset):
        if self.document.move_named('scales', self.place, offset):
            self.place += offset


class ChainsPage(ListPage):
    crumbs = ('CHAINS',)
    HELP = (
        'A chain is a list of generators that run on a clip when rendering. A clip chooses one chain on its own page.',
        '',
        'Enter edits the selected chain. + adds one, C copies it, N renames it, and U and D move it.',
        'Bksp deletes it, but only once no clip uses it.',
    )
    columns = (('NAME', None, 'left'), ('STEPS', 5, 'right'), ('USED', 4, 'right'))

    def rows(self):
        song = self.document.song()
        return [
            (name, [name, len(song.get_chain(name).get_steps()), len(self.document.chain_uses(name))])
            for name in song.get_chain_names()
        ]

    def keys(self):
        result = [*self.move_keys(), key('+', 'add', self.add)]
        if self.current() is not None:
            result += [
                key('enter', 'edit', lambda: self.show_page(ChainEditor(self.holder, self.current()))),
                key('n', 'rename', self.rename),
                key('c', 'copy', self.copy),
                key('backspace', 'delete', self.delete),
                key('u', 'move up', lambda: self.shift(-1)),
                key('d', 'move down', lambda: self.shift(1)),
            ]
        result.append(key('tab', 'back', self.go_back))
        return result

    def add(self):
        chains = self.document.song().get_chain_names()

        def named(text):
            self.document.add_chain(text)
            self.place = len(chains)
        self.ask_name('New chain name', '', chains, named)

    def rename(self):
        name = self.current()
        self.ask_name('Rename chain', name, self.document.song().get_chain_names(), lambda new: self.document.rename_chain(name, new))

    def copy(self):
        self.document.copy_chain(self.current())
        self.place = len(self.document.song().get_chain_names()) - 1

    def delete(self):
        name = self.current()
        self.delete_after_checks(f'chain {name}', self.document.chain_uses(name), lambda: self.document.delete_chain(name))

    def shift(self, offset):
        if self.document.move_named('chains', self.place, offset):
            self.place += offset


class ChainEditor(ListPage):
    """A chain's steps, each an arpeggiator or AutoRatchet chosen by name."""

    HELP = (
        'The steps run from top to bottom, each working on what the last one made.',
        '',
        '+ adds an arpeggiator or AutoRatchet, which you make on the Generators page. Enter changes one, C copies it, and Bksp removes it. U and D move a step.',
    )
    columns = (('STEP', None, 'left'),)

    def __init__(self, holder, name):
        super().__init__(holder)
        self.item = name
        self.crumbs = ('CHAINS', name)

    def steps(self):
        """Return the chain's steps, each (kind of generator, its name)."""
        return self.document.song().get_chain(self.item).get_steps()

    def rows(self):
        return [(place, [CHAIN_STEP_SHOWN.format(kind=kind, name=name)]) for place, (kind, name) in enumerate(self.steps())]

    def keys(self):
        result = [*self.move_keys(), key('+', 'add', self.add)]
        if self.current() is not None:
            result += [
                key('enter', 'change', self.change),
                key('c', 'copy', self.copy),
                key('backspace', 'remove', self.remove_step),
                key('u', 'move up', lambda: self.shift(-1)),
                key('d', 'move down', lambda: self.shift(1)),
            ]
        result.append(key('tab', 'back', self.go_back))
        return result

    def pick_generator(self, title, then):
        song = self.document.song()
        options = [(kind, name) for kind in NAMED_GENERATORS for name in song.get_generator_names(kind)]
        if not options:
            self.tell('Nothing to add', 'Make an arpeggiator or AutoRatchet first, on the Generators page.')
            return
        labels = [CHAIN_STEP_SHOWN.format(kind=kind, name=name) for kind, name in options]
        self.ask(ChoiceDialog(title, labels), lambda chosen: then(*options[chosen]))

    def add(self):
        def chosen(kind, name):
            self.document.add_chain_step(self.item, kind, name)
            self.place = len(self.steps()) - 1
        self.pick_generator('Add to chain', chosen)

    def change(self):
        place = self.current()
        self.pick_generator('Change step', lambda kind, name: self.document.set_chain_step(self.item, place, kind, name))

    def copy(self):
        self.document.copy_chain_step(self.item, self.place)
        self.place += 1

    def remove_step(self):
        self.document.remove_chain_step(self.item, self.place)
        self.clamp()

    def shift(self, offset):
        if self.document.move_chain_step(self.item, self.place, offset):
            self.place += offset


class GeneratorsPage(ListPage):
    crumbs = ('GENERATORS',)
    HELP = (
        'Generators run on clips when rendering, as steps in a chain. Enter opens a kind of generator.',
        '',
        'Arpeggiators play each chord one note at a time.',
        'AutoRatchets chop notes into quick repeats, using a repeating list of counts.',
    )
    columns = (('GENERATOR', None, 'left'), ('COUNT', 5, 'right'))

    def rows(self):
        song = self.document.song()
        return [
            (Section.ARPS, ['Arpeggiators', len(song.get_generator_names(GeneratorKind.ARP))]),
            (Section.AUTO_RATCHETS, ['AutoRatchets', len(song.get_generator_names(GeneratorKind.AUTO_RATCHET))]),
        ]

    def keys(self):
        return [
            *self.move_keys(),
            key('enter', 'open', self.open_section),
            key('tab', 'back', self.go_back),
        ]

    def open_section(self):
        self.show_page(ArpsPage(self.holder) if self.current() == Section.ARPS else AutoRatchetsPage(self.holder))


class NamedGeneratorsPage(ListPage):
    """A list of generators of one kind, which chains use by name."""

    section = ''
    kind = ''
    label = ''

    def uses(self, name):
        return self.document.generator_uses(self.section, name)

    def names(self):
        return self.document.song().get_generator_names(self.kind)

    def settings_of(self, name):
        return self.document.song().get_generator_settings(self.kind, name)

    def keys(self):
        result = [*self.move_keys(), key('+', 'add', self.add)]
        if self.current() is not None:
            result += [
                key('enter', 'edit', lambda: self.show_page(self.editor(self.holder, self.current()))),
                key('n', 'rename', self.rename),
                key('c', 'copy', self.copy),
                key('backspace', 'delete', self.delete),
                key('u', 'move up', lambda: self.shift(-1)),
                key('d', 'move down', lambda: self.shift(1)),
            ]
        result.append(key('tab', 'back', self.go_back))
        return result

    def add(self):
        def named(text):
            self.document.add_generator(self.section, text)
            self.place = len(self.names()) - 1
        self.ask_name(f'New {self.label} name', '', self.names(), named)

    def rename(self):
        name = self.current()
        self.ask_name(f'Rename {self.label}', name, self.names(), lambda new: self.document.rename_generator(self.section, name, new))

    def copy(self):
        self.document.copy_generator(self.section, self.current())
        self.place = len(self.names()) - 1

    def delete(self):
        name = self.current()
        self.delete_after_checks(f'{self.label} {name}', self.uses(name), lambda: self.document.delete_generator(self.section, name))

    def shift(self, offset):
        if self.document.move_named(self.section, self.place, offset):
            self.place += offset


class ArpsPage(NamedGeneratorsPage):
    crumbs = ('GENERATORS', 'ARPEGGIATORS')
    section = Section.ARPS
    kind = GeneratorKind.ARP
    label = 'arpeggiator'
    HELP = (
        'An arpeggiator plays each chord one note at a time. Add it to a chain to use it.',
        '',
        'Enter edits the selected one. + adds one, C copies it, N renames it, and U and D move it.',
        'Bksp deletes it, but only once no chain uses it.',
    )
    columns = (('NAME', None, 'left'), ('STEP', 6, 'right'), ('ORDER', 8, 'left'), ('USED', 4, 'right'))

    @property
    def editor(self):
        return ArpEditor

    def rows(self):
        return [(name, self.row_of(name, self.settings_of(name))) for name in self.names()]

    def row_of(self, name, arp):
        step = NO_STEP_SHOWN if arp.get_step() is None else arp.get_step()
        return [name, step, arp.get_order() or DEFAULT_ORDER, len(self.uses(name))]


class AutoRatchetsPage(NamedGeneratorsPage):
    crumbs = ('GENERATORS', 'AUTORATCHETS')
    section = Section.AUTO_RATCHETS
    kind = GeneratorKind.AUTO_RATCHET
    label = 'AutoRatchet'
    HELP = (
        'An AutoRatchet chops each note or chord into quick equal repeats in the same time, using the next count in a repeating list. Rests do not use up a count.',
        '',
        'Counts of 1 1 4 leave two notes alone, then chop the third into four. Add it to a chain to use it.',
        '',
        'Enter edits the selected one. + adds one, C copies it, N renames it, and U and D move it.',
        'Bksp deletes it, but only once no chain uses it.',
    )
    columns = (('NAME', None, 'left'), ('COUNTS', 20, 'left'), ('USED', 4, 'right'))

    @property
    def editor(self):
        return AutoRatchetEditor

    def rows(self):
        return [(name, [name, counts_text(self.settings_of(name).get_counts()), len(self.uses(name))]) for name in self.names()]


class AutoRatchetEditor(FieldPage):
    HELP = (
        'Counts: how many equal repeats to chop each note or chord into, using the next number each time and starting again at the end.',
        '',
        'Press Enter and type whole numbers with spaces between them, like 1 1 4.',
    )

    def __init__(self, holder, name):
        super().__init__(holder)
        self.item = name
        self.crumbs = ('GENERATORS', 'AUTORATCHETS', name)

    def counts(self):
        return self.document.song().get_generator_settings(GeneratorKind.AUTO_RATCHET, self.item).get_counts()

    def ask_counts(self):
        def answered(text):
            parts = text.replace(',', ' ').split()
            if not parts or not all(part.isdigit() and int(part) >= 1 for part in parts):
                self.status = 'Counts must be whole numbers of 1 or more, like 1 1 4.'
                return
            self.document.set_generator_setting(Section.AUTO_RATCHETS, self.item, AutoRatchetSetting.COUNTS, [int(part) for part in parts])
        self.ask(PromptDialog('Counts', counts_text(self.counts())), answered)

    def fields(self):
        return [Field('Counts', lambda: counts_text(self.counts()), None, self.ask_counts)]


class ArpEditor(FieldPage):
    HELP = (
        'Step: how long each note of the chord plays.',
        'Order: which way it goes through the chord. Random uses the seed.',
        'Octave range: plays the chord again in up to 4 octaves. Octave jump: up after the whole chord, or after each note.',
        'Offsets: the arp\'s own steps, like the Monomachine\'s. Each moves its note along the scale, and a blank step is silent. Bksp removes them.',
        'Seed: leave it to use the song seed, or set one for just this arpeggiator.',
        '',
        'Up and down select a setting. Left and right, or + and -, change it, and Enter types or chooses.',
    )

    def __init__(self, holder, name):
        super().__init__(holder)
        self.item = name
        self.crumbs = ('GENERATORS', 'ARPEGGIATORS', name)

    def arp(self):
        return self.document.song().get_generator_settings(GeneratorKind.ARP, self.item)

    def set_value(self, setting, value):
        """Set one of the arp's settings, or None to leave it out and use its default."""
        self.document.set_generator_setting(Section.ARPS, self.item, setting, value)

    def pick(self, title, options, setting, current):
        place = options.index(str(current)) if str(current) in options else 0
        self.ask(ChoiceDialog(title, options, place), lambda chosen: self.set_value(setting, options[chosen]))

    def set_range(self, octaves):
        self.set_value(ArpSetting.OCTAVE_RANGE, None if octaves == MIN_OCTAVE_RANGE else octaves)

    def set_jump(self, jump):
        self.set_value(ArpSetting.OCTAVE_JUMP, None if jump == JUMPS[0] else jump)

    def edit_offsets(self):
        if self.arp().get_offsets() is None:
            self.set_value(ArpSetting.OFFSETS, [NO_OFFSET] * DEFAULT_OFFSET_STEPS)
        self.show_page(OffsetsEditor(self.holder, self.item))

    def fields(self):
        arp = self.arp()
        step = arp.get_step()
        order = arp.get_order() or DEFAULT_ORDER
        octaves = arp.get_octave_range() or MIN_OCTAVE_RANGE
        jump = arp.get_octave_jump() or JUMPS[0]
        seed = arp.get_seed()
        return [
            Field('Step', lambda: NO_STEP_SHOWN if step is None else step, lambda d: self.set_value(ArpSetting.STEP, _stepped(NOTE_LENGTHS, step, d)),
                  lambda: self.pick('Step', NOTE_LENGTHS, ArpSetting.STEP, DEFAULT_ARP_STEP if step is None else step), 'choose'),
            Field('Order', lambda: order, lambda d: self.set_value(ArpSetting.ORDER, _stepped(ORDERS, order, d)),
                  lambda: self.pick('Order', ORDERS, ArpSetting.ORDER, order), 'choose'),
            Field('Octave range', lambda: octaves, lambda d: self.set_range(max(min(octaves + d, MAX_OCTAVE_RANGE), MIN_OCTAVE_RANGE)),
                  lambda: self.ask_number('Octave range', octaves, self.set_range, MIN_OCTAVE_RANGE, MAX_OCTAVE_RANGE)),
            Field('Octave jump', lambda: jump.replace('_', ' '), lambda d: self.set_jump(_stepped(JUMPS, jump, d)),
                  lambda: self.ask(ChoiceDialog('Octave jump', [name.replace('_', ' ') for name in JUMPS], JUMPS.index(jump)),
                                   lambda chosen: self.set_jump(JUMPS[chosen])), 'choose'),
            Field('Offsets', lambda: offsets_text(arp.get_offsets()), None, self.edit_offsets, 'edit',
                  lambda: self.set_value(ArpSetting.OFFSETS, None), 'remove'),
            Field('Seed', lambda: SONG_SEED_SHOWN if seed is None else seed, lambda d: self.set_value(ArpSetting.SEED, (seed or NO_SEED) + d),
                  lambda: self.ask_number('Seed', seed or NO_SEED, lambda n: self.set_value(ArpSetting.SEED, n)), 'edit',
                  lambda: self.set_value(ArpSetting.SEED, None), 'use the song seed'),
        ]

