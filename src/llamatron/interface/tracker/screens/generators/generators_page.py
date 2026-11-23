# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Generators page: every generator of the set under a heading for its type, the types sorted by name and the generators
sorted under each, always, so that nothing here moves or sorts. A heading opens and closes its type. Enter edits a generator,
A adds one of a type asked for, N renames, C copies and Bksp deletes once nothing uses it."""


from llamatron.interface.forms.cursor import Cursor
from llamatron.interface.pages import generators as generators_values
from llamatron.interface.pages.generators import GeneratorsPresenter, Listed
from llamatron.interface.tracker import key_table, keybindings, themes
from llamatron.interface.tracker.drawing import Style
from llamatron.interface.tracker.screens.generators import generator_pages
from llamatron.interface.tracker.screens.generators.generator_pages import generator_page_of_kind, generator_type_dialog
from llamatron.interface.tracker.screens.shared.list_page import ListPage
from llamatron.model.objects.naming import suggested_word
from llamatron.model.schema import generator_plugins
from llamatron.user_strings import help as help_text, labels, legends, messages

class GeneratorsPage(ListPage):

    """The Generators page: every kind of generator under its group, each opening the list of its kind."""

    THEME = themes.GENERATORS
    KEYS = keybindings.GeneratorsPage
    crumbs = (labels.Crumb.GENERATORS,)
    HELP = help_text.HELP_GENERATORS_PAGE
    columns = GeneratorsPresenter.COLUMNS
    NAME_COLUMN_WIDTH = ListPage.NAME_COLUMN_WIDTH + len(generators_values.INDENT)

    def __init__(self, holder):
        super().__init__(holder)
        # The page opens with the cursor on the first generator showing, so that ENTER edits at once, or on the first heading when every type is closed.
        self.cursor = Cursor(place=self.first_generator_place())

    # The rows.

    def can_add(self):
        """Return that the page has no + row of the list's own: the row that adds is a row the page lists, since ENTER on a heading opens and closes it."""
        return False

    def presenter(self):
        return GeneratorsPresenter(document=self.document())

    def generators(self):
        """Return every generator as (kind, name), in the page's order: by the type's name, then by the generator's own."""
        presenter = self.presenter()
        return [(kind, name) for kind in presenter.kinds() for name in presenter.names_of_kind(kind)]

    def kinds(self):
        return self.presenter().kinds()

    def is_closed(self, kind):
        return self.presenter().is_closed(kind)

    def rows_depend_on(self):
        """Return what the rows depend on besides the set: which types are closed, and a search, which looks inside every type."""
        return (tuple(self.is_closed(kind) for kind in self.kinds()), self.searching)

    def rows(self):
        return self.presenter().rows(searching=self.searching)

    def row_style(self, what):
        return Style.BOLD if what.row == generators_values.HEADING else Style.PLAIN

    def first_generator_place(self):
        """Return the place of the first generator showing, or the top row when none shows."""
        return next((place for place, (what, _) in enumerate(self.remembered_rows()) if what.row == generators_values.GENERATOR), 0)

    def listed(self):
        """Return what the cursor is on, which is never nothing, since the page always ends with the row that adds."""
        self.clamp()
        return self.remembered_rows()[self.cursor.get_place()][0]

    def current(self):
        """Return the generator the cursor is on as (kind, name), or nothing on a heading or the row that adds."""
        listed = self.listed()
        return (listed.kind, listed.name) if listed.row == generators_values.GENERATOR else None

    def remember_place(self):
        """Return what the cursor is on, a heading included, for a redraw to find again."""
        return self.listed()

    def uses(self, *, kind, name):
        return self.presenter().uses(kind=kind, name=name)

    def put_cursor_on(self, *, kind, name):
        """Put the cursor on a generator's row, opening its type if the type is closed."""
        self.document().show_generator_type(kind=kind, opened=True)
        self.restore_place(Listed(generators_values.GENERATOR, kind, name))

    # The keys, by what the cursor is on.

    def keys(self):
        listed = self.listed()
        result = [self.bind(self.KEYS.BACK, action=self.go_back), *self.move_keys()]
        if listed.row == generators_values.GENERATOR:
            result += [
                self.bind(self.KEYS.EDIT, action=self.open_item), self.bind(self.KEYS.ADD, action=self.add), self.bind(self.KEYS.RENAME, action=self.rename),
                self.bind(self.KEYS.COPY, action=self.copy), self.bind(self.KEYS.DELETE, action=self.delete),
            ]
        elif listed.row == generators_values.HEADING:
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
        places = [place for place, (what, _) in enumerate(self.remembered_rows()) if what.row == generators_values.HEADING]
        ahead = [place for place in places if place > self.cursor.get_place()] if direction == key_table.STEP_FORWARD else [place for place in places if place < self.cursor.get_place()]
        if ahead:
            self.cursor.set_place(ahead[0] if direction == key_table.STEP_FORWARD else ahead[-1])

    def open_item(self):
        kind, name = self.current()
        self.open_place(GeneratorsPresenter.place_of(kind=kind, name=name))

    def add(self):
        """Ask which type of generator to make, make one named after the type, numbered, put the cursor on it and open it."""
        listings = list(generator_pages.LISTED_PAGES.values())

        def chosen(place):
            listing = listings[place]
            name = self.document().new_name(section=listing.section, word=suggested_word(listing.label))
            self.document().add_generator(section=listing.section, name=name)
            self.put_cursor_on(kind=listing.kind, name=name)
            self.open_editor(section=listing.section, name=name)
        self.ask(dialog=generator_type_dialog(listings=generator_pages.LISTED_PAGES), then=chosen)

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
