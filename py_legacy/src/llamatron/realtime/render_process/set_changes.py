# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later


"""What changed in the set between two of its data, and the data with the changes made, which is how the set crosses into the render
process (realtime/render_process/playback_process.py): the set's data as its objects keep it (Setlist.kept_data) shares every unchanged part from
one edit to the next, so the changes are found by following the data down to the parts that are not the same objects."""


def changed_items(*, before, after):
    """Return what changed between two of the set's data, as its objects keep it: (changes, removed), each change (path, value)
    and each removal a path, a path being the keys and places that lead to the part from the top. The data is followed down to
    the smallest part that changed: a dictionary key by key and a list of the same length item by item, and a part is compared
    by identity first, since what an unchanged object keeps is the very same object from one edit to the next."""
    found = FoundChanges()
    found.compare(path=(), before=before, after=after)
    return found.changes, found.removed


class FoundChanges:
    """The changes and removals found between two of the set's data, as changed_items gives them."""

    __slots__ = ('changes', 'removed')

    def __init__(self):
        self.changes = []
        self.removed = []

    def compare(self, *, path, before, after):
        """Find what changed in the part at a path."""
        if after is before:
            return
        if isinstance(after, dict) and isinstance(before, dict):
            for key, value in after.items():
                if key in before:
                    self.compare(path=(*path, key), before=before[key], after=value)
                else:
                    self.changes.append(((*path, key), value))
            self.removed += [(*path, key) for key in before if key not in after]
        elif isinstance(after, list) and isinstance(before, list) and len(after) == len(before):
            for place, (old, new) in enumerate(zip(before, after)):
                self.compare(path=(*path, place), before=old, after=new)
        elif after != before:
            self.changes.append((path, after))


def with_changes(*, data, changes, removed):
    """Return the set's data with the changes and removals made, copying each dictionary and list on the way to a change rather
    than changing it, so that a score being built from the data before never sees it change."""
    root = dict(data)
    copied = {id(root)}
    for path, value in changes:
        _parent_of(root=root, path=path, copied=copied)[path[-1]] = value
    for path in removed:
        del _parent_of(root=root, path=path, copied=copied)[path[-1]]
    return root


def _parent_of(*, root, path, copied):
    """Return the dictionary or list that holds the part at a path, each one on the way copied the first time it is reached."""
    node = root
    for key in path[:-1]:
        child = node[key]
        if id(child) not in copied:
            if isinstance(child, dict):
                child = dict(child)
            else:
                child = list(child)
            copied.add(id(child))
            node[key] = child
        node = child
    return node
