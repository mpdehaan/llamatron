# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""One scene's page as a presenter: its name, then its tabs, Settings (how it plays), Velocity, Tempo Ramps, Shapes, Reset Draws,
More Generators and Bypass When. A scene holds no built-in generator."""

import functools

from llamatron.interface.forms import percentages
from llamatron.interface.forms.nodes import ChoiceField, Field, NameField, NumberField, Toggle
from llamatron.interface.forms.percentages import percent_shown
from llamatron.interface.forms.tab_box import columns_of_sections, Tab, TabBox, TabColumn
from llamatron.interface.forms.text import sorted_names, tempo_text
from llamatron.interface.pages import statements
from llamatron.interface.pages.arrange_tabs import fields_tab, reset_draws_tab
from llamatron.interface.pages.generators_field import generators_field
from llamatron.interface.pages.groove_choice import groove_choice_field
from llamatron.interface.pages.shape_fields import shape_section
from llamatron.interface.pages.statements import statement_section
from llamatron.interface.pages.velocity_fields import velocity_field, velocity_ramp_sections, VelocityValues
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import RampPart, shape_setting
from llamatron.user_strings import labels, legends, marks, messages

# What a scene without a name shows in its Name field.
NO_NAME = ''


class ScenePresenter:
    """What a scene's page shows and does, for one scene of the current song by its place. Its page does what only the tracker
    can: rename() and pick() among choices, heading() for a section, and the page actions the Generators field asks of it."""

    __slots__ = ('_page', '_document', '_index')

    def __init__(self, *, page, document, index):
        self._page = page
        self._document = document
        self._index = index

    def scene(self):
        song = self._document.song()
        return song.get_scenes()[self._index]

    def form(self):
        """Return the page's form: the scene's name, then its tabs."""
        return [NameField(value=self._name_shown, rename=self._page.rename), TabBox(tabs=self.tabs())]

    def pick_scale(self):
        song = self._document.song()
        setlist = song.get_setlist()
        scales = sorted_names(setlist.get_scale_names())
        scene = self.scene()
        self._page.pick(title=messages.MSG_SCENE_SCALE_TITLE, values=[None, *scales], shown=[labels.MSG_SONG_OPTION, *scales],
                  current=scene.get_scale_name(), then=self._set_scale)

    def section_field(self):
        """Return the Section field: the kind of section the scene is, chosen from the kinds a scene may be, or none."""
        section = self.scene().get_section()
        choices = [marks.MSG_NONE_SHOWN, *file_format.SECTION_KINDS]
        return ChoiceField(page=self._page, label=labels.MSG_SCENE_SECTION_LABEL, choices=choices, current=section or marks.MSG_NONE_SHOWN,
                           set=self._set_section)

    def groove_field(self):
        """Return the Groove field: the song's by default, off to play straight, or one by name."""
        song = self._document.song()
        inherited = marks.MSG_SONG_GROOVE_SHOWN.format(groove=song.get_groove_name())
        return groove_choice_field(
            page=self._page, title=messages.MSG_SCENE_GROOVE_TITLE, choice=self.scene().get_groove_choice(), inherited_option=labels.MSG_SONG_OPTION,
            inherited_shown=inherited, choose=self._set_groove, clear_what=legends.MSG_FROM_SONG_WHAT,
        )

    def clear_scale(self):
        self._set_scale(None)

    def tempo(self):
        """Return the percentage of the song's tempo the scene plays at, as an exact number, or None if it plays at the song's."""
        return self.scene().tempo_percent()

    def played_tempo(self):
        """Return the tempo the scene plays at, its percentage of the song's."""
        song = self._document.song()
        return self.scene().tempo_in(song.get_tempo())

    def set_tempo(self, value):
        self._change(self.scene().set_tempo, value)

    def clear_tempo(self):
        self._change(self.scene().clear_tempo)

    def tempo_ramp_section(self, way):
        """Return a tempo ramp's section: the percentage of the scene's tempo it starts from and the one it reaches, each 100%
        until given, and the bars it takes, with no ramp until they are given."""
        scene = self.scene()
        is_set = functools.partial(_has_ramp, scene=scene, way=way)
        fields = [self._page.heading(label=labels.MSG_RAMP_HEADINGS[way], is_set=lambda: is_set())]
        for part in (RampPart.START, RampPart.END):
            fields.append(self._ramp_tempo_field(way=way, part=part))
        over = scene.get_tempo_ramp_setting(way=way, part=RampPart.OVER)
        store = functools.partial(self._set_ramp, way=way, part=RampPart.OVER)
        fields.append(NumberField(
            page=self._page, label=labels.MSG_TEMPO_RAMP_LABELS[(way, RampPart.OVER)], shown_label=labels.MSG_RAMP_PART_LABELS[RampPart.OVER], number=over, start=limits.MIN_RAMP_BARS, shown=_ramp_bars_shown(over),
            lowest=limits.MIN_RAMP_BARS, highest=limits.MAX_RAMP_BARS, set=lambda number: store(value=number), clear=functools.partial(store, value=None),
            clear_what=marks.MSG_NONE_SHOWN,
        ))
        return fields

    def scale_text(self):
        scene_scale = self.scene().get_scale_name()
        if scene_scale is not None:
            return scene_scale
        song = self._document.song()
        return marks.MSG_SONG_SCALE_SHOWN.format(scale=song.get_scale_name() or messages.MSG_NO_SCALE)

    def tempo_text(self):
        """Return the scene's Tempo as its field shows it: its percentage of the song's tempo with the tempo it makes, or the song's."""
        percent = self.tempo()
        if percent is None:
            song = self._document.song()
            return marks.MSG_SONG_TEMPO_SHOWN.format(tempo=tempo_text(song.get_tempo()))
        return marks.MSG_TEMPO_PERCENT_SHOWN.format(percent=percent_shown(percent), tempo=tempo_text(self.played_tempo()))

    def tabs(self):
        """Return the scene's tabs: Settings, then the tabs that are not generators, Velocity, Tempo Ramps, Shapes and Reset Draws,
        then its list of generators and the statements that bypass the generators of its clips. A scene holds no built-in
        generator."""
        values = self.velocity_values()
        shapes = []
        for shape in file_format.PLACED_SHAPES:
            shapes += self.shape_section(shape)
        tempo_ramps = []
        for way in file_format.RAMP_WAYS:
            tempo_ramps += self.tempo_ramp_section(way)
        bypass = self.bypass_section()
        return [
            self._basics_tab(),
            Tab(label=labels.MSG_VELOCITY_TAB, top=[velocity_field(page=self._page, values=values)], columns=columns_of_sections(velocity_ramp_sections(page=self._page, values=values))),
            Tab(label=labels.MSG_TEMPO_RAMPS_TAB, columns=columns_of_sections(tempo_ramps)),
            Tab(label=labels.MSG_SHAPES_TAB, columns=columns_of_sections(shapes)),
            reset_draws_tab(page=self._page, holder=self.scene()),
            fields_tab(label=labels.MSG_USER_TAB, fields=[generators_field(page=self._page, names=self._chain_names, store=self._set_chain_names)]),
            fields_tab(label=labels.MSG_BYPASS_WHEN_TAB, fields=bypass),
        ]

    def velocity_values(self):
        """Return what the velocity fields read the scene's own velocity settings with, what gives a blank one from above,
        which nothing does for a scene, and what keeps one."""
        scene = self.scene()
        return VelocityValues(own=scene.get_written, above=lambda name: None, store=lambda name, value: self._set_written(name=name, value=value))

    def bypass_section(self):
        """Return the statements that bypass the generators of the scene's clips."""
        scene = self.scene()
        return statement_section(
            page=self._page, label=labels.MSG_BYPASS_WHEN_LABEL, table=statements.FIRST_TABLE, statements=scene.get_bypass_when,
            store=lambda place, statement: self._change(self.scene().set_bypass_statement, place=place, statement=statement),
        )

    def shape_section(self, shape):
        """Return a shape's section: how busy, loud or long every clip of the scene plays over it."""
        scene = self.scene()

        def value(part):
            return scene.get_written(shape_setting(shape=shape, part=part))

        def store(part, value):
            self._set_written(name=shape_setting(shape=shape, part=part), value=value)
        return shape_section(page=self._page, shape=shape, value=value, store=store)

    def _set_scale(self, name):
        """Give the scene a scale, or the song's with None."""
        song = self._document.song()
        self._change(self.scene().set_scale_name, name=name, song=song)

    def _set_section(self, choice):
        """Make the scene a kind of section, or none."""
        if choice == marks.MSG_NONE_SHOWN:
            choice = None
        self._change(self.scene().set_section, choice)

    def _set_groove(self, choice):
        song = self._document.song()
        self._change(self.scene().set_groove_choice, choice=choice, song=song)

    def _ramp_tempo_field(self, *, way, part):
        """Return the field of the percentage of the scene's tempo a ramp starts from or reaches, shown with the tempo it makes,
        and the scene's tempo until given."""
        scene = self.scene()
        number = scene.ramp_end_percent(way=way, part=part)
        if number is None:
            shown = self._blank_tempo_shown()
        else:
            song = self._document.song()
            reached = scene.ramp_end_tempo(way=way, part=part, song_tempo=song.get_tempo())
            shown = marks.MSG_TEMPO_PERCENT_SHOWN.format(percent=percent_shown(number), tempo=tempo_text(reached))
        store = functools.partial(self._set_ramp, way=way, part=part)
        return NumberField(
            page=self._page, label=labels.MSG_TEMPO_RAMP_LABELS[(way, part)], shown_label=labels.MSG_RAMP_PART_LABELS[part], number=whole_or_none(number), start=percentages.UNCHANGED, shown=shown, lowest=limits.MIN_TEMPO_PERCENT,
            highest=limits.MAX_TEMPO_PERCENT, set=lambda value: store(value=value), clear=functools.partial(store, value=None), clear_what=self._blank_tempo_shown(),
        )

    def _set_ramp(self, *, way, part, value):
        self._change(self.scene().set_tempo_ramp_setting, way=way, part=part, value=value)

    def _blank_tempo_shown(self):
        """Return what a blank end of a tempo ramp shows: 100%, the tempo the scene plays at, with that tempo."""
        return marks.MSG_TEMPO_PERCENT_SHOWN.format(percent=percent_shown(percentages.UNCHANGED), tempo=tempo_text(self.played_tempo()))

    def _basics_tab(self):
        """Return the Settings tab: how the scene plays."""
        scene = self.scene()
        playing = [
            self.section_field(),
            NumberField(page=self._page, label=labels.MSG_REPEAT_LABEL, number=scene.get_repeat(), lowest=limits.MIN_REPEAT, highest=limits.MAX_SCENE_REPEAT, set=self._set_repeat),
            Toggle(label=labels.MSG_LAUNCH_TOGETHER_LABEL, on=scene.launches_together(), set=self._set_launch_together),
            Field(label=labels.MSG_SCALE_LABEL, value=self.scale_text, adjust=None, enter=self.pick_scale, enter_what=legends.What.CHOOSE,
                  clear=self.clear_scale, clear_what=legends.MSG_FROM_SONG_WHAT),
            self.groove_field(),
            NumberField(
                page=self._page, label=labels.MSG_TEMPO_LABEL, number=whole_or_none(self.tempo()), start=percentages.UNCHANGED, shown=self.tempo_text(),
                lowest=limits.MIN_TEMPO_PERCENT, highest=limits.MAX_TEMPO_PERCENT, set=self.set_tempo, clear=self.clear_tempo, clear_what=legends.MSG_FROM_SONG_WHAT,
            ),
        ]
        return Tab(label=labels.MSG_SETTINGS_TAB, columns=[TabColumn(heading=labels.MSG_PLAYING_HEADING, fields=playing)])

    def _set_repeat(self, number):
        self._change(self.scene().set_repeat, number)

    def _set_launch_together(self, on):
        self._change(self.scene().set_launch_together, on)

    def _chain_names(self):
        return self.scene().get_chain_names()

    def _set_chain_names(self, names):
        song = self._document.song()
        self._change(self.scene().set_chain_names, names=names, song=song)

    def _set_written(self, *, name, value):
        self._change(self.scene().set_written, name=name, value=value)

    def _change(self, setter, *arguments, **named):
        """Change the scene through one of its setters, as one edit of the set."""
        self._document.change_set(setter, *arguments, **named)

    def _name_shown(self):
        return self.scene().get_name() or NO_NAME


def _has_ramp(*, scene, way):
    """Return whether a scene ramps its tempo one way."""
    return scene.ramps_tempo(way)


def whole_or_none(percent):
    """Return a percentage as the nearest whole number a field steps and types from, or None for none."""
    if percent is None:
        return None
    return round(percent)


def _ramp_bars_shown(over):
    """Return the bars a tempo ramp takes as its field shows them, or none."""
    if over is None:
        return marks.MSG_NONE_SHOWN
    if over == limits.MIN_RAMP_BARS:
        return marks.MSG_RAMP_ONE_BAR_SHOWN
    return marks.MSG_RAMP_BARS_SHOWN.format(bars=over)
