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

"""The Scene page: a scene's settings, and how long it lasts."""

from rich.text import Text

from llamatron.composition import limits
from llamatron.strings import help as help_text, labels, legends, marks, messages
from llamatron.composition.file_format import SECTION_KINDS, SHAPES, shape_setting, REGISTER_NAMES, Section
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.text import clock, plain_number, sorted_names, tempo_text
from llamatron.tui.drawing import NOTHING, Style
from llamatron.tui.screens.shared.field import ChoiceField, Field, NameField, NumberField, Toggle
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.arrange.groove_choice import groove_choice_field
from llamatron.tui.screens.shared.shared import scene_name
from llamatron.tui.screens.arrange.chains_field import chains_field
from llamatron.tui.screens.generators.shape_fields import shape_section
from llamatron.tui import themes
from llamatron.tui import keybindings


class ScenePage(FieldPage):
    """A scene's settings, and how long it lasts."""

    THEME = themes.FROM_ARRANGE

    KEYS = keybindings.ScenePage

    HELP = help_text.HELP_SCENE_PAGE

    def __init__(self, *, holder, index):
        super().__init__(holder)
        self.index = index
        # Scenes go by their place, so the name tells an undo that took this scene away from one that only moved it.
        self.shown_name = self.scene().get_name()

    def still_exists(self):
        return self.index < len(self.document().song().get_scenes()) and self.scene().get_name() == self.shown_name

    def follow_renames(self, renames):
        # Scenes are renamed by their place, and a name can be taken away as well as changed.
        renamed_scenes = renames.get(Section.SCENES, {})
        if self.index in renamed_scenes:
            self.shown_name = renamed_scenes[self.index]

    def crumb_trail(self):
        return (labels.Crumb.ARRANGE, labels.MSG_SCENE_CRUMB.format(name=scene_name(scene=self.scene(), index=self.index)))

    def caption(self):
        return labels.MSG_EDITING_CAPTION.format(what=labels.MSG_SCENE_CAPTION_WORD.upper(), name=scene_name(scene=self.scene(), index=self.index))

    def duration(self):
        return self.document().lengths().scene_seconds(self.index)

    def scene(self):
        return self.document().song().get_scenes()[self.index]

    def rename(self):
        def named(text):
            text = text.strip()
            if text:
                self.document().set_scene_name(index=self.index, name=text)
                self.shown_name = text
                self.crumbs = (labels.Crumb.ARRANGE, labels.MSG_SCENE_CRUMB.format(name=text))
        self.ask(dialog=PromptDialog(title=messages.MSG_SCENE_NAME_PROMPT, value=self.scene().get_name() or NOTHING, max_length=limits.MAX_NAME_LENGTH), then=named)

    def pick_scale(self):
        scales = sorted_names(self.document().song().get_scale_names())
        options = [labels.MSG_SONG_OPTION, *scales]
        current = self.scene().get_scale_name()

        def chosen(place):
            self.document().set_scene_scale(index=self.index, name=None if place == 0 else scales[place - 1])
        self.ask(dialog=ChoiceDialog(title=messages.MSG_SCENE_SCALE_TITLE, options=options, current=options.index(current) if current in options else 0), then=chosen)

    def section_field(self):
        """Return the Section field: the kind of section the scene is, chosen from the kinds a scene may be, or none."""
        section = self.scene().get_section()
        choices = [marks.MSG_NONE_SHOWN, *SECTION_KINDS]
        return ChoiceField(page=self, label=labels.MSG_SCENE_SECTION_LABEL, choices=choices, current=section or marks.MSG_NONE_SHOWN,
                           set=lambda choice: self.document().set_scene_section(index=self.index, section=None if choice == marks.MSG_NONE_SHOWN else choice))

    def groove_field(self):
        """Return the Groove field: the song's by default, off to play straight, or one by name."""
        song_groove = self.document().song().get_groove_name()
        return groove_choice_field(
            page=self, title=messages.MSG_SCENE_GROOVE_TITLE, choice=self.scene().get_groove_choice(),
            inherited_option=labels.MSG_SONG_OPTION, inherited_shown=marks.MSG_SONG_GROOVE_SHOWN.format(groove=song_groove),
            choose=lambda choice: self.document().set_scene_groove(index=self.index, choice=choice), clear_what=legends.MSG_USE_SONG_GROOVE_WHAT,
        )

    def clear_scale(self):
        self.document().set_scene_scale(index=self.index, name=None)

    def tempo(self):
        """Return the tempo the scene sets, or starts its ramp from, or None if it uses the song's."""
        scene = self.scene()
        return scene.get_tempo_start() if scene.get_tempo_setting() is None else scene.get_tempo_setting()

    def set_tempo(self, value):
        self.document().set_scene_tempo(index=self.index, tempo=value)

    def clear_tempo(self):
        self.document().clear_scene_tempo(self.index)

    def set_ramp(self, value):
        self.document().set_scene_tempo_ramp(index=self.index, end=value)

    def clear_ramp(self):
        self.document().clear_scene_tempo_ramp(self.index)

    def scale_text(self):
        scene_scale = self.scene().get_scale_name()
        if scene_scale is not None:
            return scene_scale
        return marks.MSG_SONG_SCALE_SHOWN.format(scale=self.document().song().get_scale_name() or messages.MSG_NO_SCALE)

    def tempo_text(self):
        tempo = self.tempo()
        if tempo is not None:
            return marks.MSG_TEMPO_SHOWN.format(tempo=tempo)
        return marks.MSG_SONG_TEMPO_SHOWN.format(tempo=tempo_text(self.document().song().get_tempo()))

    def fields(self):
        scene = self.scene()
        song_tempo = plain_number(self.document().song().get_tempo())
        tempo = self.tempo()
        end = scene.get_tempo_end()
        repeat = scene.get_repeat()
        return [
            NameField(value=lambda: scene.get_name() or NOTHING, rename=self.rename),
            self.section_field(),
            Field(label=labels.MSG_SCALE_LABEL, value=self.scale_text, adjust=None, enter=self.pick_scale, enter_what=legends.What.CHOOSE, clear=self.clear_scale, clear_what=legends.MSG_USE_SONG_SCALE_WHAT),
            self.groove_field(),
            NumberField(
                page=self, label=labels.MSG_TEMPO_LABEL, number=tempo, start=song_tempo, shown=self.tempo_text(), lowest=limits.MIN_TEMPO, highest=limits.MAX_TEMPO,
                set=self.set_tempo, clear=self.clear_tempo, clear_what=legends.MSG_USE_SONG_TEMPO_WHAT,
            ),
            NumberField(
                page=self, label=labels.MSG_TEMPO_RAMP_LABEL, number=end, start=tempo or song_tempo, shown=marks.MSG_RAMP_OFF_SHOWN if end is None else marks.MSG_TEMPO_SHOWN.format(tempo=end),
                lowest=limits.MIN_TEMPO, highest=limits.MAX_TEMPO, set=self.set_ramp, clear=self.clear_ramp, clear_what=legends.MSG_NO_RAMP_WHAT,
            ),
            NumberField(
                page=self, label=labels.MSG_REPEAT_LABEL, number=repeat, lowest=limits.MIN_REPEAT, highest=limits.MAX_SCENE_REPEAT,
                set=lambda number: self.document().set_scene_repeat(index=self.index, repeat=number),
            ),
            *[self.reset_field(name) for name in REGISTER_NAMES],
            # Real-time playback alone reads it, so it comes last, after everything the export reads.
            Toggle(label=labels.MSG_LAUNCH_TOGETHER_LABEL, on=scene.launches_together(), set=lambda on: self.document().set_scene_launch_together(index=self.index, value=on)),
            chains_field(page=self, names=lambda: self.scene().get_chain_names(), store=lambda names: self.document().set_scene_chains(index=self.index, names=names)),
            *[field for shape in SHAPES for field in self.shape_section(shape)],
        ]

    def shape_section(self, shape):
        """Return a shape's section: how busy, loud or long every clip of the scene plays over it."""
        scene = self.scene()
        return shape_section(
            page=self, shape=shape, value=lambda part: scene.get_setting(shape_setting(shape=shape, part=part)),
            store=lambda part, value: self.document().set_scene_shape_setting(index=self.index, name=shape_setting(shape=shape, part=part), value=value),
        )

    def reset_field(self, register):
        """Return the field that makes the scene reset a register as it starts."""
        on = self.document().resets(index=self.index, register=register)
        return Toggle(label=labels.MSG_RESET_LABEL.format(name=register), on=on, set=lambda on: self.document().set_reset(index=self.index, register=register, on=on))

    def notes(self, width):
        document = self.document()
        lines = [Text(messages.MSG_SCENE_LENGTH_NOTE.format(length=clock(document.lengths().scene_seconds(self.index))), style=Style.DIM)]
        problem = document.lengths().scene_problem(self.index)
        if problem:
            lines.append(Text(messages.MSG_PROBLEM_NOTE.format(problem=problem)[:width]))
        return lines
