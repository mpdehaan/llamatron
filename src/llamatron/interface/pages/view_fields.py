# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The fields a generator's view describes (model/schema/generator_views.py), made from the description alone: Enabled, its Mode
where it has one, then the settings of each column its mode shows. A generator's own page and a built-in generator's tab on a
clip's or a track's page both draw them."""


import functools

from llamatron.interface.forms.nodes import ChoiceField, Field, gauge_shown, NumberField, Toggle
from llamatron.interface.forms.tab_box import Tab, TabColumn, without_headings
from llamatron.interface.forms.text import numbers_text, sorted_names
from llamatron.interface.pages import places
from llamatron.interface.pages.drift_values import drift_value_rows
from llamatron.interface.pages.guitar_bar_field import guitar_bar_field
from llamatron.interface.pages.octave_field import octave_field
from llamatron.interface.pages.progression_field import progression_field
from llamatron.interface.pages.restart_field import restart_field
from llamatron.interface.pages.section_table import section_table
from llamatron.interface.pages.shape_fields import shape_section
from llamatron.interface.pages.time_field import time_field
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import shape_setting
from llamatron.model.schema.generator_views import ChoiceView, DriftValuesView, GaugeView, GuitarBarView, InheritedChoiceView, NumberView, OctaveView, OffsetsView, ProgressionView, RestartView, SectionsView, SectionView, ShapeView, StepsView, TimeView, ToggleView, TrackView, WhenView
from llamatron.user_strings import labels, legends, marks

# What a register add left out of the file is, and the offsets an arpeggiator starts its editor with where it has none.
NO_ADD = 0
NO_OFFSET = 0
NEW_OFFSET_STEPS = 8

# The method that makes the fields of each kind of setting a view holds, a field or a list of them.
FIELD_MAKERS = {
    ChoiceView: '_choice_field', NumberView: '_number_field', ShapeView: '_shape_fields', RestartView: '_restart_field', TimeView: '_time_field',
    StepsView: '_steps_field', SectionView: '_section_fields', ToggleView: '_toggle', OctaveView: '_octave_field', TrackView: '_track_field',
    ProgressionView: '_progression_field', GuitarBarView: '_guitar_bar_field', OffsetsView: '_offsets_field',
    DriftValuesView: '_drift_value_rows', WhenView: '_when_fields', InheritedChoiceView: '_inherited_choice', GaugeView: '_gauge',
    SectionsView: '_section_table',
}



class ViewFields:
    """What makes the fields of a generator's view. Its user gives view(), the plugin's view, settings(), the generator's
    settings, store(setting=, value=), which keeps one of them, open_part(part, **given), which opens a page on a part of
    the generator, and the dialogs every page has, which the fields ask for."""

    __slots__ = ()

    def view(self):
        """Return the plugin's view the fields are made from."""
        raise NotImplementedError

    def view_tab(self, *, label):
        """Return the view as a tab of a tab box: Enabled and the Mode across the top, then a column of each of the view's columns
        the mode shows, each section of one standing as a column of its own under its heading, marked on or off."""
        view = self.view()
        top = [self._enabled_field()]
        mode = None
        if view.mode is not None:
            top.append(self._choice_field(view.mode))
            mode = self.chosen(view.mode)
        columns = []
        for column in view.columns:
            if not column.modes or mode in column.modes:
                columns += self._tab_columns(column)
        return Tab(label=label, top=top, columns=columns, on=self.settings().is_enabled())

    def view_fields(self):
        """Return Enabled, the Mode where the view has one, then the fields of every column the mode shows, in order."""
        view = self.view()
        fields = [self._enabled_field()]
        mode = None
        if view.mode is not None:
            fields.append(self._choice_field(view.mode))
            mode = self.chosen(view.mode)
        for column in view.columns:
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
        return setting.by_mode.get(self.chosen(self.view().mode), setting.default)

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

    def open_offsets(self, setting):
        """Open the offsets editor, giving the generator a row of offsets of nothing first where it has none."""
        if self.settings().get_written(setting.setting) is None:
            self.store(setting=setting.setting, value=[NO_OFFSET] * NEW_OFFSET_STEPS)
        self.open_part(places.OFFSETS)

    def offsets_shown(self, setting):
        """Return the offsets on one line, or (none) where the generator has none."""
        offsets = self.settings().get_written(setting.setting)
        if offsets is None:
            return marks.MSG_NONE_SHOWN
        return numbers_text(offsets)

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

    def store_inherited(self, chosen, *, setting):
        """Keep a choice that comes from above until chosen, the first choice giving it back to what is above."""
        if chosen == setting.inherited_choice:
            chosen = None
        self.store(setting=setting.setting, value=chosen)

    def store_time(self, value, *, setting):
        """Keep a step length, None leaving the pattern's step size."""
        self.store(setting=setting, value=value)

    def open_steps(self, steps):
        """Open the page that edits one of the generator's rows of steps."""
        self.open_part(places.STEP_ROW, section=self.SECTION, steps=steps)

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

    def store_unless_default(self, value, *, setting):
        """Keep a setting's value, left out of the file where it is the value the setting takes when left out."""
        if value == setting.default:
            value = None
        self.store(setting=setting.setting, value=value)

    def _tab_columns(self, column):
        """Return a view's column as the columns of a tab: its settings under its heading, each section among them a column of
        its own after them, under the section's heading."""
        own = []
        sections = []
        for setting in column.settings:
            if type(setting) is SectionView:
                fields = []
                for inside in setting.settings:
                    fields += self._fields_of(inside)
                sections.append(TabColumn(heading=setting.heading, fields=without_headings(fields)))
            else:
                own += without_headings(self._fields_of(setting))
        if own:
            return [TabColumn(heading=column.heading, fields=own, under=column.under), *sections]
        return sections

    def _enabled_field(self):
        """Return the generator's switch, written only where it differs from how a generator of its kind starts."""
        settings = self.settings()
        return Toggle(label=labels.MSG_ENABLED_LABEL, on=settings.is_enabled(), set=self._store_enabled)

    def _store_enabled(self, on):
        """Keep the generator's switch, left out of the file where it is as a generator of its kind starts: on for one of the
        set's list, off for a built-in one."""
        value = on
        if on != self.settings().is_built_in():
            value = None
        self.store(setting=file_format.GENERATOR_ENABLED, value=value)

    def _fields_of(self, setting):
        """Return the fields that edit one of the view's settings, made by the method its kind of setting names."""
        made = getattr(self, FIELD_MAKERS[type(setting)])(setting)
        if isinstance(made, list):
            return made
        return [made]

    def _restart_field(self, setting):
        """Return the generator's Restart field."""
        return restart_field(self)

    def _progression_field(self, setting):
        """Return the field of the generator's progression, ENTER opening the chord editor."""
        return progression_field(page=self, label=setting.label)

    def _guitar_bar_field(self, setting):
        """Return the field of a Guitarify's bar of strokes, ENTER opening the bar editor."""
        return guitar_bar_field(page=self, label=setting.label)

    def _drift_value_rows(self, setting):
        """Return a row of version A and version B for each of a drift's values."""
        return drift_value_rows(self)

    def _section_table(self, setting):
        """Return the table of what the generator does in each kind of section the song's scenes have."""
        return section_table(page=self, view=setting)

    def _when_fields(self, setting):
        """Return a setting's fields while its condition holds, and none while it doesn't."""
        if not self.settings().holds(setting.when):
            return []
        return self._fields_of(setting.view)

    def _inherited_choice(self, setting):
        """Return a choice whose value comes from above until chosen: its first choice gives it back, and a value from above says so."""
        settings = self.settings()
        value = settings.get_own(setting.setting)
        current = value
        shown = value
        if settings.inherits(setting.setting):
            current = setting.inherited_choice
            shown = setting.inherited_shown.format(value=value)
        return ChoiceField(
            page=self, label=setting.label, choices=[setting.inherited_choice, *setting.choices], current=current, shown=shown,
            set=functools.partial(self.store_inherited, setting=setting), clear=functools.partial(self.store, setting=setting.setting, value=None),
            clear_what=setting.inherited_what,
        )

    def _gauge(self, setting):
        """Return a number stepped or typed and drawn as a horizontal gauge, empty at its lowest."""
        written = self.settings().get_written(setting.setting)
        number = setting.default
        if written is not None:
            number = written
        return NumberField(
            page=self, label=setting.label, number=number, shown=gauge_shown(place=number, lowest=setting.lowest + 1, highest=setting.highest),
            lowest=setting.lowest, highest=setting.highest, set=functools.partial(self.store_number, setting=setting),
        )

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
        cleared = marks.MSG_NONE_SHOWN
        if setting.default is not None:
            cleared = _number_shown(number=setting.default, setting=setting) or str(setting.default)
        return NumberField(
            page=self, label=setting.label, number=number, start=start, shown=shown, lowest=described.get_lowest(),
            highest=described.get_highest(), set=functools.partial(self.store_number, setting=setting),
            clear=functools.partial(self.store, setting=setting.setting, value=None), clear_what=cleared,
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

    def _offsets_field(self, setting):
        """Return the field of an arpeggiator's offsets, ENTER opening the offsets editor and Bksp removing them."""
        return Field(
            label=setting.label, value=functools.partial(self.offsets_shown, setting), adjust=None, enter=functools.partial(self.open_offsets, setting),
            enter_what=legends.What.EDIT, clear=functools.partial(self.store, setting=setting.setting, value=None), clear_what=marks.MSG_NONE_SHOWN,
        )

    def _track_field(self, setting):
        """Return the field that chooses a track of the current song, (none) first."""
        named = self.settings().get_written(setting.setting) or marks.MSG_NONE_SHOWN
        return ChoiceField(
            page=self, label=setting.label, choices=[marks.MSG_NONE_SHOWN, *self.tracks(setting)], current=named,
            set=functools.partial(self.store_track, setting=setting), clear=functools.partial(self.store_track, None, setting=setting),
            clear_what=marks.MSG_NONE_SHOWN,
        )

    def _steps_field(self, setting):
        """Return the field of a row of steps, which shows [configure], ENTER opening the row on its own page."""
        return Field(
            label=setting.label, value=lambda: marks.MSG_CONFIGURE_STEPS, adjust=None,
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
