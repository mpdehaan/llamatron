# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Holding Python's garbage collector back from what the tracker keeps for good.

The tracker keeps about a hundred thousand objects for as long as it runs: Textual's widgets, the imports, the set it edits.
Python's full collection walks all of them, about 12 to 18 ms on the screen's thread every second or so while a song plays,
which a key press or a redraw then waits for. Freezing them, as the Realtime Sender Process does with its own, leaves the
collector only the objects made since. A set opened in place of another is let go first, so that the old set is collected
rather than kept frozen."""

import gc


def hold_long_lived():
    """Let go of what was frozen before, collect what is no longer used, and freeze everything left, so that no collection
    walks it again. Called once the tracker has opened and whenever it holds another set."""
    gc.unfreeze()
    gc.collect()
    gc.freeze()
