# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Patterns page, which lists the patterns in a tab for each group."""

from rich.text import Text
from typing import NamedTuple

from llamatron.interface.tracker import drawing, key_table, keybindings
from llamatron.interface.tracker.cursor import Cursor, key_between, place_of
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.dialogs.confirm_dialog import ConfirmDialog
from llamatron.interface.tracker.dialogs.new_pattern_dialog import NewPatternDialog
from llamatron.interface.tracker.drawing import Align, Style
from llamatron.interface.tracker.screens.shared import tab_box
from llamatron.interface.tracker.screens.shared.listening import pattern_listen_keys
from llamatron.interface.tracker.screens.shared.named_list_page import NamedListPage
from llamatron.interface.tracker.screens.shared.tab_box import Tab
from llamatron.interface.tracker.text import clock
from llamatron.interface.tracker.themes import text_style, theme_of
from llamatron.model.objects.naming import copy_name, is_taken, name_order, new_name
from llamatron.model.schema import limits
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import errors, help as help_text, labels, legends, marks, messages, names as names_text

# The kinds of row the page lists: a pattern, the + (New) row that makes a pattern in the chosen group, and the button that makes a group.
PATTERN = 'pattern'
NEW_PATTERN = 'new pattern'
NEW_GROUP = 'new group'
# The kinds of tab: a group's, the patterns in no group, which an older file's are, and the last, which makes a group.
GROUP_TAB = 'group'
UNGROUPED_TAB = 'ungrouped'
NEW_TAB = 'new'
# The group of the patterns in no group.
UNGROUPED = None
# The blank lines inside the box, above the column headings and under the last row.
INSIDE_ABOVE = 1
INSIDE_BELOW = 1


class Listed(NamedTuple):
    """What a row of the Patterns page is: its kind, and the name of its pattern or of its group."""

    kind: str
    name: object


class PatternTab(NamedTuple):
    """One tab of the Patterns page: its kind, and the group it shows on a group's tab."""

    kind: str
    group: object = None


