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
from llamatron.composition.defaults import DEFAULT_REPEAT
from llamatron.composition.file_format import DIRECTIONS, REGISTER_NAMES, CellSetting
from llamatron.composition.cell import MORPH_STYLES
from llamatron.composition.limits import MAX_TEMPO, MIN_REPEAT, MIN_TEMPO
from llamatron.tui.document import DIRECTION_NAMES, FIRST_MORPH_STYLE, clock, plain_number, tempo_text, unique_name
from llamatron.tui.lists import PLUS, Field, FieldPage
from llamatron.tui.pattern_editor import TOGGLE_OFF, TOGGLE_ON

SCENE_WIDTH = 24
# A scene's field for each register it can reset, like "Reset AX".
RESET_LABEL = 'Reset {name}'
RESET_WHAT = 'toggle'
CELL_WIDTH = 13
# What a scene is called when the file gives it no name, by its place from 1.
UNNAMED_SCENE = 'scene {number}'
# The marks after a clip's pattern on the grid, for anything beyond the pattern itself.
DIRECTION_MARK = 'd'
GRAB_MARK = 'g'
MORPH_MARK = '~'
LOOP_MARK = '∞'
REPEAT_MARK = '×{repeat}'
NONE_SHOWN = '(none)'
NO_SCALE_SHOWN = 'none'
SONG_SCALE_SHOWN = '(song: {scale})'
SONG_TEMPO_SHOWN = '(song: {tempo} BPM)'
TEMPO_SHOWN = '{tempo} BPM'
MSG_PASTED_WITHOUT_GRAB = 'Pasted without its grab from {track}, which would go round in a circle here.'
# How many times a clip can play, and how many a scene can.
MAX_CLIP_REPEAT = 9999
MAX_SCENE_REPEAT = 999


def scene_name(scene, index):
    """Return a scene's name, or what it's called by its place if the file gives it none."""
    name = scene.get_name()
    return UNNAMED_SCENE.format(number=index + 1) if name is None else str(name)


