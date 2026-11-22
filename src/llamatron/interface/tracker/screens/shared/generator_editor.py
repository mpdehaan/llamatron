# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What every page of one generator shares: its settings, found one way, and a value stored one way."""

from llamatron.interface.tracker.screens.shared.field import NumberField
from llamatron.interface.tracker.screens.shared.shows_named_item import ShowsNamedItem


class GeneratorEditor(ShowsNamedItem):
    """A page of one generator of the set: `settings()` is the generator's settings, and `store()` keeps one of them.

    SECTION, which every page of a named thing says, is the section of the generator's kind.
    """

    __slots__ = ()

    # Where the built-in generator the page edits is, a BuiltInPlace, or None for a generator of the set's list.
    built_in = None

    def __init__(self, *, holder, name, built_in=None):
        """Open on a generator of the set's list by its name, or on a clip's or a track's built-in one by its place, name then
        being what its kind is called."""
        self.built_in = built_in
        super().__init__(holder=holder, name=name)

    def settings(self):
        """Return the settings of the generator the page shows: the set's by its name, or a built-in's by its place."""
        if self.built_in is not None:
            return self.document().built_in(self.built_in)
        return self.document().generator(section=self.SECTION, name=self.item)

    def still_exists(self):
        """Return whether the generator is still there, which an undo or redo can take away: by its name, or a built-in's by
        whether its clip or track is still there."""
        if self.built_in is not None:
            return self.document().has_built_in(self.built_in)
        return super().still_exists()

    def open_part(self, page_class, **given):
        """Open a page that edits a part of the generator, such as its offsets, on the same generator."""
        page = page_class(holder=self.holder, name=self.item, built_in=self.built_in, **given)
        if self.opener is not None:
            page.opened_from(page=self.opener, word=self.opener_word)
        self.show_page(page)

    def store(self, *, setting, value):
        """Keep one setting by its file name, checked as reading a file checks it, or None to leave it out of the file."""
        self.document().change_set(self.settings().set_setting, name=setting, value=value)

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
