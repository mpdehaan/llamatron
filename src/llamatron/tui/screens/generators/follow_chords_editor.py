# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Follow Chords editor: its name and the track whose chords it follows."""

from llamatron.model.objects.generator_settings import FollowChordsSetting
from llamatron.model.vocabulary.file_format import Section
from llamatron.tui import keybindings
from llamatron.tui.screens.shared.field import ChoiceField, NameField
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.generator_editor import GeneratorEditor
from llamatron.tui.text import sorted_names
from llamatron.user_strings import help as help_text, labels, legends, marks, messages


class FollowChordsEditor(GeneratorEditor, FieldPage):

    """The page that edits a Follow Chords generator, which moves a part's notes along the song's chords."""

    KEYS = keybindings.FollowChordsEditor
    HELP = help_text.HELP_FOLLOW_CHORDS_EDITOR
    SECTION = Section.FOLLOW_CHORDS
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_FOLLOW_CHORDS_LABEL)

    def store_chords_from(self, track):
        self.store(setting=FollowChordsSetting.CHORDS_FROM, value=track)

    def tracks(self):
        """Return the tracks that can be followed: the current song's, sorted, and the one followed among them even when the song has no such track, so that it is seen and kept."""
        names = set(self.document().song().get_track_names())
        if self.settings().get_chords_from() is not None:
            names.add(self.settings().get_chords_from())
        return sorted_names(names)

    def fields(self):
        followed = self.settings().get_chords_from()
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            ChoiceField(
                page=self, label=labels.MSG_CHORDS_FROM_LABEL, choices=[marks.MSG_NONE_SHOWN, *self.tracks()], current=followed or marks.MSG_NONE_SHOWN,
                set=lambda choice: self.store_chords_from(None if choice == marks.MSG_NONE_SHOWN else choice), clear=lambda: self.store_chords_from(None), clear_what=legends.MSG_NO_TRACK_WHAT,
            ),
        ]
