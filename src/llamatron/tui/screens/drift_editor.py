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
"""The Drift editor page: a drift's own settings, then each of its values for version A and version B side by side."""

from llamatron.composition.file_format import ONE_BAR_WRITTEN
from llamatron.tui.screens.restart_field import restart_field
from llamatron.tui.screens.time_field import time_field
from llamatron.composition.file_format import DRIFT_DIRECTIONS, DRIFT_VERSIONS, DriftValue, GeneratorKind, Section
from llamatron.composition.generator_settings import DRIFT_NUMBERS, DriftSetting, MAX_STEPS_TO_B, MIN_STEPS_TO_B, versioned
from llamatron.music.note import ROOT_NAMES
from llamatron.strings.help import HELP_DRIFT_EDITOR
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.key_table import cursor_moved
from llamatron.tui.screens.field import ChoiceField, Field, NameField, NumberField
from llamatron.tui.screens.field_page import FieldPage
from llamatron.tui.screens.shared import NO_SEED
from llamatron.tui.screens.shows_named_item import ShowsNamedItem
from llamatron.tui.text import sorted_names
from llamatron.strings.labels import (
    Crumb, MSG_DRIFT_DIRECTION_LABEL, MSG_DRIFT_LABEL, MSG_DRIFT_PAIR, MSG_DRIFT_PICKED, MSG_DRIFT_VALUE_LABELS, MSG_EVERY_LABEL, MSG_ONE_BAR, MSG_TIME_NAMES,
    MSG_SEED_LABEL, MSG_STEPS_TO_B_LABEL,
)
from llamatron.strings.legends import MSG_USE_SONG_SEED_WHAT, What
from llamatron.strings.marks import MSG_NONE_SHOWN, MSG_SONG_SEED_SHOWN
from llamatron.strings.messages import MSG_NUMBER_PROMPT, MSG_RENAME_GENERATOR_PROMPT
from llamatron.tui import keybindings

# What a value of a version is when the drift leaves it out.
NOTHING = 0


def every_text(every):
    """Return how often a drift triggers, as the Drifts page shows it: 1 bar when left blank, and a dotted or triplet length by its name."""
    shown = MSG_ONE_BAR if every is None else str(every)
    return MSG_TIME_NAMES.get(shown, shown)


