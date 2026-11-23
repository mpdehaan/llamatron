# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Field page: settings in a column, where the keys depend on the setting under the cursor."""

import functools
from rich.text import Text

from llamatron.interface.tracker import drawing, key_table, keybindings
from llamatron.interface.tracker.components.button_row import button_row
from llamatron.interface.tracker.cursor import Cursor, key_between, NoSuchPlace
from llamatron.interface.tracker.drawing import cursor_mark, Style
from llamatron.interface.tracker.key_table import cursor_moved
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.shared import tab_box as tab_box_values
from llamatron.interface.tracker.screens.shared.field import Button, Cells, Field, Heading, NameField, NumberField
from llamatron.interface.tracker.screens.shared.page import Page
from llamatron.interface.tracker.screens.shared.tab_box import box_lines, TabRow
from llamatron.model.objects import setlist
from llamatron.user_strings import errors, labels as labels_text, legends, marks


# How wide a tab box is drawn where a page is drawn with no width, as a test draws it.
BOX_WIDTH = 80


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
        self.box_width = BOX_WIDTH

    def fields(self):
        return []

    def shared_sections(self):
        """Return the sections every page of its kind shows after its own fields, such as a generator's statements about the registers; none unless a page says."""
        return []

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
        return Field(label=label, value=current, adjust=None, enter=lambda: self.ask_text(title=label, value=current(), then=set_text), enter_what=legends.What.EDIT,
                     clear=lambda: set_text(setlist.NO_TEXT), clear_what=legends.What.CLEAR)

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
        if not isinstance(row, Cells) and tab_box_values.has_columns_beside(spots=self.box_spots(), here=here):
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
        self.cursor.set_place(row + 1 + tab_box_values.spot_like(spots=self.box_spots(), spot=spot))

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
        """Return the key that brings the cursor nearer the field or the button with a label, or None when the cursor is on it.

        A field in a closed section is reached as a person reaches it: the way to its section's heading, then the key that opens the section.
        Down from the last field reaches the buttons, which Left and Right go along, or Up and Down where they are stacked.
        """
        labels = [field.label for field in self.shown_fields()]
        box = self.tab_box()
        if target not in labels and box is not None and box.place_holding(target) is not None:
            return self.key_toward(box.label) or _key_toward_tab(here=self.chosen_tab(box), there=box.place_holding(target))
        if target not in labels:
            return self.key_toward(self.closed_heading_over(target).label) or Key.ENTER
        there = labels.index(target)
        here = self.cursor.get_place()
        row = self.box_place()
        if self.in_box() and row < there <= row + self.box_field_count():
            return self.key_inside_box(here=here - row - 1, there=there - row - 1)
        first_button = self.first_button_place()
        if here < first_button or there < first_button or self.buttons_stacked():
            return key_between(here=here, there=there)
        return key_between(here=here, there=there, back=Key.LEFT, forward=Key.RIGHT)

    def key_inside_box(self, *, here, there):
        """Return the key that brings the cursor nearer a field of the chosen tab from another: along a column, across a band, or
        toward the band that holds it."""
        spots = self.box_spots()
        start = spots[here]
        end = spots[there]
        if start.band == end.band and start.column == end.column:
            return key_between(here=start.line, there=end.line)
        if start.band == end.band:
            return _key_across(here=start.column, there=end.column)
        return key_between(here=start.band, there=end.band)

    def move_cursor(self, name):
        """Move between the fields with Up and Down, Down from the last field reaching the row of buttons and Up from any button
        going back to the last field; Down on the buttons stays. Inside the tab box, Up and Down keep to a column."""
        fields = self.shown_fields()
        if not fields:
            return
        # A row is come to at its first cell.
        self.cell = 0
        if self.box_place() is not None:
            self.move_with_box(name)
            return
        self.move_in_order(name)

    def move_with_box(self, name):
        """Move with Up or Down on a page with a tab box: inside it, along a column and out at its head or foot; from under it, Up
        comes in at the foot of its first column; elsewhere, as on any page."""
        row = self.box_place()
        count = self.box_field_count()
        place = self.cursor.get_place()
        if row < place <= row + count:
            self.move_inside_box(name=name, row=row, here=place - row - 1)
            return
        self.move_in_order(name)
        if name == Key.UP and place > row + count and self.cursor.get_place() == row + count:
            self.cursor.set_place(row + 1 + tab_box_values.spot_from_below(self.box_spots()))

    def move_inside_box(self, *, name, row, here):
        """Move with Up or Down from the field at a place among the chosen tab's: to the field it leads to, the row of tabs, or
        what is under the box, staying put where nothing is."""
        spots = self.box_spots()
        if name == Key.DOWN:
            there = tab_box_values.spot_below(spots=spots, here=here)
        else:
            there = tab_box_values.spot_above(spots=spots, here=here)
        if there == tab_box_values.ON_TAB_ROW:
            self.cursor.set_place(row)
        elif there == tab_box_values.BELOW_BOX:
            below = row + len(spots) + 1
            if below < len(self.shown_fields()):
                self.cursor.set_place(below)
        else:
            self.cursor.set_place(row + 1 + there)

    def move_across(self, direction):
        """Move with Left or Right inside the tab box, to the field beside in the column to that side, stopping at the sides."""
        row = self.box_place()
        here = self.cursor.get_place() - row - 1
        self.cursor.set_place(row + 1 + tab_box_values.spot_beside(spots=self.box_spots(), here=here, direction=direction))

    def box_place(self):
        """Return the place of the row of tabs among the fields shown, or None on a page with no tab box."""
        for place, field in enumerate(self.shown_fields()):
            if field.IS_TAB_ROW:
                return place
        return None

    def box_field_count(self):
        """Return how many fields the chosen tab shows."""
        box = self.tab_box()
        return len(box.tabs[self.chosen_tab(box)].every_field())

    def in_box(self):
        """Return whether the cursor is on a field inside the tab box, not its row of tabs."""
        row = self.box_place()
        return row is not None and row < self.cursor.get_place() <= row + self.box_field_count()

    def box_spots(self):
        """Return where each field of the chosen tab is drawn, as the box was last drawn."""
        box = self.tab_box()
        return tab_box_values.spots_of(page=self, tab=box.tabs[self.chosen_tab(box)], width=self.box_width)

    def move_in_order(self, name):
        """Move with Up or Down through the fields in order, then the buttons."""
        fields = self.shown_fields()
        first_button = self.first_button_place()
        if self.buttons_stacked():
            # Buttons too wide for one row stand one under another, and Up and Down go through them as through the fields.
            self.cursor.move(name=name, count=len(fields))
            return
        if self.cursor.get_place() >= first_button:
            if name == Key.UP and first_button:
                self.cursor.set_place(first_button - 1)
            return
        self.cursor.move(name=name, count=min(first_button + 1, len(fields)))

    def buttons_stacked(self):
        """Return whether the page's buttons were last drawn one under another, a row of them being wider than the page."""
        return getattr(self, 'stacked_buttons', False)

    def row_of_buttons(self, *, buttons, selected, width):
        """Return the lines of the page's buttons: boxed in one row where the row fits the width, and otherwise one a line, each
        in brackets, the selected one marked and bold."""
        keys_and_names = [(button.key_name, button.label) for button in buttons]
        row = [Text(drawing.INDENT) + line for line in button_row(buttons=keys_and_names, selected=selected)]
        self.stacked_buttons = width is not None and max(line.cell_len for line in row) > width
        if not self.stacked_buttons:
            return row
        lines = []
        for place, button in enumerate(buttons):
            line = Text(no_wrap=True)
            line.append(cursor_mark(place == selected))
            line.append(marks.MSG_STACKED_BUTTON.format(name=button.label), style=Style.BOLD if place == selected else Style.PLAIN)
            lines.append(line)
        return lines

    def cell_field(self):
        """Return what the keys act on: the field under the cursor, or, in a row of cells, the cell the cursor is on."""
        field = self.field()
        if not isinstance(field, Cells):
            return field
        self.cell = max(min(self.cell, len(field.cells) - 1), 0)
        return field.cells[self.cell]

    def move_along_cells(self, name):
        """Move between the cells of a row with Left and Right, stopping at both ends."""
        self.cell = cursor_moved(place=self.cell, name=name, count=len(self.field().cells))

    def first_button_place(self):
        """Return the place of the page's first button among the fields shown, or how many fields show when there's none: after
        the chosen tab's fields, whose last may be a button of the tab's own."""
        start = page_buttons_start(self.shown_fields())
        box = self.box_place()
        if box is None:
            return start
        return max(start, box + 1 + self.box_field_count())

    def move_along_buttons(self, name):
        """Move along the row of buttons with Left and Right, stopping at both ends."""
        first_button = self.first_button_place()
        count = len(self.shown_fields()) - first_button
        self.cursor.set_place(first_button + cursor_moved(place=self.cursor.get_place() - first_button, name=name, count=count))

    def remember_place(self):
        field = self.field()
        return None if field is None else field.label

    def restore_place(self, place):
        """Put the cursor back on the field with the same label, since an undo can add or remove fields above it."""
        labels = [field.label for field in self.shown_fields()]
        if place in labels:
            self.cursor.set_place(labels.index(place))

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

    def body(self, *, width, height):
        """Return the settings after a blank line, the first section after another, then the page's buttons after one blank line, then its notes after another.

        The labels take the width of the longest of every field, shown or not, so that opening a
        section never moves the values beside them.
        """
        fields = self.shown_fields()
        self.field()
        label_width = max((len(field.get_drawn_label(self)) for field in self.every_field() if not isinstance(field, Button) and not field.IS_TAB_BOX), default=0) + 2
        cursor = self.cursor.get_place()
        lines = [Text(drawing.NOTHING)]
        selected = 0
        seen_heading = False
        first_button = self.first_button_place()
        buttons = fields[first_button:]
        inside_box = 0
        for place, field in enumerate(fields):
            if place >= first_button:
                continue
            if inside_box:
                # The chosen tab's fields are drawn with the box, by its row of tabs.
                inside_box -= 1
                continue
            if field.IS_TAB_ROW:
                inside_box, box, box_selected = self._box_at(place=place, cursor=cursor, width=width)
                if box_selected is not None:
                    selected = len(lines) + box_selected
                lines += [*box, Text(drawing.NOTHING)]
                continue
            if isinstance(field, Heading) and (not seen_heading or self.HEADINGS_APART):
                seen_heading = True
                if place:
                    lines.append(Text(drawing.NOTHING))
            here = place == cursor
            if here:
                selected = len(lines) + field.SELECTED_LINE
            lines += field.lines(page=self, here=here, label_width=label_width, width=width)
            if field.MAY_LEAVE_A_GAP and self.has_gap_after(place=place, field=field, fields=fields):
                lines.append(Text(drawing.NOTHING))
        if buttons:
            # The buttons sit in one row under the settings after a blank line, boxed as the dialogs' are.
            first_button = self.first_button_place()
            lines.append(Text(drawing.NOTHING))
            row = self.row_of_buttons(buttons=buttons, selected=cursor - first_button, width=width)
            if cursor >= first_button:
                selected = len(lines) + (cursor - first_button if self.buttons_stacked() else 1)
            lines += row
        remarks = self.remarks(width)
        if remarks:
            lines += [Text(drawing.NOTHING), *remarks]
        return self.window_of_lines(lines=lines, selected=selected, height=height)

    def _box_at(self, *, place, cursor, width):
        """Return how many of the chosen tab's fields follow the row of tabs at a place, the box's lines, and the place of the
        cursor's line among them, or None where the cursor is outside the box."""
        box = self.tab_box()
        chosen = self.chosen_tab(box)
        count = len(box.tabs[chosen].every_field())
        inside = None
        if cursor == place:
            inside = tab_box_values.ON_TAB_ROW
        elif place < cursor <= place + count:
            inside = cursor - place - 1
        self.box_width = width or BOX_WIDTH
        lines, selected = box_lines(page=self, box=box, chosen=chosen, cursor=inside, width=self.box_width)
        return count, lines, selected

    def has_gap_after(self, *, place, field, fields):
        """Return whether a blank line follows a setting: a Name that starts the page before its other settings, and the last of a list."""
        if place == 0 and field.label == labels_text.MSG_NAME_LABEL and len(fields) > 1 and not isinstance(fields[1], Button):
            return True
        return self.ends_a_list(field)

    def window_of_lines(self, *, lines, selected, height):
        """Return the lines that fit the height, scrolled so that the selected line shows, a settings page being taller than a console at times."""
        if height is None or len(lines) <= height:
            self.first_line = 0
            return lines
        first = min(max(getattr(self, 'first_line', 0), selected - height + 1), selected)
        self.first_line = max(min(first, len(lines) - height), 0)
        return lines[self.first_line:self.first_line + height]

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


def _key_toward_tab(*, here, there):
    """Return the key on the row of tabs that brings the chosen tab nearer another, by their places."""
    if there < here:
        return Key.LEFT
    return Key.RIGHT


def _key_across(*, here, there):
    """Return Left or Right, toward a column of the tab box from another."""
    if there < here:
        return Key.LEFT
    return Key.RIGHT


def page_buttons_start(fields):
    """Return the place where a page's own buttons start among its fields: the run of buttons at the end, which the page draws
    in a row below its settings, or how many fields there are when none end it. A button among a tab's columns stands before
    that run and is drawn in its tab."""
    start = len(fields)
    while start and isinstance(fields[start - 1], Button):
        start -= 1
    return start
