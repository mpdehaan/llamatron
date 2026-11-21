# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The wizard's Create branch: what will be made, to read, and the button that makes it."""

from llamatron.macro_composer.wizard_choices import genre_title
from llamatron.tui import drawing
from llamatron.tui.screens.shared.field import Button, Field
from llamatron.tui.screens.wizard.branch import Branch
from llamatron.tui.text import clock
from llamatron.user_strings import errors, labels, legends, marks


class CreateBranch(Branch):
    """A summary of the choices and the Create button, which works once a genre and a subgenre are chosen."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_CREATE_BRANCH

    def note(self):
        return drawing.NOTHING if self.get_choices().is_ready() else marks.MSG_WIZARD_NEEDS_GENRE

    def refusal(self):
        return None if self.get_choices().is_ready() else errors.ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE

    def fields(self):
        choices = self.get_choices()
        page = self.get_page()
        fields = [Field(label=labels.MSG_WIZARD_SONG_LABEL, value=page.get_song_name)]
        if choices.is_ready():
            fields += [
                Field(label=labels.MSG_GENRE_LABEL, value=lambda: marks.MSG_WIZARD_GENRE_SHOWN.format(genre=genre_title(choices.get_genre()), subgenre=choices.get_subgenre())),
                Field(label=labels.MSG_WIZARD_KEY_LABEL, value=lambda: marks.MSG_WIZARD_KEY_SHOWN.format(root=choices.get_root(), scale=labels.MSG_WIZARD_SCALE_TYPE_NAMES[choices.get_scale_type()])),
                Field(label=labels.MSG_TEMPO_LABEL, value=choices.get_tempo),
                Field(label=labels.MSG_WIZARD_FORM_LABEL, value=lambda: marks.MSG_WIZARD_FORM_SHOWN.format(form=marks.MSG_WIZARD_OWN_FORM if choices.get_song_form().has_own_form() else choices.get_song_form().get_form(), count=len(choices.get_song_form().form_sections()))),
                Field(label=labels.MSG_WIZARD_LENGTH_LABEL, value=lambda: clock(choices.get_song_form().form_seconds())),
            ]
        return [*fields, Button(label=labels.MSG_WIZARD_CREATE_BUTTON, key_name=legends.KeyName.ENTER, enter=page.create, enter_what=legends.MSG_WIZARD_CREATE_WHAT)]
