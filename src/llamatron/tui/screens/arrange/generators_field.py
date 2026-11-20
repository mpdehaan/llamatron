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
"""The Chains field, which the clip page, the Scene page and the track editor share: the chains something runs, and the list page that edits them."""

from llamatron.strings import labels, legends, marks
from llamatron.tui.screens.generators.generator_list_page import GeneratorListPage
from llamatron.tui.screens.shared.field import Field
from llamatron.tui.screens.shared.generator_names import listed_generator


def generators_field(*, page, names, store):
    """Return a Generators field: the generators, a chain among them, in the order they run, or none, with Enter opening the list that edits them and Bksp clearing it.

    names() returns the list as it is now and store(names) keeps a new one, so that the clip page,
    the Scene page and the track editor share the field and the page it opens.
    """
    return Field(
        label=labels.MSG_GENERATORS_FIELD_LABEL, value=lambda: marks.MSG_CHAIN_JOIN.join(listed_generator(setlist=page.document().get_setlist(), name=name) for name in names()) or marks.MSG_NONE_SHOWN, adjust=None,
        enter=lambda: page.show_page(GeneratorListPage(holder=page.holder, opener=page, names=names, store=store)), enter_what=legends.What.EDIT,
        clear=lambda: store([]), clear_what=legends.MSG_NO_GENERATOR_WHAT,
    )
