# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Patterns page as a presenter: every pattern of the set in a tab of its group, a tab per group sorted by name, then
Ungrouped while a pattern is in no group, then + New; each group's patterns sorted by name, with + (New) under them."""

from typing import NamedTuple

from llamatron.interface.forms.table import Align, ListColumn
from llamatron.interface.forms.text import clock
from llamatron.interface.pages.places import ItemPlace
from llamatron.model.objects.naming import name_order
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import labels, marks

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
NO_TEXT = ''


class Listed(NamedTuple):
    """What a row of the Patterns page is: its kind, and the name of its pattern or of its group."""

    kind: str
    name: object


class PatternTab(NamedTuple):
    """One tab of the Patterns page: its kind, and the group it shows on a group's tab."""

    kind: str
    group: object = None


class PatternListPresenter:
    """What the Patterns page lists: its tabs and their rows, from the set and the groups made on the page that hold no
    pattern yet (new_groups), which the page keeps for the session."""

    COLUMNS = (
        ListColumn(heading=labels.Column.SELECT_PATTERN, width=None, align=Align.LEFT), ListColumn(heading=labels.Column.TYPE, width=5, align=Align.LEFT),
        ListColumn(heading=labels.Column.STEPS, width=5, align=Align.RIGHT), ListColumn(heading=labels.Column.TIME, width=6, align=Align.RIGHT),
        ListColumn(heading=labels.Column.USED, width=4, align=Align.RIGHT),
    )

    __slots__ = ('_document', '_new_groups')

    def __init__(self, *, document, new_groups):
        self._document = document
        self._new_groups = new_groups

    def groups(self):
        """Return every group's name, sorted: the ones patterns are in, and the ones made on the page that hold none yet."""
        held = self._document.get_setlist().get_pattern_groups()
        return sorted([*held, *(group for group in self._new_groups if group not in held)], key=name_order)

    def tabs(self):
        """Return the page's tabs in order: each group's, sorted, then Ungrouped while a pattern is in no group, then + New."""
        tabs = [PatternTab(GROUP_TAB, group) for group in self.groups()]
        if self._document.get_setlist().patterns_in_group(UNGROUPED):
            tabs.append(PatternTab(UNGROUPED_TAB))
        return [*tabs, PatternTab(NEW_TAB)]

    @staticmethod
    def tab_label(tab):
        """Return the name a tab shows: its group's, Ungrouped, or + New."""
        if tab.kind == GROUP_TAB:
            return tab.group
        if tab.kind == UNGROUPED_TAB:
            return labels.MSG_UNGROUPED
        return labels.MSG_NEW_GROUP_TAB

    def rows(self, *, tab, searching):
        """Return a tab's rows, or, while a search looks inside every group, every pattern, group by group."""
        if searching:
            rows = []
            for each in self.tabs():
                rows += self.pattern_rows(each.group)
            return rows
        if tab.kind == NEW_TAB:
            return [(Listed(NEW_GROUP, None), self.one_cell(labels.MSG_NEW_GROUP_BUTTON))]
        rows = self.pattern_rows(tab.group)
        if tab.kind == GROUP_TAB:
            rows.append((Listed(NEW_PATTERN, tab.group), self.one_cell(marks.MSG_NEW_ROW)))
        return rows

    def pattern_rows(self, group):
        """Return the rows of a group's patterns, sorted by name: each pattern's name, kind, steps, time and uses."""
        document = self._document
        setlist = document.get_setlist()
        rows = []
        for name in setlist.patterns_in_group(group):
            pattern = setlist.get_pattern(name)
            kind = labels.MSG_DRUM_KIND if pattern.is_drum() else labels.MSG_NOTES_KIND
            uses = document.uses(section=Section.PATTERNS, name=name)
            rows.append((Listed(PATTERN, name), [name, kind, pattern.get_steps(), clock(document.lengths().pattern_seconds(name)), len(uses)]))
        return rows

    def one_cell(self, text):
        """Return the cells of a row that holds only its first."""
        return [text, *[NO_TEXT] * (len(self.COLUMNS) - 1)]

    @staticmethod
    def is_button(listed):
        """Return whether a row is a button, + (New) or the one that makes a group, which the page draws in its theme colour."""
        return listed.kind in (NEW_PATTERN, NEW_GROUP)

    @staticmethod
    def place_of(name):
        """Return the place of a pattern's own page, the pattern editor."""
        return ItemPlace(section=Section.PATTERNS, name=name)

    def tab_of_pattern(self, name):
        """Return the tab a pattern is listed in: its group's, or Ungrouped."""
        group = self._document.pattern_group(name)
        if group is UNGROUPED:
            return PatternTab(UNGROUPED_TAB)
        return PatternTab(GROUP_TAB, group)
