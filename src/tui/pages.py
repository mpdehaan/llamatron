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

"""The main screen, and the pages for the song, patterns, tracks, chains, arps and scales."""

import os

from rich.text import Text

from src.generators.arp import ChordOrder
from src.song_file import GRANULARITIES, SongFileError
from src.tui.arrange import ArrangePage
from src.tui.base import ChoiceDialog, ConfirmDialog, Page, PromptDialog, key
from src.tui.document import Document, GENERATOR_SECTIONS, ROOTS, SCALE_KINDS, clock, unique_name
from src.tui.lists import Field, FieldPage, ListPage
from src.tui.pattern_editor import PatternEditor

NOTE_LENGTHS = ['1/256', '1/128', '1/64', '1/32', '1/16', '1/8', '1/4', '1/2', '1']
ORDERS = [order.name.lower() for order in ChordOrder]

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
            key('a', 'Arrange', lambda: self.show_page(ArrangePage(self.holder))),
            key('q', 'Quit', self.app.request_quit),
        ]

    def duration(self):
        return self.document.song_seconds()

    def body(self, width, height):
        data = self.document.data
        lines = [Text('')]
        lines.append(Text(f"  {self.document.name}   {clock(self.document.song_seconds())}", style='bold'))
        summary = (
            f"{data['tempo']} BPM   {data.get('scale') or 'no scale'}   "
            f"{len(data['patterns'])} patterns   {len(data['tracks'])} tracks   {len(data['scenes'])} scenes"
        )
        lines += [Text('  ' + summary), Text('')]
        for item in self.key_table():
            line = Text(no_wrap=True)
            line.append('  ')
            line.append(f' {item.shown_label()} ', style='reverse')
            line.append(f'  {item.what.ljust(11)}', style='bold')
            line.append(self.ABOUT[item.what], style='dim')
            lines.append(line)
        return lines


