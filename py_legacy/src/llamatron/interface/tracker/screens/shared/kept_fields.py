# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""What a settings page's kept fields say, which the tests hold against the fields built again, so that a page whose key
leaves something out is caught keeping fields that are stale."""

# The values a field may be built holding, rather than asking for as it is drawn, which a kept field could hold stale.
BUILT_HOLDING = ('on', 'number', 'current', 'key_name', 'shown')





def fields_said(fields):
    """Return what a page's kept fields say, to hold against the fields built again while the tests check every remembered
    answer: each field's kind and label and the values it was built holding, and each tab of a tab box with its own fields. A
    field's shown value is never asked, since some ask the page for its fields in turn."""
    said = []
    for field in fields:
        if field.IS_TAB_BOX:
            said.append(tuple((tab.label, tuple(fields_said(tab.every_field()))) for tab in field.tabs))
            continue
        held = tuple(held_value(field=field, name=name) for name in BUILT_HOLDING)
        said.append((type(field).__name__, field.label, held))
    return said


def held_value(*, field, name):
    """Return a value a field holds, as text that compares, or None where it holds none or the name is one of its methods."""
    value = getattr(field, name, None)
    if callable(value):
        return None
    return repr(value)
