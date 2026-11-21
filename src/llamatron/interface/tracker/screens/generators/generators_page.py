# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Generators page: every generator of the set under a heading for its type, the types sorted by name and the generators
sorted under each, always, so that nothing here moves or sorts. A heading opens and closes its type. Enter edits a generator,
A adds one of a type asked for, N renames, C copies and Bksp deletes once nothing uses it."""

from typing import NamedTuple

from llamatron.interface.tracker import drawing, key_table, keybindings, themes
from llamatron.interface.tracker.cursor import Cursor
from llamatron.interface.tracker.drawing import Align, Style
from llamatron.interface.tracker.screens.generators import generator_pages
from llamatron.interface.tracker.screens.generators.generator_pages import generator_page_of_kind, generator_type_dialog
from llamatron.interface.tracker.screens.shared.list_page import ListPage
from llamatron.model.objects.naming import name_order, suggested_word
from llamatron.model.schema import generator_plugins
from llamatron.user_strings import help as help_text, labels, legends, marks, messages

# The kinds of row the page lists: a generator, a type's heading, and the row that adds a generator.
GENERATOR = 'generator'
HEADING = 'heading'
NEW_GENERATOR = 'new generator'
# How far a type's generators stand in from its heading.
INDENT = '    '
USED_WIDTH = 4


class Listed(NamedTuple):
    """What a row of the Generators page is: the row's kind, the generators' kind, and the generator's name on a generator's row."""

    row: str
    kind: object = None
    name: object = None


class GeneratorsPage(ListPage):

    """The Generators page: every kind of generator under its group, each opening the list of its kind."""

    THEME = themes.GENERATORS
    KEYS = keybindings.GeneratorsPage
    crumbs = (labels.Crumb.GENERATORS,)
    HELP = help_text.HELP_GENERATORS_PAGE
    columns = ((labels.Column.SELECT_ANY_GENERATOR, None, Align.LEFT), (labels.Column.USED, USED_WIDTH, Align.RIGHT))
    NAME_COLUMN_WIDTH = ListPage.NAME_COLUMN_WIDTH + len(INDENT)

    def __init__(self, holder):
        super().__init__(holder)
        # The page opens with the cursor on the first generator showing, so that ENTER edits at once, or on the first heading when every type is closed.
        self.cursor = Cursor(place=self.first_generator_place())

    # The rows.

    def can_add(self):
        """Return that the page has no + row of the list's own: the row that adds is a row the page lists, since ENTER on a heading opens and closes it."""
        return False

    def generators(self):
        """Return every generator as (kind, name), in the page's order: by the type's name, then by the generator's own."""
        return [(kind, name) for kind in self.kinds() for name in self.names_of_kind(kind)]

    def kinds(self):
        """Return the kinds of generator the set has any of, sorted by what the tracker calls each."""
        held = {kind for kind, _ in self.document().get_setlist().ordered_generators()}
        return sorted(held, key=lambda kind: name_order(generator_page_of_kind(kind).label))

    def names_of_kind(self, kind):
        return sorted(self.document().names_of(generator_plugins.listed_sections()[kind]), key=name_order)

    def is_closed(self, kind):
        """Return whether a type is closed, as every type is until opened; the set keeps which are open, so that the page comes back as it was left."""
        return not self.document().get_page_memory().is_generator_type_open(kind)

    def rows_depend_on(self):
        """Return what the rows depend on besides the set: which types are closed, and a search, which looks inside every type."""
        return (tuple(self.is_closed(kind) for kind in self.kinds()), self.searching)

    def rows(self):
        rows = []
        for kind in self.kinds():
            rows += self.kind_rows(kind)
        rows.append((Listed(NEW_GENERATOR), self.one_cell(marks.MSG_ADD_ROW_MARK)))
        return rows

    def kind_rows(self, kind):
        """Return a type's rows: its heading, and while it is open, or a search looks inside it, its generators."""
        names = self.names_of_kind(kind)
        closed = self.is_closed(kind) and not self.searching
        heading = labels.MSG_GROUP_HEADING.format(mark=marks.MSG_SECTION_CLOSED_MARK if closed else marks.MSG_SECTION_OPEN_MARK, name=generator_page_of_kind(kind).label, count=len(names))
        rows = [(Listed(HEADING, kind), self.one_cell(heading))]
        if not closed:
            rows += [(Listed(GENERATOR, kind, name), [INDENT + name, len(self.uses(kind=kind, name=name))]) for name in names]
        return rows

    def one_cell(self, text):
        """Return the cells of a row that holds only its first."""
        return [text, *[drawing.NOTHING] * (len(self.columns) - 1)]

    def row_style(self, what):
        return Style.BOLD if what.row == HEADING else Style.PLAIN

    def first_generator_place(self):
        """Return the place of the first generator showing, or the top row when none shows."""
        return next((place for place, (what, _) in enumerate(self.remembered_rows()) if what.row == GENERATOR), 0)

    def listed(self):
        """Return what the cursor is on, which is never nothing, since the page always ends with the row that adds."""
        self.clamp()
        return self.remembered_rows()[self.cursor.get_place()][0]

    def current(self):
        """Return the generator the cursor is on as (kind, name), or nothing on a heading or the row that adds."""
        listed = self.listed()
        return (listed.kind, listed.name) if listed.row == GENERATOR else None

    def remember_place(self):
        """Return what the cursor is on, a heading included, for a redraw to find again."""
        return self.listed()

    def uses(self, *, kind, name):
        return self.document().uses(section=generator_plugins.listed_sections()[kind], name=name)

    def put_cursor_on(self, *, kind, name):
        """Put the cursor on a generator's row, opening its type if the type is closed."""
        self.document().show_generator_type(kind=kind, opened=True)
        self.restore_place(Listed(GENERATOR, kind, name))

    # The keys, by what the cursor is on.

    def keys(self):
        listed = self.listed()
        result = [self.bind(self.KEYS.BACK, action=self.go_back), *self.move_keys()]
        if listed.row == GENERATOR:
            result += [
                self.bind(self.KEYS.EDIT, action=self.open_item), self.bind(self.KEYS.ADD, action=self.add), self.bind(self.KEYS.RENAME, action=self.rename),
                self.bind(self.KEYS.COPY, action=self.copy), self.bind(self.KEYS.DELETE, action=self.delete),
            ]
        elif listed.row == HEADING:
            result += [self.bind(self.KEYS.TOGGLE_TYPE, action=self.toggle_type), self.bind(self.KEYS.ADD, action=self.add)]
        else:
            result += [self.bind(self.KEYS.ADD_HERE, action=self.add), self.bind(self.KEYS.ADD, action=self.add)]
        return [*result, self.bind(self.KEYS.NEXT_TYPE, action=self.jump_type)]

    def toggle_type(self):
        """Open or close the type whose heading the cursor is on, which the set keeps."""
        kind = self.listed().kind
        self.document().show_generator_type(kind=kind, opened=self.is_closed(kind))

    def jump_type(self, direction):
        """Move the cursor to the next type's heading, or the one before, staying put past the last or the first."""
        places = [place for place, (what, _) in enumerate(self.remembered_rows()) if what.row == HEADING]
        ahead = [place for place in places if place > self.cursor.get_place()] if direction == key_table.STEP_FORWARD else [place for place in places if place < self.cursor.get_place()]
        if ahead:
            self.cursor.set_place(ahead[0] if direction == key_table.STEP_FORWARD else ahead[-1])

    def open_item(self):
        kind, name = self.current()
        self.open_editor(section=generator_page_of_kind(kind).section, name=name)

    def add(self):
        """Ask which type of generator to make, make one named after the type, numbered, put the cursor on it and open it."""
        listings = list(generator_pages.LISTED_PAGES.values())

        def chosen(place):
            listing = listings[place]
            name = self.document().new_name(section=listing.section, word=suggested_word(listing.label))
            self.document().add_generator(section=listing.section, name=name)
            self.put_cursor_on(kind=listing.kind, name=name)
            self.open_editor(section=listing.section, name=name)
        self.ask(dialog=generator_type_dialog(opened=self.holder.open_generator_groups, listings=generator_pages.LISTED_PAGES), then=chosen)

    def rename(self):
        kind, name = self.current()
        section = generator_plugins.listed_sections()[kind]

        def renamed(new):
            self.document().rename_named(section=section, old=name, new=new)
            self.put_cursor_on(kind=kind, name=new)
        self.ask_name(title=messages.MSG_RENAME_GENERATOR_PROMPT.format(label=generator_page_of_kind(kind).label), value=name, taken=self.document().names_of(section), then=renamed)

    def copy(self):
        """Copy the selected generator, say what the copy is called and put the cursor on it."""
        kind, name = self.current()
        new = self.document().copy_named(section=generator_plugins.listed_sections()[kind], name=name)
        self.say(messages.MSG_COPIED_TO.format(name=new))
        self.put_cursor_on(kind=kind, name=new)

    def delete(self):
        """Delete the selected generator after asking, saying which chains and lists it is taken out of."""
        kind, name = self.current()
        what = legends.MSG_GENERATOR_WHAT.format(label=generator_page_of_kind(kind).label, name=name)
        self.delete_taking_out(what=what, uses=self.uses(kind=kind, name=name), delete=lambda: self.document().delete_generator(section=generator_plugins.listed_sections()[kind], name=name))
