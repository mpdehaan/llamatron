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
"""The Restart field every generator's editor ends its own settings with: when the generator starts over, every clip, on new scene or whole song."""

from llamatron.composition.file_format import GENERATOR_RESTART, NAMED_GENERATORS, RESTARTS, Restart
from llamatron.strings.labels import MSG_RESTART_LABEL, MSG_RESTART_NAMES
from llamatron.tui.screens.field import ChoiceField

# Each named section's generator kind, the other way round from NAMED_GENERATORS.
KINDS_BY_SECTION = {section: kind for kind, section in NAMED_GENERATORS.items()}


def restart_field(page):
    """Return the Restart field of the generator a page of one named generator shows, by its SECTION and its item."""
    settings = page.document().song().get_generator_settings(kind=KINDS_BY_SECTION[page.SECTION], name=page.item)
    current = settings.get_restart()
    return ChoiceField(
        page=page, label=MSG_RESTART_LABEL, choices=RESTARTS, current=current, names=[MSG_RESTART_NAMES[choice] for choice in RESTARTS],
        shown=MSG_RESTART_NAMES[current],
        set=lambda chosen: page.document().set_generator_setting(section=page.SECTION, name=page.item, setting=GENERATOR_RESTART, value=None if chosen == Restart.EVERY_CLIP else chosen),
    )
