# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A solo's notes in the wizard: one of the song's solos, to edit by hand and to hear.

Each solo of the song has a panel under Melodies, after the melodies of the sections, named
Solo, Solo 2 and so on in the form's order, since no two solos of a song are alike. The panel
has buttons to edit the solo's notes in the pattern editor, to have the solo written again,
and to hear the solo, its player alone and with the band. What shapes a solo, its kind, bars and energy, is on the solo's own
section under Form.
"""


from llamatron.interface.forms.nodes import Button, Field
from llamatron.interface.forms.remarks import dim_remark
from llamatron.interface.pages.wizard.branch import Branch
from llamatron.user_strings import labels, legends, messages
from llamatron.wizards.create_song import wizard_limits

# What a solo's panel is remembered by, apart from a section of the form called solo.
SOLO_MELODY_KEY = 'notes of solo {number}'
FIRST_SOLO = 1


class SoloMelodyBranch(Branch):
    """The notes of one solo of the song, by its number among the song's solos."""

    __slots__ = ('_number',)

    def __init__(self, *, page, number):
        super().__init__(page=page)
        self._number = number

    def key(self):
        return SOLO_MELODY_KEY.format(number=self._number)

    def name(self):
        return wizard_limits.SOLO.capitalize() if self._number == FIRST_SOLO else labels.MSG_WIZARD_SOLO_NUMBERED.format(kind=wizard_limits.SOLO.capitalize(), number=self._number)

    def place(self):
        """Return the solo's place in the form, or None once the song has fewer solos."""
        places = self.get_choices().get_solos().solo_places()
        return places[self._number - FIRST_SOLO] if self._number - FIRST_SOLO < len(places) else None

    def summary(self):
        """Return whether the solo's notes were edited by hand, or who plays the solo."""
        choices = self.get_choices()
        if self.place() is None:
            return None
        return labels.MSG_WIZARD_NOTES_EDITED if choices.get_solos().solo_is_own(self.place()) else choices.player(choices.get_solos().solo_player()).title()

    def fields(self):
        choices = self.get_choices()
        place = self.place()
        if place is None:
            return []
        played_by = Field(label=labels.MSG_WIZARD_SOLO_PLAYED_BY_LABEL, value=lambda: choices.player(choices.get_solos().solo_player()).title())
        section = Field(label=labels.MSG_WIZARD_SOLO_SECTION_LABEL, value=lambda: choices.get_song_form().section_labels()[place])
        return [played_by, section, *self.buttons()]

    def buttons(self):
        """Return the buttons that open the solo's notes in the pattern editor and that hear the solo, its player alone and with the band."""
        choices = self.get_choices()
        page = self.get_page()
        place = self.place()

        def give_back():
            question = messages.MSG_WIZARD_TUNE_GIVE_BACK_QUESTION.format(kind=wizard_limits.SOLO)
            page.confirm(title=question, lines=[], starts_on_no=True,
                         then=lambda: page.choosing(lambda _: choices.get_solos().set_solo_pattern(place=place, pattern=None))(None))
        # On notes edited by hand, the delete key on the button gives the notes back to the wizard, after a question.
        return [Button(label=labels.MSG_WIZARD_EDIT_NOTES_BUTTON, enter=lambda: page.edit_solo(place), enter_what=legends.MSG_WIZARD_EDIT_NOTES_WHAT, clear=give_back if choices.get_solos().solo_is_own(place) else None,
                       clear_what=legends.MSG_TUNE_USUAL_WHAT),
                Button(label=labels.MSG_WIZARD_REGENERATE_BUTTON, enter=self.regenerate, enter_what=legends.MSG_REGENERATE_WHAT),
                Button(label=labels.MSG_LISTEN_LABEL, key_name=legends.KeyName.L, enter=lambda: page.listen_to(self.listens()), enter_what=legends.MSG_LISTEN_WHAT),
                Button(label=labels.MSG_WIZARD_LISTEN_BAND_BUTTON, enter=lambda: page.listen_to(self.heard_with_band()), enter_what=legends.MSG_LISTEN_WHAT)]

    def regenerate(self):
        """Have this solo written again, with nothing kept of the old one and the song's other solos left alone, after asking."""
        choices = self.get_choices()
        page = self.get_page()
        place = self.place()
        name = messages.MSG_WIZARD_MELODY_OF.format(kind=wizard_limits.SOLO)

        def written():
            page.choosing(choices.get_solos().new_solo_take)(place)
            page.say(messages.MSG_WIZARD_REGENERATED.format(name=name))
        page.confirm(title=messages.MSG_WIZARD_REGENERATE_TITLE.format(name=name), lines=[messages.MSG_WIZARD_REGENERATE_SAYS.format(name=name)], starts_on_no=True, then=written)

    def listens_alone(self):
        return True

    def listens(self):
        """Listen plays the solo's player alone in the solo."""
        if self.place() is None:
            return None
        return messages.MSG_WIZARD_MELODY_OF.format(kind=wizard_limits.SOLO), self.place(), self.get_choices().get_solos().solo_player()

    def heard_with_band(self):
        """Return what Listen With Band plays: everybody in the solo."""
        return messages.MSG_WIZARD_SECTION_WITH_BAND.format(kind=wizard_limits.SOLO), self.place(), None

    def remarks(self, width):
        """Return the line under the buttons that says whose the solo's notes are: the wizard's, or edited by hand."""
        choices = self.get_choices()
        if not choices.is_ready() or self.place() is None:
            return []
        return [dim_remark(messages.MSG_WIZARD_NOTES_BY_HAND if choices.get_solos().solo_is_own(self.place()) else messages.MSG_WIZARD_HOOK_MADE)]
