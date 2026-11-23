# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The wizard's Genre branch: the genre and the subgenre, which must be chosen, then the key, the tempo and the song's name, which arrive filled in."""

from llamatron.interface.forms.nodes import ChoiceField, Field
from llamatron.interface.forms.text import clock
from llamatron.interface.tracker.screens.wizard.branch import Branch
from llamatron.model.values import note
from llamatron.user_strings import labels, legends, marks, messages
from llamatron.wizards.create_song import wizard_limits
from llamatron.wizards.create_song.wizard_choices import genre_names, genre_title

# An empty line of text, or a value that shows nothing.
NO_TEXT = ''

# How the Change Genre question words each kind of thing lost and kept.
LOST_SHOWN = {
    wizard_limits.LOST_BAND_SETTINGS: messages.MSG_CHANGE_GENRE_BAND_SETTINGS,
    wizard_limits.LOST_OWN_CHORDS: messages.MSG_CHANGE_GENRE_OWN_CHORDS,
    wizard_limits.LOST_FORM: messages.MSG_CHANGE_GENRE_FORM,
    wizard_limits.LOST_TUNE_TAKES: messages.MSG_CHANGE_GENRE_TUNE_TAKES,
    wizard_limits.LOST_RIFFS: messages.MSG_CHANGE_GENRE_RIFFS,
}
KEPT_SHOWN = {wizard_limits.KEPT_OWN_TUNES: messages.MSG_CHANGE_GENRE_OWN_TUNES, wizard_limits.KEPT_OWN_RIFFS: messages.MSG_CHANGE_GENRE_OWN_RIFFS}


class GenreBranch(Branch):
    """The genre, and what follows from the genre and the subgenre chosen after it."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_GENRE_BRANCH

    def set_genre(self, genre):
        """Choose a genre, asking first where another genre would give up what was chosen by hand: the question counts what is lost
        and what is kept, by kind and never by name."""
        choices = self.get_choices()
        lost, kept = choices.lost_with_genre() if genre != choices.get_genre() else ({}, {})
        if not lost:
            choices.set_genre(genre)
            return
        said = [messages.MSG_CHANGE_GENRE_LOST, *(LOST_SHOWN[kind].format(count=count) for kind, count in lost.items())]
        if kept:
            said += [NO_TEXT, messages.MSG_CHANGE_GENRE_KEPT, *(KEPT_SHOWN[kind].format(count=count) for kind, count in kept.items())]
        page = self.get_page()
        page.confirm(title=messages.MSG_CHANGE_GENRE_TITLE, lines=[*said, NO_TEXT, messages.MSG_CHANGE_GENRE_QUESTION], starts_on_no=True,
                     then=lambda: page.choosing(choices.set_genre)(genre))

    def fields(self):
        choices = self.get_choices()
        page = self.get_page()
        genres = genre_names()
        fields = [
            self.choice_from_nothing(label=labels.MSG_GENRE_LABEL, values=genres, names=[genre_title(genre) for genre in genres], current=choices.get_genre(), set_value=self.set_genre),
        ]
        if choices.is_ready():
            fields += [
                ChoiceField(page=page, label=labels.MSG_WIZARD_KEY_LABEL, choices=note.ROOT_NAMES, current=choices.get_root(), set=page.choosing(choices.set_root)),
                ChoiceField(page=page, label=labels.MSG_SCALE_LABEL, choices=wizard_limits.SCALE_TYPES, names=[labels.MSG_WIZARD_SCALE_TYPE_NAMES[kind] for kind in wizard_limits.SCALE_TYPES], current=choices.get_scale_type(),
                            shown=labels.MSG_WIZARD_SCALE_TYPE_NAMES[choices.get_scale_type()], set=page.choosing(choices.set_scale_type)),
                # The meter is the subgenre's, so it is only shown; the length follows the sections, so stepping it chooses a longer or a shorter form.
                Field(label=labels.MSG_WIZARD_METER_LABEL, value=choices.meter),
                self.length_field(),
            ]
        if page.replaces():
            # A replaced song keeps its name, so the name is only shown.
            return [*fields, Field(label=labels.MSG_NAME_LABEL, value=page.get_song_name)]
        return [*fields, Field(label=labels.MSG_NAME_LABEL, value=page.get_song_name, enter=page.ask_song_name, enter_what=legends.What.RENAME)]

    def length_field(self):
        """Return the Length field, whose steps choose a shorter or a longer suggested form; once the form is the song's own,
        the length is only shown, since a step would put a suggested form in place of the sections changed."""
        choices = self.get_choices()
        if choices.get_song_form().has_own_form():
            return Field(label=labels.MSG_WIZARD_LENGTH_LABEL, value=lambda: marks.MSG_WIZARD_LENGTH_SHOWN.format(length=clock(choices.get_song_form().form_seconds()), form=marks.MSG_WIZARD_OWN_FORM))
        return Field(label=labels.MSG_WIZARD_LENGTH_LABEL, value=lambda: marks.MSG_WIZARD_LENGTH_SHOWN.format(length=clock(choices.get_song_form().form_seconds()), form=choices.get_song_form().get_form()),
                     adjust=self.get_page().choosing(choices.step_length))
