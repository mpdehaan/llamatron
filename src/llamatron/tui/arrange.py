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

"""The Arrange page, with scenes as rows and tracks as columns, and the scene and clip pages."""

from rich.text import Text

from llamatron.tui.base import ChoiceDialog, ConfirmDialog, Page, PromptDialog, columns, fit, key
from llamatron.song_file import DIRECTIONS
from llamatron.tui.document import DIRECTION_NAMES, MORPH_STYLES, clock, unique_name
from llamatron.tui.lists import PLUS, Field, FieldPage

FIRST_MORPH_STYLE = next(iter(MORPH_STYLES))
SCENE_WIDTH = 24
CELL_WIDTH = 13


def cell_text(cell):
    """Return what a clip shows on the grid, with marks for anything beyond its pattern."""
    if cell is None:
        return '+'
    name = cell['pattern']
    marks = ''
    if cell.get('direction'):
        marks += 'd'
    if cell.get('rhythm_from'):
        marks += 'r'
    if cell.get('notes_from'):
        marks += 'n'
    if cell.get('morph_to'):
        marks += '~'
    if cell.get('loop'):
        marks += '∞'
    if cell.get('repeat', 1) > 1:
        marks += f"×{cell['repeat']}"
    if marks:
        return f'{fit(name, max(CELL_WIDTH - len(marks) - 2, 1)).rstrip()} {marks}'
    return name