def cell_text(cell):
    """Return what a clip shows on the grid, with marks for anything beyond its pattern."""
    if cell is None:
        return PLUS
    name = cell.get_pattern_name()
    marks = ''
    if cell.get_direction():
        marks += DIRECTION_MARK
    if cell.get_grab_track():
        marks += GRAB_MARK
    if cell.get_morph_target():
        marks += MORPH_MARK
    if cell.loops():
        marks += LOOP_MARK
    if cell.get_repeat() > DEFAULT_REPEAT:
        marks += REPEAT_MARK.format(repeat=cell.get_repeat())
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
        '×3 means repeats, ∞ loop, ~ morph, d its own direction, and g grabs from another track.',
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
        return self.document.song().get_scenes()

    def tracks(self):
        return self.document.track_names()

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
        repeat = scene.get_repeat()
        name = scene_name(scene, index)
        if repeat > DEFAULT_REPEAT:
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
        name = scene_name(self.scenes()[self.row], self.row)
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
        names = {scene.get_name() for scene in self.scenes()}
        self.document.add_scene(index, unique_name(UNNAMED_SCENE.format(number=len(self.scenes()) + 1), names))
        self.row, self.column = index, 0

    def copy_scene(self):
        self.document.copy_scene(self.row)
        self.row += 1

    def delete_scene(self):
        scene = self.scenes()[self.row]
        count = len(scene.get_track_names())
        message = [f'Delete scene {scene_name(scene, self.row)}?']
        if count:
            message.append(f'This also deletes its {count} clip(s).')
        self.ask(ConfirmDialog('Delete', message), lambda _: self.document.delete_scene(self.row))

    def shift(self, offset):
        if self.document.move_scene(self.row, offset):
            self.row += offset

    def add_clip(self):
        patterns = self.document.song().get_pattern_names()
        if not patterns:
            self.tell('No patterns', 'Add a pattern first, on the Patterns page.')
            return
        row, track = self.row, self.track()

        def chosen(place):
            self.document.add_cell(row, track, patterns[place])
            self.show_page(ClipPage(self.holder, row, track))
        self.ask(ChoiceDialog('Pattern for this clip', patterns), chosen)

    def copy_clip(self):
        self.copied = self.document.cell(self.row, self.track()).to_data()
        self.status = 'Copied the clip. Press V on another cell to paste it.'

    def paste_clip(self):
        dropped = self.document.paste_cell(self.row, self.track(), self.copied)
        if dropped is not None:
            self.status = MSG_PASTED_WITHOUT_GRAB.format(track=dropped)

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
        'Reset AX to DX: sets that register back to its default as the scene starts, but not on its repeats.',
        '',
        'Up and down select a setting. Left and right, or + and -, change it, and Enter types or chooses. Bksp goes back to the song\'s value.',
    )

    def __init__(self, holder, index):
        super().__init__(holder)
        self.index = index
        self.crumbs = ('ARRANGE', scene_name(self.scene(), index))

    def duration(self):
        return self.document.scene_seconds(self.index)

    def scene(self):
        return self.document.song().get_scenes()[self.index]

    def rename(self):
        def named(text):
            text = text.strip()
            if text:
                self.document.set_scene_name(self.index, text)
                self.crumbs = ('ARRANGE', text)
        self.ask(PromptDialog('Scene name', self.scene().get_name() or ''), named)

    def pick_scale(self):
        scales = self.document.song().get_scale_names()
        options = ['(song)', *scales]
        current = self.scene().get_scale_name()

        def chosen(place):
            self.document.set_scene_scale(self.index, None if place == 0 else scales[place - 1])
        self.ask(ChoiceDialog('Scene scale', options, options.index(current) if current in options else 0), chosen)

    def clear_scale(self):
        self.document.set_scene_scale(self.index, None)

    def tempo(self):
        """Return the tempo the scene sets, or starts its ramp from, or None if it uses the song's."""
        scene = self.scene()
        return scene.get_tempo_start() if scene.get_tempo_setting() is None else scene.get_tempo_setting()

    def set_tempo(self, value):
        self.document.set_scene_tempo(self.index, value)

    def clear_tempo(self):
        self.document.clear_scene_tempo(self.index)

    def set_ramp(self, value):
        self.document.set_scene_tempo_ramp(self.index, value)

    def clear_ramp(self):
        self.document.clear_scene_tempo_ramp(self.index)

    def scale_text(self):
        scene_scale = self.scene().get_scale_name()
        if scene_scale is not None:
            return scene_scale
        return SONG_SCALE_SHOWN.format(scale=self.document.song().get_scale_name() or NO_SCALE_SHOWN)

    def fields(self):
        scene = self.scene()
        song_tempo = plain_number(self.document.song().get_tempo())
        tempo = self.tempo()
        end = scene.get_tempo_end()
        repeat = scene.get_repeat()
        return [
            Field('Name', lambda: scene.get_name() or '', None, self.rename),
            Field('Scale', self.scale_text, None, self.pick_scale, 'choose', self.clear_scale, 'use the song scale'),
            Field('Tempo', lambda: TEMPO_SHOWN.format(tempo=tempo) if tempo is not None else SONG_TEMPO_SHOWN.format(tempo=tempo_text(self.document.song().get_tempo())),
                  lambda d: self.set_tempo((tempo or song_tempo) + d),
                  lambda: self.ask_number('Tempo', tempo or song_tempo, self.set_tempo, MIN_TEMPO, MAX_TEMPO), 'edit',
                  self.clear_tempo, 'use the song tempo'),
            Field('Tempo ramps to', lambda: TEMPO_SHOWN.format(tempo=end) if end is not None else '(off)',
                  lambda d: self.set_ramp((end or tempo or song_tempo) + d),
                  lambda: self.ask_number('Tempo ramps to', end or tempo or song_tempo, self.set_ramp, MIN_TEMPO, MAX_TEMPO), 'edit',
                  self.clear_ramp, 'no ramp'),
            Field('Repeat', lambda: repeat, lambda d: self.document.set_scene_repeat(self.index, max(repeat + d, MIN_REPEAT)),
                  lambda: self.ask_number('Repeat', repeat, lambda n: self.document.set_scene_repeat(self.index, n), MIN_REPEAT, MAX_SCENE_REPEAT)),
            *[self.reset_field(name) for name in REGISTER_NAMES],
        ]

    def reset_field(self, register):
        """Return the field that makes the scene reset a register as it starts."""
        on = self.document.resets(self.index, register)
        return Field(RESET_LABEL.format(name=register), lambda: TOGGLE_ON if on else TOGGLE_OFF, None,
                     lambda: self.document.set_reset(self.index, register, not on), RESET_WHAT)

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
        'Grab track: Grab steps play the note that track last started.',
        '',
        'Up and down select. Left and right, or + and -, change. Enter chooses.',
    )

    def __init__(self, holder, index, track):
        super().__init__(holder)
        self.index, self.track = index, track
        self.crumbs = ('ARRANGE', scene_name(holder.document.song().get_scenes()[index], index), track)

    def duration(self):
        return self.document.clip_seconds(self.index, self.track)

    def cell(self):
        return self.document.cell(self.index, self.track)

    def set_value(self, setting, value):
        """Set one of the clip's settings, or None to leave it out and use its default."""
        self.document.set_cell_setting(self.index, self.track, setting, value)

    def clear(self, setting):
        self.set_value(setting, None)

    def pick_pattern(self, title, current, then):
        """Ask for one of the song's patterns, starting on the current one, and pass its name to then."""
        patterns = self.document.song().get_pattern_names()
        place = patterns.index(current) if current in patterns else 0
        self.ask(ChoiceDialog(title, patterns, place), lambda item: then(patterns[item]))

    def set_morph_target(self, pattern):
        self.document.set_cell_morph_target(self.index, self.track, pattern)

    def clear_morph(self):
        self.document.clear_cell_morph(self.index, self.track)

    def pick_grab_track(self):
        tracks = [name for name in self.document.track_names() if name != self.track]
        if not tracks:
            self.tell('No other tracks', 'Add another track to grab notes from, on the Tracks page.')
            return
        options = [NONE_SHOWN, *tracks]
        current = self.cell().get_grab_track()

        def chosen(item):
            if item == 0:
                self.clear(CellSetting.GRAB_TRACK)
                return
            other = tracks[item - 1]
            circle = self.document.grab_circle(self.index, self.track, other)
            if circle:
                self.tell('Circular grab', f"Grabbing from {other} would go round in a circle: {' → '.join(circle)}.",
                          'Remove the grab from another clip in this scene first.')
                return
            self.set_value(CellSetting.GRAB_TRACK, other)
        self.ask(ChoiceDialog('Grab track', options, options.index(current) if current in options else 0), chosen)

    def pick_chain(self):
        chains = self.document.song().get_chain_names()
        options = [NONE_SHOWN, *chains]
        current = self.cell().get_chain_name()

        def chosen(item):
            self.set_value(CellSetting.CHAIN, None if item == 0 else chains[item - 1])
        self.ask(ChoiceDialog('Chain', options, options.index(current) if current in options else 0), chosen)

    def set_repeat(self, value):
        self.document.set_cell_repeat(self.index, self.track, value)

    def set_direction(self, direction):
        self.set_value(CellSetting.DIRECTION, direction)

    def step_direction(self, offset):
        options = [None, *DIRECTIONS]
        place = options.index(self.cell().get_direction())
        self.set_direction(options[(place + offset) % len(options)])

    def pick_direction(self):
        options = [None, *DIRECTIONS]
        labels = columns([
            ('(pattern)', "use each pattern's direction"),
            *[(name.replace('_', ' '), DIRECTION_NAMES[name]) for name in DIRECTIONS],
        ])
        place = options.index(self.cell().get_direction())
        self.ask(ChoiceDialog('Play direction', labels, place), lambda chosen: self.set_direction(options[chosen]))

    def direction_text(self):
        direction = self.cell().get_direction()
        if direction:
            return direction.replace('_', ' ')
        pattern = self.document.song().get_pattern(self.cell().get_pattern_name())
        return f"(pattern: {pattern.get_direction().replace('_', ' ')})"

    def toggle_loop(self):
        self.set_value(CellSetting.LOOP, None if self.cell().loops() else True)

    def morph_style(self):
        return self.cell().get_morph_style_name() or FIRST_MORPH_STYLE

    def step_style(self, offset):
        styles = list(MORPH_STYLES)
        place = styles.index(self.morph_style())
        self.set_value(CellSetting.MORPH_STYLE, styles[(place + offset) % len(styles)])

    def fields(self):
        cell = self.cell()
        repeat = cell.get_repeat()
        result = [
            Field('Pattern', cell.get_pattern_name, None,
                  lambda: self.pick_pattern('Pattern', cell.get_pattern_name(), lambda name: self.set_value(CellSetting.PATTERN, name)), 'choose'),
            Field('Chain', lambda: cell.get_chain_name() or NONE_SHOWN, None, self.pick_chain, 'choose', lambda: self.clear(CellSetting.CHAIN), 'no chain'),
            Field('Repeat', lambda: repeat, lambda d: self.set_repeat(repeat + d),
                  lambda: self.ask_number('Repeat', repeat, self.set_repeat, MIN_REPEAT, MAX_CLIP_REPEAT)),
            Field('Loop', lambda: 'on' if cell.loops() else 'off', None, self.toggle_loop, 'toggle'),
            Field('Direction', self.direction_text, self.step_direction, self.pick_direction, 'choose',
                  lambda: self.clear(CellSetting.DIRECTION), 'use the pattern\'s'),
        ]
        if repeat > DEFAULT_REPEAT:
            result.append(Field('Morph to', lambda: cell.get_morph_target() or NONE_SHOWN, None,
                                lambda: self.pick_pattern('Morph to', cell.get_morph_target(), self.set_morph_target), 'choose',
                                self.clear_morph, 'no morph'))
            if cell.get_morph_target():
                result.append(Field('Morph direction', self.morph_style, self.step_style, lambda: self.step_style(1), 'next'))
        result += [
            Field('Grab track', lambda: cell.get_grab_track() or NONE_SHOWN, None, self.pick_grab_track, 'choose',
                  lambda: self.clear(CellSetting.GRAB_TRACK), 'no grab'),
        ]
        return result

    def notes(self, width):
        document = self.document
        cell = self.cell()
        lines = [Text(f'  Length    {clock(document.clip_seconds(self.index, self.track))}  of a {clock(document.scene_seconds(self.index))} scene', style='dim')]
        if cell.loops():
            lines.append(Text('  Plays until the other clips are done. One clip in a scene must not loop.', style='dim'))
        elif cell.get_repeat() == DEFAULT_REPEAT:
            lines.append(Text('  Set Repeat above 1 to choose a pattern to morph to.', style='dim'))
        if cell.get_grab_track() is not None and not self.document.has_grab_steps(cell.get_pattern_name()):
            lines.append(Text('  Grab track only changes Grab steps, and this pattern has none yet.', style='dim'))
        problem = document.scene_problem(self.index)
        if problem:
            lines.append(Text(f'  Problem   {problem}'[:width]))
        return lines
