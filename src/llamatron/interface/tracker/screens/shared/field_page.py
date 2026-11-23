# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Field page: settings in a column, where the keys depend on the setting under the cursor."""

import functools

from llamatron.caching.cached import cached_while
from llamatron.interface.forms import moves, tab_box as tab_box_nodes
from llamatron.interface.forms.cursor import Cursor, NoSuchPlace
from llamatron.interface.forms.navigator import FormNavigator, page_buttons_start
from llamatron.interface.forms.nodes import Button, Cells, Heading, NameField, NumberField, TextField
from llamatron.interface.forms.tab_box import TabRow
from llamatron.interface.tracker import drawing, key_table, keybindings
from llamatron.interface.tracker.renderers import settings_page, tab_box as tab_box_drawing
from llamatron.interface.tracker.renderers.settings_page import SettingsPageDrawing
from llamatron.interface.tracker.screens.shared.kept_fields import fields_said
from llamatron.interface.tracker.screens.shared.page import Page
from llamatron.model.objects import setlist
from llamatron.user_strings import errors


# How wide a tab box is drawn where a page is drawn with no width, as a test draws it.
# The attribute of a page that says it is in Move mode, carrying something, which only some pages have.
MOVING = 'moving'


class FieldPage(Page):
    """Settings in a column, where the keys depend on the setting under the cursor."""

    KEYS = keybindings.FieldPage
    # Whether a blank line comes before every section's heading, as on the Draws page, rather than before the first alone.
    HEADINGS_APART = False

    def __init__(self, holder):
        super().__init__(holder)
        self.cursor = Cursor(place=0)
        # The cell the cursor is on in a row of cells, counted from the left.
        self.cell = 0
        # How wide the tab box was last drawn, which decides how its columns stand and so where the arrows lead in it.
        self.box_width = settings_page.BOX_WIDTH
        # The page's fields, built once for as long as nothing they are made from changes (cached_while).
        self._cached = {}

    def fields(self):
        return []

    def shared_sections(self):
        """Return the sections every page of its kind shows after its own fields, such as a generator's statements about the registers; none unless a page says."""
        return []

    def fields_state(self):
        """Return everything the page's fields are built from besides the page's own code, the key they are kept by: the
        document's revision, which moves with every change to the set, the sections open, the tabs chosen, where the cursor is and whether it carries something, and what the
        page itself says its fields read. A key asks for the fields dozens of times, to find the cursor, list the keys and draw,
        and each asking built every field and tab again: the clip page's took 13 ms a key."""
        moving = getattr(self, MOVING, False)
        shared = (self.document().get_revision(), tuple(sorted(self.app.open_field_sections)), frozendict(self.app.chosen_tabs))
        return (*shared, self.cursor.get_place(), self.cell, moving, self.fields_depend_on())

    def fields_depend_on(self):
        """Return what else a page's fields are built from, outside the set and the page's cursor: nothing, unless a page says."""
        return ()

    # The key is asked of the page, so that a page of its own kind can say it keeps nothing, as the wizard does.
    @cached_while(lambda page: page.fields_state(), said=lambda fields: fields_said(fields))
    def every_field(self):
        """Return the page's fields with the sections every page of its kind shares put after them, before the page's buttons, which always come last."""
        fields = self.fields()
        shared = self.shared_sections()
        if not shared:
            return fields
        first_button = page_buttons_start(fields)
        return [*fields[:first_button], *shared, *fields[first_button:]]

    def text_field(self, *, label, current, set_text):
        """A field for text like the title: current() reads it, and set_text(text) stores it, blank text clearing it."""
        return TextField(label=label, page=self, current=current, set_text=set_text, blank=setlist.NO_TEXT)

    def setting_number_field(self, *, label, holder, name, shown=None, in_effect=None, start=None, typed=None, clear_what=None):
        """A field for a whole number that is a setting of something in the set, by the setting's file name.

        The range is the setting's own, said once where the setting is described, and the number is stored through
        the document, which the holder checks; Bksp leaves the setting out. in_effect is the number shown and stepped
        from where that is not the number written, as a track's accent is its default until one is set.
        """
        described = holder.SETTINGS[name]

        def store(number):
            self.document().set_setting(holder=holder, name=name, value=number)
        return NumberField(
            page=self, label=label, number=holder.get_written(name) if in_effect is None else in_effect, start=start, shown=shown, typed=typed,
            lowest=described.get_lowest(), highest=described.get_highest(), set=store, clear=lambda: store(None), clear_what=clear_what,
        )

    def page_keys(self):
        return []

    def remarks(self, width):
        """Return lines to show under the settings."""
        return []

    def shown_fields(self):
        """Return the fields that show: every one, except those after a closed section's heading, up to the next heading; a page's buttons always show."""
        shown = []
        open_now = True
        for field in self.every_field():
            if field.IS_TAB_BOX:
                shown.append(TabRow(label=field.label, value=functools.partial(str, drawing.NOTHING)))
                shown += field.tabs[self.chosen_tab(field)].every_field()
            elif isinstance(field, Heading):
                shown.append(field)
                open_now = self.is_open(field)
            elif open_now or isinstance(field, Button):
                shown.append(field)
        return shown

    def every_setting(self):
        """Return every field of the page, those in every tab of its box among them, as a search for a field by its label wants."""
        fields = []
        for field in self.every_field():
            if field.IS_TAB_BOX:
                for tab in field.tabs:
                    fields += tab.every_field()
            else:
                fields.append(field)
        return fields

    def tab_box(self):
        """Return the page's tab box, or None where it has none."""
        return next((field for field in self.every_field() if field.IS_TAB_BOX), None)

    def chosen_tab(self, box):
        """Return the place of the tab the box shows: the one the page's kind last showed this session, else the first."""
        return box.tab_named(self.app.chosen_tabs.get(type(self).__name__))

    def step_tab(self, direction):
        """Choose the tab before or after the chosen one, stopping at the first and the last."""
        box = self.tab_box()
        place = max(min(self.chosen_tab(box) + direction, len(box.tabs) - 1), 0)
        self.app.chosen_tabs[type(self).__name__] = box.tabs[place].label

    def go_to_tabs(self):
        """Put the cursor on the row of tabs."""
        self.cursor.set_place(self.box_place())

    def go_into_tab(self):
        """Put the cursor on the chosen tab's first field, from the row of tabs."""
        if self.box_field_count():
            self.cursor.set_place(self.box_place() + 1)

    def box_keys(self, row):
        """Return the keys of a page with a tab box, only those that do something where the cursor is: on the row of tabs, Tab
        into the box; inside it, Tab to the row, PgUp and PgDn to the tab before or after, and Left and Right to the column
        beside, where the band has one."""
        if self.cursor.get_place() == self.box_place():
            return [self.bind(self.KEYS.INTO_TAB, action=self.go_into_tab)]
        keys = [self.bind(self.KEYS.TO_TABS, action=self.go_to_tabs)]
        if not self.in_box():
            return keys
        keys.append(self.bind(self.KEYS.TAB_PAGES, action=self.page_through_tabs))
        here = self.cursor.get_place() - self.box_place() - 1
        if not isinstance(row, Cells) and tab_box_nodes.has_columns_beside(spots=self.box_spots(), here=here):
            keys.append(self.bind(self.KEYS.ACROSS, action=self.move_across))
        return keys

    def page_through_tabs(self, direction):
        """Choose the tab before or after from inside the box, the cursor going to the field standing where it stood, or to the
        row of tabs where the tab chosen has no fields."""
        row = self.box_place()
        spot = self.box_spots()[self.cursor.get_place() - row - 1]
        self.step_tab(direction)
        if not self.box_field_count():
            self.cursor.set_place(row)
            return
        self.cursor.set_place(row + 1 + tab_box_nodes.spot_like(spots=self.box_spots(), spot=spot))

    def is_open(self, heading):
        # A heading that starts open is closed by the same toggle that opens another.
        return (heading.label in self.app.open_field_sections) != heading.starts_open

    def heading(self, *, label, is_set, said=None, starts_open=False):
        """Return a section's heading, closed until opened, or open until closed, and remembered for the session; said() is what it shows after its name, where that is not the mark of a value inside."""
        return Heading(label=label, is_set=is_set, toggle=lambda: self.toggle_section(label), said=said, starts_open=starts_open)

    def heading_over_cursor(self):
        """Return the label of the heading the cursor is on or under, or None where the cursor is above every heading."""
        over = [field for field in self.shown_fields()[:self.cursor.get_place() + 1] if isinstance(field, Heading)]
        return over[-1].label if over else None

    def toggle_section(self, label):
        self.app.open_field_sections ^= {label}

    def jump_section(self, direction):
        """Move the cursor to the next section's heading, or the one before, staying put past the last or the first."""
        places = [place for place, field in enumerate(self.shown_fields()) if isinstance(field, Heading)]
        ahead = [place for place in places if place > self.cursor.get_place()] if direction == key_table.STEP_FORWARD else [place for place in places if place < self.cursor.get_place()]
        if ahead:
            self.cursor.set_place(ahead[0] if direction == key_table.STEP_FORWARD else ahead[-1])

    def ends_a_list(self, field):
        """Return whether a field is the last row of a list among the settings, which leaves a blank line after it. No field is, unless the page says so."""
        return False

    def field(self):
        fields = self.shown_fields()
        self.cursor.set_place(max(min(self.cursor.get_place(), len(fields) - 1), 0))
        return fields[self.cursor.get_place()] if fields else None

    def under_cursor(self):
        """Return the label of the field or the button the cursor is on."""
        field = self.field()
        return field.label if field else None

    def closed_heading_over(self, label):
        """Return the heading of the closed section a field is in, by the field's label, or raise NoSuchPlace where the page has no such field.

        A page that builds a section's fields only once the section is open cannot say which closed section holds
        a field, so there the last closed section is the one opened, and the next asking finds the field or opens the one before.
        """
        heading = None
        closed = []
        for field in self.every_field():
            if isinstance(field, Heading):
                heading = field
                if not self.is_open(field):
                    closed.append(field)
            if field.label == label and heading is not None:
                return heading
        if not closed:
            raise NoSuchPlace(screen=self, target=label)
        return closed[-1]

    def key_toward(self, target):
        """Return the key that brings the cursor nearer the field or the button with a label, or None when it is on it."""
        return FormNavigator(self).key_toward(target)

    def move_cursor(self, name):
        """Move with Up or Down through the form, as the navigator goes."""
        return FormNavigator(self).move_cursor(name)

    def move_across(self, direction):
        """Move with Left or Right inside the tab box, to the field beside in the column to that side."""
        return FormNavigator(self).move_across(direction)

    def box_place(self):
        """Return the place of the row of tabs among the fields shown, or None on a page with no tab box."""
        return FormNavigator(self).box_place()

    def box_field_count(self):
        """Return how many fields the chosen tab shows."""
        return FormNavigator(self).box_field_count()

    def in_box(self):
        """Return whether the cursor is on a field inside the tab box, not its row of tabs."""
        return FormNavigator(self).in_box()

    def box_spots(self):
        """Return where each field of the chosen tab is drawn, as the box was last drawn."""
        box = self.tab_box()
        return tab_box_drawing.spots_of(page=self, tab=box.tabs[self.chosen_tab(box)], width=self.box_width)

    def buttons_stacked(self):
        """Return whether the page's buttons were last drawn one under another, a row of them being wider than the page."""
        return getattr(self, 'stacked_buttons', False)

    def cell_field(self):
        """Return what the keys act on: the field under the cursor, or, in a row of cells, the cell the cursor is on."""
        field = self.field()
        if not isinstance(field, Cells):
            return field
        self.cell = max(min(self.cell, len(field.cells) - 1), 0)
        return field.cells[self.cell]

    def move_along_cells(self, name):
        """Move between the cells of a row with Left and Right, stopping at both ends."""
        self.cell = moves.moved(place=self.cell, name=name, count=len(self.field().cells))

    def first_button_place(self):
        """Return the place of the page's first button among the fields shown, or how many fields show when there's none."""
        return FormNavigator(self).first_button_place()

    def move_along_buttons(self, name):
        """Move along the row of buttons with Left and Right, stopping at both ends."""
        return FormNavigator(self).move_along_buttons(name)

    def remember_place(self):
        field = self.field()
        return None if field is None else field.label

    def restore_place(self, place):
        """Put the cursor back on the field with the same label, since an undo can add or remove fields above it."""
        labels = [field.label for field in self.shown_fields()]
        if place in labels:
            self.cursor.set_place(labels.index(place))

    def body(self, *, width, height):
        """Return the page's lines, as SettingsPageDrawing draws them: its settings, its buttons and its remarks."""
        return SettingsPageDrawing(self).body(width=width, height=height)

    def keys(self):
        result = [self.bind(self.KEYS.SELECT, action=self.move_cursor, wants_key=True)]
        row = self.field()
        if row is not None:
            result += row.row_keys(self)
        field = self.cell_field()
        if field is not None:
            result += field.keys(self)
        name = next((item for item in self.every_field() if isinstance(item, NameField)), None)
        if name is not None:
            result.append(self.bind(self.KEYS.RENAME, action=name.rename))
        if self.cursor.get_place() >= self.first_button_place() and field is not None and not self.buttons_stacked():
            result.append(self.bind(self.KEYS.ALONG_BUTTONS, action=self.move_along_buttons, wants_key=True))
        if self.tab_box() is not None:
            result += self.box_keys(row)
        if any(isinstance(item, Heading) for item in self.every_field()) and not self.in_box():
            result.append(self.bind(self.KEYS.SECTION, action=self.jump_section))
        result += self.page_keys()
        return [self.bind(self.KEYS.BACK, action=self.go_back), *result]

    def button(self, *, binding, label, action):
        """Return a button that runs one of the keys that work everywhere on Enter, labelled as the main screen labels it and showing the key's name."""
        return Button(label=label, key_name=binding.name, enter=action, enter_what=binding.what)

    # Common kinds of setting.

    def ask_number(self, *, title, value, then, low=None, high=None):
        def answered(text):
            try:
                number = int(text.strip())
            except ValueError:
                self.refuse(errors.ERR_TYPED_NOT_AN_INTEGER.format(text=text))
                return
            if (low is not None and number < low) or (high is not None and number > high):
                self.refuse(errors.ERR_OUT_OF_RANGE.format(number=number, low=low, high=high))
                return
            then(number)
        self.ask_text(title=title, value=value, then=answered)
