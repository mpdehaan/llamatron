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

from llamatron.strings.labels import MSG_CHAINS_LABEL
from llamatron.strings.legends import MSG_NO_CHAIN_WHAT, What
from llamatron.strings.marks import MSG_CHAIN_JOIN, MSG_NONE_SHOWN
from llamatron.tui.screens.chain_list_page import ChainListPage
from llamatron.tui.screens.field import Field


def chains_field(*, page, names, store):
    """Return a Chains field: the chains, in the order they run, or none, with Enter opening the list that edits them and Bksp clearing it.

    names() returns the list as it is now and store(names) keeps a new one, so that the clip page,
    the Scene page and the track editor share the field and the page it opens.
    """
    return Field(
        label=MSG_CHAINS_LABEL, value=lambda: MSG_CHAIN_JOIN.join(names()) or MSG_NONE_SHOWN, adjust=None,
        enter=lambda: page.show_page(ChainListPage(holder=page.holder, opener=page, names=names, store=store)), enter_what=What.EDIT,
        clear=lambda: store([]), clear_what=MSG_NO_CHAIN_WHAT,
    )
