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
