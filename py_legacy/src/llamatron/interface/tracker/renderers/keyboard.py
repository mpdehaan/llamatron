# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How the tracker draws a keyboard (interface/tracker/components/keyboard.py, which gives its rows as plain pieces of text,
each with the kind of key it is): each kind of key in its style, the Chord dialog's scale outlined and the note picker's not."""

from rich.text import Text

from llamatron.interface.tracker import drawing
from llamatron.interface.tracker.components.keyboard import KeyKind
from llamatron.interface.tracker.drawing import Style

# The style of each kind of key: the Chord dialog's, which outlines the scale's keys, and the note picker's, which has no scale.
CHORD_KEY_STYLES = {KeyKind.CHORD: Style.CHORD_KEY, KeyKind.SCALE: Style.SCALE_KEY, KeyKind.OUTSIDE: Style.DIM}
NOTE_PICKER_KEY_STYLES = {KeyKind.CHORD: Style.CHORD_KEY, KeyKind.OUTSIDE: Style.DIM}


def keyboard_lines(*, rows, styles):
    """Return a keyboard's rows drawn, each piece in the style of its kind of key, or plain."""
    lines = []
    for row in rows:
        line = Text(drawing.NOTHING, no_wrap=True)
        for text, kind in row:
            line.append(text, style=styles.get(kind, Style.PLAIN))
        lines.append(line)
    return lines
