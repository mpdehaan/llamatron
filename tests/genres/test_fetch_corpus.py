# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The corpus fetcher of internal_tools/analysis_and_generation/, one quick check of its main path: a member climbing out or absolute is refused. A research tool fails loudly when it is run, so one check is enough (.claude/TESTING.md)."""

import os
import sys
import unittest

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, 'internal_tools', 'analysis_and_generation')
sys.path.insert(0, TOOLS)
import fetch_corpus  # noqa: E402

TOP = 'essen-folksong-collection-main'
CLIMBING = TOP + '/../../etc/passwd.krn'
ABSOLUTE = '/etc/passwd.krn'
README = TOP + '/README.txt'


class TestFetchCorpus(unittest.TestCase):

    def test_a_member_climbing_out_or_absolute_is_refused(self):
        self.assertIsNone(fetch_corpus.safe_member_path(CLIMBING))
        self.assertIsNone(fetch_corpus.safe_member_path(ABSOLUTE))
        self.assertIsNone(fetch_corpus.safe_member_path(TOP))

if __name__ == '__main__':
    unittest.main()
