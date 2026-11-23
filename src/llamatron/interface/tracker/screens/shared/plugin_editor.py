# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The page of a generator whose plugin describes its view (model/schema/generator_views.py): its Name, then each of the view's
settings, drawn from the description alone, so that the plugin's page needs no code outside its folder."""

import functools

from llamatron.interface.pages.generator import GeneratorPresenter
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.generator_editor import GeneratorEditor
from llamatron.model.schema import generator_plugins
from llamatron.user_strings import help as help_text, labels, messages


def plugin_editor_of(section):
    """Return what opens the page of a generator of a section: this page, made for the section's plugin."""
    return functools.partial(PluginEditor, section=section)


class PluginEditor(GeneratorEditor, FieldPage):
    """The page that edits a generator of any plugin that describes its view: the Generator presenter's form
    (interface/pages/generator.py), its Name, then the view's settings, column by column."""

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
        super().__init__(holder=holder, name=name)

    def presenter(self):
        """Return what the page shows and does, for its generator as it is now."""
        return GeneratorPresenter(page=self, section=self.SECTION, name=self.item)

    def fields(self):
        return self.presenter().form()
