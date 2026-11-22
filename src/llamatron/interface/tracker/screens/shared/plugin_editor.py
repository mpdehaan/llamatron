# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The page of a generator whose plugin describes its view (model/schema/generator_views.py): its Name, then each of the view's
settings, drawn from the description alone, so that the plugin's page needs no code outside its folder."""

import functools

from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.shared.field import ChoiceField, Field, NameField, NumberField, Toggle
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.generator_editor import GeneratorEditor
from llamatron.interface.tracker.screens.shared.guitar_bar_editor import guitar_bar_field
from llamatron.interface.tracker.screens.shared.octave_field import octave_field
from llamatron.interface.tracker.screens.shared.progression_field import progression_field
from llamatron.interface.tracker.screens.shared.restart_field import restart_field
from llamatron.interface.tracker.screens.shared.shape_fields import shape_section
from llamatron.interface.tracker.screens.shared.step_row_editor import StepRowEditor
from llamatron.interface.tracker.screens.shared.time_field import time_field
from llamatron.interface.tracker.text import sorted_names
from llamatron.model.schema import generator_plugins
from llamatron.model.schema.file_format import shape_setting
from llamatron.model.schema.generator_views import ChoiceView, GuitarBarView, NumberView, OctaveView, ProgressionView, RestartView, SectionView, ShapeView, StepsView, TimeView, ToggleView, TrackView
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
        mode = None
        if self._view.mode is not None:
            fields.append(self._choice_field(self._view.mode))
            mode = self.chosen(self._view.mode)
        for column in self._view.columns:
            if column.modes and mode not in column.modes:
                continue
            for setting in column.settings:
                fields += self._fields_of(setting)
        return fields

    def chosen(self, setting):
        """Return the value a choice holds, the value it takes when the file leaves it out where it is not written."""
        current = self.settings().get_written(setting.setting)
        if current is None:
            return setting.default
        return current

    def is_toggled(self, setting):
        """Return whether a toggle is on: as written, else as it is when left out."""
        written = self.settings().get_written(setting.setting)
        if written is None:
            return self.toggle_default(setting)
        return written

    def toggle_default(self, setting):
        """Return whether a toggle is on when the file leaves it out, which may depend on the generator's mode."""
        if setting.by_mode is None:
            return setting.default
        return setting.by_mode.get(self.chosen(self._view.mode), setting.default)

    def store_toggle(self, on, *, setting):
        """Keep a toggle, left out of the file where it is what the toggle is when left out."""
        value = on
        if on == self.toggle_default(setting):
            value = None
        self.store(setting=setting.setting, value=value)

    def store_octave(self, octave, *, setting):
        """Keep an end of a range of octaves, left out of the file where it is the end taken when left out."""
        if octave == setting.default:
            octave = None
        self.store(setting=setting.setting, value=octave)

    def octave_of(self, setting):
        """Return an end of a range of octaves, its default where the file leaves it out."""
        written = self.settings().get_written(setting.setting)
        if written is None:
            return setting.default
        return written

    def lowest_of(self, setting):
        """Return the lowest a number may be, which another setting may raise."""
        return self.settings().limits_of(setting.setting)[0]

    def highest_of(self, setting):
        """Return the highest a number may be, which another setting may lower."""
        return self.settings().limits_of(setting.setting)[1]

    def tracks(self, setting):
        """Return the tracks that can be named: the current song's, sorted, and the one named among them even when the song has no
        such track, so that it is seen and kept."""
        names = set(self.document().song().get_track_names())
        written = self.settings().get_written(setting.setting)
        if written is not None:
            names.add(written)
        return sorted_names(names)

    def store_track(self, choice, *, setting):
        """Keep the track a setting names, None or (none) naming none."""
        if choice == marks.MSG_NONE_SHOWN:
            choice = None
        self.store(setting=setting.setting, value=choice)

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
        if kind is ToggleView:
            return [self._toggle(setting)]
        if kind is OctaveView:
            return [self._octave_field(setting)]
        if kind is TrackView:
            return [self._track_field(setting)]
        if kind is ProgressionView:
            return [progression_field(page=self, label=setting.label)]
        if kind is GuitarBarView:
            return [guitar_bar_field(page=self, label=setting.label)]
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
        if number is not None:
            shown = _number_shown(number=number, setting=setting)
        return NumberField(
            page=self, label=setting.label, number=number, start=start, shown=shown, lowest=described.get_lowest(),
            highest=described.get_highest(), set=functools.partial(self.store_number, setting=setting),
            clear=functools.partial(self.store, setting=setting.setting, value=None),
        )

    def _time_field(self, setting):
        """Return the field that chooses a length of time, the value taken when left out first: the pattern's step size unless the
        view says otherwise."""
        first = setting.first
        if first is None:
            first = marks.MSG_PATTERN_STEP_SHOWN
        return time_field(
            page=self, label=setting.label, written=self.settings().get_written(setting.setting), first=first,
            store=functools.partial(self.store_time, setting=setting.setting),
        )

    def _toggle(self, setting):
        """Return the field that turns a setting on and off."""
        return Toggle(label=setting.label, on=self.is_toggled(setting), set=functools.partial(self.store_toggle, setting=setting))

    def _octave_field(self, setting):
        """Return the field for one end of a range of octaves, kept from crossing the other end."""
        return octave_field(
            page=self, label=setting.label, current=functools.partial(self.octave_of, setting), lowest=functools.partial(self.lowest_of, setting),
            highest=functools.partial(self.highest_of, setting), default=setting.default, set_octave=functools.partial(self.store_octave, setting=setting),
        )

    def _track_field(self, setting):
        """Return the field that chooses a track of the current song, (none) first."""
        named = self.settings().get_written(setting.setting) or marks.MSG_NONE_SHOWN
        return ChoiceField(
            page=self, label=setting.label, choices=[marks.MSG_NONE_SHOWN, *self.tracks(setting)], current=named,
            set=functools.partial(self.store_track, setting=setting), clear=functools.partial(self.store_track, None, setting=setting),
            clear_what=legends.MSG_NO_TRACK_WHAT,
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


def _number_shown(*, number, setting):
    """Return how a number of a view shows: the word for 0 where it has one, else its template filled, or None for the number alone."""
    if number == 0 and setting.zero_shown is not None:
        return setting.zero_shown
    if setting.shown is None:
        return None
    return setting.shown.format(number=number)
