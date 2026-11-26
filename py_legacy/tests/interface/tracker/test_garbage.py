# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Holding the garbage collector back from what the tracker keeps: what is held is frozen, and what is let go is still collected."""

import gc
import unittest
import weakref

from llamatron.interface.tracker import garbage
from llamatron.interface.tracker.document import Document


class Kept:
    """Something kept, which refers to itself, as a set's objects and Textual's widgets do, so that only the collector frees it."""

    __slots__ = ('itself', '__weakref__')

    def __init__(self):
        self.itself = self


class TestHoldingLongLivedObjects(unittest.TestCase):

    def tearDown(self):
        gc.unfreeze()

    def test_what_is_kept_is_frozen(self):
        document = Document()
        garbage.hold_long_lived()
        self.assertGreater(gc.get_freeze_count(), 0)
        self.assertIsNotNone(document)

    def test_what_was_let_go_is_collected_when_the_tracker_holds_again(self):
        kept = Kept()
        gone = weakref.ref(kept)
        garbage.hold_long_lived()
        kept = None
        garbage.hold_long_lived()
        self.assertIsNone(gone())
        self.assertIsNone(kept)
