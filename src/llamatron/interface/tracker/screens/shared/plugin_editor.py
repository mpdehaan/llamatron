# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The page of a generator whose plugin describes its view (model/schema/generator_views.py): its Name, then each of the view's
settings, drawn from the description alone, so that the plugin's page needs no code outside its folder."""

import functools

from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.shared.field import ChoiceField, Field, NameField, NumberField
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.generator_editor import GeneratorEditor
from llamatron.interface.tracker.screens.shared.restart_field import restart_field
from llamatron.interface.tracker.screens.shared.shape_fields import shape_section
from llamatron.interface.tracker.screens.shared.step_row_editor import StepRowEditor
from llamatron.interface.tracker.screens.shared.time_field import time_field
from llamatron.model.schema import generator_plugins
from llamatron.model.schema.file_format import shape_setting
from llamatron.model.schema.generator_views import ChoiceView, NumberView, RestartView, SectionView, ShapeView, StepsView, TimeView
from llamatron.user_strings import help as help_text, labels, legends, marks, messages


def has_view(section):
    """Return whether the generator plugin of a section describes its view, so that this page edits its generators."""
    plugin = generator_plugins.plugins_by_section()[section]
    return plugin.view is not None


def plugin_editor_of(section):
    """Return what opens the page of a generator of a section: this page, made for the section's plugin."""
    return functools.partial(PluginEditor, section=section)


class PluginEditor(GeneratorEditor, FieldPage):
    """The page that edits a generator of any plugin that describes its view: its Name, then the view's settings, column by column."""

    KEYS = keybindings.PluginEditor
    # The help every such page shares, which each page replaces with its plugin's own.
    HELP = help_text.HELP_PLUGIN_EDITOR
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)

    def __init__(self, *, holder, name, section):
        # The section names the plugin before the page opens, since opening asks for the page's crumbs and caption.
        self.SECTION = section
        plugin = generator_plugins.plugins_by_section()[section]
        self.HELP = plugin.view.help
        self.RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=plugin.strings.MSG_LABEL)
        self._view = plugin.view
        super().__init__(holder=holder, name=name)

    def fields(self):
        fields = [NameField(value=self.shown_name, rename=self.rename)]
        for column in self._view.columns:
            for setting in column.settings:
                fields += self._fields_of(setting)
        return fields

    def store_number(self, number, *, setting):
        """Keep a number of the generator, left out of the file where it is the number taken when left out, or cleared."""
        if number == setting.default or (setting.default is None and not number):
            number = None
        self.store(setting=setting.setting, value=number)

    def store_time(self, value, *, setting):
        """Keep a step length, None leaving the pattern's step size."""
        self.store(setting=setting, value=value)

    def open_steps(self, steps):
        """Open the page that edits one of the generator's rows of steps."""
        self.show_page(StepRowEditor(holder=self.holder, name=self.item, section=self.SECTION, steps=steps))

    def steps_shown(self, steps):
        """Return a row of steps on one line, the dot for a step that's on and a point for one that's off, like ● . ● ."""
        values = self.settings().step_row(steps.row).get_steps()
        return ' '.join(marks.MSG_TOGGLE_ON if value else marks.MSG_STEP_OFF for value in values)

    def is_section_set(self, section):
        """Return whether anything inside a section holds a value, so that its closed heading says (set)."""
        settings = self.settings()
        for name in _settings_named(section.settings):
            if settings.get_written(name) is not None:
                return True
        return False

    def shape_part(self, part, *, shape):
        """Return one part of a shape as the file holds it, or None where it is blank."""
        return self.settings().get_written(shape_setting(shape=shape, part=part))

    def shown_name(self):
        return self.item

    def store_unless_default(self, value, *, setting):
        """Keep a setting's value, left out of the file where it is the value the setting takes when left out."""
        if value == setting.default:
            value = None
        self.store(setting=setting.setting, value=value)

    def _fields_of(self, setting):
        """Return the fields that edit one of the view's settings, by the kind of setting it is."""
        kind = type(setting)
        if kind is ChoiceView:
            return [self._choice_field(setting)]
        if kind is NumberView:
            return [self._number_field(setting)]
        if kind is ShapeView:
            return self._shape_fields(setting)
        if kind is RestartView:
            return [restart_field(self)]
        if kind is TimeView:
            return [self._time_field(setting)]
        if kind is StepsView:
            return [self._steps_field(setting)]
        if kind is SectionView:
            return self._section_fields(setting)
        raise TypeError(setting)

    def _number_field(self, setting):
        """Return the field that steps a whole number between its setting's limits, its default where left out, else blank."""
        number = self.settings().get_written(setting.setting)
        described = self.settings().SETTINGS[setting.setting]
        shown = None
        start = described.get_lowest()
        if number is None and setting.default is None:
            shown = marks.MSG_NONE_SHOWN
        elif number is None:
            number = setting.default
            start = setting.default
        return NumberField(
            page=self, label=setting.label, number=number, start=start, shown=shown, lowest=described.get_lowest(),
            highest=described.get_highest(), set=functools.partial(self.store_number, setting=setting),
            clear=functools.partial(self.store, setting=setting.setting, value=None),
        )

    def _time_field(self, setting):
        """Return the field that chooses how long each step of a row is, the pattern's step size first."""
        return time_field(
            page=self, label=setting.label, written=self.settings().get_written(setting.setting), first=marks.MSG_PATTERN_STEP_SHOWN,
            store=functools.partial(self.store_time, setting=setting.setting),
        )

    def _steps_field(self, setting):
        """Return the field that shows a row of steps on one line, ENTER opening it on its own page."""
        return Field(
            label=setting.label, value=functools.partial(self.steps_shown, setting), adjust=None,
            enter=functools.partial(self.open_steps, setting), enter_what=legends.What.EDIT,
        )

    def _section_fields(self, section):
        """Return a section's heading, closed until opened, then the fields of its settings."""
        fields = [self.heading(label=section.heading, is_set=functools.partial(self.is_section_set, section))]
        for setting in section.settings:
            fields += self._fields_of(setting)
        return fields

    def _shape_fields(self, setting):
        """Return a shape's section: its heading, then its start, end, over and then."""
        return shape_section(
            page=self, shape=setting.shape, value=functools.partial(self.shape_part, shape=setting.shape),
            store=lambda part, value: self.store(setting=shape_setting(shape=setting.shape, part=part), value=value),
        )

    def _choice_field(self, setting):
        """Return the field that chooses a setting's value from its list, shown by its name where the view gives one."""
        current = self.settings().get_written(setting.setting)
        if current is None:
            current = setting.default
        names = None
        shown = None
        if setting.names is not None:
            names = [setting.names[choice] for choice in setting.choices]
            shown = setting.names[current]
        return ChoiceField(
            page=self, label=setting.label, choices=list(setting.choices), names=names, current=current, shown=shown,
            set=functools.partial(self.store_unless_default, setting=setting),
        )


def _settings_named(views):
    """Return the file names of the settings some of a view's settings edit, those that name one."""
    names = []
    for view in views:
        if hasattr(view, 'setting'):
            names.append(view.setting)
    return names
