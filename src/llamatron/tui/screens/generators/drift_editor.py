# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Drift editor page: a drift's own settings, then each of its values for version A and version B side by side."""

from llamatron.composition import file_format, generator_settings
from llamatron.composition.file_format import DriftValue, Section
from llamatron.composition.generator_settings import DriftSetting, versioned
from llamatron.music import note
from llamatron.strings import help as help_text, labels, legends, marks, messages
from llamatron.tui import keybindings
from llamatron.tui.key_table import cursor_moved
from llamatron.tui.screens.generators.restart_field import restart_field
from llamatron.tui.screens.generators.time_field import time_field
from llamatron.tui.screens.shared.field import ChoiceField, Field, NameField, NumberField
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.generator_editor import GeneratorEditor
from llamatron.tui.text import sorted_names

# What a value of a version is when the drift leaves it out.
NOTHING = 0


class DriftEditor(GeneratorEditor, FieldPage):
    """A drift's settings. Up and Down pick a row; on a row of values, Left and Right pick version A or B, and [ and ] change the one picked."""

    KEYS = keybindings.DriftEditor
    HELP = help_text.HELP_DRIFT_EDITOR
    SECTION = Section.DRIFTS
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_DRIFT_LABEL)

    def __init__(self, *, holder, name):
        super().__init__(holder=holder, name=name)
        # Which version the cursor is on, on a row of values: A (0) or B (1).
        self.version = 0

    def own_fields(self):
        drift = self.settings()
        every = drift.get_every()
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            time_field(page=self, label=labels.MSG_EVERY_LABEL, written=every, first=file_format.ONE_BAR_WRITTEN, store=lambda value: self.store(setting=DriftSetting.EVERY, value=value)),
            NumberField(page=self, label=labels.MSG_STEPS_TO_B_LABEL, number=drift.get_steps_to_b(), lowest=generator_settings.MIN_STEPS_TO_B, highest=generator_settings.MAX_STEPS_TO_B,
                        set=lambda number: self.store(setting=DriftSetting.STEPS_TO_B, value=number)),
            ChoiceField(page=self, label=labels.MSG_DRIFT_DIRECTION_LABEL, choices=file_format.DRIFT_DIRECTIONS, current=drift.get_direction(),
                        set=lambda value: self.store(setting=DriftSetting.DIRECTION, value=None if value == file_format.DRIFT_DIRECTIONS[0] else value)),
            restart_field(self),
        ]

    def fields(self):
        return [*self.own_fields(), *[self.version_field(value) for value in self.version_values()]]

    def version_values(self):
        """Return each value a version has, in the editor's order."""
        numbers = [name for name, _, _ in generator_settings.DRIFT_NUMBERS]
        return [*numbers[:-2], DriftValue.SCALE, numbers[-2], DriftValue.ROOT, numbers[-1]]

    def is_version_row(self):
        return self.cursor.get_place() >= len(self.own_fields())

    def keys(self):
        result = super().keys()
        if self.is_version_row():
            result.append(self.bind(self.KEYS.VERSION, action=self.pick_version, wants_key=True))
        return result

    def pick_version(self, name):
        self.version = cursor_moved(place=self.version, name=name, count=len(file_format.DRIFT_VERSIONS))

    def version_field(self, value):
        """Return the row of one value, showing A's and B's, the one picked marked, and changing only the one picked."""
        label = labels.MSG_DRIFT_VALUE_LABELS[value]
        drift = self.settings()
        shown = [self.value_text(value=value, written=drift.get_value(version=version, value=value)) for version in file_format.DRIFT_VERSIONS]
        shown[self.version] = labels.MSG_DRIFT_PICKED.format(value=shown[self.version])
        setting = versioned(version=file_format.DRIFT_VERSIONS[self.version], value=value)
        current = drift.get_value(version=file_format.DRIFT_VERSIONS[self.version], value=value)
        if value in (DriftValue.SCALE, DriftValue.ROOT):
            choices = [None, *self.choices_of(value)]
            return Field(
                label=label, value=lambda: labels.MSG_DRIFT_PAIR.format(a=shown[0], b=shown[1]),
                adjust=lambda offset: self.store(setting=setting, value=choices[max(min(choices.index(current) + offset, len(choices) - 1), 0)]),
                enter=lambda: self.pick_choice(setting=setting, value=value, current=current), enter_what=legends.What.CHOOSE,
                clear=lambda: self.store(setting=setting, value=None),
            )
        lowest, highest = self.range_of(value)
        number = current or NOTHING
        return Field(
            label=label, value=lambda: labels.MSG_DRIFT_PAIR.format(a=shown[0], b=shown[1]),
            adjust=lambda offset: self.store(setting=setting, value=max(min(number + offset, highest), lowest) or None),
            enter=lambda: self.ask_number(title=messages.MSG_NUMBER_PROMPT.format(row=label, low=lowest, high=highest), value=number, low=lowest, high=highest,
                                          then=lambda typed: self.store(setting=setting, value=typed or None)),
            clear=lambda: self.store(setting=setting, value=None),
        )

    def value_text(self, *, value, written):
        if written is None:
            return marks.MSG_NONE_SHOWN if value in (DriftValue.SCALE, DriftValue.ROOT) else str(NOTHING)
        return str(written)

    def range_of(self, value):
        for name, lowest, highest in generator_settings.DRIFT_NUMBERS:
            if name == value:
                return lowest, highest
        raise KeyError(value)

    def choices_of(self, value):
        """Return what a scale or root override can be: the song's scales by name, or the roots."""
        return sorted_names(self.document().song().get_scale_names()) if value == DriftValue.SCALE else list(note.ROOT_NAMES)

    def pick_choice(self, *, setting, value, current):
        choices = self.choices_of(value)
        self.pick(title=labels.MSG_DRIFT_VALUE_LABELS[value], values=[None, *choices], shown=[marks.MSG_NONE_SHOWN, *choices], current=current, then=lambda chosen: self.store(setting=setting, value=chosen))
