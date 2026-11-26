# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The built-in generators a clip and a track each hold: one of each kind a plugin declares built in, such as Chords and the
Arpeggiator, kept in the file by kind under one setting, switched off until switched on, and with no name, since nothing but
its holder runs it. Each is read as its plugin's settings, marked built in, which hand themselves back to their holder after
every change, so that the holder keeps them and its revision moves."""

import functools

from llamatron.caching.revised import notes_change
from llamatron.model.file.checks import listed, reading
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.schema import generator_plugins
from llamatron.model.schema.setting import Checked
from llamatron.user_strings import errors


def built_ins_setting(name):
    """Return the description of a holder's built-in generators, written under a name: each built-in kind's settings by kind."""
    return Checked(name=name, check=check_built_ins)


def check_built_ins(value):
    """Refuse built-in generators unless they are settings by kind, each of a kind a plugin declares built in and each right as
    the plugin's settings would be in the set's list."""
    if not isinstance(value, dict):
        raise InvalidValue(errors.ERR_NOT_SETTINGS.format(value=value))
    kinds = generator_plugins.built_in_kinds()
    for kind, settings in value.items():
        if kind not in kinds:
            raise InvalidValue(errors.ERR_NOT_A_BUILT_IN.format(kind=kind, kinds=listed(kinds)))
        with reading(kind):
            generator_plugins.settings_of(kind).check_data(settings)


def pass_over_unknown_built_ins(*, data, name):
    """Take out of a file's built-in generators every setting their kind doesn't have, as reading the set's list does, so that
    a file from another version opens; a kind no plugin builds in is left for the check to refuse."""
    built_ins = data.get(name)
    if not isinstance(built_ins, dict):
        return
    kinds = generator_plugins.built_in_kinds()
    for kind, settings in built_ins.items():
        if kind in kinds and isinstance(settings, dict):
            generator_plugins.settings_of(kind).pass_over_unknown_names(settings)


class HoldsBuiltIns:
    """Something that holds a built-in generator of each kind a plugin declares built in: a clip and a track. Its class names
    the setting they are written under in BUILT_IN_SETTING."""

    __slots__ = ()

    BUILT_IN_SETTING = None

    def get_built_in(self, kind):
        """Return the settings of its built-in generator of a kind, as its plugin's settings marked built in, blank and switched off
        where it holds none: every change made through their setters is kept here."""
        written = self._written_built_ins().get(kind) or {}
        return generator_plugins.settings_of(kind)(written, built_in=True, keeper=functools.partial(self._keep_built_in, kind=kind))

    def has_built_in_on(self, kind):
        """Return whether its built-in generator of a kind is switched on."""
        written = self._written_built_ins().get(kind)
        return written is not None and self.get_built_in(kind).is_enabled()

    def built_ins_on(self):
        """Return the kinds of its built-in generators that are switched on, in the order they run: at once none where it holds
        none, as most do, since every clip asks as it plays."""
        if not self._written_built_ins():
            return []
        return [kind for kind in generator_plugins.built_in_kinds() if self.has_built_in_on(kind)]

    def set_built_in_setting(self, *, kind, name, value):
        """Set one setting of its built-in generator of a kind, checked as the set's list checks it, or None to leave it out."""
        settings = self.get_built_in(kind)
        settings.set_written(name=name, value=value)

    def names_item(self, *, section, name):
        """Return whether one of its own settings, or one of its built-in generators, names an item of a section."""
        if super().names_item(section=section, name=name):
            return True
        return any(self.get_built_in(kind).names_item(section=section, name=name) for kind in self._written_built_ins())

    def named_items(self):
        """Return everything its own settings and its built-in generators name, as a set of (section, name)."""
        named = super().named_items()
        for kind in self._written_built_ins():
            named |= self.get_built_in(kind).named_items()
        return named

    def rename_references(self, *, section, old, new):
        """Follow the rename of an item of a section in its own settings and in each built-in generator that names it."""
        super().rename_references(section=section, old=old, new=new)
        for kind in list(self._written_built_ins()):
            settings = self.get_built_in(kind)
            if settings.names_item(section=section, name=old):
                settings.rename_references(section=section, old=old, new=new)
                self._keep_built_in(settings, kind=kind)

    def _written_built_ins(self):
        """Return its built-in generators' settings as written, by kind."""
        return self.get_written(self.BUILT_IN_SETTING) or {}

    @notes_change
    def _keep_built_in(self, settings, *, kind):
        """Keep a built-in generator's settings as they now are, leaving out of the file a kind with nothing written."""
        built_ins = dict(self._written_built_ins())
        built_ins[kind] = settings.to_data()
        if not built_ins[kind]:
            del built_ins[kind]
        self.set_written(name=self.BUILT_IN_SETTING, value=built_ins or None)
