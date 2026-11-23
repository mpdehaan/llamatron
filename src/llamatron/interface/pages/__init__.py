# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The pages as presenters: what each page shows and does, as a form of the forms' nodes (interface/forms/), built from the
set as it is now, with nothing of how it looks or of Textual. The tracker shows a presenter's form on a page of its own, which
hands it the page to ask through and what only the tracker can do, such as opening a set.

- file_global: the File/Global page, the set's own settings.
- visualizer_fields: the fields that choose the visualizer's modes, which the File/Global and Song pages share.
"""
