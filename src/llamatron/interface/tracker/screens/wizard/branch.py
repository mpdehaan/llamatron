# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A branch of the song wizard's tree: one part of the song a person may look at and change.

The wizard's page knows nothing of any one branch. It asks each branch for its name, the
branches under it and its fields, and draws the tree and the fields from the answers, so that a
branch is added, moved or split by changing the branches alone (who expects to
revise how the wizard is organized).
"""

from llamatron.interface.forms.nodes import Field, NumberField
from llamatron.interface.tracker import drawing
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.screens.shared.field import ChoiceField
from llamatron.music_theory.hooks import hook_bars
from llamatron.user_strings import labels, legends, marks

# Where a picker opens, and what stepping picks, before anything is chosen.
FIRST_CHOICE = 0

# The key of the answer kept of whether a panel has a field that does something.
EDITABLE_ANSWER = 'editable'


class Branch:
    """One part of the wizard's tree. A subclass says what the part is called and what it holds."""

    __slots__ = ('_page',)

    def __init__(self, *, page):
        self._page = page

    def get_page(self):
        """Return the wizard's page, which shows this branch's dialogs and keeps the song's name."""
        return self._page

    def get_choices(self):
        """Return the choices of this run of the wizard, which every branch reads and changes."""
        return self._page.get_choices()

    def key(self):
        """Return what the page remembers the branch by, open or closed: its name, unless two branches share one."""
        return self.name()

    def name(self):
        """Return the branch's name in the tree."""
        raise NotImplementedError

    def title(self):
        """Return the heading over the branch's fields: its name in capitals, unless the branch says more."""
        return self.name().upper()

    def note(self):
        """Return a few words after the branch's name in the tree, such as what it waits for, or nothing."""
        return drawing.NOTHING

    def summary(self):
        """Return in a few words what the branch has chosen, which the branch over it lists beside the branch's name, or None for a branch with nothing to say."""
        return None

    def children(self):
        """Return the branches under this one, in order."""
        return []

    def fields(self):
        """Return the branch's fields, as a settings page's, made afresh each time."""
        return []

    def remarks(self, width):
        """Return lines shown under the fields, such as an overview of what the branches under this one hold."""
        return []

    def choice_from_nothing(self, *, label, values, names, current, set_value):
        """Return a field that picks one of a list and starts with nothing chosen, as the genre and the subgenre do:
        it shows (choose) until then, and stepping it or opening its list starts from the first."""
        page = self.get_page()
        chosen = page.choosing(set_value)
        if current is not None:
            return ChoiceField(page=page, label=label, choices=values, names=names, current=current, shown=names[values.index(current)], set=chosen)

        def pick():
            page.ask(dialog=ChoiceDialog(title=label, options=names, current=FIRST_CHOICE), then=lambda place: chosen(values[place]))
        return Field(label=label, value=lambda: marks.MSG_WIZARD_CHOOSE, adjust=lambda offset: chosen(values[FIRST_CHOICE]), enter=pick, enter_what=legends.What.CHOOSE)

    def writing_gauge_field(self, *, label, position, moved, set_position):
        """Return the field of a gauge of how a melody is written: a number from 0 to 9, stepped or typed, drawn as a horizontal gauge
        with its number, said to be the genre's until the song moves it; Bksp gives a moved gauge back to the genre."""
        page = self.get_page()
        drawn = marks.MSG_WIZARD_GAUGE_FULL * (position - hook_bars.LOWEST_GAUGE) + marks.MSG_WIZARD_GAUGE_EMPTY * (hook_bars.HIGHEST_GAUGE - position)
        said = position if moved else labels.MSG_WIZARD_VALUE_FROM.format(value=position, origin=labels.MSG_WIZARD_USUAL_MELODY)
        return NumberField(page=page, label=label, number=position, shown=marks.MSG_WIZARD_WRITING_GAUGE_SHOWN.format(gauge=drawn, place=said), lowest=hook_bars.LOWEST_GAUGE, highest=hook_bars.HIGHEST_GAUGE,
                           set=page.choosing(set_position), clear=(lambda: page.choosing(set_position)(None)) if moved else None, clear_what=legends.MSG_WIZARD_FROM_GENRE_WHAT)

    def refusal(self):
        """Return why the cursor cannot move into the branch's fields yet, or None when it can."""
        return None

    def listens_alone(self):
        """Return whether Listen plays the branch's player with nothing under the line. A melody is heard bare, since its panel has
        Listen With Band for the rest; a player's part or a riff is heard over the section's drums, which it is judged against."""
        return False

    def listens(self):
        """Return what Listen plays on this branch, as what it is called, the place of its section in the form and the player whose clip
        alone plays, None for everybody in the section; or None for a branch with nothing to hear."""
        return None

    # A branch that holds a list, or is one of a list, as the form and its sections: the page gives such a branch the tracker's keys for a list.

    def field_keys(self):
        """Return the keys of the branch's own that work while the cursor is in its fields, bound through the page, as a list's keys to
        add, rename and copy are."""
        return []

    def adds(self):
        """Return whether a new thing can be added from this branch."""
        return False

    def kinds_to_add(self):
        """Return the kinds of thing that can be added from here, which a picker offers."""
        return []

    def add(self, kind):
        """Add a new thing of a kind at the end of the list this branch holds or is one of."""
        raise NotImplementedError

    def insert(self, kind):
        """Put a new thing of a kind before this branch, which is one of a list."""
        raise NotImplementedError

    def is_listed(self):
        """Return whether the branch is one of a list, so that it can be copied, removed and moved."""
        return False

    def copy(self):
        raise NotImplementedError

    def remove(self):
        raise NotImplementedError

    def shift(self, offset):
        """Move the branch earlier or later in its list, and return whether it moved."""
        raise NotImplementedError

    def can_be_edited(self):
        """Return whether any field of the branch does something, so that a branch only to be read takes no cursor."""
        # The legend asks at every key, and making a panel's fields may mean making the song, so the answer is kept with the choices.
        return self.get_choices().offered(key=(EDITABLE_ANSWER, type(self).__name__, self.name()), compute=lambda: any(field.enter or field.adjust for field in self.fields()))
