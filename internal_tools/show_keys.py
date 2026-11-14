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

"""Print the tracker's key bindings from tui/keybindings.py: every class's, one class's, or every binding that has one key.

Run from the top folder:

    .venv/bin/python internal_tools/show_keys.py                # every page, dialog and component, with its bindings in the F1 dialog's order
    .venv/bin/python internal_tools/show_keys.py PatternEditor  # the bindings of one class
    .venv/bin/python internal_tools/show_keys.py --key s        # every binding that has a key, to see what a key is taken for before giving it a new meaning

`internal_tools/keys.sh` runs the first, and `internal_tools/keys.sh PatternEditor` and `internal_tools/keys.sh --key s` the others.
Each line is a binding's name in its class, the keys it has, what the legend calls them, what
they do, and `F1 only` where the legend leaves the binding to the F1 dialog. A class that lists
no bindings of its own has the ones of the class it builds on.
"""

import inspect
import sys

from llamatron.tui import keybindings
from llamatron.tui.key_table import every_key, place_of
from llamatron.tui.keys import Steps

KEY_FLAG = '--key'
SEPARATOR = ' '
# How a class is headed and how each of its bindings is shown under it.
HEADING = '{name}{base}'
BUILDS_ON = ' ({bases})'
BASE_SEPARATOR = ', '
ROW = '  {constant:18s} {keys:28s} {shown:14s} {what:20s} {note}'
# How one binding is shown when the bindings that have a key are listed, across the classes.
KEY_ROW = '{owner:34s} {keys:28s} {shown:14s} {what:20s} {note}'
OWNER = '{kind}.{constant}'
F1_ONLY = 'F1 only'
EVERYWHERE = 'everywhere'
NOTHING = ''
# How many keys of a binding are shown before the rest are counted, since a search binds every letter.
KEYS_SHOWN = 6
MORE_KEYS = ' +{count}'
MSG_NO_SUCH_CLASS = 'no class called {name} in tui/keybindings.py: expected one of: {names}'
MSG_NOTHING_HAS_KEY = 'no binding has the key {key}'
# How many things a binding holds: its keys, its name on screen and what it does.
BINDING_PARTS = 3
EVERYWHERE_LIST = 'EVERYWHERE'


def binding_classes():
    """Return every class of tui/keybindings.py by name, in the order the module defines them."""
    found = [(name, kind) for name, kind in inspect.getmembers(keybindings, inspect.isclass) if kind.__module__ == keybindings.__name__]
    return dict(sorted(found, key=first_line))


def first_line(named):
    _, kind = named
    return inspect.getsourcelines(kind)[1]


def is_binding(value):
    return isinstance(value, tuple) and not isinstance(value, Steps) and len(value) == BINDING_PARTS


def name_of(*, kind, binding):
    """Return the name a class of bindings gives one of its bindings, its own or an inherited one."""
    return next(name for name, value in inspect.getmembers(kind) if name.isupper() and value is binding)


def keys_shown(binding):
    keys = every_key(binding)
    shown = SEPARATOR.join(keys[:KEYS_SHOWN])
    return shown + MORE_KEYS.format(count=len(keys) - KEYS_SHOWN) if len(keys) > KEYS_SHOWN else shown


def note_for(*, kind, binding):
    """Return where a binding is listed, when that isn't the legend: every page's keys are in the F1 dialog alone, and so is a binding the legend leaves out."""
    if place_of(binding=binding, bindings=getattr(kind, EVERYWHERE_LIST, [])) is not None:
        return EVERYWHERE
    return NOTHING if place_of(binding=binding, bindings=kind.IN_LEGEND) is not None else F1_ONLY


def bindings_of(kind):
    """Return a class's bindings in the order they're listed: the keys that work everywhere, then the F1 dialog's order, then any the legend alone shows."""
    listed = [*getattr(kind, EVERYWHERE_LIST, []), *kind.IN_HELP]
    return listed + [binding for binding in kind.IN_LEGEND if place_of(binding=binding, bindings=listed) is None]


def heading(*, name, kind):
    bases = [base.__name__ for base in kind.__bases__ if base is not object]
    return HEADING.format(name=name, base=BUILDS_ON.format(bases=BASE_SEPARATOR.join(bases)) if bases else NOTHING)


def show_class(*, name, kind):
    print(heading(name=name, kind=kind))
    for binding in bindings_of(kind):
        _, shown, what = binding
        print(ROW.format(constant=name_of(kind=kind, binding=binding), keys=keys_shown(binding), shown=shown, what=what, note=note_for(kind=kind, binding=binding)).rstrip())
    print()


def show_key(key):
    """Print every binding a class defines itself that has a key, so that each is listed once."""
    found = False
    for name, kind in binding_classes().items():
        for constant, binding in vars(kind).items():
            if constant.isupper() and is_binding(binding) and key in every_key(binding):
                _, shown, what = binding
                print(KEY_ROW.format(owner=OWNER.format(kind=name, constant=constant), keys=keys_shown(binding), shown=shown, what=what, note=note_for(kind=kind, binding=binding)).rstrip())
                found = True
    if not found:
        print(MSG_NOTHING_HAS_KEY.format(key=key))


def main(arguments):
    classes = binding_classes()
    if arguments[:1] == [KEY_FLAG] and len(arguments) > 1:
        show_key(arguments[1].lower())
        return 0
    for name in arguments:
        if name not in classes:
            print(MSG_NO_SUCH_CLASS.format(name=name, names=BASE_SEPARATOR.join(classes)))
            return 1
    for name in arguments or classes:
        show_class(name=name, kind=classes[name])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
