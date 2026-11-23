# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""How a page, dialog or component binds the keys its class in interface/tracker/keybindings.py lists, and how a key press is read as one name."""

from dataclasses import dataclass
from textual import events
from typing import Callable

from llamatron.interface.tracker import keys as keys_values
from llamatron.interface.tracker.keys import Key, Steps

# The keys matched by name rather than by the character they type: a control key's character is an
# unprintable control code, and a function key has none, so neither can be matched any other way.
_NAMED_KEYS = {
    Key.TAB, Key.SHIFT_TAB, Key.ENTER, Key.BACKSPACE, Key.UP, Key.DOWN, Key.LEFT, Key.RIGHT,
    Key.SHIFT_UP, Key.SHIFT_DOWN, Key.SHIFT_LEFT, Key.SHIFT_RIGHT, Key.HOME, Key.END, Key.PAGE_UP, Key.PAGE_DOWN,
    Key.CTRL_C, Key.CTRL_O, Key.CTRL_S, Key.CTRL_T, Key.CTRL_X, Key.CTRL_Y, Key.CTRL_Z, Key.ESCAPE, Key.F1, Key.F2, Key.F3, Key.F4,
}
# The two directions a stepping key passes to its action: back towards the first, the lower or the shorter, and forward.
STEP_BACK = -1
STEP_FORWARD = 1


@dataclass(slots=True, kw_only=True)
class KeyBinding:
    """One binding of a keybindings class, tied to what it does where it's bound: its keys, what they're called on screen, and the action."""

    keys: tuple
    what: str
    action: Callable
    label: str
    # The constant of interface/tracker/keybindings.py this was bound from, which the tests press and the lists order.
    binding: tuple
    # The class of interface/tracker/keybindings.py it was bound for, whose lists order it.
    owner: type
    wants_key: bool = False
    # Whether the legend shows it: a binding left out of its class's IN_LEGEND works and is listed only in the F1 dialog, like Home and End.
    shown: bool = True
    # For keys that step something one way or the other: each key's direction, STEP_BACK or STEP_FORWARD, which the action is called with.
    steps: dict = None

    def shown_label(self):
        return self.label

    def press(self, name):
        """Do what the key does: a stepping key passes its direction, a key that wants its own name passes that, and any other passes nothing."""
        if self.steps is not None:
            self.action(self.steps[name])
        elif self.wants_key:
            self.action(name)
        else:
            self.action()


def keys_of(which):
    """Return one key's name, or several, as a tuple of names: both ways of keys that step, back first."""
    if isinstance(which, Steps):
        return (*which.back, *which.forward)
    return (which,) if isinstance(which, str) else tuple(which)


def every_key(binding):
    """Return every key of a binding of interface/tracker/keybindings.py."""
    return keys_of(binding.keys)


def first_key(binding):
    """Return the first key of a binding of interface/tracker/keybindings.py, which is the one its name on screen stands for."""
    return every_key(binding)[0]


def step_directions(steps):
    """Return each key of a Steps with the direction it steps in."""
    return {**dict.fromkeys(steps.back, STEP_BACK), **dict.fromkeys(steps.forward, STEP_FORWARD)}


def place_of(*, binding, bindings):
    """Return where a binding is in a list of a keybindings class, or None when the list leaves it out.

    A binding is found as the constant it is, not by what it holds, since two bindings of one class
    can hold the same keys and words: on Arrange, [ and ] move a track from its name and from any
    of its clips, and the legend lists each in a place of its own.
    """
    for place, listed in enumerate(bindings):
        if listed is binding:
            return place
    return None


