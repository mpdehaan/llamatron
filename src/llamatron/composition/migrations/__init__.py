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

"""Migrations: each moves a set file's data from the layout before one breaking change to the layout after it.

A file records the version that saved it. Reading a file runs, in order, every migration whose change came after that version
(running.py), so that each one meets the layout the one before it left, and the reader only ever sees the layout written now.
A change that only adds a setting needs no migration, since every setting has a default, and a feature taken away leaves
nothing to move: a removed setting is never migrated, since the reader passes over every name it does not know and nothing
writes such a name again. A migration is never changed once released: a later change of layout is a migration of its own, and the list
is kept until a major version starts afresh.

Every piece of code that only runs on an older layout lives here and nowhere else, and nothing outside this package imports
anything of it but migrated() and Conversion. Each migration is a module of its own, short, made of the helpers in
helpers.py, and knows nothing of the objects or the reader.
"""

from llamatron.composition.migrations.running import Conversion, migrated

__all__ = ['Conversion', 'migrated']
