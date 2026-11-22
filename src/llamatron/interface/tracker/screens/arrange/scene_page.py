# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Scene page: a scene's settings, and how long it lasts."""

import functools
from rich.text import Text

from llamatron.interface.tracker import drawing, keybindings, themes
from llamatron.interface.tracker.drawing import Style
from llamatron.interface.tracker.screens.arrange.generators_field import generators_field
from llamatron.interface.tracker.screens.arrange.groove_choice import groove_choice_field
from llamatron.interface.tracker.screens.arrange.velocity_fields import velocity_field, velocity_ramp_sections
from llamatron.interface.tracker.screens.generators.shape_fields import shape_section
from llamatron.interface.tracker.screens.shared import statements
from llamatron.interface.tracker.screens.shared.field import ChoiceField, Field, NameField, NumberField, Toggle
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.shared import scene_name
from llamatron.interface.tracker.screens.shared.statements import register_fields, statement_section
from llamatron.interface.tracker.text import clock, plain_number, sorted_names, tempo_text
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import RampPart, Section, shape_setting
from llamatron.user_strings import help as help_text, labels, legends, marks, messages


def _has_ramp(*, scene, way):
    """Return whether a scene ramps its tempo one way."""
    return scene.get_tempo_ramp(way) is not None


def _ramp_bars_shown(over):
    """Return the bars a tempo ramp takes as its field shows them, or none."""
    if over is None:
        return marks.MSG_NONE_SHOWN
    if over == limits.MIN_RAMP_BARS:
        return marks.MSG_RAMP_ONE_BAR_SHOWN
    return marks.MSG_RAMP_BARS_SHOWN.format(bars=over)


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
        song = self.document().song()
        return self.index < len(song.get_scenes()) and self.scene().get_name() == self.shown_name

    def follow_renames(self, renames):
        # Scenes are renamed by their place, and a name can be taken away as well as changed.
        renamed_scenes = renames.get(Section.SCENES, {})
        if self.index in renamed_scenes:
            self.shown_name = renamed_scenes[self.index]

    def crumb_trail(self):
        name = scene_name(scene=self.scene(), index=self.index)
        return (labels.Crumb.ARRANGE, labels.MSG_SCENE_CRUMB.format(name=name))

    def caption(self):
        name = scene_name(scene=self.scene(), index=self.index)
        return labels.MSG_EDITING_CAPTION.format(what=labels.MSG_SCENE_CAPTION_WORD.upper(), name=name)

    def duration(self):
        lengths = self.document().lengths()
        return lengths.scene_seconds(self.index)

    def scene(self):
        song = self.document().song()
        return song.get_scenes()[self.index]

    def rename(self):
        scene = self.scene()
        self.ask_text(title=messages.MSG_SCENE_NAME_PROMPT, value=scene.get_name() or drawing.NOTHING, then=self._renamed, is_name=True)

    def _renamed(self, text):
        """Give the scene the name typed, unless it is blank, and follow it in the crumbs."""
        text = text.strip()
        if not text:
            return
        self._change(self.scene().set_name, text)
        self.shown_name = text
        self.crumbs = (labels.Crumb.ARRANGE, labels.MSG_SCENE_CRUMB.format(name=text))

    def pick_scale(self):
        song = self.document().song()
        setlist = song.get_setlist()
        scales = sorted_names(setlist.get_scale_names())
        scene = self.scene()
        self.pick(title=messages.MSG_SCENE_SCALE_TITLE, values=[None, *scales], shown=[labels.MSG_SONG_OPTION, *scales],
                  current=scene.get_scale_name(), then=self._set_scale)

    def _set_scale(self, name):
        """Give the scene a scale, or the song's with None."""
        song = self.document().song()
        self._change(self.scene().set_scale_name, name=name, song=song)

    def section_field(self):
        """Return the Section field: the kind of section the scene is, chosen from the kinds a scene may be, or none."""
        section = self.scene().get_section()
        choices = [marks.MSG_NONE_SHOWN, *file_format.SECTION_KINDS]
        return ChoiceField(page=self, label=labels.MSG_SCENE_SECTION_LABEL, choices=choices, current=section or marks.MSG_NONE_SHOWN,
                           set=self._set_section)

    def _set_section(self, choice):
        """Make the scene a kind of section, or none."""
        if choice == marks.MSG_NONE_SHOWN:
            choice = None
        self._change(self.scene().set_section, choice)

    def groove_field(self):
        """Return the Groove field: the song's by default, off to play straight, or one by name."""
        song = self.document().song()
        inherited = marks.MSG_SONG_GROOVE_SHOWN.format(groove=song.get_groove_name())
        return groove_choice_field(
            page=self, title=messages.MSG_SCENE_GROOVE_TITLE, choice=self.scene().get_groove_choice(), inherited_option=labels.MSG_SONG_OPTION,
            inherited_shown=inherited, choose=self._set_groove, clear_what=legends.MSG_USE_SONG_GROOVE_WHAT,
        )

    def _set_groove(self, choice):
        song = self.document().song()
        self._change(self.scene().set_groove_choice, choice=choice, song=song)

    def clear_scale(self):
        self._set_scale(None)

    def tempo(self):
        """Return the tempo the scene sets, or None if it uses the song's."""
        return self.scene().get_tempo_setting()

    def set_tempo(self, value):
        self._change(self.scene().set_tempo, value)

    def clear_tempo(self):
        self._change(self.scene().clear_tempo)

    def tempo_ramp_section(self, way):
        """Return a tempo ramp's section, closed until opened: the tempo it starts from, the tempo it reaches, each the scene's
        tempo until given, and the bars it takes, with no ramp until they are given."""
        scene = self.scene()
        is_set = functools.partial(_has_ramp, scene=scene, way=way)
        fields = [self.heading(label=labels.MSG_TEMPO_RAMP_SECTIONS[way], is_set=lambda: is_set())]
        for part in (RampPart.START, RampPart.END):
            fields.append(self._ramp_tempo_field(way=way, part=part))
        over = scene.get_tempo_ramp_setting(way=way, part=RampPart.OVER)
        store = functools.partial(self._set_ramp, way=way, part=RampPart.OVER)
        fields.append(NumberField(
            page=self, label=labels.MSG_TEMPO_RAMP_LABELS[(way, RampPart.OVER)], number=over, start=limits.MIN_RAMP_BARS, shown=_ramp_bars_shown(over),
            lowest=limits.MIN_RAMP_BARS, highest=limits.MAX_RAMP_BARS, set=lambda number: store(value=number), clear=functools.partial(store, value=None),
            clear_what=legends.MSG_RAMP_BLANK_WHAT,
        ))
        return fields

    def _ramp_tempo_field(self, *, way, part):
        """Return the field of the tempo a ramp starts from or reaches, the scene's or the song's tempo until given."""
        scene = self.scene()
        number = scene.get_tempo_ramp_setting(way=way, part=part)
        here = self.tempo()
        if here is None:
            song = self.document().song()
            base = plain_number(song.get_tempo())
            shown = marks.MSG_SONG_TEMPO_SHOWN.format(tempo=base)
        else:
            base = here
            shown = marks.MSG_SCENE_TEMPO_SHOWN.format(tempo=base)
        if number is not None:
            shown = marks.MSG_TEMPO_SHOWN.format(tempo=number)
        store = functools.partial(self._set_ramp, way=way, part=part)
        return NumberField(
            page=self, label=labels.MSG_TEMPO_RAMP_LABELS[(way, part)], number=number, start=base, shown=shown, lowest=limits.MIN_TEMPO,
            highest=limits.MAX_TEMPO, set=lambda value: store(value=value), clear=functools.partial(store, value=None), clear_what=legends.MSG_RAMP_BLANK_WHAT,
        )

    def _set_ramp(self, *, way, part, value):
        self._change(self.scene().set_tempo_ramp_setting, way=way, part=part, value=value)

    def scale_text(self):
        scene_scale = self.scene().get_scale_name()
        if scene_scale is not None:
            return scene_scale
        song = self.document().song()
        return marks.MSG_SONG_SCALE_SHOWN.format(scale=song.get_scale_name() or messages.MSG_NO_SCALE)

    def tempo_text(self):
        tempo = self.tempo()
        if tempo is not None:
            return marks.MSG_TEMPO_SHOWN.format(tempo=tempo)
        song = self.document().song()
        return marks.MSG_SONG_TEMPO_SHOWN.format(tempo=tempo_text(song.get_tempo()))

    def fields(self):
        scene = self.scene()
        song = self.document().song()
        own_velocity, velocity_above, store_velocity = self.velocity_values()
        fields = [
            NameField(value=self._name_shown, rename=self.rename),
            self.section_field(),
            Field(label=labels.MSG_SCALE_LABEL, value=self.scale_text, adjust=None, enter=self.pick_scale, enter_what=legends.What.CHOOSE,
                  clear=self.clear_scale, clear_what=legends.MSG_USE_SONG_SCALE_WHAT),
            self.groove_field(),
            NumberField(
                page=self, label=labels.MSG_TEMPO_LABEL, number=self.tempo(), start=plain_number(song.get_tempo()), shown=self.tempo_text(),
                lowest=limits.MIN_TEMPO, highest=limits.MAX_TEMPO, set=self.set_tempo, clear=self.clear_tempo, clear_what=legends.MSG_USE_SONG_TEMPO_WHAT,
            ),
            velocity_field(page=self, own=own_velocity, above=velocity_above, store=store_velocity),
            NumberField(page=self, label=labels.MSG_REPEAT_LABEL, number=scene.get_repeat(), lowest=limits.MIN_REPEAT,
                        highest=limits.MAX_SCENE_REPEAT, set=self._set_repeat),
        ]
        for name in file_format.REGISTER_NAMES:
            fields.append(self.reset_field(name))
        for name in file_format.DRAW_NAMES:
            fields.append(self.reset_draw_field(name))
        # Real-time playback alone reads it, so it comes last, after everything the export reads.
        fields.append(Toggle(label=labels.MSG_LAUNCH_TOGETHER_LABEL, on=scene.launches_together(), set=self._set_launch_together))
        fields.append(generators_field(page=self, names=self._chain_names, store=self._set_chain_names))
        for way in file_format.RAMP_WAYS:
            fields += self.tempo_ramp_section(way)
        fields += velocity_ramp_sections(page=self, own=own_velocity, above=velocity_above, store=store_velocity)
        for shape in file_format.PLACED_SHAPES:
            fields += self.shape_section(shape)
        return fields + self.register_sections()

    def _name_shown(self):
        return self.scene().get_name() or drawing.NOTHING

    def _set_repeat(self, number):
        self._change(self.scene().set_repeat, number)

    def _set_launch_together(self, on):
        self._change(self.scene().set_launch_together, on)

    def _chain_names(self):
        return self.scene().get_chain_names()

    def _set_chain_names(self, names):
        song = self.document().song()
        self._change(self.scene().set_chain_names, names=names, song=song)

    def _set_written(self, *, name, value):
        self._change(self.scene().set_written, name=name, value=value)

    def velocity_values(self):
        """Return what the velocity fields read the scene's own velocity settings with, what gives a blank one from above,
        which nothing does for a scene, and what keeps one."""
        scene = self.scene()
        return scene.get_written, lambda name: None, lambda name, value: self._set_written(name=name, value=value)

    def register_sections(self):
        """Return the scene's sections about the registers: what it sets them to as it first starts, what it adds every time it
        plays, and the statements that bypass the generators of its clips."""
        scene = self.scene()
        return [
            *register_fields(
                page=self, label=labels.MSG_SET_REGISTERS_LABEL, name_label=labels.MSG_SET_REGISTER_LABEL, values=scene.get_register_sets,
                store=lambda register, value: self._change(self.scene().set_register_set, register=register, value=value),
            ),
            *register_fields(
                page=self, label=labels.MSG_ADD_REGISTERS_LABEL, name_label=labels.MSG_ADD_REGISTER_LABEL, values=scene.get_register_adds,
                store=lambda register, value: self._change(self.scene().set_register_add, register=register, value=value),
            ),
            *statement_section(
                page=self, label=labels.MSG_BYPASS_WHEN_LABEL, table=statements.FIRST_TABLE, statements=scene.get_bypass_when,
                store=lambda place, statement: self._change(self.scene().set_bypass_statement, place=place, statement=statement),
            ),
        ]

    def shape_section(self, shape):
        """Return a shape's section: how busy, loud or long every clip of the scene plays over it."""
        scene = self.scene()

        def value(part):
            return scene.get_written(shape_setting(shape=shape, part=part))

        def store(part, value):
            self._set_written(name=shape_setting(shape=shape, part=part), value=value)
        return shape_section(page=self, shape=shape, value=value, store=store)

    def reset_draw_field(self, draw):
        """Return the field that makes the scene reset a draw as it first starts: back to its first slot, or a serial draw to a
        new round."""
        scene = self.scene()
        return Toggle(label=labels.MSG_RESET_LABEL.format(name=draw), on=draw in scene.get_reset_draw_names(),
                      set=functools.partial(self._set_reset_draw, draw=draw))

    def _set_reset_draw(self, on, *, draw):
        self._change(self.scene().set_reset_draw, draw=draw, on=on)

    def reset_field(self, register):
        """Return the field that makes the scene reset a register as it starts."""
        on = self.document().resets(index=self.index, register=register)
        return Toggle(label=labels.MSG_RESET_LABEL.format(name=register), on=on, set=functools.partial(self._set_reset, register=register))

    def _set_reset(self, on, *, register):
        self._change(self.scene().set_reset, register=register, on=on)

    def remarks(self, width):
        lengths = self.document().lengths()
        length = clock(lengths.scene_seconds(self.index))
        lines = [Text(messages.MSG_SCENE_LENGTH_NOTE.format(length=length), style=Style.DIM)]
        problem = lengths.scene_problem(self.index)
        if problem:
            lines.append(Text(messages.MSG_PROBLEM_NOTE.format(problem=problem)[:width]))
        return lines

    def _change(self, setter, *arguments, **named):
        """Change the scene through one of its setters, as one edit of the set."""
        self.document().change_set(setter, *arguments, **named)