class ArrangePage(Page):
    crumbs = ('ARRANGE',)
    HELP = (
        'Scenes are the rows and tracks are the columns. Scenes render from top to bottom, and a + is an empty clip.',
        '',
        'On a +: Enter chooses a pattern and adds a clip. On a clip: Enter edits it, C copies it, V pastes it on another cell, and Bksp deletes it.',
        'On a scene name: Enter opens its settings, C copies it, and Bksp deletes it.',
        '+ adds a scene, or Enter on the + at the bottom. U and D move the selected one.',
        '',
        '×3 means repeats, ∞ loop, ~ morph, d its own direction, r rhythm from and n notes from another pattern.',
    )

    def __init__(self, holder):
        super().__init__(holder)
        self.row = 0
        self.column = 0
        self.top = 0
        self.left = 0
        self.copied = None

    def duration(self):
        return self.document.song_seconds()

    def scenes(self):
        return self.document.data['scenes']

    def tracks(self):
        return self.document.data['tracks']

    def on_scene_name(self):
        return self.column == 0

    def on_plus_row(self):
        return self.row == len(self.scenes())

    def track(self):
        return self.tracks()[self.column - 1]

    def clamp(self):
        self.row = max(min(self.row, len(self.scenes())), 0)
        self.column = 0 if self.on_plus_row() else max(min(self.column, len(self.tracks())), 0)

    def keys(self):
        self.clamp()
        result = [key(('left', 'right', 'up', 'down'), 'move', self.move, label='←↑↓→', wants_key=True), key('+', 'add scene', self.add_scene)]
        if self.on_plus_row():
            return [*result, key('enter', 'add scene', self.add_scene), key('tab', 'back', self.go_back)]
        if self.on_scene_name():
            result += [
                key('enter', 'scene settings', lambda: self.show_page(ScenePage(self.holder, self.row))),
                key('c', 'copy scene', self.copy_scene),
                key('backspace', 'delete scene', self.delete_scene),
            ]
        else:
            cell = self.document.cell(self.row, self.track())
            if cell is None:
                result.append(key('enter', 'add clip', self.add_clip))
            else:
                result += [
                    key('enter', 'edit clip', lambda: self.show_page(ClipPage(self.holder, self.row, self.track()))),
                    key('c', 'copy clip', self.copy_clip),
                    key('backspace', 'delete clip', self.delete_clip),
                ]
            if self.copied is not None:
                result.append(key('v', 'paste clip', self.paste_clip))
        result += [
            key('u', 'scene up', lambda: self.shift(-1)),
            key('d', 'scene down', lambda: self.shift(1)),
            key('tab', 'back', self.go_back),
        ]
        return result

    def move(self, name):
        if name == 'up':
            self.row -= 1
        elif name == 'down':
            self.row += 1
        elif name == 'left':
            self.column -= 1
        else:
            self.column += 1
        self.clamp()

    def visible_tracks(self, width):
        count = max((width - SCENE_WIDTH - 2) // (CELL_WIDTH + 1), 1)
        if self.column > 0:
            place = self.column - 1
            if place < self.left:
                self.left = place
            elif place >= self.left + count:
                self.left = place - count + 1
        self.left = max(min(self.left, max(len(self.tracks()) - count, 0)), 0)
        return self.left, min(self.left + count, len(self.tracks()))

    def scene_label(self, index):
        scene = self.scenes()[index]
        repeat = scene.get('repeat', 1)
        name = str(scene.get('name', f'scene {index + 1}'))
        if repeat > 1:
            name += f' ×{repeat}'
        length = clock(self.document.scene_seconds(index))
        return f'{fit(f"{index + 1:>2} {name}", SCENE_WIDTH - len(length) - 1)}{length} '

    def body(self, width, height):
        self.clamp()
        scenes, tracks = self.scenes(), self.tracks()
        first, last = self.visible_tracks(width)
        head = Text(no_wrap=True, style='bold')
        head.append(fit(' SCENE', SCENE_WIDTH))
        for name in tracks[first:last]:
            head.append('│')
            head.append(fit(f' {name}', CELL_WIDTH))
        more = last < len(tracks)
        head.append('›' if more else '')
        rule = '─' * SCENE_WIDTH + ('┼' + '─' * CELL_WIDTH) * (last - first)
        lines = [head, Text(rule, style='dim', no_wrap=True)]
        room = max(height - 4, 1)
        if self.row < self.top:
            self.top = self.row
        elif self.row >= self.top + room:
            self.top = self.row - room + 1
        for index in range(self.top, min(self.top + room, len(scenes))):
            line = Text(no_wrap=True)
            selected = index == self.row and self.column == 0
            line.append(fit(self.scene_label(index), SCENE_WIDTH), style='reverse' if selected else 'bold')
            for place in range(first, last):
                line.append('│', style='dim')
                cell = self.document.cell(index, tracks[place])
                text = cell_text(cell)
                if cell is None:
                    text = text.center(CELL_WIDTH)
                style = 'reverse' if index == self.row and self.column == place + 1 else ('dim' if cell is None else '')
                line.append(fit(text if cell is None else f' {text}', CELL_WIDTH), style=style)
            lines.append(line)
        if self.top + room > len(scenes):
            plus = fit(f'   {PLUS}', SCENE_WIDTH)
            lines.append(Text(plus, style='reverse' if self.on_plus_row() else 'dim', no_wrap=True))
        lines += [Text(''), Text(' ' + fit(self.details(), width - 1), style='bold')]
        return lines

    def details(self):
        if self.on_plus_row():
            return 'Press Enter to add a scene.'
        document = self.document
        scene = self.scenes()[self.row]
        name = scene.get('name', f'scene {self.row + 1}')
        length = clock(document.scene_seconds(self.row))
        problem = document.scene_problem(self.row)
        if problem and 'every clip' in problem:
            problem = 'every clip loops, so turn off loop on at least one'
        suffix = f'  ({problem})' if problem else ''
        if self.on_scene_name():
            return f'Scene {name}: {length}{suffix}'
        if not self.tracks():
            return 'Add tracks on the Tracks page.'
        track = self.track()
        cell = document.cell(self.row, track)
        if cell is None:
            return f'{name} / {track}: empty{suffix}'
        return f'{name} / {track}: {clock(document.clip_seconds(self.row, track))} of {length}{suffix}'

    def add_scene(self):
        index = len(self.scenes()) if self.on_plus_row() else self.row + 1
        names = {scene.get('name') for scene in self.scenes()}
        self.document.add_scene(index, unique_name(f'scene {len(self.scenes()) + 1}', names))
        self.row, self.column = index, 0

    def copy_scene(self):
        self.document.copy_scene(self.row)
        self.row += 1

    def delete_scene(self):
        scene = self.scenes()[self.row]
        count = len(scene.get('tracks') or {})
        message = [f"Delete scene {scene.get('name', self.row + 1)}?"]
        if count:
            message.append(f'This also deletes its {count} clip(s).')
        self.ask(ConfirmDialog('Delete', message), lambda _: self.document.delete_scene(self.row))

    def shift(self, offset):
        if self.document.move_scene(self.row, offset):
            self.row += offset

    def add_clip(self):
        patterns = list(self.document.data['patterns'])
        if not patterns:
            self.tell('No patterns', 'Add a pattern first, on the Patterns page.')
            return
        row, track = self.row, self.track()

        def chosen(place):
            self.document.set_cell(row, track, {'pattern': patterns[place]})
            self.show_page(ClipPage(self.holder, row, track))
        self.ask(ChoiceDialog('Pattern for this clip', patterns), chosen)

    def copy_clip(self):
        self.copied = dict(self.document.cell(self.row, self.track()))
        self.status = 'Copied the clip. Press V on another cell to paste it.'

    def paste_clip(self):
        self.document.set_cell(self.row, self.track(), dict(self.copied))

    def delete_clip(self):
        track, row = self.track(), self.row
        self.ask(ConfirmDialog('Delete', [f'Delete the clip on track {track}?']), lambda _: self.document.delete_cell(row, track))


class ScenePage(FieldPage):
    """A scene's settings, and how long it lasts."""

    HELP = (
        'A scene starts all of its clips together, and lasts as long as its longest clip that does not loop.',
        '',
        'Scale: used by its clips, instead of the song\'s. Tempo: instead of the song\'s.',
        'Tempo ramps to: moves from Tempo to this across the scene\'s repeats.',
        'Repeat: plays the whole scene that many times.',
        '',
        'Up and down select a setting. Left and right, or + and -, change it, and Enter types or chooses. Bksp goes back to the song\'s value.',
    )

    def __init__(self, holder, index):
        super().__init__(holder)
        self.index = index
        self.crumbs = ('ARRANGE', self.scene().get('name', f'scene {index + 1}'))

    def duration(self):
        return self.document.scene_seconds(self.index)

    def scene(self):
        return self.document.data['scenes'][self.index]

    def rename(self):
        def named(text):
            text = text.strip()
            if text:
                self.scene()['name'] = text
                self.document.changed()
                self.crumbs = ('ARRANGE', text)
        self.ask(PromptDialog('Scene name', self.scene().get('name', '')), named)

    def pick_scale(self):
        scales = list(self.document.data['scales'])
        options = ['(song)', *scales]
        current = self.scene().get('scale')

        def chosen(place):
            if place == 0:
                self.clear_scale()
            else:
                self.scene()['scale'] = scales[place - 1]
                self.document.changed()
        self.ask(ChoiceDialog('Scene scale', options, options.index(current) if current in options else 0), chosen)

    def clear_scale(self):
        self.scene().pop('scale', None)
        self.document.changed()

    def tempo(self):
        scene = self.scene()
        return scene.get('tempo', scene.get('tempo_start'))

    def set_tempo(self, value):
        scene = self.scene()
        if 'tempo_end' in scene:
            scene['tempo_start'] = value
        else:
            scene['tempo'] = value
        self.document.changed()

    def clear_tempo(self):
        for name in ('tempo', 'tempo_start', 'tempo_end'):
            self.scene().pop(name, None)
        self.document.changed()

    def set_ramp(self, value):
        scene = self.scene()
        start = self.tempo() or self.document.data['tempo']
        scene.pop('tempo', None)
        scene['tempo_start'], scene['tempo_end'] = start, value
        self.document.changed()

    def clear_ramp(self):
        scene = self.scene()
        start = scene.pop('tempo_start', None)
        scene.pop('tempo_end', None)
        if start is not None:
            scene['tempo'] = start
        self.document.changed()

    def fields(self):
        scene, song_tempo = self.scene(), self.document.data['tempo']
        tempo = self.tempo()
        end = scene.get('tempo_end')
        return [
            Field('Name', lambda: scene.get('name', ''), None, self.rename),
            Field('Scale', lambda: scene.get('scale') or f"(song: {self.document.data.get('scale') or 'none'})", None, self.pick_scale, 'choose', self.clear_scale, 'use the song scale'),
            Field('Tempo', lambda: f'{tempo} BPM' if tempo is not None else f'(song: {song_tempo} BPM)',
                  lambda d: self.set_tempo((tempo or song_tempo) + d),
                  lambda: self.ask_number('Tempo', tempo or song_tempo, self.set_tempo, 10, 999), 'edit',
                  self.clear_tempo, 'use the song tempo'),
            Field('Tempo ramps to', lambda: f'{end} BPM' if end is not None else '(off)',
                  lambda d: self.set_ramp((end or tempo or song_tempo) + d),
                  lambda: self.ask_number('Tempo ramps to', end or tempo or song_tempo, self.set_ramp, 10, 999), 'edit',
                  self.clear_ramp, 'no ramp'),
            Field('Repeat', lambda: scene.get('repeat', 1), lambda d: self.document.set_scene_repeat(self.index, max(scene.get('repeat', 1) + d, 1)),
                  lambda: self.ask_number('Repeat', scene.get('repeat', 1), lambda n: self.document.set_scene_repeat(self.index, n), 1, 999)),
        ]

    def notes(self, width):
        document = self.document
        lines = [Text(f'  Length    {clock(document.scene_seconds(self.index))}  (its longest clip that does not loop, with repeats)', style='dim')]
        problem = document.scene_problem(self.index)
        if problem:
            lines.append(Text(f'  Problem   {problem}'[:width]))
        return lines


class ClipPage(FieldPage):
    """One clip: what it plays, how many times, and whether it morphs into another pattern."""

    HELP = (
        'Pattern: what it plays. Chain: generators to run on it when rendering.',
        'Repeat: how many times it plays, then silence while other clips finish.',
        'Loop: plays until the other clips are done. One clip in each scene must not loop, or rendering stops with a message.',
        'Direction: overrides the play direction of its patterns.',
        '',
        'With Repeat above 1, Morph to chooses a second pattern to change into across the repeats, and Morph direction is where the change starts.',
        '',
        'Rhythm from takes Duration, rests, Velocity, Prob, Ratchet and Glide from another pattern. Notes from takes Degree, #/b, Octave and Chord, skips rests, and carries on across repeats.',
        '',
        'Up and down select. Left and right, or + and -, change. Enter chooses.',
    )

    def __init__(self, holder, index, track):
        super().__init__(holder)
        self.index, self.track = index, track
        name = holder.document.data['scenes'][index].get('name', f'scene {index + 1}')
        self.crumbs = ('ARRANGE', str(name), track)

    def duration(self):
        return self.document.clip_seconds(self.index, self.track)

    def cell(self):
        return self.document.cell(self.index, self.track)

    def set_value(self, name, value):
        self.cell()[name] = value
        self.document.changed()

    def clear(self, *names):
        for name in names:
            self.cell().pop(name, None)
        self.document.changed()

    def pick_pattern(self, title, name):
        patterns = list(self.document.data['patterns'])
        current = self.cell().get(name)
        place = patterns.index(current) if current in patterns else 0

        def chosen(item):
            self.set_value(name, patterns[item])
            if name == 'morph_to':
                self.cell().setdefault('morph_style', FIRST_MORPH_STYLE)
        self.ask(ChoiceDialog(title, patterns, place), chosen)

    def pick_other_pattern(self, title, name):
        patterns = list(self.document.data['patterns'])
        options = ['(none)', *patterns]
        current = self.cell().get(name)

        def chosen(item):
            if item == 0:
                self.clear(name)
            else:
                self.set_value(name, patterns[item - 1])
        self.ask(ChoiceDialog(title, options, options.index(current) if current in options else 0), chosen)

    def pick_chain(self):
        chains = list(self.document.data['chains'])
        options = ['(none)', *chains]
        current = self.cell().get('chain')

        def chosen(item):
            if item == 0:
                self.clear('chain')
            else:
                self.set_value('chain', chains[item - 1])
        self.ask(ChoiceDialog('Chain', options, options.index(current) if current in options else 0), chosen)

    def set_repeat(self, value):
        cell = self.cell()
        value = max(value, 1)
        if value > 1:
            cell['repeat'] = value
        else:
            # A morph runs across repeats, so it can't stay without them.
            for name in ('repeat', 'morph_to', 'morph_style'):
                cell.pop(name, None)
        self.document.changed()

    def set_direction(self, direction):
        if direction is None:
            self.clear('direction')
        else:
            self.set_value('direction', direction)

    def step_direction(self, offset):
        options = [None, *DIRECTIONS]
        place = options.index(self.cell().get('direction'))
        self.set_direction(options[(place + offset) % len(options)])

    def pick_direction(self):
        options = [None, *DIRECTIONS]
        labels = columns([
            ('(pattern)', "use each pattern's direction"),
            *[(name.replace('_', ' '), DIRECTION_NAMES[name]) for name in DIRECTIONS],
        ])
        place = options.index(self.cell().get('direction'))
        self.ask(ChoiceDialog('Play direction', labels, place), lambda chosen: self.set_direction(options[chosen]))

    def direction_text(self):
        direction = self.cell().get('direction')
        if direction:
            return direction.replace('_', ' ')
        pattern = self.document.data['patterns'][self.cell()['pattern']]
        return f"(pattern: {pattern.get('direction', 'forward').replace('_', ' ')})"

    def toggle_loop(self):
        if self.cell().get('loop'):
            self.clear('loop')
        else:
            self.set_value('loop', True)

    def step_style(self, offset):
        style = self.cell().get('morph_style', FIRST_MORPH_STYLE)
        styles = list(MORPH_STYLES)
        place = styles.index(style)
        self.set_value('morph_style', styles[(place + offset) % len(styles)])

    def fields(self):
        cell = self.cell()
        result = [
            Field('Pattern', lambda: cell['pattern'], None, lambda: self.pick_pattern('Pattern', 'pattern'), 'choose'),
            Field('Chain', lambda: cell.get('chain', '(none)'), None, self.pick_chain, 'choose', lambda: self.clear('chain'), 'no chain'),
            Field('Repeat', lambda: cell.get('repeat', 1), lambda d: self.set_repeat(cell.get('repeat', 1) + d),
                  lambda: self.ask_number('Repeat', cell.get('repeat', 1), self.set_repeat, 1, 9999)),
            Field('Loop', lambda: 'on' if cell.get('loop') else 'off', None, self.toggle_loop, 'toggle'),
            Field('Direction', self.direction_text, self.step_direction, self.pick_direction, 'choose',
                  lambda: self.clear('direction'), 'use the pattern\'s'),
        ]
        if cell.get('repeat', 1) > 1:
            result.append(Field('Morph to', lambda: cell.get('morph_to', '(none)'), None, lambda: self.pick_pattern('Morph to', 'morph_to'), 'choose',
                                lambda: self.clear('morph_to', 'morph_style'), 'no morph'))
            if cell.get('morph_to'):
                result.append(Field('Morph direction', lambda: cell.get('morph_style', FIRST_MORPH_STYLE), self.step_style, lambda: self.step_style(1), 'next'))
        result += [
            Field('Rhythm from', lambda: cell.get('rhythm_from', '(none)'), None, lambda: self.pick_other_pattern('Rhythm from', 'rhythm_from'), 'choose',
                  lambda: self.clear('rhythm_from'), 'no pattern'),
            Field('Notes from', lambda: cell.get('notes_from', '(none)'), None, lambda: self.pick_other_pattern('Notes from', 'notes_from'), 'choose',
                  lambda: self.clear('notes_from'), 'no pattern'),
        ]
        return result

    def notes(self, width):
        document = self.document
        lines = [Text(f'  Length    {clock(document.clip_seconds(self.index, self.track))}  of a {clock(document.scene_seconds(self.index))} scene', style='dim')]
        if self.cell().get('loop'):
            lines.append(Text('  Plays until the other clips are done. One clip in a scene must not loop.', style='dim'))
        elif self.cell().get('repeat', 1) == 1:
            lines.append(Text('  Set Repeat above 1 to choose a pattern to morph to.', style='dim'))
        if 'rhythm_from' in self.cell() and 'notes_from' in self.cell():
            lines.append(Text('  With Rhythm from and Notes from both set, Pattern is not played.', style='dim'))
        problem = document.scene_problem(self.index)
        if problem:
            lines.append(Text(f'  Problem   {problem}'[:width]))
        return lines
