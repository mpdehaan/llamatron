# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The page of a generator whose plugin describes its view (model/schema/generator_views.py): its Name, then each of the view's
settings, drawn from the description alone, so that the plugin's page needs no code outside its folder."""

import functools

from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.shared.field import ChoiceField, NameField
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.generator_editor import GeneratorEditor
from llamatron.model.schema import generator_plugins
from llamatron.user_strings import help as help_text, labels, messages


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
                fields.append(self._choice_field(setting))
        return fields

    def shown_name(self):
        return self.item

    def store_unless_default(self, value, *, setting):
        """Keep a setting's value, left out of the file where it is the value the setting takes when left out."""
        if value == setting.default:
            value = None
        self.store(setting=setting.setting, value=value)

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