def bound(*, of, binding, action, wants_key=False, keys=None, name=None, what=None):
    """Return a binding of the keybindings class `of`, tied to an action.

    The binding says its keys, its name and what it does. The few places where one of those depends
    on the set say so here: the Degree row binds only the digits of its scale's degrees (keys and
    name), and a settings page says what Enter does on the field under the cursor (what). An
    action bound to a Steps is called with STEP_BACK or STEP_FORWARD, so that no handler asks which
    key was pressed; one bound with wants_key is passed the key's name, which is only for a key
    that types its own character or an arrow that moves a cursor.
    """
    which = binding.keys if keys is None else keys
    steps = step_directions(which) if isinstance(which, Steps) else None
    return KeyBinding(
        keys=keys_of(which), what=binding.what if what is None else what, action=action, label=binding.name if name is None else name,
        binding=binding, owner=of, wants_key=wants_key, shown=place_of(binding=binding, bindings=of.IN_LEGEND) is not None, steps=steps,
    )


class BindsKeys:
    """What a page, a dialog and a component that has keys share: KEYS is the class of interface/tracker/keybindings.py with the same name, which lists the keys and their order."""

    __slots__ = ()

    KEYS = None

    def bind(self, binding, *, action, wants_key=False, keys=None, name=None, what=None):
        """Return one of this class's bindings, tied to what it does here."""
        return bound(of=self.KEYS, binding=binding, action=action, wants_key=wants_key, keys=keys, name=name, what=what)

    def place_in_help(self, item):
        return place_of(binding=item.binding, bindings=self.KEYS.IN_HELP)

    def in_order(self, bindings):
        """Return bindings with this class's own in the order its IN_HELP lists them, which is the order of the legend and of the F1 dialog.

        A page made of parts lists its parts' keys among its own, and each part has put its keys
        in its own class's order already, so those stay where they are: each run of this class's
        own bindings between them is put in order.
        """
        result = []
        run = []
        for item in bindings:
            if item.owner is self.KEYS:
                run.append(item)
            else:
                result += sorted(run, key=self.place_in_help)
                run = []
                result.append(item)
        return result + sorted(run, key=self.place_in_help)




# What Textual calls the three keys whose names here are the marks themselves.
TEXTUAL_NAMES = {Key.PLUS: 'plus', Key.MINUS: 'minus', Key.SLASH: 'slash'}
# The character a terminal sends with each named key, or None for a key that types nothing. A control key's character is its control code, not the key's name.
KEY_CHARACTERS = {
    Key.SPACE: keys_values.SPACE_CHARACTER, Key.PLUS: Key.PLUS, Key.MINUS: Key.MINUS, Key.SLASH: Key.SLASH,
    Key.ENTER: '\r', Key.BACKSPACE: '\x7f', Key.ESCAPE: '\x1b', Key.UP: None, Key.DOWN: None,
    Key.LEFT: None, Key.RIGHT: None, Key.TAB: '\t', Key.SHIFT_TAB: None, Key.F1: None, Key.F2: None, Key.F3: None, Key.F4: None,
    Key.HOME: None, Key.END: None, Key.PAGE_UP: None, Key.PAGE_DOWN: None,
    Key.CTRL_C: '\x03', Key.CTRL_O: '\x0f', Key.CTRL_S: '\x13', Key.CTRL_T: '\x14', Key.CTRL_X: '\x18', Key.CTRL_Y: '\x19', Key.CTRL_Z: '\x1a',
}


def key_event(name):
    """Return the event a terminal sends for a key named as interface/tracker/keys.py names it, which the tests and the tutorial press into a screen directly."""
    if name in KEY_CHARACTERS:
        return events.Key(TEXTUAL_NAMES.get(name, name), KEY_CHARACTERS[name])
    return events.Key(name, name)


def pressed_key(event):
    """Return a key press as one name: upper and lower case are the same, and so are both deletes."""
    name = event.key
    if name == Key.DELETE:
        return Key.BACKSPACE
    if name in _NAMED_KEYS:
        return name
    if name == Key.SPACE or event.character == keys_values.SPACE_CHARACTER:
        return Key.SPACE
    if event.character and event.character.isprintable():
        return event.character.lower()
    return None


def quits_at_once(name):
    """Return whether a pressed key quits the tracker at once, whatever has the keys: Ctrl+C, which closes FluidSynth and the MIDI sender as quitting does."""
    return name == Key.CTRL_C
