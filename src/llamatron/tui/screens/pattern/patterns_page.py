"""The Patterns page, which lists the patterns by group."""

from typing import NamedTuple

from llamatron.composition import limits
from llamatron.composition.file_format import Section
from llamatron.composition.naming import copy_name, is_taken, name_order, new_name
from llamatron.strings import errors, help as help_text, labels, legends, marks, messages, names as names_text
from llamatron.tui import drawing, key_table, keybindings
from llamatron.tui.cursor import Cursor
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.new_pattern_dialog import NewPatternDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.drawing import Align, Style
from llamatron.tui.screens.pattern.pattern_editor import PatternEditor
from llamatron.tui.screens.shared.listening import pattern_listen_keys
from llamatron.tui.screens.shared.named_list_page import NamedListPage
from llamatron.tui.text import clock
from llamatron.tui.themes import text_style, theme_of

# The kinds of row the page lists: a pattern, a group's heading, the button that makes a pattern in a group, and the button that makes a group.
PATTERN = 'pattern'
HEADING = 'heading'
NEW_PATTERN = 'new pattern'
NEW_GROUP = 'new group'
# How far a group's rows stand in from its heading.
INDENT = '    '
# The group of the patterns in no group, which an older file's are.
UNGROUPED = None


class Listed(NamedTuple):
    """What a row of the Patterns page is: its kind, and the name of its pattern or of its group."""

    kind: str
    name: object


