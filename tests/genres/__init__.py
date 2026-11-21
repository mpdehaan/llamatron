# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The tests of the research tools in internal_tools/analysis_and_generation/: the measuring of a song's style and the corpus
layer. The tools import one another by their own folder, so the folder goes on the path before any test module is read."""

import os
import sys

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, 'internal_tools', 'analysis_and_generation')
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