class SongPage(FieldPage):
    crumbs = ('SONG',)
    HELP = (
        'Settings for the whole song. Up and down select one. Left and right, or + and -, change it, and Enter types or chooses.',
        '',
        'Default note length: what a new note gets. Granularity: how much + and - change a duration. Default octaves: what a new note or drum hit gets.',
        'Seed: decides what probability drops, so a song renders the same every time.',
        '',
        'L loads, N starts a new song, S saves, and W saves under a new name.',
        'R writes an Ableton set and M writes a folder of MIDI clips, both under output/. Both ask before replacing an earlier render.',
    )

    def duration(self):
        return self.document.song_seconds()

    def set_value(self, name, value):
        self.document.data[name] = value
        self.document.changed()

    def fields(self):
        data = self.document.data
        return [
            Field('Tempo', lambda: f"{data['tempo']} BPM", lambda d: self.set_value('tempo', max(10, int(data['tempo']) + d)),
                  lambda: self.ask_number('Tempo', data['tempo'], lambda n: self.set_value('tempo', n), 10, 999)),
            Field('Scale', lambda: data.get('scale') or '(none)', self.step_scale, self.pick_scale, 'choose',
                  lambda: self.set_value('scale', None), 'no scale'),
            Field('Seed', lambda: data['seed'], lambda d: self.set_value('seed', data['seed'] + d),
                  lambda: self.ask_number('Seed', data['seed'], lambda n: self.set_value('seed', n))),
            Field('Default note length', lambda: data['default_length'],
                  lambda d: self.set_value('default_length', _stepped(NOTE_LENGTHS, data['default_length'], d)),
                  lambda: self.pick('Default note length', NOTE_LENGTHS, 'default_length'), 'choose'),
            Field('Granularity', lambda: data['granularity'],
                  lambda d: self.set_value('granularity', _stepped(GRANULARITIES, data['granularity'], d)),
                  lambda: self.pick('Granularity', GRANULARITIES, 'granularity'), 'choose'),
            Field('Default octave', lambda: data['default_octave'], lambda d: self.adjust_octave('default_octave', d)),
            Field('Default drum octave', lambda: data['default_drum_octave'], lambda d: self.adjust_octave('default_drum_octave', d)),
        ]

    def adjust_octave(self, name, offset):
        self.set_value(name, max(min(self.document.data[name] + offset, 8), -2))

    def pick(self, title, options, name):
        current = str(self.document.data[name])
        place = options.index(current) if current in options else 0
        self.ask(ChoiceDialog(title, options, place), lambda chosen: self.set_value(name, options[chosen]))

    def step_scale(self, offset):
        names = [None, *self.document.data['scales']]
        place = names.index(self.document.data.get('scale'))
        self.set_value('scale', names[max(min(place + offset, len(names) - 1), 0)])

    def pick_scale(self):
        scales = list(self.document.data['scales'])
        if not scales:
            self.status = 'Add a scale first, on the Scales page.'
            return
        current = self.document.data.get('scale')
        place = scales.index(current) if current in scales else 0
        self.ask(ChoiceDialog('Song scale', scales, place), lambda chosen: self.set_value('scale', scales[chosen]))

    def notes(self, width):
        return [
            Text(f"  File      {self.document.path or '(not saved yet)'}", style='dim'),
            Text(f"  Renders   {self.document.output_directory()}", style='dim'),
        ]

    def page_keys(self):
        return [
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
        document = self.document
        return [
            (name, [
                name, 'drum' if pattern.get('drum') else 'notes', pattern['steps'],
                clock(document.pattern_seconds(name)), len(document.pattern_uses(name)),
            ])
            for name, pattern in document.data['patterns'].items()
        ]

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
        patterns = self.document.data['patterns']
        default = unique_name('pattern', patterns)

        def named(text):
            text = text.strip()
            if not text or text in patterns:
                self.status = 'That name is empty or already in use.'
                return
            self.document.add_pattern(text)
            self.place = len(patterns) - 1
            self.show_page(PatternEditor(self.holder, text))
        self.ask(PromptDialog('New pattern name', default), named)

    def rename(self):
        name = self.current()
        self.ask_name('Rename pattern', name, self.document.data['patterns'], lambda new: self.document.rename_pattern(name, new))

    def copy(self):
        self.document.copy_pattern(self.current())
        names = list(self.document.data['patterns'])
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
        self.place = list(self.document.data['patterns']).index(current)


class TracksPage(ListPage):
    crumbs = ('TRACKS',)
    HELP = (
        'The columns of the song, which become tracks in Ableton in this order.',
        '',
        '+ adds one, Enter or N renames it, and C copies it along with its clips.',
        'U and D move it. Bksp deletes it and its clips, after asking.',
    )
    columns = (('NAME', None, 'left'), ('CLIPS', 5, 'right'))

    def rows(self):
        return [(name, [name, self.document.track_clips(name)]) for name in self.document.data['tracks']]

    def keys(self):
        result = [*self.move_keys(), key('+', 'add', self.add)]
        if self.current() is not None:
            result += [
                key(('enter', 'n'), 'rename', self.rename, label='Enter'),
                key('c', 'copy', self.copy),
                key('backspace', 'delete', self.delete),
                key('u', 'move up', lambda: self.shift(-1)),
                key('d', 'move down', lambda: self.shift(1)),
            ]
        result.append(key('tab', 'back', self.go_back))
        return result

    def add(self):
        tracks = self.document.data['tracks']

        def named(text):
            self.document.add_track(text)
            self.place = len(tracks) - 1
        self.ask_name('New track name', '', tracks, named)

    def rename(self):
        name = self.current()
        self.ask_name('Rename track', name, self.document.data['tracks'], lambda new: self.document.rename_track(name, new))

    def copy(self):
        self.document.copy_track(self.current())
        self.place += 1

    def delete(self):
        name = self.current()
        clips = self.document.track_clips(name)
        extra = f'This also deletes its {clips} clip(s).' if clips else None
        self.delete_after_checks(f'track {name}', [], lambda: self.document.delete_track(name), extra)

    def shift(self, offset):
        if self.document.move_track(self.place, offset):
            self.place += offset


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
        document = self.document
        return [
            (name, [
                name + (' (song)' if document.data.get('scale') == name else ''),
                document.scale_notes_text(name), document.scale_size(name), len(document.scale_uses(name)),
            ])
            for name in document.data['scales']
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
        """Ask for a root, and then a kind of scale."""
        kinds = [text.replace('_', ' ') for text in SCALE_KINDS]

        def rooted(root_place):
            def kinded(kind_place):
                then(ROOTS[root_place], SCALE_KINDS[kind_place])
            place = SCALE_KINDS.index(kind) if kind in SCALE_KINDS else 0
            self.ask(ChoiceDialog(f'{title}: {ROOTS[root_place]}', kinds, place), kinded)
        self.ask(ChoiceDialog(f'{title}: root note', ROOTS, ROOTS.index(root) if root in ROOTS else 0), rooted)

    def add(self):
        scales = self.document.data['scales']
        current = scales.get(self.current()) or {'root': 'C', 'type': 'major'}

        def chosen(root, kind):
            default = unique_name(f"{root} {kind.replace('_', ' ').title()}", scales)

            def named(text):
                text = text.strip()
                if not text or text in scales:
                    self.status = 'That name is empty or already in use.'
                    return
                self.document.add_scale(text, root, kind)
                self.place = len(scales) - 1
            self.ask(PromptDialog('Scale name', default), named)
        self.pick_scale('New scale', current['root'], current['type'], chosen)

    def change(self):
        name = self.current()
        scale = self.document.data['scales'][name]
        self.pick_scale(f'Change {name}', scale['root'], scale['type'], lambda root, kind: self.document.change_scale(name, root, kind))

    def rename(self):
        name = self.current()
        self.ask_name('Rename scale', name, self.document.data['scales'], lambda new: self.document.rename_scale(name, new))

    def copy(self):
        self.document.copy_scale(self.current())
        self.place = len(self.document.data['scales']) - 1

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
        return [
            (name, [name, len(steps), len(self.document.chain_uses(name))])
            for name, steps in self.document.data['chains'].items()
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
        chains = self.document.data['chains']

        def named(text):
            self.document.add_chain(text)
            self.place = len(chains) - 1
        self.ask_name('New chain name', '', chains, named)

    def rename(self):
        name = self.current()
        self.ask_name('Rename chain', name, self.document.data['chains'], lambda new: self.document.rename_chain(name, new))

    def copy(self):
        self.document.copy_chain(self.current())
        self.place = len(self.document.data['chains']) - 1

    def delete(self):
        name = self.current()
        self.delete_after_checks(f'chain {name}', self.document.chain_uses(name), lambda: self.document.delete_chain(name))

    def shift(self, offset):
        if self.document.move_named('chains', self.place, offset):
            self.place += offset


class ChainEditor(ListPage):
    """A chain's steps. Only generators chosen by name can be changed, and anything else is kept as it is."""

    HELP = (
        'The steps run from top to bottom, each working on what the last one made.',
        '',
        '+ adds an arpeggiator or AutoRatchet, which you make on the Generators page. Enter changes one, C copies it, and Bksp removes it. U and D move any step.',
        '',
        'Steps marked read-only are older generators, which are kept as they are.',
    )
    columns = (('STEP', None, 'left'), ('', 9, 'left'))

    def __init__(self, holder, name):
        super().__init__(holder)
        self.item = name
        self.crumbs = ('CHAINS', name)

    def steps(self):
        return self.document.data['chains'][self.item]

    def editable(self, step):
        return isinstance(next(iter(step.values())), str)

    def rows(self):
        rows = []
        for place, step in enumerate(self.steps()):
            generator, settings = next(iter(step.items()))
            if self.editable(step):
                rows.append((place, [f'{generator}: {settings}', '']))
            else:
                detail = ', '.join(f'{k}: {v}' for k, v in (settings or {}).items())
                rows.append((place, [f'{generator}  {detail}'.rstrip(), 'read-only']))
        return rows

    def keys(self):
        result = [*self.move_keys(), key('+', 'add', self.add)]
        step = self.current()
        if step is not None and self.editable(self.steps()[step]):
            result += [
                key('enter', 'change', self.change),
                key('c', 'copy', self.copy),
                key('backspace', 'remove', self.remove_step),
            ]
        if step is not None:
            result += [key('u', 'move up', lambda: self.shift(-1)), key('d', 'move down', lambda: self.shift(1))]
        result.append(key('tab', 'back', self.go_back))
        return result

    def pick_generator(self, title, then):
        data = self.document.data
        options = [
            (kind, name) for section, kind in GENERATOR_SECTIONS.items() for name in data[section]
        ]
        if not options:
            self.tell('Nothing to add', 'Make an arpeggiator or AutoRatchet first, on the Generators page.')
            return
        labels = [f'{kind}: {name}' for kind, name in options]
        self.ask(ChoiceDialog(title, labels), lambda chosen: then(*options[chosen]))

    def add(self):
        def chosen(kind, name):
            self.steps().append({kind: name})
            self.document.changed()
            self.place = len(self.steps()) - 1
        self.pick_generator('Add to chain', chosen)

    def change(self):
        place = self.current()

        def chosen(kind, name):
            self.steps()[place] = {kind: name}
            self.document.changed()
        self.pick_generator('Change step', chosen)

    def copy(self):
        self.steps().insert(self.place + 1, dict(self.steps()[self.place]))
        self.document.changed()
        self.place += 1

    def remove_step(self):
        self.steps().pop(self.place)
        self.document.changed()
        self.clamp()

    def shift(self, offset):
        steps = self.steps()
        target = self.place + offset
        if 0 <= target < len(steps):
            steps.insert(target, steps.pop(self.place))
            self.document.changed()
            self.place = target


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
        data = self.document.data
        return [
            ('arps', ['Arpeggiators', len(data['arps'])]),
            ('auto_ratchets', ['AutoRatchets', len(data['auto_ratchets'])]),
        ]

    def keys(self):
        return [
            *self.move_keys(),
            key('enter', 'open', self.open_section),
            key('tab', 'back', self.go_back),
        ]

    def open_section(self):
        self.show_page(ArpsPage(self.holder) if self.current() == 'arps' else AutoRatchetsPage(self.holder))


class NamedGeneratorsPage(ListPage):
    """A list of generators of one kind, which chains use by name."""

    section = ''
    label = ''

    def uses(self, name):
        return self.document.generator_uses(self.section, name)

    def items(self):
        return self.document.data[self.section]

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
            self.place = len(self.items()) - 1
        self.ask_name(f'New {self.label} name', '', self.items(), named)

    def rename(self):
        name = self.current()
        self.ask_name(f'Rename {self.label}', name, self.items(), lambda new: self.document.rename_generator(self.section, name, new))

    def copy(self):
        self.document.copy_generator(self.section, self.current())
        self.place = len(self.items()) - 1

    def delete(self):
        name = self.current()
        self.delete_after_checks(f'{self.label} {name}', self.uses(name), lambda: self.document.delete_generator(self.section, name))

    def shift(self, offset):
        if self.document.move_named(self.section, self.place, offset):
            self.place += offset


class ArpsPage(NamedGeneratorsPage):
    crumbs = ('GENERATORS', 'ARPEGGIATORS')
    section = 'arps'
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
        return [
            (name, [name, arp.get('step', ''), arp.get('order', 'up'), len(self.uses(name))])
            for name, arp in self.items().items()
        ]


class AutoRatchetsPage(NamedGeneratorsPage):
    crumbs = ('GENERATORS', 'AUTORATCHETS')
    section = 'auto_ratchets'
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
        return [
            (name, [name, ' '.join(str(count) for count in item.get('counts', [])), len(self.uses(name))])
            for name, item in self.items().items()
        ]


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

    def settings(self):
        return self.document.data['auto_ratchets'][self.item]

    def ask_counts(self):
        def answered(text):
            parts = text.replace(',', ' ').split()
            if not parts or not all(part.isdigit() and int(part) >= 1 for part in parts):
                self.status = 'Counts must be whole numbers of 1 or more, like 1 1 4.'
                return
            self.settings()['counts'] = [int(part) for part in parts]
            self.document.changed()
        self.ask(PromptDialog('Counts', ' '.join(str(count) for count in self.settings()['counts'])), answered)

    def fields(self):
        return [Field('Counts', lambda: ' '.join(str(count) for count in self.settings()['counts']), None, self.ask_counts)]


class ArpEditor(FieldPage):
    HELP = (
        'Step: how long each note of the chord plays.',
        'Order: which way it goes through the chord. Random uses the seed.',
        'Seed: leave it to use the song seed, or set one for just this arpeggiator.',
        '',
        'Up and down select a setting. Left and right, or + and -, change it, and Enter types or chooses.',
    )

    def __init__(self, holder, name):
        super().__init__(holder)
        self.item = name
        self.crumbs = ('GENERATORS', 'ARPEGGIATORS', name)

    def arp(self):
        return self.document.data['arps'][self.item]

    def set_value(self, name, value):
        self.arp()[name] = value
        self.document.changed()

    def clear_seed(self):
        self.arp().pop('seed', None)
        self.document.changed()

    def pick(self, title, options, name, default):
        current = str(self.arp().get(name, default))
        self.ask(ChoiceDialog(title, options, options.index(current) if current in options else 0), lambda chosen: self.set_value(name, options[chosen]))

    def fields(self):
        arp = self.arp()
        return [
            Field('Step', lambda: arp.get('step', ''), lambda d: self.set_value('step', _stepped(NOTE_LENGTHS, arp.get('step'), d)),
                  lambda: self.pick('Step', NOTE_LENGTHS, 'step', '1/16'), 'choose'),
            Field('Order', lambda: arp.get('order', 'up'), lambda d: self.set_value('order', _stepped(ORDERS, arp.get('order', 'up'), d)),
                  lambda: self.pick('Order', ORDERS, 'order', 'up'), 'choose'),
            Field('Seed', lambda: arp.get('seed', '(song)'), lambda d: self.set_value('seed', arp.get('seed', 0) + d),
                  lambda: self.ask_number('Seed', arp.get('seed', 0), lambda n: self.set_value('seed', n)), 'edit',
                  self.clear_seed, 'use the song seed'),
        ]

