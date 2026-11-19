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
"""The wizard's Genre branch: the genre and the subgenre, which must be chosen, then the key, the tempo and the song's name, which arrive filled in."""

from llamatron.macro_composer import wizard_choices
from llamatron.macro_composer.wizard_choices import genre_names, genre_title
from llamatron.music import note
from llamatron.strings import labels, legends, marks, messages
from llamatron.tui import drawing
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.screens.shared.field import ChoiceField, Field
from llamatron.tui.screens.wizard.branch import Branch
from llamatron.tui.text import clock

# How the Change Genre question words each kind of thing lost and kept.
LOST_SHOWN = {
    wizard_choices.LOST_BAND_SETTINGS: messages.MSG_CHANGE_GENRE_BAND_SETTINGS,
    wizard_choices.LOST_OWN_CHORDS: messages.MSG_CHANGE_GENRE_OWN_CHORDS,
    wizard_choices.LOST_FORM: messages.MSG_CHANGE_GENRE_FORM,
    wizard_choices.LOST_TUNE_TAKES: messages.MSG_CHANGE_GENRE_TUNE_TAKES,
    wizard_choices.LOST_RIFFS: messages.MSG_CHANGE_GENRE_RIFFS,
}
KEPT_SHOWN = {wizard_choices.KEPT_OWN_TUNES: messages.MSG_CHANGE_GENRE_OWN_TUNES, wizard_choices.KEPT_OWN_RIFFS: messages.MSG_CHANGE_GENRE_OWN_RIFFS}


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
            said += [drawing.NOTHING, messages.MSG_CHANGE_GENRE_KEPT, *(KEPT_SHOWN[kind].format(count=count) for kind, count in kept.items())]
        dialog = ConfirmDialog(title=messages.MSG_CHANGE_GENRE_TITLE, messages=[*said, drawing.NOTHING, messages.MSG_CHANGE_GENRE_QUESTION], starts_on_no=True)
        self.get_page().ask(dialog=dialog, then=lambda _: self.get_page().choosing(choices.set_genre)(genre))

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
                ChoiceField(page=page, label=labels.MSG_SCALE_LABEL, choices=wizard_choices.SCALE_TYPES, names=[labels.MSG_WIZARD_SCALE_TYPE_NAMES[kind] for kind in wizard_choices.SCALE_TYPES], current=choices.get_scale_type(),
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
        if choices.has_own_form():
            return Field(label=labels.MSG_WIZARD_LENGTH_LABEL, value=lambda: marks.MSG_WIZARD_LENGTH_SHOWN.format(length=clock(choices.form_seconds()), form=marks.MSG_WIZARD_OWN_FORM))
        return Field(label=labels.MSG_WIZARD_LENGTH_LABEL, value=lambda: marks.MSG_WIZARD_LENGTH_SHOWN.format(length=clock(choices.form_seconds()), form=choices.get_form()),
                     adjust=self.get_page().choosing(choices.step_length))
