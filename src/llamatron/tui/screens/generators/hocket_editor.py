# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Hocket editor: its name, the track whose notes it shares out, and its Restart."""

from llamatron.engine.generators import hocket as hocket_plugin
from llamatron.engine.generators.hocket import strings as hocket_strings
from llamatron.engine.generators.hocket.model import HocketSetting
from llamatron.tui import keybindings
from llamatron.tui.screens.generators.restart_field import restart_field
from llamatron.tui.screens.shared.field import ChoiceField, NameField
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.generator_editor import GeneratorEditor
from llamatron.tui.text import sorted_names
from llamatron.user_strings import help as help_text, labels, legends, marks, messages


class HocketEditor(GeneratorEditor, FieldPage):

    """The page that edits a Hocket, which passes a part's notes in turn among tracks."""

    KEYS = keybindings.HocketEditor
    HELP = help_text.HELP_HOCKET_EDITOR
    SECTION = hocket_plugin.SECTION
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=hocket_strings.MSG_LABEL)

    def store_source(self, source):
        self.store(setting=HocketSetting.SOURCE, value=source)

    def sources(self):
        """Return the tracks the source can be: the current song's, sorted, and the Hocket's own source among them even when the song has no such track, so that it is seen and kept."""
        names = set(self.document().song().get_track_names())
        if self.settings().get_source() is not None:
            names.add(self.settings().get_source())
        return sorted_names(names)

    def fields(self):
        source = self.settings().get_source()
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            ChoiceField(
                page=self, label=labels.MSG_SOURCE_TRACK_LABEL, choices=[marks.MSG_NONE_SHOWN, *self.sources()], current=source or marks.MSG_NONE_SHOWN,
                set=lambda choice: self.store_source(None if choice == marks.MSG_NONE_SHOWN else choice), clear=lambda: self.store_source(None), clear_what=legends.MSG_NO_SOURCE_WHAT,
            ),
            restart_field(self),
        ]