class PatternsPage(NamedListPage):
    """Every pattern of the set under its group's heading, the groups sorted and the patterns sorted in each, always, so that
    nothing here moves or sorts. A heading opens and closes its group, each open group ends with a button that makes a pattern
    in it, and the page ends with a button that makes a group. The patterns in no group, an older file's, come last under
    Ungrouped, to which nothing can be added: a group is made before a pattern is."""

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
    NAME_COLUMN_WIDTH = limits.MAX_NAME_LENGTH + len(INDENT)

    def __init__(self, holder):
        super().__init__(holder)
        # The groups made here that hold no pattern yet. A group is only the text its patterns hold, so one with none is the page's own until a pattern is made in it.
        self.new_groups = []
        # What the cursor was on when a search began, which ESC goes back to.
        self.before_search = None
        # The page opens with the cursor on its first pattern, where one shows, so that ENTER edits at once, as on every list.
        self.cursor = Cursor(place=self.first_pattern_place())

    # The rows.

    def can_add(self):
        """Return that the page has no + row of its own: its buttons are rows it lists."""
        return False

    def groups(self):
        """Return every group's name, sorted: the ones patterns are in, and the ones made here that hold none yet."""
        held = self.document().setlist().get_pattern_groups()
        return sorted([*held, *(group for group in self.new_groups if group not in held)], key=name_order)

    def is_closed(self, group):
        return self.document().setlist().is_pattern_group_closed(group)

    def rows_depend_on(self):
        """Return what the rows depend on besides the set: which groups are closed, the groups made here, and a search, which looks inside every group."""
        return (tuple(self.is_closed(group) for group in [*self.groups(), UNGROUPED]), tuple(self.new_groups), self.searching)

    def rows(self):
        rows = []
        for group in self.groups():
            rows += self.group_rows(group)
        if self.document().setlist().patterns_in_group(UNGROUPED):
            rows += self.group_rows(UNGROUPED)
        rows.append((Listed(NEW_GROUP, None), self.one_cell(labels.MSG_NEW_GROUP_BUTTON)))
        return rows

    def group_rows(self, group):
        """Return a group's rows: its heading, and while it is open, or a search looks inside it, its patterns and its button."""
        document = self.document()
        names = document.setlist().patterns_in_group(group)
        closed = self.is_closed(group) and not self.searching
        heading = labels.MSG_GROUP_HEADING.format(mark=marks.MSG_SECTION_CLOSED_MARK if closed else marks.MSG_SECTION_OPEN_MARK, name=labels.MSG_UNGROUPED if group is UNGROUPED else group, count=len(names))
        rows = [(Listed(HEADING, group), self.one_cell(heading))]
        if closed:
            return rows
        rows += [(Listed(PATTERN, name), self.row_of(name=name, pattern=document.song().get_pattern(name), document=document)) for name in names]
        if group is not UNGROUPED:
            rows.append((Listed(NEW_PATTERN, group), self.one_cell(INDENT + labels.MSG_NEW_PATTERN_BUTTON)))
        return rows

    def one_cell(self, text):
        """Return the cells of a row that holds only its first."""
        return [text, *[drawing.NOTHING] * (len(self.columns) - 1)]

    def row_of(self, *, name, pattern, document):
        kind = labels.MSG_DRUM_KIND if pattern.is_drum() else labels.MSG_NOTES_KIND
        return [INDENT + name, kind, pattern.get_steps(), clock(document.lengths().pattern_seconds(name)), len(self.uses(name))]

    def row_style(self, what):
        """Return a heading in bold and a button in the page's theme colour, so that neither is taken for the other."""
        if what.kind == HEADING:
            return Style.BOLD
        if what.kind in (NEW_PATTERN, NEW_GROUP):
            return text_style(theme_of(Section.PATTERNS))
        return Style.PLAIN

    def first_pattern_place(self):
        """Return the place of the first pattern showing, or the top row when none shows."""
        return next((place for place, (what, _) in enumerate(self.remembered_rows()) if what.kind == PATTERN), 0)

    def current(self):
        """Return the name of the pattern the cursor is on, or nothing on a heading or a button, as a list answers on its + row."""
        listed = self.listed()
        return listed.name if listed.kind == PATTERN else None

    def row_names(self):
        """Return each row's pattern's name, in the rows' order, with nothing for a heading or a button."""
        return [what.name if what.kind == PATTERN else None for what, _ in self.remembered_rows()]

    def listed(self):
        """Return what the cursor is on, which is never nothing, since the page always ends with its button."""
        self.clamp()
        return self.remembered_rows()[self.cursor.get_place()][0]

    def remember_place(self):
        """Return what the cursor is on, a heading and a button included, for a redraw to find again."""
        return self.listed()

    def group_under_cursor(self):
        """Return the group of the cursor's row: a pattern's own, or the heading's or button's."""
        listed = self.listed()
        return self.document().pattern_group(listed.name) if listed.kind == PATTERN else listed.name

    def put_cursor_on_row(self, listed):
        rows = [what for what, _ in self.remembered_rows()]
        if listed in rows:
            self.cursor.set_place(rows.index(listed))
        self.clamp()

    def put_cursor_on(self, name):
        """Put the cursor on a pattern's row, opening its group if the group is closed."""
        self.document().show_pattern_group(group=self.document().pattern_group(name), closed=False)
        self.put_cursor_on_row(Listed(PATTERN, name))

    # The keys, by what the cursor is on.

    def keys(self):
        listed = self.listed()
        result = [self.bind(self.KEYS.BACK, action=self.go_back), *self.move_keys()]
        if listed.kind == PATTERN:
            result += self.pattern_keys(listed.name)
        elif listed.kind == HEADING:
            result += self.heading_keys(listed.name)
        elif listed.kind == NEW_PATTERN:
            result.append(self.bind(self.KEYS.NEW_PATTERN, action=self.add))
        else:
            result.append(self.bind(self.KEYS.NEW_GROUP, action=self.new_group))
        return [*result, self.bind(self.KEYS.NEXT_GROUP, action=self.jump_group)]

    def pattern_keys(self, name):
        result = [self.bind(self.KEYS.EDIT, action=self.open_item), self.bind(self.KEYS.GROUP, action=self.choose_group)]
        if self.document().pattern_group(name) is not UNGROUPED:
            result.append(self.bind(self.KEYS.ADD, action=self.add))
        result += [self.bind(self.KEYS.RENAME, action=self.rename), self.bind(self.KEYS.COPY, action=self.copy), self.bind(self.KEYS.DELETE, action=self.delete)]
        return [*result, *pattern_listen_keys(page=self, pattern=name)]

    def heading_keys(self, group):
        result = [self.bind(self.KEYS.TOGGLE_GROUP, action=self.toggle_group)]
        if group is UNGROUPED:
            return result
        return [
            *result, self.bind(self.KEYS.ADD, action=self.add), self.bind(self.KEYS.RENAME, action=self.rename_group),
            self.bind(self.KEYS.COPY, action=self.copy_group), self.bind(self.KEYS.UNGROUP, action=self.ungroup),
        ]

    def jump_group(self, direction):
        """Move the cursor to the next group's heading, or the one before, staying put past the last or the first."""
        places = [place for place, (what, _) in enumerate(self.remembered_rows()) if what.kind == HEADING]
        ahead = [place for place in places if place > self.cursor.get_place()] if direction == key_table.STEP_FORWARD else [place for place in places if place < self.cursor.get_place()]
        if ahead:
            self.cursor.set_place(ahead[0] if direction == key_table.STEP_FORWARD else ahead[-1])

    # A pattern.

    def open_item(self):
        self.show_page(PatternEditor(holder=self.holder, name=self.listed().name))

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
            self.show_page(PatternEditor(holder=self.holder, name=text))
        self.ask(dialog=PromptDialog(title=messages.MSG_NEW_PATTERN_PROMPT, value=new_name(word=names_text.MSG_NEW_PATTERN_WORD, taken=patterns), max_length=limits.MAX_NAME_LENGTH), then=named)

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
            self.document().change(self.document().setlist().get_pattern(name).set_group, group)
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
        self.ask(dialog=PromptDialog(title=messages.MSG_NEW_GROUP_PROMPT, value=new_name(word=names_text.MSG_NEW_GROUP_WORD, taken=groups), max_length=limits.MAX_NAME_LENGTH), then=named)

    def new_group(self):
        """Make a group, which shows open with only its button until a pattern is made in it."""
        def made(group):
            self.new_groups.append(group)
            self.document().show_pattern_group(group=group, closed=False)
            self.put_cursor_on_row(Listed(NEW_PATTERN, group))
        self.ask_new_group(then=made)

    def toggle_group(self):
        group = self.listed().name
        self.document().show_pattern_group(group=group, closed=not self.is_closed(group))

    def rename_group(self):
        group = self.listed().name

        def renamed(new):
            if group in self.new_groups:
                self.new_groups = [new if made == group else made for made in self.new_groups]
            self.document().change(self.document().setlist().rename_pattern_group, old=group, new=new)
            self.put_cursor_on_row(Listed(HEADING, new))
        self.ask_name(title=messages.MSG_RENAME_GROUP_PROMPT, value=group, taken=self.groups(), then=renamed)

    def ungroup(self):
        """Take every pattern out of the group after asking, deleting none; a group made here that holds none is simply gone."""
        group = self.listed().name

        def confirmed(_):
            self.new_groups = [made for made in self.new_groups if made != group]
            self.document().change(self.document().setlist().ungroup_patterns, group)
            self.put_cursor_on_row(Listed(HEADING, UNGROUPED))
        self.ask(dialog=ConfirmDialog(title=messages.MSG_UNGROUP_TITLE, messages=[messages.MSG_UNGROUP_QUESTION.format(name=group)]), then=confirmed)

    def copy_group(self):
        """Copy the whole group under a new name, asked for in a confirmation that starts from the group's name counted up."""
        group = self.listed().name
        groups = self.groups()

        def named(text):
            text = text.strip()
            if not text or is_taken(name=text, taken=groups):
                self.refuse(errors.ERR_NAME_EMPTY_OR_IN_USE)
                return
            try:
                copies = self.document().change(self.document().setlist().copy_pattern_group, group=group, new=text)
            except ValueError as problem:
                self.refuse(str(problem))
                return
            if not copies:
                self.new_groups.append(text)
            self.document().show_pattern_group(group=text, closed=False)
            self.say(messages.MSG_GROUP_COPIED.format(name=text))
            self.put_cursor_on_row(Listed(HEADING, text))
        self.ask(dialog=PromptDialog(title=messages.MSG_COPY_GROUP_TITLE, label=labels.MSG_NEW_GROUP_NAME_LABEL, value=copy_name(name=group, taken=groups), max_length=limits.MAX_NAME_LENGTH), then=named)

    # Searching, which looks at the patterns alone, inside every group, closed or open.

    def row_texts(self):
        return [what.name if what.kind == PATTERN else drawing.NOTHING for what, _ in self.remembered_rows()]

    def matches(self):
        rows = self.remembered_rows()
        if not self.searching:
            return list(range(len(rows)))
        typed = self.search.get_typed().lower()
        return [place for place, (what, _) in enumerate(rows) if what.kind == PATTERN and typed in what.name.lower()]

    def start_search(self):
        self.before_search = self.listed()
        self.searching = True
        self.search.clear()
        self.put_cursor_on_row(self.before_search)
        self.settle()

    def keep(self):
        """Keep the cursor on the pattern the search found, opening its group."""
        found = self.listed()
        self.searching = False
        if found.kind == PATTERN:
            self.put_cursor_on(found.name)
        else:
            self.put_cursor_on_row(found)

    def stop_search(self):
        self.searching = False
        self.put_cursor_on_row(self.before_search)