class DriftEditor(ShowsNamedItem, FieldPage):
    """A drift's settings. Up and Down pick a row; on a row of values, Left and Right pick version A or B, and [ and ] change the one picked."""

    KEYS = keybindings.DriftEditor
    HELP = HELP_DRIFT_EDITOR
    SECTION = Section.DRIFTS
    CRUMBS_BEFORE = (Crumb.GENERATORS,)
    RENAME_PROMPT = MSG_RENAME_GENERATOR_PROMPT.format(label=MSG_DRIFT_LABEL)

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)
        # Which version the cursor is on, on a row of values: A (0) or B (1).
        self.version = 0

    def drift(self):
        return self.document().song().get_generator_settings(kind=GeneratorKind.DRIFT, name=self.item)

    def set_value(self, *, setting, value):
        self.document().set_generator_setting(section=Section.DRIFTS, name=self.item, setting=setting, value=value)

    def own_fields(self):
        drift = self.drift()
        seed = drift.get_seed()
        every = drift.get_every()
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            time_field(page=self, label=MSG_EVERY_LABEL, written=every, first=ONE_BAR_WRITTEN, store=lambda value: self.set_value(setting=DriftSetting.EVERY, value=value)),
            NumberField(page=self, label=MSG_STEPS_TO_B_LABEL, number=drift.get_steps_to_b(), lowest=MIN_STEPS_TO_B, highest=MAX_STEPS_TO_B,
                        set=lambda number: self.set_value(setting=DriftSetting.STEPS_TO_B, value=number)),
            ChoiceField(page=self, label=MSG_DRIFT_DIRECTION_LABEL, choices=DRIFT_DIRECTIONS, current=drift.get_direction(),
                        set=lambda value: self.set_value(setting=DriftSetting.DIRECTION, value=None if value == DRIFT_DIRECTIONS[0] else value)),
            NumberField(
                page=self, label=MSG_SEED_LABEL, number=seed, start=NO_SEED, shown=MSG_SONG_SEED_SHOWN if seed is None else None,
                set=lambda number: self.set_value(setting=DriftSetting.SEED, value=number),
                clear=lambda: self.set_value(setting=DriftSetting.SEED, value=None), clear_what=MSG_USE_SONG_SEED_WHAT,
            ),
            restart_field(self),
        ]

    def fields(self):
        return [*self.own_fields(), *[self.version_field(value) for value in self.version_values()]]

    def version_values(self):
        """Return each value a version has, in the editor's order."""
        numbers = [name for name, _, _ in DRIFT_NUMBERS]
        return [*numbers[:-2], DriftValue.SCALE, numbers[-2], DriftValue.ROOT, numbers[-1]]

    def is_version_row(self):
        return self.place >= len(self.own_fields())

    def keys(self):
        result = super().keys()
        if self.is_version_row():
            result.append(self.bind(self.KEYS.VERSION, action=self.pick_version, wants_key=True))
        return result

    def pick_version(self, name):
        self.version = cursor_moved(place=self.version, name=name, count=len(DRIFT_VERSIONS))

    def version_field(self, value):
        """Return the row of one value, showing A's and B's, the one picked marked, and changing only the one picked."""
        label = MSG_DRIFT_VALUE_LABELS[value]
        drift = self.drift()
        shown = [self.value_text(value=value, written=drift.get_value(version=version, value=value)) for version in DRIFT_VERSIONS]
        shown[self.version] = MSG_DRIFT_PICKED.format(value=shown[self.version])
        setting = versioned(version=DRIFT_VERSIONS[self.version], value=value)
        current = drift.get_value(version=DRIFT_VERSIONS[self.version], value=value)
        if value in (DriftValue.SCALE, DriftValue.ROOT):
            choices = [None, *self.choices_of(value)]
            return Field(
                label=label, value=lambda: MSG_DRIFT_PAIR.format(a=shown[0], b=shown[1]),
                adjust=lambda offset: self.set_value(setting=setting, value=choices[max(min(choices.index(current) + offset, len(choices) - 1), 0)]),
                enter=lambda: self.pick_choice(setting=setting, value=value, current=current), enter_what=What.CHOOSE,
                clear=lambda: self.set_value(setting=setting, value=None),
            )
        lowest, highest = self.range_of(value)
        number = current or NOTHING
        return Field(
            label=label, value=lambda: MSG_DRIFT_PAIR.format(a=shown[0], b=shown[1]),
            adjust=lambda offset: self.set_value(setting=setting, value=max(min(number + offset, highest), lowest) or None),
            enter=lambda: self.ask_number(title=MSG_NUMBER_PROMPT.format(row=label, low=lowest, high=highest), value=number, low=lowest, high=highest,
                                          then=lambda typed: self.set_value(setting=setting, value=typed or None)),
            clear=lambda: self.set_value(setting=setting, value=None),
        )

    def value_text(self, *, value, written):
        if written is None:
            return MSG_NONE_SHOWN if value in (DriftValue.SCALE, DriftValue.ROOT) else str(NOTHING)
        return str(written)

    def range_of(self, value):
        for name, lowest, highest in DRIFT_NUMBERS:
            if name == value:
                return lowest, highest
        raise KeyError(value)

    def choices_of(self, value):
        """Return what a scale or root override can be: the song's scales by name, or the roots."""
        return sorted_names(self.document().song().get_scale_names()) if value == DriftValue.SCALE else list(ROOT_NAMES)

    def pick_choice(self, *, setting, value, current):
        options = [MSG_NONE_SHOWN, *self.choices_of(value)]

        def chosen(item):
            self.set_value(setting=setting, value=None if item == 0 else options[item])
        self.ask(dialog=ChoiceDialog(title=MSG_DRIFT_VALUE_LABELS[value], options=options, current=options.index(current) if current in options else 0), then=chosen)
