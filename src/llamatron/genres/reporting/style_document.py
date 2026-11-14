# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""A style as a document: the traits a subject sets and each trait's fields, as plain data that can be written as JSON, read by
a person or a tool, and in time handed to a generator. It holds nothing of a song's notes, patterns or sections: it says what kind
of music, not which music. A trait the subject does not set, and a field with no value, are left out."""

import dataclasses
import enum

from llamatron.genres.measures.traits import TRAITS


def plain(value):
    """Return a trait or one of its values as plain data: dictionaries, lists, numbers and text."""
    if dataclasses.is_dataclass(value):
        fields = {field.name: plain(getattr(value, field.name)) for field in dataclasses.fields(value)}
        return {name: held for name, held in fields.items() if is_set(held)}
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, dict):
        return {str(name): plain(held) for name, held in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [plain(each) for each in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def is_set(value):
    """Return whether a field holds a value worth writing: not none, and not an empty list or dictionary."""
    return value is not None and value != [] and value != {}


def style_document(subject):
    """Return a subject's style as a document, by the trait, in the traits' order: every trait the subject sets with its fields."""
    document = {}
    for trait in TRAITS:
        held = subject.trait(trait)
        if held is not None:
            fields = plain(held)
            if fields:
                document[trait] = fields
    return document