class PatternsPage(NamedListPage):
    """Every pattern of the set in a tab of its group: a tab per group, sorted by name, then Ungrouped while a pattern is in no
    group, then + New, which holds the button that makes a group. A group's tab lists its patterns sorted by name, always, so that
    nothing here moves or sorts, and ends with + (New), which makes a pattern in the group. Tab goes between the row of tabs and
    the list, Left and Right choose a tab on the row, and PgUp and PgDn choose one from the list. Nothing can be added to
    Ungrouped: a group is made before a pattern is."""

    KEYS = keybindings.PatternsPage
    LISTED_SECTION = Section.PATTERNS
    RENAME_PROMPT = messages.MSG_RENAME_PATTERN_PROMPT
    WHAT = legends.MSG_PATTERN_WHAT
    crumbs = (labels.Crumb.PATTERNS,)
    HELP = help_text.HELP_PATTERNS_PAGE
    columns = (
        (labels.Column.SELECT_PATTERN, None, Align.LEFT), (labels.Column.TYPE, 5, Align.LEFT), (labels.Column.STEPS, 5, Align.RIGHT), (labels.Column.TIME, 6, Align.RIGHT),
        (labels.Column.USED, 4, Align.RIGHT),
    )
    NAME_COLUMN_WIDTH = limits.MAX_NAME_LENGTH

    def __init__(self, holder):
        super().__init__(holder)
        # The groups made here that hold no pattern yet. A group is only the text its patterns hold, so one with none is the page's own until a pattern is made in it.
        self.new_groups = []
        # What the cursor was on when a search began, which ESC goes back to.
        self.before_search = None
        # Whether the cursor is on the row of tabs rather than in the list.
        self.on_tabs = False
        # The page opens with the cursor on the chosen tab's first pattern, where one shows, so that ENTER edits at once, as on every list.
        self.cursor = Cursor(place=self.first_pattern_place())

    # The tabs.

    def tabs(self):
        """Return the page's tabs in order: each group's, sorted, then Ungrouped while a pattern is in no group, then + New."""
        tabs = [PatternTab(GROUP_TAB, group) for group in self.groups()]
        if self.document().get_setlist().patterns_in_group(UNGROUPED):
            tabs.append(PatternTab(UNGROUPED_TAB))
        return [*tabs, PatternTab(NEW_TAB)]

    def chosen(self):
        """Return the tab the page shows: the one chosen last this session while it still exists, else the first."""
        tabs = self.tabs()
        held = self.app.chosen_tabs.get(type(self).__name__)
        return held if held in tabs else tabs[0]

    def choose(self, tab):
        self.app.chosen_tabs[type(self).__name__] = tab

    def tab_label(self, tab):
        """Return the name a tab shows: its group's, Ungrouped, or + New."""
        if tab.kind == GROUP_TAB:
            return tab.group
        if tab.kind == UNGROUPED_TAB:
            return labels.MSG_UNGROUPED
        return labels.MSG_NEW_GROUP_TAB

    def step_tab(self, direction):
        """Choose the tab before or after the chosen one, stopping at the first and the last, the cursor going to the new tab's
        first row unless it is on the row of tabs."""
        tabs = self.tabs()
        place = max(min(tabs.index(self.chosen()) + direction, len(tabs) - 1), 0)
        self.choose(tabs[place])
        self.cursor.set_place(self.first_pattern_place())

    def go_to_tabs(self):
        self.on_tabs = True

    def go_into_tab(self):
        self.on_tabs = False
        self.cursor.set_place(self.first_pattern_place())

    # The rows.

    def can_add(self):
        """Return that the page has no + row of its own: a group's tab lists its own."""
        return False

    def groups(self):
        """Return every group's name, sorted: the ones patterns are in, and the ones made here that hold none yet."""
        held = self.document().get_setlist().get_pattern_groups()
        return sorted([*held, *(group for group in self.new_groups if group not in held)], key=name_order)

    def rows_depend_on(self):
        """Return what the rows depend on besides the set: the chosen tab, the groups made here, and a search, which looks inside every group."""
        return (self.chosen(), tuple(self.new_groups), self.searching)

    def rows(self):
        """Return the chosen tab's rows, or, while a search looks inside every group, every pattern, group by group."""
        if self.searching:
            rows = []
            for tab in self.tabs():
                rows += self.pattern_rows(tab.group)
            return rows
        tab = self.chosen()
        if tab.kind == NEW_TAB:
            return [(Listed(NEW_GROUP, None), self.one_cell(labels.MSG_NEW_GROUP_BUTTON))]
        rows = self.pattern_rows(tab.group)
        if tab.kind == GROUP_TAB:
            rows.append((Listed(NEW_PATTERN, tab.group), self.one_cell(marks.MSG_NEW_ROW)))
        return rows

    def pattern_rows(self, group):
        """Return the rows of a group's patterns, sorted by name."""
        document = self.document()
        names = document.get_setlist().patterns_in_group(group)
        return [(Listed(PATTERN, name), self.row_of(name=name, pattern=document.song().get_setlist().get_pattern(name), document=document)) for name in names]

    def one_cell(self, text):
        """Return the cells of a row that holds only its first."""
        return [text, *[drawing.NOTHING] * (len(self.columns) - 1)]

    def row_of(self, *, name, pattern, document):
        kind = labels.MSG_DRUM_KIND if pattern.is_drum() else labels.MSG_NOTES_KIND
        return [name, kind, pattern.get_steps(), clock(document.lengths().pattern_seconds(name)), len(self.uses(name))]

    def row_style(self, what):
        """Return a button in the page's theme colour, so that it isn't taken for a pattern."""
        if what.kind in (NEW_PATTERN, NEW_GROUP):
            return text_style(theme_of(Section.PATTERNS))
        return Style.PLAIN

    def row_selected(self, place):
        """Return whether a row is the cursor's: never while the cursor is on the row of tabs."""
        return not self.on_tabs and super().row_selected(place)

    def body(self, *, width, height):
        """Return the row of tabs over a box holding the chosen tab's list, as a settings page's tab box is drawn."""
        rows = super().body(width=tab_box.inner_width(width), height=height - tab_box.TAB_ROW_LINES - INSIDE_ABOVE - INSIDE_BELOW - 1)
        lines = [Text(drawing.NOTHING)] * INSIDE_ABOVE + rows + [Text(drawing.NOTHING)] * INSIDE_BELOW
        tabs = [Tab(label=self.tab_label(tab)) for tab in self.tabs()]
        return tab_box.boxed_tabs(tabs=tabs, chosen=self.tabs().index(self.chosen()), width=width, here=self.on_tabs, lines=lines)

    def first_pattern_place(self):
        """Return the place of the chosen tab's first pattern, or its top row when it has none."""
        return next((place for place, (what, _) in enumerate(self.remembered_rows()) if what.kind == PATTERN), 0)

    def current(self):
        """Return the name of the pattern the cursor is on, or nothing on a button or the row of tabs, as a list answers on its + row."""
        if self.on_tabs:
            return None
        listed = self.listed()
        return listed.name if listed.kind == PATTERN else None

    def under_cursor(self):
        """Return what the cursor is on: a pattern or a button, as a Listed."""
        return self.listed()

    def key_toward(self, target):
        """Return the key that brings the cursor nearer a row of the chosen tab, named by what it lists (a Listed) or, for a pattern, by the pattern's name; None when the cursor is on it."""
        rows = [what for what, _ in self.remembered_rows()] if isinstance(target, Listed) else self.row_names()
        return key_between(here=self.cursor.get_place(), there=place_of(screen=self, names=rows, target=target))

    def row_names(self):
        """Return each row's pattern's name, in the rows' order, with nothing for a button."""
        return [what.name if what.kind == PATTERN else None for what, _ in self.remembered_rows()]

    def listed(self):
        """Return what the cursor's row is, which is never nothing, since every tab holds a row."""
        self.clamp()
        return self.remembered_rows()[self.cursor.get_place()][0]

    def remember_place(self):
        """Return what the cursor is on, a button included, for a redraw to find again."""
        return self.listed()

    def group_under_cursor(self):
        """Return the group of the chosen tab, or nothing on Ungrouped and + New."""
        return self.chosen().group

    def put_cursor_on_row(self, listed):
        rows = [what for what, _ in self.remembered_rows()]
        if listed in rows:
            self.cursor.set_place(rows.index(listed))
        self.clamp()

    def put_cursor_on(self, name):
        """Put the cursor on a pattern's row, choosing its group's tab."""
        group = self.document().pattern_group(name)
        self.choose(PatternTab(GROUP_TAB, group) if group is not UNGROUPED else PatternTab(UNGROUPED_TAB))
        self.on_tabs = False
        self.put_cursor_on_row(Listed(PATTERN, name))

    def move_cursor(self, name):
        """Move with Up and Down through the list, Up from its first row going to the row of tabs and Down from there coming back."""
        matches = self.matches()
        if self.on_tabs:
            if name not in key_table.BACK_KEYS and matches:
                self.on_tabs = False
                self.cursor.set_place(matches[0])
            return
        if name in key_table.BACK_KEYS and not self.searching and matches and self.cursor.get_place() == matches[0]:
            self.on_tabs = True
            return
        super().move_cursor(name)

    # The keys, by where the cursor is.

    def keys(self):
        result = [self.bind(self.KEYS.BACK, action=self.go_back), *self.move_keys()]
        if self.on_tabs:
            return [*result, *self.tab_row_keys(), self.bind(self.KEYS.TAB_PAGES, action=self.step_tab)]
        listed = self.listed()
        if listed.kind == PATTERN:
            result += self.pattern_keys(listed.name)
        elif listed.kind == NEW_PATTERN:
            result.append(self.bind(self.KEYS.NEW_PATTERN, action=self.add))
        else:
            result.append(self.bind(self.KEYS.NEW_GROUP, action=self.new_group))
        return [*result, self.bind(self.KEYS.TO_TABS, action=self.go_to_tabs), self.bind(self.KEYS.TAB_PAGES, action=self.step_tab)]

    def tab_row_keys(self):
        """Return the keys of the row of tabs: those that choose a tab, Tab into the list, and the chosen tab's own: on a group's,
        those that add to, rename, copy and ungroup the group; on + New, the one that makes a group."""
        result = [self.bind(self.KEYS.ALONG_TABS, action=self.step_tab), self.bind(self.KEYS.INTO_TAB, action=self.go_into_tab)]
        tab = self.chosen()
        if tab.kind == NEW_TAB:
            return [*result, self.bind(self.KEYS.NEW_GROUP, action=self.new_group)]
        if tab.kind == UNGROUPED_TAB:
            return result
        return [
            *result, self.bind(self.KEYS.ADD, action=self.add), self.bind(self.KEYS.RENAME, action=self.rename_group),
            self.bind(self.KEYS.COPY, action=self.copy_group), self.bind(self.KEYS.UNGROUP, action=self.ungroup),
        ]

    def pattern_keys(self, name):
        result = [self.bind(self.KEYS.EDIT, action=self.open_item), self.bind(self.KEYS.GROUP, action=self.choose_group)]
        if self.document().pattern_group(name) is not UNGROUPED:
            result.append(self.bind(self.KEYS.ADD, action=self.add))
        result += [self.bind(self.KEYS.RENAME, action=self.rename), self.bind(self.KEYS.COPY, action=self.copy), self.bind(self.KEYS.DELETE, action=self.delete)]
        return [*result, *pattern_listen_keys(page=self, pattern=name)]

    # A pattern.

    def open_item(self):
        self.open_editor(section=Section.PATTERNS, name=self.listed().name)

    def add(self):
        """Ask what kind of pattern to make, a drum pattern or one written for a scale of so many notes, then its name, make it in the cursor's group and open it."""
        self.ask(dialog=NewPatternDialog(), then=self.add_of_kind)

    def add_of_kind(self, kind):
        group = self.group_under_cursor()
        patterns = self.names()

        def named(text):
            text = text.strip()
            if not text or is_taken(name=text, taken=patterns):
                self.refuse(errors.ERR_NAME_EMPTY_OR_IN_USE)
                return
            self.document().add_pattern(name=text, group=group, drum=kind.drum, scale_length=kind.scale_length)
            self.new_groups = [made for made in self.new_groups if made != group]
            self.put_cursor_on(text)
            self.open_editor(section=Section.PATTERNS, name=text)
        self.ask_text(title=messages.MSG_NEW_PATTERN_PROMPT, value=self.new_name(names_text.MSG_NEW_PATTERN_WORD), then=named, is_name=True)

    def rename(self):
        name = self.listed().name

        def renamed(new):
            self.document().rename_named(section=self.LISTED_SECTION, old=name, new=new)
            self.put_cursor_on(new)
        self.ask_name(title=self.rename_title(), value=name, taken=self.names(), then=renamed)

    def copy(self):
        """Copy the selected pattern into its own group, say what the copy is called and put the cursor on it."""
        new = self.document().copy_named(section=self.LISTED_SECTION, name=self.listed().name)
        self.say(messages.MSG_COPIED_TO.format(name=new))
        self.put_cursor_on(new)

    def delete(self):
        name = self.listed().name
        self.delete_after_checks(what=self.what_is(name), uses=self.uses(name), delete=lambda: self.document().delete_named(section=self.LISTED_SECTION, name=name))

    def choose_group(self):
        """Move the selected pattern to another group, picked from the groups, or to a new one, the picker's last entry."""
        name = self.listed().name
        groups = self.groups()
        current = self.document().pattern_group(name)

        def moved(group):
            self.document().change_pattern(self.document().pattern(name).set_group, group)
            self.new_groups = [made for made in self.new_groups if made != group]
            self.put_cursor_on(name)

        def chosen(place):
            if place < len(groups):
                moved(groups[place])
            else:
                self.ask_new_group(then=moved)
        self.ask(dialog=ChoiceDialog(title=messages.MSG_GROUP_TITLE, options=[*groups, labels.MSG_NEW_GROUP_BUTTON], current=groups.index(current) if current in groups else 0), then=chosen)

    # A group.

    def ask_new_group(self, *, then):
        """Ask for a new group's name, one no group has, and hand it on."""
        groups = self.groups()

        def named(text):
            text = text.strip()
            if not text or is_taken(name=text, taken=groups):
                self.refuse(errors.ERR_NAME_EMPTY_OR_IN_USE)
                return
            then(text)
        self.ask_text(title=messages.MSG_NEW_GROUP_PROMPT, value=new_name(word=names_text.MSG_NEW_GROUP_WORD, taken=groups), then=named, is_name=True)

    def new_group(self):
        """Make a group, whose tab shows with only its + (New) row until a pattern is made in it."""
        def made(group):
            self.new_groups.append(group)
            self.choose(PatternTab(GROUP_TAB, group))
            self.on_tabs = False
            self.put_cursor_on_row(Listed(NEW_PATTERN, group))
        self.ask_new_group(then=made)

    def rename_group(self):
        group = self.chosen().group

        def renamed(new):
            if group in self.new_groups:
                self.new_groups = [new if made == group else made for made in self.new_groups]
            self.document().rename_pattern_group(old=group, new=new)
            self.choose(PatternTab(GROUP_TAB, new))
        self.ask_name(title=messages.MSG_RENAME_GROUP_PROMPT, value=group, taken=self.groups(), then=renamed)

    def ungroup(self):
        """Take every pattern out of the group after asking, deleting none; a group made here that holds none is simply gone."""
        group = self.chosen().group

        def confirmed(_):
            self.new_groups = [made for made in self.new_groups if made != group]
            self.document().change_set(self.document().get_setlist().ungroup_patterns, group)
            self.choose(PatternTab(UNGROUPED_TAB))
        self.ask(dialog=ConfirmDialog(title=messages.MSG_UNGROUP_TITLE, messages=[messages.MSG_UNGROUP_QUESTION.format(name=group)]), then=confirmed)

    def copy_group(self):
        """Copy the whole group under a new name, asked for in a confirmation that starts from the group's name counted up."""
        group = self.chosen().group
        groups = self.groups()

        def named(text):
            text = text.strip()
            if not text or is_taken(name=text, taken=groups):
                self.refuse(errors.ERR_NAME_EMPTY_OR_IN_USE)
                return
            try:
                copies = self.document().change_set(self.document().get_setlist().copy_pattern_group, group=group, new=text)
            except ValueError as problem:
                self.refuse(str(problem))
                return
            if not copies:
                self.new_groups.append(text)
            self.say(messages.MSG_GROUP_COPIED.format(name=text))
            self.choose(PatternTab(GROUP_TAB, text))
        self.ask_text(title=messages.MSG_COPY_GROUP_TITLE, value=copy_name(name=group, taken=groups), then=named, is_name=True, label=labels.MSG_NEW_GROUP_NAME_LABEL)

    # Searching, which looks at the patterns alone, inside every group.

    def row_texts(self):
        return [what.name if what.kind == PATTERN else drawing.NOTHING for what, _ in self.remembered_rows()]

    def matches(self):
        rows = self.remembered_rows()
        if not self.searching:
            return list(range(len(rows)))
        typed = self.search.get_typed().lower()
        return [place for place, (what, _) in enumerate(rows) if what.kind == PATTERN and typed in what.name.lower()]

    def start_search(self):
        self.on_tabs = False
        self.before_search = self.listed()
        self.searching = True
        self.search.clear()
        self.put_cursor_on_row(self.before_search)
        self.settle()

    def keep(self):
        """Keep the cursor on the pattern the search found, choosing its group's tab."""
        found = self.listed()
        self.searching = False
        if found.kind == PATTERN:
            self.put_cursor_on(found.name)
        else:
            self.put_cursor_on_row(found)

    def stop_search(self):
        self.searching = False
        self.put_cursor_on_row(self.before_search)
