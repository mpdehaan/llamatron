# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What every page of one generator shares: its settings, found one way, and a value stored one way."""

from llamatron.tui.screens.shared.field import NumberField
from llamatron.tui.screens.shared.shows_named_item import ShowsNamedItem


class GeneratorEditor(ShowsNamedItem):
    """A page of one generator of the set: `settings()` is the generator's settings, and `store()` keeps one of them.

    SECTION, which every page of a named thing says, is the section of the generator's kind.
    """

    __slots__ = ()

    def settings(self):
        """Return the settings of the generator the page shows."""
        return self.document().generator(section=self.SECTION, name=self.item)

    def store(self, *, setting, value):
        """Keep one setting by its file name, checked as reading a file checks it, or None to leave it out of the file."""
        self.document().change(self.settings().set_setting, name=setting, value=value)

    def number_field(self, *, label, setting, current, default, shown=None):
        """Return a field for a whole number of the generator, by the setting's file name.

        The range is the setting's own, said once where the setting is described. A number that is the
        default is left out of the file, and so is one cleared.
        """
        described = self.settings().SETTINGS[setting]
        return NumberField(
            page=self, label=label, number=current, lowest=described.get_lowest(), highest=described.get_highest(), shown=shown,
            set=lambda number: self.store(setting=setting, value=None if number == default else number), clear=lambda: self.store(setting=setting, value=None),
        )
